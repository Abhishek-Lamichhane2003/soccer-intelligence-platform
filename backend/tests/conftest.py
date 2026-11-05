import asyncio
import os
from pathlib import Path

# Tests must NEVER inherit the development/production database from Docker or the shell.
# Force an isolated SQLite file before importing any application modules/settings.
TEST_DB_PATH = Path('/tmp/soccer_intelligence_test.db')
os.environ['APP_ENV'] = 'test'
os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{TEST_DB_PATH}'
os.environ['REDIS_URL'] = 'redis://localhost:6379/15'
os.environ['FOOTBALL_DATA_API_KEY'] = ''
os.environ['JWT_SECRET'] = 'test-secret-that-is-long-enough-for-tests-only'

import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
import app.models.entities  # noqa: E402,F401


def _assert_safe_test_database() -> None:
    database_url = str(settings.database_url)
    assert settings.app_env == 'test', f'Refusing destructive test setup outside test env: {settings.app_env}'
    assert 'soccer_intelligence_test.db' in database_url, f'Refusing destructive test setup on non-test DB: {database_url}'


@pytest.fixture(scope='session', autouse=True)
def test_database_schema():
    _assert_safe_test_database()
    TEST_DB_PATH.unlink(missing_ok=True)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    yield

    async def teardown():
        await engine.dispose()

    asyncio.run(teardown())
    TEST_DB_PATH.unlink(missing_ok=True)
