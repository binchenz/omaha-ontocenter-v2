"""Process-local, session-scoped ObjectSet store (last-1 per session, LRU-capped)."""
from __future__ import annotations
from collections import OrderedDict
from typing import Any

_MAX_SESSIONS = 512
_store: OrderedDict[int, dict[str, Any]] = OrderedDict()

def set_last_objectset(session_id: int, objectset: dict[str, Any]) -> None:
    _store[session_id] = objectset
    _store.move_to_end(session_id)
    while len(_store) > _MAX_SESSIONS:
        _store.popitem(last=False)

def get_last_objectset(session_id: int) -> dict[str, Any] | None:
    return _store.get(session_id)

def clear_session(session_id: int) -> None:
    _store.pop(session_id, None)
