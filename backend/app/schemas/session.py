"""Session-related schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Schema for creating a new session."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Session title"
    )
    description: str | None = Field(
        default=None,
        description="Session purpose/description"
    )
    duration: int | None = Field(
        default=7200,
        ge=60,
        le=31536000,  # 1 year maximum
        description="Session duration in seconds (None for unlimited)"
    )
    password: str | None = Field(
        default=None,
        description="Optional password for session protection"
    )
    formatting_prompt: str | None = Field(
        default=None,
        max_length=2000,
        description="Custom prompt for idea formatting"
    )
    summarization_prompt: str | None = Field(
        default=None,
        max_length=2000,
        description="Custom prompt for cluster summarization"
    )


class SessionUpdate(BaseModel):
    """Schema for updating session."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration: int | None = Field(default=None, ge=60, le=31536000)  # Up to 1 year
    password: str | None = None
    formatting_prompt: str | None = Field(default=None, max_length=2000)
    summarization_prompt: str | None = Field(default=None, max_length=2000)


class SessionResponse(BaseModel):
    """Schema for session data in responses."""

    id: UUID = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    description: str | None = Field(None, description="Session description")
    start_time: datetime = Field(..., description="Start timestamp")
    duration: int = Field(..., description="Duration in seconds")
    status: str = Field(..., description="Session status (active/ended)")
    has_password: bool = Field(..., description="Whether session is password-protected")
    accepting_ideas: bool = Field(..., description="Whether accepting new ideas")
    participant_count: int = Field(default=0, description="Number of participants")
    idea_count: int = Field(default=0, description="Number of ideas")
    formatting_prompt: str | None = Field(None, description="Custom formatting prompt")
    summarization_prompt: str | None = Field(None, description="Custom summarization prompt")
    created_at: datetime = Field(..., description="Creation timestamp")
    ended_at: datetime | None = Field(None, description="End timestamp")

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """Schema for session list."""

    sessions: list[SessionResponse] = Field(..., description="List of sessions")


class SessionJoin(BaseModel):
    """Schema for joining a session."""

    user_id: UUID = Field(..., description="Global user ID")
    name: str = Field(..., min_length=1, description="Display name")
    password: str | None = Field(default=None, description="Session password if protected")


class AcceptingIdeasToggle(BaseModel):
    """Schema for toggling idea acceptance."""

    accepting_ideas: bool = Field(..., description="New acceptance state")
