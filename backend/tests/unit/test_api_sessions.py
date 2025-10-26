"""Unit tests for sessions API endpoints."""

import pytest


class TestSessionsAPI:
    """Test cases for sessions API endpoints."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, test_client_with_db):
        """Test creating a new session successfully."""
        response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "Test Session",
                "description": "Test description",
                "duration": 3600,
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Session"
        assert data["description"] == "Test description"
        assert data["duration"] == 3600
        assert data["status"] == "active"
        assert data["accepting_ideas"] is True
        assert "id" in data
        assert "start_time" in data

    @pytest.mark.asyncio
    async def test_create_session_with_password(self, test_client_with_db):
        """Test creating a session with password protection."""
        response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "Protected Session",
                "duration": 7200,
                "password": "test123",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Protected Session"
        assert "password_hash" not in data  # Password hash should not be exposed

    @pytest.mark.asyncio
    async def test_create_session_missing_title(self, test_client_with_db):
        """Test creating a session without required title."""
        response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "duration": 3600,
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, test_client_with_db):
        """Test listing sessions when database is empty."""
        response = await test_client_with_db.get("/api/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, test_client_with_db):
        """Test listing sessions with existing data."""
        # Create two sessions
        await test_client_with_db.post(
            "/api/sessions/",
            json={"title": "Session 1", "duration": 3600}
        )
        await test_client_with_db.post(
            "/api/sessions/",
            json={"title": "Session 2", "duration": 7200}
        )

        response = await test_client_with_db.get("/api/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_active_only(self, test_client_with_db):
        """Test listing only active sessions."""
        # Create an active session
        create_response = await test_client_with_db.post(
            "/api/sessions/",
            json={"title": "Active Session", "duration": 3600}
        )
        session_id = create_response.json()["id"]

        # End the session
        await test_client_with_db.post(f"/api/sessions/{session_id}/end")

        # List active sessions only
        response = await test_client_with_db.get("/api/sessions/?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 0  # No active sessions

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, test_client_with_db):
        """Test getting a specific session by ID."""
        # Create a session
        create_response = await test_client_with_db.post(
            "/api/sessions/",
            json={"title": "Test Session", "duration": 3600}
        )
        session_id = create_response.json()["id"]

        # Get the session
        response = await test_client_with_db.get(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["title"] == "Test Session"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, test_client_with_db):
        """Test getting a non-existent session."""
        response = await test_client_with_db.get("/api/sessions/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_end_session(self, test_client_with_db):
        """Test ending an active session."""
        # Create a session
        create_response = await test_client_with_db.post(
            "/api/sessions/",
            json={"title": "Test Session", "duration": 3600}
        )
        session_id = create_response.json()["id"]

        # End the session
        response = await test_client_with_db.post(f"/api/sessions/{session_id}/end")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ended"
        assert data["ended_at"] is not None

    @pytest.mark.asyncio
    async def test_toggle_accepting_ideas(self, test_client_with_db):
        """Test toggling accepting_ideas flag."""
        # Create a session
        create_response = await test_client_with_db.post(
            "/api/sessions/",
            json={"title": "Test Session", "duration": 3600}
        )
        session_id = create_response.json()["id"]

        # Toggle accepting ideas to False
        response = await test_client_with_db.post(
            f"/api/sessions/{session_id}/toggle-accepting",
            json={"accepting_ideas": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepting_ideas"] is False

    @pytest.mark.asyncio
    async def test_create_session_with_custom_prompts(self, test_client_with_db):
        """Test creating a session with custom formatting and summarization prompts."""
        response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "Custom Prompt Session",
                "duration": 3600,
                "formatting_prompt": "Format this idea creatively",
                "summarization_prompt": "Summarize this cluster briefly",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["formatting_prompt"] == "Format this idea creatively"
        assert data["summarization_prompt"] == "Summarize this cluster briefly"
