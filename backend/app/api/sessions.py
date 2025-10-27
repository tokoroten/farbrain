"""Session management API endpoints."""

import asyncio
from datetime import datetime, timedelta
from uuid import UUID
import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.db.base import get_db
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.models.idea import Idea
from backend.app.websocket.manager import manager
from backend.app.schemas.session import (
    AcceptingIdeasToggle,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from backend.app.services.starter_ideas import generate_starter_ideas
from backend.app.services.llm import get_llm_service
from backend.app.services.embedding import EmbeddingService

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _get_session_statistics(session_id: str, db: AsyncSession) -> tuple[int, int]:
    """
    Get participant and idea counts for a session.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Tuple of (participant_count, idea_count)
    """
    # Count participants
    participant_query = select(User).where(User.session_id == session_id)
    participant_result = await db.execute(participant_query)
    participant_count = len(participant_result.scalars().all())

    # Count ideas
    idea_query = select(Idea).where(Idea.session_id == session_id)
    idea_result = await db.execute(idea_query)
    idea_count = len(idea_result.scalars().all())

    return participant_count, idea_count


def _to_session_response(
    session: Session,
    participant_count: int,
    idea_count: int
) -> SessionResponse:
    """
    Convert Session model to SessionResponse.

    Args:
        session: Session model
        participant_count: Number of participants
        idea_count: Number of ideas

    Returns:
        SessionResponse object
    """
    return SessionResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        start_time=session.start_time,
        duration=session.duration,
        status=session.status,
        has_password=session.password_hash is not None,
        accepting_ideas=session.accepting_ideas,
        participant_count=participant_count,
        idea_count=idea_count,
        formatting_prompt=session.formatting_prompt,
        summarization_prompt=session.summarization_prompt,
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


async def _create_starter_ideas_bg(
    session_id: str,
    system_user_id: str,
    session_data: SessionCreate,
) -> None:
    """
    Background task wrapper to create starter ideas for a new session.

    Creates its own database session to avoid issues with closed sessions.
    """
    # Get a new database session for the background task
    async for db in get_db():
        try:
            await _create_starter_ideas(session_id, system_user_id, session_data, db)
        finally:
            await db.close()
        break  # Only need one iteration


async def _create_starter_ideas(
    session_id: str,
    system_user_id: str,
    session_data: SessionCreate,
    db: AsyncSession,
) -> None:
    """
    Create starter ideas for a new session.

    Uses McDonald's theory to seed the session with mediocre ideas
    that encourage participants to contribute better ones.
    """
    try:
        # Generate starter idea texts
        starter_texts = generate_starter_ideas(count=3)

        # Initialize services
        llm_service = get_llm_service()
        embedding_service = EmbeddingService()

        # Create each starter idea
        for raw_text in starter_texts:
            # Format idea with LLM (with session context)
            formatted_text = await llm_service.format_idea(
                raw_text,
                custom_prompt=session_data.formatting_prompt,
                session_context=session_data.description
            )

            # Generate embedding
            embedding = await embedding_service.embed(formatted_text)
            embedding_list = embedding.tolist()

            # Assign random coordinates (starter ideas always use random)
            x = float(np.random.uniform(-10, 10))
            y = float(np.random.uniform(-10, 10))

            # Create idea
            idea = Idea(
                session_id=session_id,
                user_id=system_user_id,
                raw_text=raw_text,
                formatted_text=formatted_text,
                embedding=embedding_list,
                x=x,
                y=y,
                cluster_id=None,
                novelty_score=50.0,  # Mediocre score for starter ideas
            )

            db.add(idea)

        # Update system user idea count
        result = await db.execute(
            select(User).where(User.user_id == system_user_id)
        )
        system_user = result.scalar_one_or_none()
        if system_user:
            system_user.idea_count = 3
            system_user.total_score = 150.0  # 3 ideas * 50 score

        await db.commit()

        # Broadcast new ideas via WebSocket
        ideas_result = await db.execute(
            select(Idea).where(
                Idea.session_id == session_id,
                Idea.user_id == system_user_id
            )
        )
        ideas = ideas_result.scalars().all()

        for idea in ideas:
            await manager.send_idea_created(
                session_id=session_id,
                idea_id=idea.id,
                user_id=idea.user_id,
                user_name="システム",
                formatted_text=idea.formatted_text,
                raw_text=idea.raw_text,
                x=idea.x,
                y=idea.y,
                cluster_id=idea.cluster_id,
                novelty_score=idea.novelty_score,
            )

    except Exception as e:
        # Log error but don't fail session creation
        print(f"Error creating starter ideas: {e}")


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    Create a new brainstorming session.

    Automatically seeds the session with 3 mediocre starter ideas
    using McDonald's theory - people are more willing to improve
    mediocre ideas than to start from scratch.
    """
    start_time = datetime.utcnow()
    session = Session(
        title=session_data.title,
        description=session_data.description,
        start_time=start_time,
        duration=session_data.duration,
        status="active",
        accepting_ideas=True,
        password_hash=hash_password(session_data.password) if session_data.password else None,
        formatting_prompt=session_data.formatting_prompt,
        summarization_prompt=session_data.summarization_prompt,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Create system user for starter ideas
    system_user = User(
        user_id=str(uuid.uuid4()),
        session_id=session.id,
        name="システム",
        total_score=0.0,
        idea_count=0,
    )
    db.add(system_user)
    await db.commit()
    await db.refresh(system_user)

    # Generate and add starter ideas in background
    # Note: Pass session ID and user_id, not the db session (it will be closed)
    asyncio.create_task(
        _create_starter_ideas_bg(session.id, system_user.user_id, session_data)
    )

    # Return response with initial counts (system user, no ideas yet)
    return _to_session_response(session, participant_count=1, idea_count=0)


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """List all brainstorming sessions."""
    query = select(Session)

    if active_only:
        query = query.where(Session.status == "active")

    query = query.order_by(Session.created_at.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()

    session_responses = []
    for session in sessions:
        participant_count, idea_count = await _get_session_statistics(session.id, db)
        session_responses.append(_to_session_response(session, participant_count, idea_count))

    return SessionListResponse(sessions=session_responses)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Get a specific session by ID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    participant_count, idea_count = await _get_session_statistics(session_id, db)
    return _to_session_response(session, participant_count, idea_count)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    session_update: SessionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Update session settings (admin only)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Update fields if provided
    if session_update.title is not None:
        session.title = session_update.title
    if session_update.description is not None:
        session.description = session_update.description
    if session_update.duration is not None:
        session.duration = session_update.duration
    if session_update.password is not None:
        session.password_hash = hash_password(session_update.password)
    if session_update.formatting_prompt is not None:
        session.formatting_prompt = session_update.formatting_prompt
    if session_update.summarization_prompt is not None:
        session.summarization_prompt = session_update.summarization_prompt

    await db.commit()
    await db.refresh(session)

    participant_count, idea_count = await _get_session_statistics(session_id, db)
    return _to_session_response(session, participant_count, idea_count)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """End a session early (admin only)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status == "ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already ended"
        )

    session.status = "ended"
    session.ended_at = datetime.utcnow()
    session.accepting_ideas = False

    await db.commit()
    await db.refresh(session)

    # Broadcast session status change via WebSocket
    await manager.send_session_status_changed(
        session_id=session_id,
        status="ended",
        accepting_ideas=False,
    )

    participant_count, idea_count = await _get_session_statistics(session_id, db)
    return _to_session_response(session, participant_count, idea_count)


@router.post("/{session_id}/toggle-accepting", response_model=SessionResponse)
async def toggle_accepting_ideas(
    session_id: str,
    toggle_data: AcceptingIdeasToggle,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Toggle whether session accepts new ideas (admin only)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status == "ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify ended session"
        )

    session.accepting_ideas = toggle_data.accepting_ideas

    await db.commit()
    await db.refresh(session)

    # Broadcast session status change via WebSocket
    await manager.send_session_status_changed(
        session_id=session_id,
        status=session.status,
        accepting_ideas=session.accepting_ideas,
    )

    participant_count, idea_count = await _get_session_statistics(session_id, db)
    return _to_session_response(session, participant_count, idea_count)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a session and all related data (admin only)."""
    from backend.app.models.cluster import Cluster
    from sqlalchemy import delete as sql_delete

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Delete related data in correct order (due to foreign key constraints)
    # Delete clusters
    await db.execute(
        sql_delete(Cluster).where(Cluster.session_id == session_id)
    )

    # Delete ideas
    from backend.app.models.idea import Idea
    await db.execute(
        sql_delete(Idea).where(Idea.session_id == session_id)
    )

    # Delete users
    from backend.app.models.user import User
    await db.execute(
        sql_delete(User).where(User.session_id == session_id)
    )

    # Delete session
    await db.delete(session)
    await db.commit()

    return {"message": "Session deleted successfully", "session_id": session_id}
