"""User management API endpoints."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.schemas.session import SessionJoin
from backend.app.schemas.user import UserRegister, UserRegisterResponse, UserResponse
from backend.app.websocket.manager import manager

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
) -> UserRegisterResponse:
    """Register a new user and generate global user_id (stored in localStorage)."""
    from datetime import datetime

    user_id = uuid4()

    return UserRegisterResponse(
        user_id=user_id,
        name=user_data.name,
        created_at=datetime.utcnow(),
    )


@router.post("/{session_id}/join", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def join_session(
    session_id: UUID,
    join_data: SessionJoin,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Join a brainstorming session."""
    # Verify session exists and is active
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status == "ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has ended"
        )

    # Verify password if session is protected
    if session.password_hash:
        if not join_data.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password required"
            )
        # TODO: Proper password hashing comparison
        if join_data.password != session.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )

    # Check if user already joined this session
    existing_user_result = await db.execute(
        select(User).where(
            User.user_id == join_data.user_id,
            User.session_id == session_id
        )
    )
    existing_user = existing_user_result.scalar_one_or_none()

    if existing_user:
        # Return existing user data
        rank_query = select(func.rank().over(order_by=User.total_score.desc())).where(
            User.session_id == session_id
        )
        rank_result = await db.execute(rank_query)
        # Simplified rank calculation
        rank = None  # TODO: Implement proper ranking

        return UserResponse(
            id=existing_user.id,
            user_id=existing_user.user_id,
            session_id=existing_user.session_id,
            name=existing_user.name,
            total_score=existing_user.total_score,
            idea_count=existing_user.idea_count,
            rank=rank,
            joined_at=existing_user.joined_at,
        )

    # Create new session-specific user
    user = User(
        user_id=join_data.user_id,
        session_id=session_id,
        name=join_data.name,
        total_score=0.0,
        idea_count=0,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Broadcast user joined via WebSocket
    await manager.send_user_joined(
        session_id=session_id,
        user_id=user.user_id,
        user_name=user.name,
    )

    return UserResponse(
        id=user.id,
        user_id=user.user_id,
        session_id=user.session_id,
        name=user.name,
        total_score=user.total_score,
        idea_count=user.idea_count,
        rank=None,
        joined_at=user.joined_at,
    )


@router.get("/{session_id}/{user_id}", response_model=UserResponse)
async def get_user(
    session_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user information in a specific session."""
    result = await db.execute(
        select(User).where(
            User.session_id == session_id,
            User.user_id == user_id
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this session"
        )

    # Calculate rank (simplified)
    all_users_result = await db.execute(
        select(User)
        .where(User.session_id == session_id)
        .order_by(User.total_score.desc())
    )
    all_users = all_users_result.scalars().all()
    rank = next((i + 1 for i, u in enumerate(all_users) if u.id == user.id), None)

    return UserResponse(
        id=user.id,
        user_id=user.user_id,
        session_id=user.session_id,
        name=user.name,
        total_score=user.total_score,
        idea_count=user.idea_count,
        rank=rank,
        joined_at=user.joined_at,
    )
