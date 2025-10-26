"""Visualization and scoreboard API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.cluster import Cluster
from backend.app.models.idea import Idea
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.schemas.visualization import (
    ClusterResponse,
    IdeaVisualization,
    Point2D,
    ScoreboardEntry,
    ScoreboardResponse,
    VisualizationResponse,
)

router = APIRouter(prefix="/visualization", tags=["visualization"])


@router.get("/{session_id}", response_model=VisualizationResponse)
async def get_visualization(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> VisualizationResponse:
    """Get complete visualization data for a session."""
    # Verify session exists
    session_result = await db.execute(
        select(Session).where(Session.id == str(session_id))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all ideas
    ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == str(session_id)).order_by(Idea.timestamp)
    )
    ideas = ideas_result.scalars().all()

    # Get all users for name lookup
    users_result = await db.execute(
        select(User).where(User.session_id == str(session_id))
    )
    users = {user.user_id: user.name for user in users_result.scalars().all()}

    # Build idea visualization data
    idea_visualizations = [
        IdeaVisualization(
            id=idea.id,
            x=idea.x,
            y=idea.y,
            cluster_id=idea.cluster_id,
            novelty_score=idea.novelty_score,
            user_id=idea.user_id,
            user_name=users.get(idea.user_id, "Unknown"),
            formatted_text=idea.formatted_text,
            raw_text=idea.raw_text,
            closest_idea_id=idea.closest_idea_id,
            timestamp=idea.timestamp.isoformat(),
        )
        for idea in ideas
    ]

    # Get all clusters
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.session_id == str(session_id))
    )
    clusters = clusters_result.scalars().all()

    # Build cluster response data
    cluster_responses = [
        ClusterResponse(
            id=cluster.id,
            label=cluster.label,
            convex_hull=[Point2D(x=point[0], y=point[1]) for point in cluster.convex_hull_points],
            idea_count=cluster.idea_count,
            avg_novelty_score=cluster.avg_novelty_score,
        )
        for cluster in clusters
    ]

    return VisualizationResponse(
        ideas=idea_visualizations,
        clusters=cluster_responses,
    )


@router.get("/{session_id}/scoreboard", response_model=ScoreboardResponse)
async def get_scoreboard(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ScoreboardResponse:
    """Get scoreboard/rankings for a session."""
    # Verify session exists
    session_result = await db.execute(
        select(Session).where(Session.id == str(session_id))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all users sorted by total score
    users_result = await db.execute(
        select(User)
        .where(User.session_id == str(session_id))
        .order_by(User.total_score.desc())
    )
    users = users_result.scalars().all()

    # Build scoreboard entries
    scoreboard_entries = []
    for rank, user in enumerate(users, start=1):
        # Get user's top idea
        top_idea_result = await db.execute(
            select(Idea)
            .where(
                Idea.session_id == str(session_id),
                Idea.user_id == user.user_id
            )
            .order_by(Idea.novelty_score.desc())
            .limit(1)
        )
        top_idea = top_idea_result.scalar_one_or_none()

        top_idea_data = None
        if top_idea:
            top_idea_data = {
                "id": str(top_idea.id),
                "formatted_text": top_idea.formatted_text,
                "novelty_score": top_idea.novelty_score,
            }

        # Calculate average novelty score
        avg_novelty_score = user.total_score / user.idea_count if user.idea_count > 0 else 0.0

        scoreboard_entries.append(
            ScoreboardEntry(
                rank=rank,
                user_id=user.user_id,
                user_name=user.name,
                total_score=user.total_score,
                idea_count=user.idea_count,
                avg_novelty_score=avg_novelty_score,
                top_idea=top_idea_data,
            )
        )

    return ScoreboardResponse(rankings=scoreboard_entries)
