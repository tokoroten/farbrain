"""Vote API endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.vote import Vote
from backend.app.models.idea import Idea
from backend.app.models.user import User
from backend.app.api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ideas", tags=["votes"])


@router.post("/{idea_id}/vote", status_code=status.HTTP_201_CREATED)
async def vote_idea(
    idea_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Upvote an idea.

    If the user has already voted, this endpoint returns success (idempotent).
    """
    try:
        # Check if idea exists
        idea_result = await db.execute(
            select(Idea).where(Idea.id == str(idea_id))
        )
        idea = idea_result.scalar_one_or_none()
        if not idea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found"
            )

        # Check if user exists in this session
        user_result = await db.execute(
            select(User).where(
                User.user_id == str(user_id),
                User.session_id == idea.session_id
            )
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this session"
            )

        # Check if vote already exists
        vote_result = await db.execute(
            select(Vote).where(
                Vote.idea_id == str(idea_id),
                Vote.user_id == user.id
            )
        )
        existing_vote = vote_result.scalar_one_or_none()

        if existing_vote:
            # Already voted, return success (idempotent)
            return {"message": "Already voted", "vote_id": existing_vote.id}

        # Create new vote
        new_vote = Vote(
            idea_id=str(idea_id),
            user_id=user.id
        )
        db.add(new_vote)
        await db.commit()
        await db.refresh(new_vote)

        logger.info(f"[VOTE] User {user_id} voted for idea {idea_id}")

        # Broadcast vote update via WebSocket
        await manager.broadcast_to_session(
            idea.session_id,
            {
                "type": "vote_added",
                "idea_id": str(idea_id),
                "user_id": str(user_id),
                "vote_id": new_vote.id,
            }
        )

        return {"message": "Vote recorded", "vote_id": new_vote.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VOTE] Error voting for idea: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to vote for idea"
        )


@router.delete("/{idea_id}/vote", status_code=status.HTTP_200_OK)
async def unvote_idea(
    idea_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove upvote from an idea.

    If the user has not voted, this endpoint returns success (idempotent).
    """
    try:
        # Check if idea exists
        idea_result = await db.execute(
            select(Idea).where(Idea.id == str(idea_id))
        )
        idea = idea_result.scalar_one_or_none()
        if not idea:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Idea not found"
            )

        # Check if user exists in this session
        user_result = await db.execute(
            select(User).where(
                User.user_id == str(user_id),
                User.session_id == idea.session_id
            )
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this session"
            )

        # Delete vote if exists
        result = await db.execute(
            delete(Vote).where(
                Vote.idea_id == str(idea_id),
                Vote.user_id == user.id
            )
        )
        await db.commit()

        if result.rowcount == 0:
            # No vote found, return success (idempotent)
            return {"message": "No vote to remove"}

        logger.info(f"[UNVOTE] User {user_id} removed vote from idea {idea_id}")

        # Broadcast vote update via WebSocket
        await manager.broadcast_to_session(
            idea.session_id,
            {
                "type": "vote_removed",
                "idea_id": str(idea_id),
                "user_id": str(user_id),
            }
        )

        return {"message": "Vote removed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UNVOTE] Error removing vote: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove vote"
        )
