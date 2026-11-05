from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.config import settings
from app.db.session import SessionLocal, verify_db
from app.models.entities import MatchSnapshot
from app.providers.football_data import provider
from app.services.cache import cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger('soccer-worker')


async def persist_snapshot(match: dict) -> None:
    async with SessionLocal() as db:
        db.add(MatchSnapshot(
            external_match_id=match['id'],
            competition_code=(match.get('competition') or {}).get('code') or 'UNKNOWN',
            status=match.get('status') or 'UNKNOWN',
            payload=match,
        ))
        await db.commit()


async def cleanup_snapshots() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.snapshot_retention_days)
    async with SessionLocal() as db:
        result = await db.execute(delete(MatchSnapshot).where(MatchSnapshot.captured_at < cutoff))
        await db.commit()
        return int(result.rowcount or 0)


async def run() -> None:
    await verify_db()
    if not provider.configured:
        log.warning('FOOTBALL_DATA_API_KEY is empty. Worker is alive but real-data polling is disabled.')

    previous: dict[str, str] = {}
    next_cleanup = datetime.now(timezone.utc)
    while True:
        if datetime.now(timezone.utc) >= next_cleanup:
            try:
                removed = await cleanup_snapshots()
                log.info('Snapshot retention cleanup removed %s rows.', removed)
            except Exception as exc:
                log.warning('Snapshot cleanup failed: %s', exc)
            next_cleanup = datetime.now(timezone.utc) + timedelta(hours=12)

        if provider.configured:
            try:
                matches = await provider.live_matches()
                await cache.set_json('api:live_matches', matches, ttl=max(10, settings.live_poll_seconds + 5))
                await cache.set_json('api:live_matches:stale', matches, ttl=300)
                for match in matches:
                    fingerprint = json.dumps(match, sort_keys=True)
                    if previous.get(match['id']) != fingerprint:
                        previous[match['id']] = fingerprint
                        await persist_snapshot(match)
                        await cache.publish_event('match_update', match)
                log.info('Polled %s live matches.', len(matches))
            except Exception as exc:
                log.warning('Provider polling failed; API can continue from cache: %s', exc)
        await asyncio.sleep(settings.live_poll_seconds)


if __name__ == '__main__':
    asyncio.run(run())
