from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import Settings, should_simulate


LLM_MODEL_NAME = "glm-5.1"
LLM_REQUEST_TIMEOUT_SECONDS = 30.0


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

    async def complete_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM API is disabled because SIMULATIVE=True.")
        if not self.api_key:
            raise RuntimeError("LLM API key is required when SIMULATIVE=False. Set COMPETESCOPE_LLM_API_KEY or LLM_API_KEY.")

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "max_tokens": 4096,
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
        data = await self._post_chat_completions(payload)
        usage = data.get("usage") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        self.last_cost_estimate = 0.0
        content = data["choices"][0]["message"]["content"]
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
