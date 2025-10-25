"""Session model."""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class SessionStatus(str, Enum):
    """Session status enum."""
    ACTIVE = "active"
    ENDED = "ended"


class Session(Base):
    """
    Session model representing a brainstorming session.

    Attributes:
        id: Unique session identifier (UUID)
        title: Session title
        description: Session purpose/description
        start_time: Session start timestamp
        duration: Session duration in seconds
        status: Session status (active/ended)
        password_hash: Hashed password for protected sessions (nullable)
        accepting_ideas: Whether session is accepting new ideas
        formatting_prompt: Custom prompt for idea formatting
        summarization_prompt: Custom prompt for cluster summarization
        created_at: Creation timestamp
        ended_at: End timestamp (nullable)
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    duration: Mapped[int] = mapped_column(Integer, nullable=False)  # seconds
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE.value,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepting_ideas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    formatting_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    summarization_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    ideas: Mapped[list["Idea"]] = relationship(
        "Idea",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    clusters: Mapped[list["Cluster"]] = relationship(
        "Cluster",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, title={self.title}, status={self.status})>"
