"""Unit tests for users API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db.base import engine, Base


@pytest.fixture(scope="function")
async def test_client():
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
    """Create a test session for user tests."""
    response = await test_client.post(
        "/api/sessions/",
        json={"title": "Test Session", "duration": 3600}
    )
    return response.json()


class TestUsersAPI:
    """Test cases for users API endpoints."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client):
        """Test registering a new user successfully."""
        response = await test_client.post(
            "/api/users/register",
            json={"name": "Test User"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test User"
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_register_user_missing_name(self, test_client):
        """Test registering a user without a name."""
        response = await test_client.post(
            "/api/users/register",
            json={}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_join_session_success(self, test_client, test_session):
        """Test joining a session successfully."""
        session_id = test_session["id"]

        # Register a user
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": "Test User"}
        )
        user_id = register_response.json()["user_id"]

        # Join the session
        response = await test_client.post(
            f"/api/users/{session_id}/join",
            json={"user_id": user_id, "name": "Test User"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        assert data["name"] == "Test User"
        assert data["session_id"] == session_id
        assert data["total_score"] == 0.0

    @pytest.mark.asyncio
    async def test_join_session_with_password(self, test_client):
        """Test joining a password-protected session."""
        # Create a session with password
        session_response = await test_client.post(
            "/api/sessions/",
            json={
                "title": "Protected Session",
                "duration": 3600,
                "password": "test123"
            }
        )
        session_id = session_response.json()["id"]

        # Register a user
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": "Test User"}
        )
        user_id = register_response.json()["user_id"]

        # Join with correct password
        response = await test_client.post(
            f"/api/users/{session_id}/join",
            json={
                "user_id": user_id,
                "name": "Test User",
                "password": "test123"
            }
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_join_session_wrong_password(self, test_client):
        """Test joining a session with wrong password."""
        # Create a session with password
        session_response = await test_client.post(
            "/api/sessions/",
            json={
                "title": "Protected Session",
                "duration": 3600,
                "password": "test123"
            }
        )
        session_id = session_response.json()["id"]

        # Register a user
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": "Test User"}
        )
        user_id = register_response.json()["user_id"]

        # Join with wrong password
        response = await test_client.post(
            f"/api/users/{session_id}/join",
            json={
                "user_id": user_id,
                "name": "Test User",
                "password": "wrong_password"
            }
        )

        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_join_nonexistent_session(self, test_client):
        """Test joining a session that doesn't exist."""
        # Register a user
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": "Test User"}
        )
        user_id = register_response.json()["user_id"]

        # Try to join non-existent session
        response = await test_client.post(
            "/api/users/nonexistent-session-id/join",
            json={"user_id": user_id, "name": "Test User"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user(self, test_client, test_session):
        """Test getting user information."""
        session_id = test_session["id"]

        # Register and join
        register_response = await test_client.post(
            "/api/users/register",
            json={"name": "Test User"}
        )
        user_id = register_response.json()["user_id"]

        join_response = await test_client.post(
            f"/api/users/{session_id}/join",
            json={"user_id": user_id, "name": "Test User"}
        )

        # Get user info using the global user_id, not the internal database id
        response = await test_client.get(f"/api/users/{session_id}/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, test_client, test_session):
        """Test getting a non-existent user."""
        session_id = test_session["id"]

        response = await test_client.get(
            f"/api/users/{session_id}/nonexistent-user-id"
        )

        assert response.status_code == 404
