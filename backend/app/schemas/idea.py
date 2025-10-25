"""Idea-related schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class IdeaCreate(BaseModel):
    """Schema for creating a new idea."""

    session_id: UUID = Field(..., description="Target session ID")
    user_id: UUID = Field(..., description="Session-specific user ID")
    raw_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's raw input"
    )


class IdeaResponse(BaseModel):
    """Schema for idea data in responses."""

    id: UUID = Field(..., description="Idea ID")
    session_id: UUID = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    user_name: str = Field(..., description="User's display name")
    raw_text: str = Field(..., description="Original input")
    formatted_text: str = Field(..., description="LLM-formatted idea")
    x: float = Field(..., description="UMAP x-coordinate")
    y: float = Field(..., description="UMAP y-coordinate")
    cluster_id: int | None = Field(None, description="Assigned cluster ID")
    novelty_score: float = Field(..., description="Novelty score (0-100)")
    timestamp: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class IdeaListResponse(BaseModel):
    """Schema for idea list."""

    ideas: list[IdeaResponse] = Field(..., description="List of ideas")
    total: int = Field(..., description="Total number of ideas")
