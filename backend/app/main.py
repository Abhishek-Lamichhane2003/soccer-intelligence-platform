from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from redis.asyncio import Redis
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.session import verify_db
from app.services.cache import cache
from app.services.metrics import RequestMetricsMiddleware
from app.services.rate_limit import RedisRateLimitMiddleware
from app.services.security_headers import SecurityHeadersMiddleware
from app.services.websocket_manager import ws_manager


async def relay_redis_events() -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    last_id = '$'
    try:
        while True:
            try:
                streams = await redis.xread({'soccer:events': last_id}, block=5000, count=20)
                for _, entries in streams:
                    for event_id, fields in entries:
                        last_id = event_id
                        payload = json.loads(fields.get('payload', '{}'))
                        await ws_manager.broadcast({'type': fields.get('event_type', 'event'), 'payload': payload})
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(1.0)
    finally:
        await redis.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_db()
    task = asyncio.create_task(relay_redis_events())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await cache.close()


app = FastAPI(
    title=settings.app_name,
    version='7.0.0',
    description=(
        'Hardened soccer intelligence platform with provider-backed real data, isolated 22-player Demo Lab, '
        'event streaming, auth, resilient caching, model-status transparency, observability and production configs.'
    ),
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestMetricsMiddleware)
app.add_middleware(RedisRateLimitMiddleware)
if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin] + ([] if settings.is_production else ['http://127.0.0.1:5173']),
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type'],
)

app.include_router(router, prefix=settings.api_v1_prefix)
app.mount('/metrics', make_asgi_app())


@app.get('/')
async def root():
    return {'name': settings.app_name, 'version': '7.0.0', 'docs': '/docs'}


@app.get('/health/live')
async def liveness():
    return {'status': 'ok', 'service': 'api'}


@app.get('/health')
@app.get('/health/ready')
async def readiness():
    db_ok = True
    try:
        await verify_db()
    except Exception:
        db_ok = False
    redis_ok = await cache.ping()
    payload = {
        'status': 'ok' if db_ok else 'not-ready',
        'service': 'api',
        'database': 'ok' if db_ok else 'unavailable',
        'redis': 'ok' if redis_ok else 'fallback-local-cache',
        'real_data_configured': bool(settings.football_data_api_key),
    }
    return JSONResponse(payload, status_code=200 if db_ok else 503)
