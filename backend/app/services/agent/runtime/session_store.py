"""Process-local, session-scoped ObjectSet store (last-1 per session)."""
from __future__ import annotations
from typing import Any

_store: dict[int, dict[str, Any]] = {}


def set_last_objectset(session_id: int, objectset: dict[str, Any]) -> None:
    _store[session_id] = objectset


def get_last_objectset(session_id: int) -> dict[str, Any] | None:
    return _store.get(session_id)


def clear_session(session_id: int) -> None:
    _store.pop(session_id, None)
