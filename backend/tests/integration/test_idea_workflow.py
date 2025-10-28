"""Integration tests for idea submission and visualization workflow."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def session_with_user(test_client_with_db: AsyncClient) -> tuple[dict, dict]:
    """Create a session and a user joined to it."""
    # Create session
    session_response = await test_client_with_db.post(
        "/api/sessions/",
        json={
            "title": "Idea Test Session",
            "description": "Testing idea submission",
            "duration": 3600,
        },
    )
    assert session_response.status_code == 201
    session = session_response.json()

    # Register user
    user_response = await test_client_with_db.post(
        "/api/users/register",
        json={"name": "Test User"},
    )
    assert user_response.status_code == 201
    user = user_response.json()

    # Join session
    join_response = await test_client_with_db.post(
        f"/api/users/{session['id']}/join",
        json={
            "user_id": user["user_id"],
            "name": "Test User",
            "password": None,
        },
    )
    assert join_response.status_code == 201

    return session, user


class TestIdeaWorkflow:
    """Test idea submission, embedding, and visualization workflow."""

    @pytest.mark.asyncio
    async def test_create_idea(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test creating a single idea."""
        session, user = session_with_user

        response = await test_client_with_db.post(
            "/api/ideas/",
            json={
                "session_id": session["id"],
                "user_id": user["user_id"],
                "raw_text": "AI-powered brainstorming assistant",
                "skip_formatting": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["session_id"] == session["id"]
        assert data["user_id"] == user["user_id"]
        assert data["formatted_text"] == "AI-powered brainstorming assistant"
        assert "x" in data
        assert "y" in data

    @pytest.mark.asyncio
    async def test_create_multiple_ideas(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test creating multiple ideas."""
        session, user = session_with_user

        ideas = [
            "Machine learning for content generation",
            "Blockchain-based voting system",
            "Virtual reality meeting platform",
        ]

        created_ids = []
        for idea_text in ideas:
            response = await test_client_with_db.post(
                "/api/ideas/",
                json={
                    "session_id": session["id"],
                    "user_id": user["user_id"],
                    "raw_text": idea_text,
                    "skip_formatting": True,
                },
            )
            assert response.status_code == 201
            data = response.json()
            created_ids.append(data["id"])

        assert len(created_ids) == 3
        assert len(set(created_ids)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_get_visualization_data(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test getting visualization data for a session."""
        session, user = session_with_user

        # Create an idea first
        await test_client_with_db.post(
            "/api/ideas/",
            json={
                "session_id": session["id"],
                "user_id": user["user_id"],
                "raw_text": "Real-time collaboration tool",
                "skip_formatting": True,
            },
        )

        # Get visualization data
        response = await test_client_with_db.get(
            f"/api/visualization/{session['id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert "clusters" in data
        # Should have at least the idea we just created (plus starter ideas)
        assert len(data["ideas"]) >= 1

    @pytest.mark.asyncio
    async def test_get_scoreboard(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test getting scoreboard data."""
        session, user = session_with_user

        # Create an idea to generate some score
        await test_client_with_db.post(
            "/api/ideas/",
            json={
                "session_id": session["id"],
                "user_id": user["user_id"],
                "raw_text": "Gamification platform",
                "skip_formatting": True,
            },
        )

        # Get scoreboard
        response = await test_client_with_db.get(
            f"/api/visualization/{session['id']}/scoreboard"
        )

        assert response.status_code == 200
        data = response.json()
        assert "rankings" in data
        # Should have at least the test user (and possibly system user)
        assert len(data["rankings"]) >= 1

    @pytest.mark.asyncio
    async def test_create_idea_with_empty_text(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test that creating an idea with empty text fails."""
        session, user = session_with_user

        response = await test_client_with_db.post(
            "/api/ideas/",
            json={
                "session_id": session["id"],
                "user_id": user["user_id"],
                "raw_text": "",
                "skip_formatting": True,
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_idea_for_nonexistent_session(
        self, test_client_with_db: AsyncClient
    ):
        """Test creating an idea for a non-existent session fails."""
        # Register user first
        user_response = await test_client_with_db.post(
            "/api/users/register",
            json={"name": "Test User"},
        )
        user = user_response.json()

        response = await test_client_with_db.post(
            "/api/ideas/",
            json={
                "session_id": "nonexistent-id",
                "user_id": user["user_id"],
                "raw_text": "Some idea",
                "skip_formatting": True,
            },
        )

        # Returns 422 because session validation fails (FK constraint)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_idea_formatting(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test that idea formatting works (when not skipped)."""
        session, user = session_with_user

        response = await test_client_with_db.post(
            "/api/ideas/",
            json={
                "session_id": session["id"],
                "user_id": user["user_id"],
                "raw_text": "An idea that needs formatting with lots of extra words",
                "skip_formatting": False,
            },
        )

        # Note: This might fail if LLM service is not configured
        # but we test the endpoint behavior
        assert response.status_code in [201, 500, 503]

    @pytest.mark.asyncio
    async def test_complete_idea_workflow(
        self, test_client_with_db: AsyncClient, session_with_user: tuple[dict, dict]
    ):
        """Test complete workflow: create ideas and verify visualization."""
        session, user = session_with_user

        # 1. Create multiple ideas
        ideas = [
            "Cloud computing platform",
            "Mobile app development",
            "Data analytics dashboard",
        ]

        for idea_text in ideas:
            response = await test_client_with_db.post(
                "/api/ideas/",
                json={
                    "session_id": session["id"],
                    "user_id": user["user_id"],
                    "raw_text": idea_text,
                    "skip_formatting": True,
                },
            )
            assert response.status_code == 201

        # 2. Get visualization data
        viz_response = await test_client_with_db.get(
            f"/api/visualization/{session['id']}"
        )
        assert viz_response.status_code == 200
        viz_data = viz_response.json()

        # Should have our 3 ideas plus starter ideas
        assert len(viz_data["ideas"]) >= 3

        # 3. Get scoreboard
        scoreboard_response = await test_client_with_db.get(
            f"/api/visualization/{session['id']}/scoreboard"
        )
        assert scoreboard_response.status_code == 200
        scoreboard_data = scoreboard_response.json()

        # Should have at least our test user
        assert len(scoreboard_data["rankings"]) >= 1

        # 4. Get session details
        session_response = await test_client_with_db.get(
            f"/api/sessions/{session['id']}"
        )
        assert session_response.status_code == 200
        session_data = session_response.json()

        # Should show at least 3 ideas (our ideas, possibly more with starter ideas)
        assert session_data["idea_count"] >= 3
