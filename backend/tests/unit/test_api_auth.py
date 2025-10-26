"""Unit tests for auth API endpoints."""

import pytest
from backend.app.core.config import settings


class TestAuthAPI:
    """Test cases for auth API endpoints."""

    @pytest.mark.asyncio
    async def test_verify_admin_correct_password(self, test_client_with_db):
        """Test admin verification with correct password."""
        response = await test_client_with_db.post(
            "/api/admin/verify",
            json={"password": settings.admin_password}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "認証成功" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_admin_wrong_password(self, test_client_with_db):
        """Test admin verification with wrong password."""
        response = await test_client_with_db.post(
            "/api/admin/verify",
            json={"password": "wrong_password"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "正しくありません" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_admin_missing_password(self, test_client_with_db):
        """Test admin verification without password."""
        response = await test_client_with_db.post(
            "/api/admin/verify",
            json={}
        )

        assert response.status_code == 422  # Validation error
