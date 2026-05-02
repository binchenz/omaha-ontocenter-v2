"""ASCII-safe slug generation for tool names.

OpenAI / DeepSeek tool names must match ^[a-zA-Z0-9_-]+$.
Chinese names are transliterated via pypinyin; falls back to sha1 hash.
"""
import re
import hashlib

_SAFE = re.compile(r"^[a-z0-9_-]+$")


def slugify(name: str) -> str:
    """Convert any name to an ASCII-safe slug suitable for tool names."""
    if not name:
        return "obj"

    text = name.lower().strip()

    if _SAFE.match(text):
        return text

    try:
        from pypinyin import lazy_pinyin

        parts = lazy_pinyin(text)
        candidate = "-".join(p for p in parts if p)
        candidate = re.sub(r"[^a-z0-9-]+", "-", candidate.lower()).strip("-")
        if candidate and _SAFE.match(candidate):
            return candidate
    except ImportError:
        pass

    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"obj_{digest}"
