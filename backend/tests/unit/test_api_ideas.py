"""Unit tests for ideas API endpoints."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db.base import engine, Base


@pytest.fixture(scope="function")
async def mock_services():
    """Mock external services (LLM and embedding)."""
    # Create mock service instances
    mock_llm_instance = AsyncMock()
    mock_llm_instance.format_idea = AsyncMock(
        side_effect=lambda text, custom_prompt=None, session_context=None, similar_ideas=None: f"Formatted: {text}"
    )

    mock_embedding_instance = AsyncMock()
    mock_embedding_instance.embed = AsyncMock(
        side_effect=lambda text: np.random.rand(384).astype(np.float32)
    )

    with patch("backend.app.api.ideas.get_llm_service", return_value=mock_llm_instance), \
         patch("backend.app.api.ideas.get_embedding_service", return_value=mock_embedding_instance):

        yield mock_llm_instance, mock_embedding_instance


@pytest.fixture(scope="function")
async def test_client(mock_services):
    """Create test client with in-memory database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_session(test_client):
    """Create a test session."""
    response = await test_client.post(
        "/api/sessions/",
        json={"title": "Test Session"}
    )
    return response.json()


@pytest.fixture
async def test_user(test_client, test_session):
    """Create and join a test user."""
    session_id = test_session["id"]

    # Register user
    register_response = await test_client.post(
        "/api/users/register",
        json={"name": "Test User"}
    )
    user_data = register_response.json()
    user_id = user_data["user_id"]

    # Join session
    await test_client.post(
        f"/api/users/{session_id}/join",
        json={"user_id": user_id, "name": "Test User"}
    )

    return {"user_id": user_id, "session_id": session_id}


class TestIdeasAPI:
    """Test cases for ideas API endpoints."""

    @pytest.mark.asyncio
    async def test_create_idea_success(self, test_client, test_user):
        """Test creating an idea successfully."""
        response = await test_client.post(
            "/api/ideas/",
            json={
                "session_id": test_user["session_id"],
                "user_id": test_user["user_id"],
                "raw_text": "This is a test idea for brainstorming"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["session_id"] == test_user["session_id"]
        assert data["user_id"] == test_user["user_id"]
        assert "formatted_text" in data
        assert "raw_text" in data
        assert data["raw_text"] == "This is a test idea for brainstorming"
        assert "x" in data
        assert "y" in data
        assert "novelty_score" in data
        assert 0 <= data["novelty_score"] <= 100

    @pytest.mark.asyncio
    async def test_create_idea_nonexistent_session(self, test_client, test_user):
        """Test creating an idea for a non-existent session."""
        response = await test_client.post(
            "/api/ideas/",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "user_id": test_user["user_id"],
                "raw_text":"Test idea"
            }
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_idea_nonexistent_user(self, test_client, test_user):
        """Test creating an idea with a non-existent user."""
        response = await test_client.post(
            "/api/ideas/",
            json={
                "session_id": test_user["session_id"],
                "user_id": "00000000-0000-0000-0000-000000000000",
                "raw_text":"Test idea"
            }
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_idea_empty_text(self, test_client, test_user):
        """Test creating an idea with empty text."""
        response = await test_client.post(
            "/api/ideas/",
            json={
                "session_id": test_user["session_id"],
                "user_id": test_user["user_id"],
                "raw_text":""
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_ideas_by_session(self, test_client, test_user):
        """Test retrieving all ideas for a session."""
        session_id = test_user["session_id"]

        # Create multiple ideas
        ideas_to_create = [
            "First test idea",
            "Second test idea",
            "Third test idea"
        ]

        for text in ideas_to_create:
            await test_client.post(
                "/api/ideas/",
                json={
                    "session_id": session_id,
                    "user_id": test_user["user_id"],
                    "raw_text":text
                }
            )

        # Get all ideas
        response = await test_client.get(f"/api/ideas/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert len(data["ideas"]) == 3

        # Verify ideas contain expected fields
        for idea in data["ideas"]:
            assert "id" in idea
            assert "user_name" in idea
            assert "formatted_text" in idea
            assert "raw_text" in idea

    @pytest.mark.asyncio
    async def test_get_ideas_empty_session(self, test_client, test_session):
        """Test retrieving ideas from a session with no ideas."""
        session_id = test_session["id"]

        response = await test_client.get(f"/api/ideas/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert len(data["ideas"]) == 0

    @pytest.mark.asyncio
    async def test_get_ideas_nonexistent_session(self, test_client):
        """Test retrieving ideas from a non-existent session."""
        response = await test_client.get("/api/ideas/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_single_idea(self, test_client, test_user):
        """Test retrieving a single idea by ID."""
        session_id = test_user["session_id"]

        # Create an idea
        create_response = await test_client.post(
            "/api/ideas/",
            json={
                "session_id": session_id,
                "user_id": test_user["user_id"],
                "raw_text":"Single test idea"
            }
        )
        idea_id = create_response.json()["id"]

        # Get the idea
        response = await test_client.get(f"/api/ideas/{session_id}/{idea_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == idea_id
        assert data["raw_text"] == "Single test idea"

    @pytest.mark.asyncio
    async def test_get_nonexistent_idea(self, test_client, test_session):
        """Test retrieving a non-existent idea."""
        session_id = test_session["id"]

        response = await test_client.get(
            f"/api/ideas/{session_id}/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_multiple_ideas_updates_user_score(self, test_client, test_user):
        """Test that creating multiple ideas updates the user's total score."""
        session_id = test_user["session_id"]
        user_id = test_user["user_id"]

        # Create first idea
        await test_client.post(
            "/api/ideas/",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "raw_text":"First idea"
            }
        )

        # Create second idea
        await test_client.post(
            "/api/ideas/",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "raw_text":"Second idea"
            }
        )

        # Get user info
        user_response = await test_client.get(f"/api/users/{session_id}/{user_id}")
        user_data = user_response.json()

        # User should have accumulated score from both ideas
        assert user_data["total_score"] > 0
        assert user_data["idea_count"] == 2


class TestIdeasValidation:
    """Test input validation for ideas API."""

    @pytest.mark.asyncio
    async def test_create_idea_missing_fields(self, test_client):
        """Test creating an idea with missing required fields."""
        response = await test_client.post(
            "/api/ideas/",
            json={"text": "Test idea"}  # Missing session_id and user_id
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_idea_invalid_session_id_format(self, test_client, test_user):
        """Test creating an idea with invalid session ID format."""
        response = await test_client.post(
            "/api/ideas/",
            json={
                "session_id": "invalid-uuid-format",
                "user_id": test_user["user_id"],
                "raw_text":"Test idea"
            }
        )

        # Should return 422 for invalid UUID format
        assert response.status_code == 422
