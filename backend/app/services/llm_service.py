from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import Settings, should_simulate


LLM_MODEL_NAME = "glm-5.1"
LLM_REQUEST_TIMEOUT_SECONDS = 600.0
DEFAULT_LLM_MAX_TOKENS = 4096


class LLMService:
    """OpenAI-compatible JSON completion gateway.

    SIMULATIVE=True keeps this disabled. SIMULATIVE=False requires an API key
    from the OS environment and sends requests to an OpenAI-compatible endpoint.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = LLM_MODEL_NAME
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = (settings.llm_api_key or "").strip()
        self.last_usage: dict[str, int] = {}
        self.last_cost_estimate: float | None = None

    @property
    def enabled(self) -> bool:
        return not should_simulate(self.settings)

    async def complete_json(self, prompt: str, schema: dict[str, Any], max_tokens: int = DEFAULT_LLM_MAX_TOKENS) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM API is disabled because SIMULATIVE=True.")
        if not self.api_key:
            raise RuntimeError("LLM API key is required when SIMULATIVE=False. Set COMPETESCOPE_LLM_API_KEY or LLM_API_KEY.")

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise competitive-intelligence research assistant. "
                        "Return only valid JSON. Do not invent sources or evidence IDs. "
                        "When evidence is insufficient, write unknown or lower-confidence language."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n"
                        "Return a JSON object matching this schema. Do not include Markdown fences.\n"
                        f"{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
            ],
        }
        if self._supports_thinking_toggle():
            payload["thinking"] = {"type": "disabled"}
        data = await self._post_chat_completions(payload)
        content = data["choices"][0]["message"]["content"]
        if not content or not str(content).strip():
            reasoning = data["choices"][0]["message"].get("reasoning_content", "")
            if reasoning:
                raise ValueError("LLM returned reasoning_content but empty content. Disable thinking or increase max_tokens.")
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        if not input_tokens:
            input_tokens = max(1, len(json.dumps(payload.get("messages", []), ensure_ascii=False)) // 4)
        if not output_tokens:
            output_tokens = max(1, len(str(content)) // 4)
        total_tokens = int(usage.get("total_tokens") or 0) or input_tokens + output_tokens
        self.last_usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
        self.last_cost_estimate = 0.0
        return parse_json_object(content)

    async def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        try:
            async with httpx.AsyncClient(timeout=LLM_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:800]
            last_error = RuntimeError(f"{exc.response.status_code} {exc.response.reason_phrase}: {detail}")
        except httpx.TimeoutException as exc:
            last_error = RuntimeError(f"request timed out after {LLM_REQUEST_TIMEOUT_SECONDS:.0f} seconds: {exc.__class__.__name__}")
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
        raise RuntimeError(f"LLM API request failed: {last_error}") from last_error

    def _supports_thinking_toggle(self) -> bool:
        marker = f"{self.model} {self.base_url}".lower()
        return "glm" in marker or "bigmodel" in marker or "z.ai" in marker


def parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object.")
    return value
