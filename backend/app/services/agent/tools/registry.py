"""ToolRegistry — central registry for agent tool handlers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

from app.services.agent.providers.base import ToolSpec


# ---------------------------------------------------------------------------
# ToolContext
# ---------------------------------------------------------------------------

@dataclass
class ToolContext:
    db: Any
    omaha_service: Any
    tenant_id: int | None = None
    project_id: int | None = None
    session_id: int | None = None
    ontology_context: dict = field(default_factory=dict)
    uploaded_tables: dict = field(default_factory=dict)
    session_store: Any = None  # app.services.agent.runtime.session_store module


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    success: bool
    data: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "error": self.error}


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Callable] = {}

    # -- registration --------------------------------------------------------

    def register(self, name: str, description: str, parameters: dict) -> Callable:
        """Decorator that registers a tool handler."""
        def decorator(fn: Callable) -> Callable:
            self._specs[name] = ToolSpec(name=name, description=description, parameters=parameters)
            self._handlers[name] = fn
            return fn
        return decorator

    # -- introspection -------------------------------------------------------

    @property
    def tool_names(self) -> list[str]:
        return list(self._specs.keys())

    def has(self, name: str) -> bool:
        return name in self._specs

    def get_specs(self, whitelist: list[str] | None = None) -> list[ToolSpec]:
        if whitelist is None:
            return list(self._specs.values())
        return [self._specs[n] for n in whitelist if n in self._specs]

    def get_openai_schemas(self, whitelist: list[str] | None = None) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self.get_specs(whitelist=whitelist)
        ]

    # -- execution -----------------------------------------------------------

    async def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        if name not in self._handlers:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        try:
            result = self._handlers[name](params, ctx)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Global singleton & convenience decorator
# ---------------------------------------------------------------------------

global_registry = ToolRegistry()


def register_tool(name: str, description: str, parameters: dict) -> Callable:
    """Module-level decorator that registers into global_registry."""
    return global_registry.register(name, description, parameters)
