from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.shared.infrastructure.config import settings

# Alembic runs migrations synchronously (psycopg) via settings.database_url as-is
# (see alembic/env.py); the app itself uses the async driver (asyncpg) for the 5
# concurrent background tasks, so the scheme is swapped here rather than
# duplicating the connection string across two env vars.
_ASYNC_DATABASE_URL = settings.database_url.replace(
    "postgresql+psycopg://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    _ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
