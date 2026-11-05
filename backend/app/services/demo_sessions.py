from __future__ import annotations

import asyncio
import json
import time
from uuid import uuid4

from redis.exceptions import RedisError

from app.core.config import settings
from app.services.cache import cache
from app.services.demo import DemoMatchEngine


class DemoSessionStore:
    def __init__(self) -> None:
        self._local: dict[str, DemoMatchEngine] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_seen: dict[str, float] = {}

    def _touch(self, session_id: str) -> None:
        self._last_seen[session_id] = time.monotonic()

    def _prune_local(self) -> None:
        cutoff = time.monotonic() - settings.demo_session_ttl_seconds
        expired = [sid for sid, seen in self._last_seen.items() if seen < cutoff]
        for sid in expired:
            self._local.pop(sid, None)
            self._locks.pop(sid, None)
            self._last_seen.pop(sid, None)

    async def create(self) -> tuple[str, dict]:
        self._prune_local()
        session_id = uuid4().hex
        engine = DemoMatchEngine()
        self._local[session_id] = engine
        self._touch(session_id)
        snapshot = engine.tick()
        await self._save(session_id, engine)
        return session_id, snapshot

    async def tick(self, session_id: str) -> dict:
        self._prune_local()
        lock = self._locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            engine = await self._load(session_id)
            snapshot = engine.tick()
            await self._save(session_id, engine)
            return snapshot

    async def _load(self, session_id: str) -> DemoMatchEngine:
        try:
            raw = await cache.client.get(f'demo:session:{session_id}')
            if raw:
                self._touch(session_id)
                return DemoMatchEngine.from_state(json.loads(raw))
        except RedisError:
            pass
        engine = self._local.get(session_id)
        if engine is None:
            engine = DemoMatchEngine()
            self._local[session_id] = engine
        self._touch(session_id)
        return engine

    async def _save(self, session_id: str, engine: DemoMatchEngine) -> None:
        self._local[session_id] = engine
        self._touch(session_id)
        try:
            await cache.client.set(
                f'demo:session:{session_id}',
                json.dumps(engine.to_state()),
                ex=settings.demo_session_ttl_seconds,
            )
        except RedisError:
            pass


sessions = DemoSessionStore()
