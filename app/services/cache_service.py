"""TTL cache with in-memory default and Redis-ready interface."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class InMemoryCacheBackend(CacheBackend):
    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() >= entry.expires_at:
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.time() + max(1, ttl_seconds),
        )

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class RedisCacheBackend(CacheBackend):
    """Redis adapter — activated when REDIS_URL is configured."""

    def __init__(self, url: str) -> None:
        try:
            import redis  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "Redis cache requested but 'redis' package is not installed."
            ) from exc
        self._client = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Any | None:
        raw = self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, default=str)
        self._client.setex(key, max(1, ttl_seconds), payload)

    def delete(self, key: str) -> None:
        self._client.delete(key)


def _create_backend() -> CacheBackend:
    if settings.cache_backend == "redis" and settings.redis_url:
        try:
            return RedisCacheBackend(settings.redis_url)
        except Exception as exc:
            logger.warning("Redis unavailable, falling back to memory cache: %s", exc)
    return InMemoryCacheBackend()


_backend: CacheBackend | None = None


def get_cache_backend() -> CacheBackend:
    global _backend
    if _backend is None:
        _backend = _create_backend()
    return _backend


class TTLCache(Generic[T]):
    """Namespace-scoped TTL cache (brief, summary, etc.)."""

    def __init__(self, namespace: str, default_ttl_seconds: int) -> None:
        self._namespace = namespace
        self._default_ttl = default_ttl_seconds
        self._backend = get_cache_backend()

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def get(self, key: str) -> T | None:
        value = self._backend.get(self._key(key))
        return value  # type: ignore[return-value]

    def set(self, key: str, value: T, *, ttl_seconds: int | None = None) -> None:
        self._backend.set(
            self._key(key),
            value,
            ttl_seconds if ttl_seconds is not None else self._default_ttl,
        )

    def delete(self, key: str) -> None:
        self._backend.delete(self._key(key))


brief_cache: TTLCache[dict[str, Any]] = TTLCache("brief", settings.brief_cache_ttl_seconds)
summary_cache: TTLCache[dict[str, Any]] = TTLCache("summary", settings.llm_cache_ttl_seconds)
