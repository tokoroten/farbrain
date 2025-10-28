"""Integration tests for complete session workflow."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_session(test_client_with_db: AsyncClient) -> dict:
    """Create a test session."""
    response = await test_client_with_db.post(
        "/api/sessions/",
        json={
            "title": "Test Session",
            "description": "Integration test session",
            "duration": 3600,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def test_user(test_client_with_db: AsyncClient, test_session: dict) -> dict:
    """Create a test user and join session."""
    # Register user
    response = await test_client_with_db.post(
        "/api/users/register",
        json={"name": "Test User"},
    )
    assert response.status_code == 201
    user_data = response.json()

    # Join session
    response = await test_client_with_db.post(
        f"/api/users/{test_session['id']}/join",
        json={
            "user_id": user_data["user_id"],
            "name": "Test User",
            "password": None,
        },
    )
    assert response.status_code == 201

    return user_data


class TestCompleteSessionFlow:
    """Test complete session workflow from creation to idea submission."""

    @pytest.mark.asyncio
    async def test_create_session(self, test_client_with_db: AsyncClient):
        """Test session creation."""
        response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "New Session",
                "description": "Test description",
                "duration": 7200,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Session"
        assert data["description"] == "Test description"
        assert data["status"] == "active"
        assert data["accepting_ideas"] is True

    @pytest.mark.asyncio
    async def test_create_session_with_password(self, test_client_with_db: AsyncClient):
        """Test session creation with password."""
        response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "Protected Session",
                "description": "Password protected",
                "duration": 3600,
                "password": "secret123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["has_password"] is True

    @pytest.mark.asyncio
    async def test_list_sessions(self, test_client_with_db: AsyncClient, test_session: dict):
        """Test listing sessions."""
        response = await test_client_with_db.get("/api/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) > 0
        assert any(s["id"] == test_session["id"] for s in data["sessions"])

    @pytest.mark.asyncio
    async def test_list_sessions_active_only(self, test_client_with_db: AsyncClient, test_session: dict):
        """Test listing active sessions only."""
        response = await test_client_with_db.get("/api/sessions/?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "active" for s in data["sessions"])

    @pytest.mark.asyncio
    async def test_get_session(self, test_client_with_db: AsyncClient, test_session: dict):
        """Test getting specific session."""
        response = await test_client_with_db.get(f"/api/sessions/{test_session['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session["id"]
        assert data["title"] == test_session["title"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, test_client_with_db: AsyncClient):
        """Test getting non-existent session."""
        response = await test_client_with_db.get("/api/sessions/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_registration(self, test_client_with_db: AsyncClient):
        """Test user registration."""
        response = await test_client_with_db.post(
            "/api/users/register",
            json={"name": "John Doe"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert len(data["user_id"]) > 0

    @pytest.mark.asyncio
    async def test_join_session_without_password(
        self, test_client_with_db: AsyncClient, test_session: dict
    ):
        """Test joining session without password."""
        # Register user first
        register_response = await test_client_with_db.post(
            "/api/users/register",
            json={"name": "Jane Doe"},
        )
        user_data = register_response.json()

        # Join session
        response = await test_client_with_db.post(
            f"/api/users/{test_session['id']}/join",
            json={
                "user_id": user_data["user_id"],
                "name": "Jane Doe",
                "password": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == test_session["id"]
        assert data["name"] == "Jane Doe"

    @pytest.mark.asyncio
    async def test_join_session_with_wrong_password(self, test_client_with_db: AsyncClient):
        """Test joining password-protected session with wrong password."""
        # Create protected session
        session_response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "Protected",
                "description": "Test",
                "duration": 3600,
                "password": "correct",
            },
        )
        session = session_response.json()

        # Register user
        user_response = await test_client_with_db.post(
            "/api/users/register",
            json={"name": "User"},
        )
        user = user_response.json()

        # Try to join with wrong password
        response = await test_client_with_db.post(
            f"/api/users/{session['id']}/join",
            json={
                "user_id": user["user_id"],
                "name": "User",
                "password": "wrong",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_join_nonexistent_session(self, test_client_with_db: AsyncClient):
        """Test joining non-existent session."""
        user_response = await test_client_with_db.post(
            "/api/users/register",
            json={"name": "User"},
        )
        user = user_response.json()

        response = await test_client_with_db.post(
            "/api/users/nonexistent-id/join",
            json={
                "user_id": user["user_id"],
                "name": "User",
                "password": None,
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_end_session(
        self, test_client_with_db: AsyncClient, test_session: dict
    ):
        """Test ending a session."""
        response = await test_client_with_db.post(
            f"/api/sessions/{test_session['id']}/end"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ended"
        assert data["accepting_ideas"] is False

    @pytest.mark.asyncio
    async def test_session_participant_count(
        self, test_client_with_db: AsyncClient, test_session: dict, test_user: dict
    ):
        """Test that participant count updates."""
        response = await test_client_with_db.get(f"/api/sessions/{test_session['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["participant_count"] >= 1

    @pytest.mark.asyncio
    async def test_complete_workflow(self, test_client_with_db: AsyncClient):
        """Test complete workflow: create session, register user, join session."""
        # 1. Create session
        session_response = await test_client_with_db.post(
            "/api/sessions/",
            json={
                "title": "Workflow Test",
                "description": "Complete workflow",
                "duration": 3600,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        # 2. Register user
        user_response = await test_client_with_db.post(
            "/api/users/register",
            json={"name": "Test User"},
        )
        assert user_response.status_code == 201
        user = user_response.json()

        # 3. Join session
        join_response = await test_client_with_db.post(
            f"/api/users/{session['id']}/join",
            json={
                "user_id": user["user_id"],
                "name": "Test User",
                "password": None,
            },
        )
        assert join_response.status_code == 201

        # 4. Verify session has participants (system user + actual user)
        session_check = await test_client_with_db.get(f"/api/sessions/{session['id']}")
        assert session_check.status_code == 200
        session_data = session_check.json()
        assert session_data["participant_count"] == 2  # System user + Test User

        # 5. End session
        end_response = await test_client_with_db.post(
            f"/api/sessions/{session['id']}/end"
        )
        assert end_response.status_code == 200

        # 6. Verify session ended
        final_check = await test_client_with_db.get(f"/api/sessions/{session['id']}")
        final_data = final_check.json()
        assert final_data["status"] == "ended"
        assert final_data["accepting_ideas"] is False
