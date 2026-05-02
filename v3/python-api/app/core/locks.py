"""Per-key async locks to prevent concurrent races on shared resources."""
import asyncio
from collections import defaultdict


class KeyedLock:
    """Async lock keyed by string. Prevents two coroutines from running on the same resource."""

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def for_key(self, key: str) -> asyncio.Lock:
        return self._locks[key]


ingest_lock = KeyedLock()
ontology_update_lock = KeyedLock()
