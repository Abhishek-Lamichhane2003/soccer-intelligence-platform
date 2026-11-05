from __future__ import annotations

import asyncio
import time
from collections import deque

from redis.exceptions import RedisError

from app.core.config import settings
from app.services.cache import cache


class ProviderQuotaExceeded(RuntimeError):
    pass


class ProviderQuota:
    """Shared fixed-window request budget with local fallback.

    football-data.org's free plan is intentionally treated conservatively; the app
    budgets below the published ceiling so user traffic and the worker do not fight.
    """

    def __init__(self) -> None:
        self.redis = cache.client
        self._local: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        limit = settings.provider_rpm_budget
        minute = int(time.time() // 60)
        key = f'provider:budget:{minute}'
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 70)
            if count > limit:
                raise ProviderQuotaExceeded('Provider request budget exhausted; cached data will be used when available.')
            return
        except RedisError:
            pass

        async with self._lock:
            now = time.monotonic()
            while self._local and now - self._local[0] > 60:
                self._local.popleft()
            if len(self._local) >= limit:
                raise ProviderQuotaExceeded('Local provider request budget exhausted.')
            self._local.append(now)


provider_quota = ProviderQuota()
