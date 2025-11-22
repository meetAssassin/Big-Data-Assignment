# api/db/postgres.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.config import POSTGRES_URL

if POSTGRES_URL is None:
    raise RuntimeError("POSTGRES_URL not set in environment / .env")

# Convert the normal postgres URI to the async psycopg driver form.
# e.g. postgresql://user:pass@host/dbname -> postgresql+psycopg://user:pass@host/dbname
ASYNC_URL = POSTGRES_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# create async engine
engine = create_async_engine(
    ASYNC_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """
    Async generator dependency for FastAPI.
    Usage:
        async with AsyncSessionLocal() as session:
            yield session
    """
    async with AsyncSessionLocal() as session:
        yield session
