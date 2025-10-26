"""Idea model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.session import Session
    from backend.app.models.user import User


class Idea(Base):
    """
    Idea model representing a user's brainstorming contribution.

    Attributes:
        id: Unique idea identifier (UUID)
        session_id: Associated session ID
        user_id: Associated user ID (session-specific)
        raw_text: Original user input
        formatted_text: LLM-formatted idea
        embedding: Vector embedding (768-dim for paraphrase-multilingual-mpnet-base-v2)
        x: UMAP x-coordinate
        y: UMAP y-coordinate
        cluster_id: Assigned cluster ID (nullable before clustering)
        novelty_score: Anomaly detection score (0-100)
        timestamp: Creation timestamp
    """

    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    formatted_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        JSON,
        nullable=False,
        comment="Vector embedding from Sentence Transformers",
    )
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    novelty_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Anomaly detection score (0-100)",
    )
    closest_idea_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="ID of the closest idea at the time of submission",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="ideas")
    user: Mapped["User"] = relationship("User", back_populates="ideas")

    def __repr__(self) -> str:
        return (
            f"<Idea(id={self.id}, formatted_text={self.formatted_text[:50]}..., "
            f"novelty_score={self.novelty_score})>"
        )
