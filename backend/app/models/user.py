"""User model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class User(Base):
    """
    User model representing a participant in a session.

    Attributes:
        id: Unique user identifier (UUID)
        session_id: Associated session ID
        user_id: Global user ID (from localStorage)
        name: User's display name
        total_score: Cumulative novelty score
        joined_at: Timestamp when user joined the session
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Global user ID from localStorage",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="users")
    ideas: Mapped[list["Idea"]] = relationship(
        "Idea",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, session_id={self.session_id})>"
