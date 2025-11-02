"""Session model."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.idea import Idea
    from backend.app.models.cluster import Cluster
    from backend.app.models.report import Report


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
        status: Session status (active/ended)
        password_hash: Hashed password for protected sessions (nullable)
        accepting_ideas: Whether session is accepting new ideas
        formatting_prompt: Custom prompt for idea formatting
        summarization_prompt: Custom prompt for cluster summarization
        created_at: Creation timestamp
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE.value,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepting_ideas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    formatting_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    summarization_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    fixed_cluster_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enable_dialogue_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_variation_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

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
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, title={self.title}, status={self.status})>"
