"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app.db.base import Base, get_db
from backend.app.main import app


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


@pytest.fixture(scope="function")
async def test_client_with_db() -> AsyncGenerator[AsyncClient, None]:
    """
    Create test client with in-memory database.

    This fixture creates a fresh test database for each test and
    overrides the app's database dependency.
    """
    # Create test database engine
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Override get_db dependency
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    await test_engine.dispose()
