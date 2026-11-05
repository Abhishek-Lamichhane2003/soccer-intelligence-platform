from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class Cache:
    """Redis-first cache with an in-process fallback and stale-if-error support."""

    def __init__(self) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)
        self._local: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _local_get(self, key: str):
        row = self._local.get(key)
        if not row:
            return None
        expires_at, value = row
        if expires_at < time.monotonic():
            self._local.pop(key, None)
            return None
        return value

    def _local_set(self, key: str, value: Any, ttl: int) -> None:
        self._local[key] = (time.monotonic() + ttl, value)

    async def get_json(self, key: str):
        try:
            raw = await self.client.get(key)
            if raw:
                value = json.loads(raw)
                self._local_set(key, value, 30)
                return value
        except RedisError:
            pass
        return self._local_get(key)

    async def set_json(self, key: str, value, ttl: int = 30):
        self._local_set(key, value, ttl)
        try:
            await self.client.set(key, json.dumps(value), ex=ttl)
        except RedisError:
            pass

    async def remember_json(
        self,
        key: str,
        ttl: int,
        stale_ttl: int,
        loader: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, str]:
        fresh = await self.get_json(key)
        if fresh is not None:
            return fresh, 'cache'

        stale_key = f'{key}:stale'
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            fresh = await self.get_json(key)
            if fresh is not None:
                return fresh, 'cache'
            try:
                value = await loader()
            except Exception:
                stale = await self.get_json(stale_key)
                if stale is not None:
                    return stale, 'stale-cache'
                raise
            await self.set_json(key, value, ttl)
            await self.set_json(stale_key, value, stale_ttl)
            return value, 'provider'

    async def publish_event(self, event_type: str, payload: dict):
        try:
            await self.client.xadd(
                'soccer:events',
                {'event_type': event_type, 'payload': json.dumps(payload)},
                maxlen=5000,
                approximate=True,
            )
        except RedisError:
            # Event delivery is best-effort; REST remains available.
            pass

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except RedisError:
            return False

    async def close(self):
        await self.client.aclose()


cache = Cache()
