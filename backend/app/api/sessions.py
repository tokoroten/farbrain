"""Session management API endpoints."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.base import get_db
from backend.app.models.session import Session
from backend.app.websocket.manager import manager
from backend.app.schemas.session import (
    AcceptingIdeasToggle,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new brainstorming session."""
    start_time = datetime.utcnow()
    session = Session(
        title=session_data.title,
        description=session_data.description,
        start_time=start_time,
        duration=session_data.duration,
        status="active",
        accepting_ideas=True,
        password_hash=session_data.password,  # TODO: Hash password
        formatting_prompt=session_data.formatting_prompt,
        summarization_prompt=session_data.summarization_prompt,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        start_time=session.start_time,
        duration=session.duration,
        status=session.status,
        has_password=session.password_hash is not None,
        accepting_ideas=session.accepting_ideas,
        participant_count=0,
        idea_count=0,
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


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
        # Count participants and ideas
        from backend.app.models.user import User
        from backend.app.models.idea import Idea

        participant_query = select(User).where(User.session_id == session.id)
        participant_result = await db.execute(participant_query)
        participant_count = len(participant_result.scalars().all())

        idea_query = select(Idea).where(Idea.session_id == session.id)
        idea_result = await db.execute(idea_query)
        idea_count = len(idea_result.scalars().all())

        session_responses.append(
            SessionResponse(
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
                created_at=session.created_at,
                ended_at=session.ended_at,
            )
        )

    return SessionListResponse(sessions=session_responses)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
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

    # Count participants and ideas
    from backend.app.models.user import User
    from backend.app.models.idea import Idea

    participant_query = select(User).where(User.session_id == session_id)
    participant_result = await db.execute(participant_query)
    participant_count = len(participant_result.scalars().all())

    idea_query = select(Idea).where(Idea.session_id == session_id)
    idea_result = await db.execute(idea_query)
    idea_count = len(idea_result.scalars().all())

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
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
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
        session.password_hash = session_update.password  # TODO: Hash password
    if session_update.formatting_prompt is not None:
        session.formatting_prompt = session_update.formatting_prompt
    if session_update.summarization_prompt is not None:
        session.summarization_prompt = session_update.summarization_prompt

    await db.commit()
    await db.refresh(session)

    # Count participants and ideas
    from backend.app.models.user import User
    from backend.app.models.idea import Idea

    participant_query = select(User).where(User.session_id == session_id)
    participant_result = await db.execute(participant_query)
    participant_count = len(participant_result.scalars().all())

    idea_query = select(Idea).where(Idea.session_id == session_id)
    idea_result = await db.execute(idea_query)
    idea_count = len(idea_result.scalars().all())

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
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
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

    # Count participants and ideas
    from backend.app.models.user import User
    from backend.app.models.idea import Idea

    participant_query = select(User).where(User.session_id == session_id)
    participant_result = await db.execute(participant_query)
    participant_count = len(participant_result.scalars().all())

    idea_query = select(Idea).where(Idea.session_id == session_id)
    idea_result = await db.execute(idea_query)
    idea_count = len(idea_result.scalars().all())

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
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


@router.post("/{session_id}/toggle-accepting", response_model=SessionResponse)
async def toggle_accepting_ideas(
    session_id: UUID,
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

    # Count participants and ideas
    from backend.app.models.user import User
    from backend.app.models.idea import Idea

    participant_query = select(User).where(User.session_id == session_id)
    participant_result = await db.execute(participant_query)
    participant_count = len(participant_result.scalars().all())

    idea_query = select(Idea).where(Idea.session_id == session_id)
    idea_result = await db.execute(idea_query)
    idea_count = len(idea_result.scalars().all())

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
        created_at=session.created_at,
        ended_at=session.ended_at,
    )
