"""Visualization and scoreboard API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.cluster import Cluster
from backend.app.models.idea import Idea
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.models.vote import Vote
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
    user_id: UUID = Query(..., description="Current user ID to check vote status"),
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

    # Get vote counts for all ideas in this session
    vote_counts_result = await db.execute(
        select(Vote.idea_id, func.count(Vote.id).label("vote_count"))
        .where(Vote.idea_id.in_([idea.id for idea in ideas]))
        .group_by(Vote.idea_id)
    )
    vote_counts = {row[0]: row[1] for row in vote_counts_result.all()}

    # Get current user's internal user ID
    current_user_result = await db.execute(
        select(User).where(
            User.user_id == str(user_id),
            User.session_id == str(session_id)
        )
    )
    current_user = current_user_result.scalar_one_or_none()

    # Get ideas that current user has voted for
    user_voted_ideas = set()
    if current_user:
        user_votes_result = await db.execute(
            select(Vote.idea_id).where(Vote.user_id == current_user.id)
        )
        user_voted_ideas = {row[0] for row in user_votes_result.all()}

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
            vote_count=vote_counts.get(idea.id, 0),
            user_has_voted=(idea.id in user_voted_ideas),
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

    # Build scoreboard entries (only include users with at least 1 idea)
    scoreboard_entries = []
    rank = 0
    for user in users:
        # Skip users with no ideas
        if user.idea_count == 0:
            continue

        rank += 1

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
        avg_novelty_score = user.total_score / user.idea_count

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
