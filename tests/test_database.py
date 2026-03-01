"""Tests for database engine and session management."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from certguard.database import Base, async_session, engine, get_db


def test_engine_is_async():
    """Engine is an async SQLAlchemy engine."""
    assert isinstance(engine, AsyncEngine)


def test_async_session_factory():
    """Session factory produces async sessions."""
    assert isinstance(async_session, async_sessionmaker)


def test_base_is_declarative():
    """Base has SQLAlchemy declarative metadata."""
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db yields an AsyncSession then closes it."""
    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    # Cleanup — drive the generator to completion
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
