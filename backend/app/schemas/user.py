"""User-related schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for user registration/session join."""

    name: str = Field(
        ...,
        min_length=1,
        description="User's display name"
    )


class UserResponse(BaseModel):
    """Schema for user data in responses."""

    id: UUID = Field(..., description="Session-specific user ID")
    user_id: UUID = Field(..., description="Global user ID")
    session_id: UUID = Field(..., description="Session ID")
    name: str = Field(..., description="Display name")
    total_score: float = Field(..., description="Cumulative novelty score")
    idea_count: int = Field(default=0, description="Number of ideas posted")
    rank: int | None = Field(default=None, description="Current rank in session")
    joined_at: datetime = Field(..., description="Join timestamp")

    model_config = {"from_attributes": True}


class UserRegister(BaseModel):
    """Schema for initial user registration (UUID generation)."""

    name: str = Field(..., min_length=1, description="User's display name")


class UserRegisterResponse(BaseModel):
    """Response for user registration."""

    user_id: UUID = Field(..., description="Generated global user ID")
    name: str = Field(..., description="Display name")
    created_at: datetime = Field(..., description="Registration timestamp")
