"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app.db.base import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.

    Each test gets a fresh database with all tables created.
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Provide session to test
    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def sample_embeddings():
    """Sample embeddings for testing."""
    import numpy as np

    np.random.seed(42)

    # Generate normalized random embeddings
    def generate_embedding(dim=384):
        emb = np.random.randn(dim)
        return (emb / np.linalg.norm(emb)).tolist()

    return {
        "new": generate_embedding(),
        "existing": [generate_embedding() for _ in range(5)],
        "similar": lambda ref: (np.array(ref) + np.random.randn(384) * 0.1).tolist(),
    }
