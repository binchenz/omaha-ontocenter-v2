"""Simple in-process EventBus for agent events."""
from __future__ import annotations

from typing import Callable

from app.services.agent.events.types import Event


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event_type: str, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event: Event) -> None:
        import asyncio
        for handler in self._handlers.get(event.type, []):
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result


event_bus = EventBus()
