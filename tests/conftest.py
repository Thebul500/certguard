"""Test fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from certguard.app import create_app
from certguard.database import Base, get_db

# Async SQLite for tests — matches the async routes, no external DB required.
SQLALCHEMY_TEST_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestAsyncSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """Yield an async SQLite session for tests."""
    async with TestAsyncSession() as session:
        yield session


@pytest.fixture
def client():
    """Create a test client backed by an in-memory SQLite database."""
    import asyncio

    async def setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.get_event_loop_policy()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(setup())

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

    loop.run_until_complete(teardown())
    loop.close()
    app.dependency_overrides.clear()
