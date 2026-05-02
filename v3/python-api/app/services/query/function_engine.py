import importlib
import json
from datetime import datetime, timedelta, timezone


ALLOWED_HANDLER_PREFIXES = ("app.functions.",)


_cache: dict[str, tuple[datetime, object]] = {}


def _validate_handler(handler: str) -> None:
    """Ensure handler path is within the whitelisted namespace.

    This is a defense in depth: handlers come from user-uploaded YAML, so even
    though they're stored in DB they must not reach arbitrary Python modules.
    """
    if not handler or not any(handler.startswith(p) for p in ALLOWED_HANDLER_PREFIXES):
        raise ValueError(
            f"handler 必须以 {' 或 '.join(ALLOWED_HANDLER_PREFIXES)} 开头，收到: {handler}"
        )


async def call_function(handler: str, caching_ttl: str, **kwargs) -> dict:
    """Dynamically import and call a whitelisted Python function.

    - handler prefix must be in ALLOWED_HANDLER_PREFIXES
    - cache key includes kwargs so different inputs don't collide
    """
    _validate_handler(handler)

    cache_key = _make_cache_key(handler, kwargs)
    if caching_ttl and caching_ttl != "0":
        cached = _cache.get(cache_key)
        if cached:
            ts, val = cached
            ttl_seconds = _parse_ttl(caching_ttl)
            if ttl_seconds and datetime.now(timezone.utc) - ts < timedelta(seconds=ttl_seconds):
                return val

    module_path, func_name = handler.rsplit(".", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    result = func(**kwargs)

    if caching_ttl and caching_ttl != "0":
        _cache[cache_key] = (datetime.now(timezone.utc), result)

    return result


def _make_cache_key(handler: str, kwargs: dict) -> str:
    try:
        kwargs_repr = json.dumps(kwargs, sort_keys=True, default=str)
    except Exception:
        kwargs_repr = repr(sorted(kwargs.items()))
    return f"{handler}::{kwargs_repr}"


def _parse_ttl(ttl: str) -> int | None:
    """Parse TTL string like '1h', '30m', '3600s' to seconds."""
    if ttl.isdigit():
        return int(ttl)
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        return int(ttl[:-1]) * units.get(ttl[-1], 1)
    except (ValueError, IndexError):
        return None
