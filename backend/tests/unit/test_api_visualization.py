"""Unit tests for visualization API endpoints."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db.base import engine, Base


@pytest.fixture(scope="function")
async def mock_services():
    """Mock external services (LLM and embedding)."""
    with patch("backend.app.api.ideas.llm_service") as mock_llm, \
         patch("backend.app.api.ideas.embedding_service") as mock_embedding:

        # Mock LLM format_idea to return formatted text
        mock_llm.format_idea = AsyncMock(
            side_effect=lambda text, custom_prompt=None: f"Formatted: {text}"
        )

        # Mock embedding service to return deterministic embeddings
        mock_embedding.embed = AsyncMock(
            side_effect=lambda text: np.random.rand(384).astype(np.float32)
        )

        yield mock_llm, mock_embedding


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
        json={"title": "Test Session", "duration": 3600}
    )
    return response.json()


@pytest.fixture
async def test_users(test_client, test_session):
    """Create and join multiple test users."""
    session_id = test_session["id"]
    users = []

    for i in range(3):
        # Register user
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": f"Test User {i+1}"}
        )
        user_data = register_response.json()
        user_id = user_data["user_id"]

        # Join session
        await test_client.post(
            f"/api/users/{session_id}/join",
            json={"user_id": user_id, "name": f"Test User {i+1}"}
        )

        users.append({"user_id": user_id, "name": f"Test User {i+1}"})

    return {"session_id": session_id, "users": users}


@pytest.fixture
async def test_ideas(test_client, test_users):
    """Create multiple test ideas."""
    session_id = test_users["session_id"]
    users = test_users["users"]
    ideas = []

    # Create ideas for each user
    for user_idx, user in enumerate(users):
        for idea_idx in range(3):
            response = await test_client.post(
                "/api/ideas/",
                json={
                    "session_id": session_id,
                    "user_id": user["user_id"],
                    "raw_text": f"Idea {idea_idx+1} from {user['name']}"
                }
            )
            ideas.append(response.json())

    return {"session_id": session_id, "users": users, "ideas": ideas}


class TestVisualizationAPI:
    """Test cases for visualization API endpoints."""

    @pytest.mark.asyncio
    async def test_get_visualization_empty_session(self, test_client, test_session):
        """Test getting visualization data for a session with no ideas."""
        session_id = test_session["id"]

        response = await test_client.get(f"/api/visualization/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert "clusters" in data
        assert len(data["ideas"]) == 0
        assert len(data["clusters"]) == 0

    @pytest.mark.asyncio
    async def test_get_visualization_with_ideas(self, test_client, test_ideas):
        """Test getting visualization data for a session with ideas."""
        session_id = test_ideas["session_id"]

        response = await test_client.get(f"/api/visualization/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "ideas" in data
        assert "clusters" in data

        # Verify we have the correct number of ideas (3 users × 3 ideas each)
        assert len(data["ideas"]) == 9

        # Verify idea structure
        for idea in data["ideas"]:
            assert "id" in idea
            assert "x" in idea
            assert "y" in idea
            assert "cluster_id" in idea
            assert "novelty_score" in idea
            assert "user_id" in idea
            assert "user_name" in idea
            assert "formatted_text" in idea
            assert "raw_text" in idea

            # Verify coordinates are numeric
            assert isinstance(idea["x"], (int, float))
            assert isinstance(idea["y"], (int, float))

            # Verify novelty score is in valid range
            assert 0 <= idea["novelty_score"] <= 100

    @pytest.mark.asyncio
    async def test_get_visualization_nonexistent_session(self, test_client):
        """Test getting visualization data for a non-existent session."""
        response = await test_client.get(
            "/api/visualization/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_visualization_invalid_session_id(self, test_client):
        """Test getting visualization data with invalid session ID format."""
        response = await test_client.get("/api/visualization/invalid-uuid")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_visualization_includes_user_names(self, test_client, test_ideas):
        """Test that visualization data includes correct user names."""
        session_id = test_ideas["session_id"]
        users = test_ideas["users"]

        response = await test_client.get(f"/api/visualization/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Get all user names from visualization
        viz_user_names = {idea["user_name"] for idea in data["ideas"]}
        expected_user_names = {user["name"] for user in users}

        assert viz_user_names == expected_user_names


class TestScoreboardAPI:
    """Test cases for scoreboard API endpoints."""

    @pytest.mark.asyncio
    async def test_get_scoreboard_empty_session(self, test_client, test_session):
        """Test getting scoreboard for a session with no users."""
        session_id = test_session["id"]

        response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert response.status_code == 200
        data = response.json()
        assert "rankings" in data
        assert len(data["rankings"]) == 0

    @pytest.mark.asyncio
    async def test_get_scoreboard_with_users(self, test_client, test_ideas):
        """Test getting scoreboard for a session with users and ideas."""
        session_id = test_ideas["session_id"]

        response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "rankings" in data
        assert len(data["rankings"]) == 3  # 3 users

        # Verify scoreboard entry structure
        for entry in data["rankings"]:
            assert "rank" in entry
            assert "user_id" in entry
            assert "user_name" in entry
            assert "total_score" in entry
            assert "idea_count" in entry
            assert "avg_novelty_score" in entry
            assert "top_idea" in entry

            # Verify data types
            assert isinstance(entry["rank"], int)
            assert isinstance(entry["total_score"], (int, float))
            assert isinstance(entry["idea_count"], int)
            assert isinstance(entry["avg_novelty_score"], (int, float))

            # Each user should have 3 ideas
            assert entry["idea_count"] == 3

    @pytest.mark.asyncio
    async def test_scoreboard_ranking_order(self, test_client, test_ideas):
        """Test that scoreboard is correctly ordered by total score."""
        session_id = test_ideas["session_id"]

        response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert response.status_code == 200
        data = response.json()

        rankings = data["rankings"]

        # Verify ranks are sequential starting from 1
        for i, entry in enumerate(rankings, start=1):
            assert entry["rank"] == i

        # Verify total scores are in descending order
        total_scores = [entry["total_score"] for entry in rankings]
        assert total_scores == sorted(total_scores, reverse=True)

    @pytest.mark.asyncio
    async def test_scoreboard_includes_top_idea(self, test_client, test_ideas):
        """Test that scoreboard includes top idea for each user."""
        session_id = test_ideas["session_id"]

        response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert response.status_code == 200
        data = response.json()

        # Each user should have a top idea (since they all have ideas)
        for entry in data["rankings"]:
            assert entry["top_idea"] is not None
            assert "id" in entry["top_idea"]
            assert "formatted_text" in entry["top_idea"]
            assert "novelty_score" in entry["top_idea"]

    @pytest.mark.asyncio
    async def test_scoreboard_avg_novelty_calculation(self, test_client, test_ideas):
        """Test that average novelty score is calculated correctly."""
        session_id = test_ideas["session_id"]

        response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert response.status_code == 200
        data = response.json()

        for entry in data["rankings"]:
            # Average should be total_score / idea_count
            expected_avg = entry["total_score"] / entry["idea_count"]
            assert abs(entry["avg_novelty_score"] - expected_avg) < 0.01  # Allow small floating point error

    @pytest.mark.asyncio
    async def test_scoreboard_nonexistent_session(self, test_client):
        """Test getting scoreboard for a non-existent session."""
        response = await test_client.get(
            "/api/visualization/00000000-0000-0000-0000-000000000000/scoreboard"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_scoreboard_invalid_session_id(self, test_client):
        """Test getting scoreboard with invalid session ID format."""
        response = await test_client.get("/api/visualization/invalid-uuid/scoreboard")

        assert response.status_code == 422  # Validation error


class TestVisualizationIntegration:
    """Integration tests for visualization and scoreboard together."""

    @pytest.mark.asyncio
    async def test_visualization_and_scoreboard_consistency(self, test_client, test_ideas):
        """Test that visualization and scoreboard data are consistent."""
        session_id = test_ideas["session_id"]

        # Get both visualization and scoreboard
        viz_response = await test_client.get(f"/api/visualization/{session_id}")
        scoreboard_response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert viz_response.status_code == 200
        assert scoreboard_response.status_code == 200

        viz_data = viz_response.json()
        scoreboard_data = scoreboard_response.json()

        # Count ideas per user in visualization
        user_idea_counts = {}
        for idea in viz_data["ideas"]:
            user_id = idea["user_id"]
            user_idea_counts[user_id] = user_idea_counts.get(user_id, 0) + 1

        # Verify counts match scoreboard
        for entry in scoreboard_data["rankings"]:
            user_id = entry["user_id"]
            assert user_idea_counts[user_id] == entry["idea_count"]

    @pytest.mark.asyncio
    async def test_scoreboard_with_single_user(self, test_client, test_session):
        """Test scoreboard with only one user."""
        session_id = test_session["id"]

        # Register and join one user
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": "Solo User"}
        )
        user_id = register_response.json()["user_id"]

        await test_client.post(
            f"/api/users/{session_id}/join",
            json={"user_id": user_id, "name": "Solo User"}
        )

        # Create one idea
        await test_client.post(
            "/api/ideas/",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "raw_text": "Solo idea"
            }
        )

        # Get scoreboard
        response = await test_client.get(f"/api/visualization/{session_id}/scoreboard")

        assert response.status_code == 200
        data = response.json()

        assert len(data["rankings"]) == 1
        assert data["rankings"][0]["rank"] == 1
        assert data["rankings"][0]["user_name"] == "Solo User"
        assert data["rankings"][0]["idea_count"] == 1
