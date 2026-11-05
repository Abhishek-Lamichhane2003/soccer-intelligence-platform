from __future__ import annotations

import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.services.cache import cache


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window abuse guard backed by Redis, failing open if Redis is unavailable."""

    def __init__(self, app, default_limit: int = 180, auth_limit: int = 20):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.redis = cache.client

    def _client_id(self, request: Request) -> str:
        if settings.is_production and settings.trust_proxy_headers:
            real_ip = request.headers.get('x-real-ip', '').strip()
            if real_ip:
                return real_ip
            forwarded = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
            if forwarded:
                return forwarded
        return request.client.host if request.client else 'unknown'

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(settings.api_v1_prefix) or request.url.path.endswith('/config'):
            return await call_next(request)
        limit = self.auth_limit if '/auth/' in request.url.path else self.default_limit
        client = self._client_id(request)
        window = int(time.time() // 60)
        bucket = 'auth' if '/auth/' in request.url.path else 'api'
        key = f'rate:{client}:{window}:{bucket}'
        count = 0
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 65)
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={'detail': 'Rate limit exceeded. Try again shortly.'},
                    headers={'Retry-After': '60', 'X-RateLimit-Limit': str(limit), 'X-RateLimit-Remaining': '0'},
                )
        except Exception:
            pass
        response = await call_next(request)
        response.headers['X-RateLimit-Limit'] = str(limit)
        response.headers['X-RateLimit-Remaining'] = str(max(0, limit - count)) if count else 'unknown'
        return response
