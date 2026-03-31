from __future__ import annotations

import os
import time
from threading import Lock
from typing import Any

_LOCK = Lock()
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_TTL_SECONDS = int(os.getenv("GITHUB_ANALYSIS_CACHE_TTL_SECONDS", "1800"))
_HITS = 0
_MISSES = 0
_PUTS = 0


def _now() -> float:
    return time.time()


def get_cached_analysis(key: str) -> dict[str, Any] | None:
    global _HITS, _MISSES
    with _LOCK:
        row = _CACHE.get(key)
        if row is None:
            _MISSES += 1
            return None
        created_at, payload = row
        if (_now() - created_at) > _TTL_SECONDS:
            _CACHE.pop(key, None)
            _MISSES += 1
            return None
        _HITS += 1
        return dict(payload)


def put_cached_analysis(key: str, payload: dict[str, Any]) -> None:
    global _PUTS
    with _LOCK:
        _CACHE[key] = (_now(), dict(payload))
        _PUTS += 1


def get_cache_stats() -> dict[str, int]:
    with _LOCK:
        return {
            "size": len(_CACHE),
            "ttlSeconds": _TTL_SECONDS,
            "hits": _HITS,
            "misses": _MISSES,
            "puts": _PUTS,
        }
