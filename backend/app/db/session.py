from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def verify_db() -> None:
    """Verify connectivity only. Schema creation belongs to Alembic migrations."""
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))


async def get_db():
    async with SessionLocal() as session:
        yield session
