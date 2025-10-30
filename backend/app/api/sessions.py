"""Session management API endpoints."""

import asyncio
import csv
import io
from datetime import datetime, timedelta
from uuid import UUID
import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.db.base import get_db
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.models.idea import Idea
from backend.app.models.cluster import Cluster
from backend.app.websocket.manager import manager
from backend.app.schemas.session import (
    AcceptingIdeasToggle,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

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
        status=session.status,
        has_password=session.password_hash is not None,
        accepting_ideas=session.accepting_ideas,
        participant_count=participant_count,
        idea_count=idea_count,
        formatting_prompt=session.formatting_prompt,
        summarization_prompt=session.summarization_prompt,
        created_at=session.created_at,
    )


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
        status="active",
        accepting_ideas=True,
        password_hash=hash_password(session_data.password) if session_data.password else None,
        formatting_prompt=session_data.formatting_prompt,
        summarization_prompt=session_data.summarization_prompt,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Return response with initial counts (no users or ideas yet)
    return _to_session_response(session, participant_count=0, idea_count=0)


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """
    List all brainstorming sessions.

    Uses eager loading to avoid N+1 query problem when fetching
    participant and idea counts for each session.
    """
    # Build query with eager loading of users and ideas
    query = select(Session).options(
        selectinload(Session.users),
        selectinload(Session.ideas)
    )

    if active_only:
        query = query.where(Session.status == "active")

    query = query.order_by(Session.created_at.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Build responses using preloaded relationships (no additional queries)
    session_responses = []
    for session in sessions:
        participant_count = len(session.users)
        idea_count = len(session.ideas)
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
    if session_update.password is not None:
        session.password_hash = hash_password(session_update.password)
    if session_update.accepting_ideas is not None:
        session.accepting_ideas = session_update.accepting_ideas
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


@router.get("/{session_id}/export")
async def export_session_ideas(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all ideas from a session as CSV."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[CSV-EXPORT] Starting export for session {session_id}")

    try:
        # Verify session exists
        session_result = await db.execute(
            select(Session).where(Session.id == str(session_id))
        )
        session = session_result.scalar_one_or_none()

        if not session:
            logger.error(f"[CSV-EXPORT] Session {session_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Get all ideas for this session
        ideas_result = await db.execute(
            select(Idea)
            .where(Idea.session_id == str(session_id))
            .order_by(Idea.timestamp)
        )
        ideas = ideas_result.scalars().all()
        logger.info(f"[CSV-EXPORT] Found {len(ideas)} ideas")

        # Get all users for name lookup
        users_result = await db.execute(
            select(User).where(User.session_id == str(session_id))
        )
        users = {user.user_id: user.name for user in users_result.scalars().all()}
        logger.info(f"[CSV-EXPORT] Found {len(users)} users")

        # Get all clusters for label lookup
        clusters_result = await db.execute(
            select(Cluster).where(Cluster.session_id == str(session_id))
        )
        clusters = {cluster.id: cluster.label for cluster in clusters_result.scalars().all()}
        logger.info(f"[CSV-EXPORT] Found {len(clusters)} clusters")

        # Create CSV in memory with UTF-8 BOM for Excel compatibility
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'ID',
            'ユーザー名',
            'ユーザーID',
            '生テキスト',
            '整形テキスト',
            '新規性スコア',
            'クラスタID',
            'クラスタ名',
            'X座標',
            'Y座標',
            'タイムスタンプ',
            '最も近いアイディアID',
        ])

        # Write data rows
        for idea in ideas:
            writer.writerow([
                str(idea.id),
                users.get(idea.user_id, "Unknown"),
                str(idea.user_id),
                idea.raw_text,
                idea.formatted_text,
                f"{idea.novelty_score:.2f}",
                str(idea.cluster_id) if idea.cluster_id is not None else "",
                clusters.get(idea.cluster_id, "") if idea.cluster_id is not None else "",
                f"{idea.x:.4f}",
                f"{idea.y:.4f}",
                idea.timestamp.isoformat(),
                str(idea.closest_idea_id) if idea.closest_idea_id else "",
            ])

        # Prepare CSV for download
        output.seek(0)

        # Create filename with session title and timestamp
        from urllib.parse import quote

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create filename with Japanese characters supported
        filename = f"ideas_{session.title}_{timestamp}.csv"
        # URL-encode filename for Content-Disposition header (RFC 5987)
        filename_encoded = quote(filename)

        logger.info(f"[CSV-EXPORT] Successfully created CSV with {len(ideas)} rows, filename: {filename}")

        # Return response with explicit CORS headers
        # Use RFC 5987 encoding for non-ASCII filenames
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except Exception as e:
        logger.error(f"[CSV-EXPORT] Error exporting session {session_id}: {str(e)}", exc_info=True)
        raise
