"""Small in-process cache for rendered subscriptions.

Building a subscription walks every inbound and every host of a user, so a
client that refreshes aggressively used to pay the full rendering cost on each
request. Responses are cached for a short TTL and tagged with a strong ETag so
well-behaved clients can be answered with ``304 Not Modified``.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from config import SUB_CACHE_MAX_ENTRIES, SUB_CACHE_TTL, SUB_ETAG_ENABLED

#: Module level so operators and tests can adjust behaviour at runtime.
TTL: int = SUB_CACHE_TTL
MAX_ENTRIES: int = SUB_CACHE_MAX_ENTRIES
ETAG_ENABLED: bool = SUB_ETAG_ENABLED

_lock = threading.Lock()


@dataclass
class CachedResponse:
    content: str
    etag: str
    expires_at: float

    @property
    def is_fresh(self) -> bool:
        return self.expires_at > time.monotonic()


_store: Dict[str, CachedResponse] = {}


def etag_for(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
    return f'"{digest}"'


def build_key(*parts) -> str:
    return "|".join("" if part is None else str(part) for part in parts)


def get(key: str) -> Optional[CachedResponse]:
    if TTL <= 0:
        return None
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        if not entry.is_fresh:
            _store.pop(key, None)
            return None
        return entry


def store(key: str, content: str) -> CachedResponse:
    """Cache ``content`` and return its entry.

    The entry is returned even when caching is disabled, so callers can always
    rely on it for the ETag header.
    """
    entry = CachedResponse(
        content=content,
        etag=etag_for(content),
        expires_at=time.monotonic() + max(TTL, 0),
    )
    if TTL <= 0:
        return entry

    with _lock:
        if len(_store) >= max(MAX_ENTRIES, 1):
            for stale_key in [k for k, v in _store.items() if not v.is_fresh]:
                _store.pop(stale_key, None)
        if len(_store) >= max(MAX_ENTRIES, 1):
            oldest = min(_store.items(), key=lambda item: item[1].expires_at)[0]
            _store.pop(oldest, None)
        _store[key] = entry
    return entry


def invalidate(prefix: Optional[str] = None) -> int:
    """Drop cached entries, optionally only those matching ``prefix``."""
    with _lock:
        if prefix is None:
            dropped = len(_store)
            _store.clear()
            return dropped
        keys = [key for key in _store if key.startswith(prefix)]
        for key in keys:
            _store.pop(key, None)
        return len(keys)


def size() -> int:
    with _lock:
        return len(_store)


def etag_matches(if_none_match: Optional[str], etag: str) -> bool:
    """Compare an ``If-None-Match`` header against an ETag.

    Handles comma separated lists, the ``W/`` weak prefix and ``*``.
    """
    if not ETAG_ENABLED or not if_none_match or not etag:
        return False

    candidates = [value.strip() for value in if_none_match.split(",")]
    normalized_etag = etag.strip().removeprefix("W/")
    for candidate in candidates:
        if candidate == "*":
            return True
        if candidate.removeprefix("W/") == normalized_etag:
            return True
    return False
