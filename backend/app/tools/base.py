from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.core.time import iso_now


class ToolResult(BaseModel):
    status: str = "success"
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    async def call(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run the tool and return a JSON-serializable dict."""

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "called_at": iso_now(),
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    async def call(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self.get(name).call(input_data)

