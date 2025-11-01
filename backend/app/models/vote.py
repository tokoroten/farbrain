"""Vote model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.idea import Idea
    from backend.app.models.user import User


class Vote(Base):
    """
    Vote model representing a user's upvote on an idea.

    Attributes:
        id: Unique vote identifier (UUID)
        idea_id: Associated idea ID
        user_id: Associated user ID
        timestamp: Creation timestamp
    """

    __tablename__ = "votes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    idea_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="votes")
    user: Mapped["User"] = relationship("User", back_populates="votes")

    # Unique constraint: one vote per user per idea
    __table_args__ = (
        Index("idx_vote_unique", "idea_id", "user_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, idea_id={self.idea_id}, user_id={self.user_id})>"
