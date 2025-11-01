"""Visualization-related schemas."""

from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class Point2D(BaseModel):
    """2D coordinate point."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class IdeaVisualization(BaseModel):
    """Schema for idea visualization data."""

    id: UUID = Field(..., description="Idea ID")
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    cluster_id: int | None = Field(None, description="Cluster ID")
    novelty_score: float = Field(..., description="Novelty score")
    user_id: UUID = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    formatted_text: str = Field(..., description="Formatted idea text")
    raw_text: str = Field(..., description="Original text")
    closest_idea_id: UUID | None = Field(None, description="ID of the closest idea at submission time")
    timestamp: str = Field(..., description="Creation timestamp (ISO format)")
    vote_count: int = Field(0, description="Number of upvotes")
    user_has_voted: bool = Field(False, description="Whether the current user has voted for this idea")


class ClusterResponse(BaseModel):
    """Schema for cluster data."""

    id: int = Field(..., description="Cluster ID")
    label: str = Field(..., description="LLM-generated label")
    convex_hull: list[Point2D] = Field(..., description="Convex hull vertices")
    idea_count: int = Field(..., description="Number of ideas in cluster")
    avg_novelty_score: float = Field(..., description="Average novelty score")


class VisualizationResponse(BaseModel):
    """Schema for complete visualization data."""

    ideas: list[IdeaVisualization] = Field(..., description="All ideas with coordinates")
    clusters: list[ClusterResponse] = Field(..., description="Cluster information")


class ScoreboardEntry(BaseModel):
    """Schema for scoreboard entry."""

    rank: int = Field(..., description="Current rank")
    user_id: UUID = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    total_score: float = Field(..., description="Total score")
    idea_count: int = Field(..., description="Number of ideas")
    avg_novelty_score: float = Field(..., description="Average score per idea")
    top_idea: dict[str, Any] | None = Field(
        None,
        description="Highest scoring idea"
    )


class ScoreboardResponse(BaseModel):
    """Schema for scoreboard."""

    rankings: list[ScoreboardEntry] = Field(..., description="Ranked users")
