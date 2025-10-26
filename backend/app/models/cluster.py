"""Cluster model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.session import Session


class Cluster(Base):
    """
    Cluster model representing a group of similar ideas.

    Attributes:
        id: Cluster ID (integer, unique within session)
        session_id: Associated session ID
        label: LLM-generated cluster label
        convex_hull_points: JSON array of convex hull vertices [[x, y], ...]
        sample_idea_ids: JSON array of idea IDs used for label generation
        idea_count: Number of ideas in this cluster
        avg_novelty_score: Average novelty score of ideas in cluster
        updated_at: Last update timestamp
    """

    __tablename__ = "clusters"

    # Composite primary key: (session_id, cluster_id)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    convex_hull_points: Mapped[list[list[float]]] = mapped_column(
        JSON,
        nullable=False,
        comment="Convex hull vertices [[x, y], ...]",
    )
    sample_idea_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        comment="Idea IDs used for label generation",
    )
    idea_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_novelty_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="clusters")

    def __repr__(self) -> str:
        return (
            f"<Cluster(id={self.id}, session_id={self.session_id}, "
            f"label={self.label}, idea_count={self.idea_count})>"
        )
