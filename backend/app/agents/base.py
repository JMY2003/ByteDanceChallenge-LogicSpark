from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.ids import new_id
from app.core.time import iso_now, utc_now
from app.db.models import AgentRun
from app.schemas.common import ToolCallLog
from app.services.llm_service import LLMService
from app.tools.base import ToolRegistry


MAX_STORED_STRING_LENGTH = 1600
MAX_STORED_LIST_ITEMS = 12
MAX_STORED_DICT_ITEMS = 50
MAX_STORED_DEPTH = 7
LARGE_TEXT_KEYS = {"content", "text", "html", "markdown", "quote", "summary"}


@dataclass
class AgentLogger:
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def record(self, log: ToolCallLog) -> None:
        self.tool_calls.append(log.model_dump(mode="json"))


@dataclass
class AgentContext:
    project_id: str
    task_id: str
    db: Session
    tools: ToolRegistry
    config: Settings
    llm: LLMService | None = None
    memory: dict[str, Any] = field(default_factory=dict)
    logger: AgentLogger = field(default_factory=AgentLogger)
    run_id: str | None = None
    llm_usage_total: dict[str, int] = field(default_factory=dict)

    async def call_tool(self, tool_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        started_at = iso_now()
        try:
            output = await self.tools.call(tool_name, input_data)
            ended_at = iso_now()
            summary = summarize_tool_output(output)
            self.logger.record(
                ToolCallLog(
                    tool_name=tool_name,
                    input=input_data,
                    output_summary=summary,
                    started_at=started_at,
                    ended_at=ended_at,
                    status="success",
                )
            )
            return output
        except Exception as exc:
            ended_at = iso_now()
            self.logger.record(
                ToolCallLog(
                    tool_name=tool_name,
                    input=input_data,
                    output_summary="",
                    started_at=started_at,
                    ended_at=ended_at,
                    status="failed",
                    error=str(exc),
                )
            )
            raise

    async def complete_json(self, prompt: str, schema: dict[str, Any], max_tokens: int = 4096) -> dict[str, Any]:
        if not self.llm:
            raise RuntimeError("LLM service is not configured.")
        started_at = iso_now()
        try:
            output = await self.llm.complete_json(prompt, schema, max_tokens=max_tokens)
            ended_at = iso_now()
            usage = self.llm.last_usage or {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                self.llm_usage_total[key] = self.llm_usage_total.get(key, 0) + int(usage.get(key) or 0)
            self.logger.record(
                ToolCallLog(
                    tool_name=f"llm:{self.llm.model}",
                    input={
                        "prompt_preview": prompt[:800],
                        "schema_keys": sorted(schema.keys()),
                    },
                    output_summary=summarize_tool_output(output),
                    started_at=started_at,
                    ended_at=ended_at,
                    status="success",
                )
            )
            return output
        except Exception as exc:
            ended_at = iso_now()
            self.logger.record(
                ToolCallLog(
                    tool_name=f"llm:{self.llm.model}",
                    input={"prompt_preview": prompt[:800], "schema_keys": sorted(schema.keys())},
                    output_summary="",
                    started_at=started_at,
                    ended_at=ended_at,
                    status="failed",
                    error=str(exc),
                )
            )
            raise


def summarize_tool_output(output: dict[str, Any]) -> str:
    text = str(output)
    return text[:300] + ("..." if len(text) > 300 else "")


class BaseAgent(ABC):
    name: ClassVar[str] = "BaseAgent"
    description: ClassVar[str] = ""
    output_model: ClassVar[type[BaseModel]]

    @property
    def output_schema(self) -> dict[str, Any]:
        return self.output_model.model_json_schema()

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        run_id = new_id("run")
        context.run_id = run_id
        context.logger = AgentLogger()
        started_at_dt = utc_now()
        started_perf = time.perf_counter()
        run = AgentRun(
            id=run_id,
            project_id=context.project_id,
            task_id=context.task_id,
            agent_name=self.name,
            status="running",
            input=compact_for_storage(input_data),
            output={},
            tool_calls=[],
            started_at=started_at_dt,
        )
        context.db.add(run)
        context.db.commit()

        try:
            raw_output = await self.run(input_data, context)
            validated = self.output_model.model_validate(raw_output)
            output = validated.model_dump(mode="json")
            run.status = "success"
            run.output = output
            run.tool_calls = context.logger.tool_calls
            run.ended_at = utc_now()
            run.duration_ms = int((time.perf_counter() - started_perf) * 1000)
            if context.llm and context.llm_usage_total:
                run.model = context.llm.model
                run.token_usage = context.llm_usage_total
                run.cost_estimate = context.llm.last_cost_estimate
            else:
                run.token_usage = estimate_token_usage(input_data, output)
                run.cost_estimate = 0.0
            context.db.commit()
            return output
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.tool_calls = context.logger.tool_calls
            run.ended_at = utc_now()
            run.duration_ms = int((time.perf_counter() - started_perf) * 1000)
            context.db.commit()
            raise

    @abstractmethod
    async def run(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        """Agent implementation. Must return data matching output_model."""


def estimate_token_usage(input_data: dict[str, Any], output: dict[str, Any]) -> dict[str, int]:
    input_tokens = max(1, len(str(input_data)) // 4)
    output_tokens = max(1, len(str(output)) // 4)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def compact_for_storage(value: Any, depth: int = 0, key: str | None = None) -> Any:
    if depth > MAX_STORED_DEPTH:
        return {"_truncated": "max_depth"}
    if isinstance(value, str):
        limit = 500 if key in LARGE_TEXT_KEYS else MAX_STORED_STRING_LENGTH
        if len(value) <= limit:
            return value
        return f"{value[:limit]}... [truncated {len(value) - limit} chars]"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        compacted = [compact_for_storage(item, depth + 1, key) for item in value[:MAX_STORED_LIST_ITEMS]]
        if len(value) > MAX_STORED_LIST_ITEMS:
            compacted.append({"_omitted_items": len(value) - MAX_STORED_LIST_ITEMS})
        return compacted
    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        items = list(value.items())
        for item_key, item_value in items[:MAX_STORED_DICT_ITEMS]:
            compacted[str(item_key)] = compact_for_storage(item_value, depth + 1, str(item_key))
        if len(items) > MAX_STORED_DICT_ITEMS:
            compacted["_omitted_keys"] = len(items) - MAX_STORED_DICT_ITEMS
        return compacted
    return str(value)
