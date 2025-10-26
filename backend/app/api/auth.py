"""Authentication endpoints for admin access."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.app.core.config import settings

router = APIRouter(tags=["auth"])


class AdminLoginRequest(BaseModel):
    """Admin login request."""

    password: str


class AdminLoginResponse(BaseModel):
    """Admin login response."""

    success: bool
    message: str


@router.post("/admin/verify", response_model=AdminLoginResponse)
async def verify_admin_password(request: AdminLoginRequest):
    """Verify admin password.

    Args:
        request: Admin login request with password

    Returns:
        AdminLoginResponse with success status
    """
    if request.password == settings.admin_password:
        return AdminLoginResponse(
            success=True,
            message="認証成功"
        )

    return AdminLoginResponse(
        success=False,
        message="パスワードが正しくありません"
    )
