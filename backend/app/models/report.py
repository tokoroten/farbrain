"""Report model for storing generated reports."""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Report(Base):
    """Report model for session analysis reports."""

    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)

    # Generation status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Report data (JSON)
    cluster_insights = Column(JSON, nullable=True)  # Insights for each cluster
    overall_conclusion = Column(JSON, nullable=True)  # Overall conclusion
    personal_analyses = Column(JSON, nullable=True)  # Personal analysis for each user

    # Cached content
    markdown_content = Column(Text, nullable=True)  # Cached markdown report
    idea_count_at_generation = Column(Integer, nullable=True)  # Number of ideas when report was generated

    # File paths
    common_pdf_path = Column(String, nullable=True)
    personal_pdfs_zip_path = Column(String, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="reports")
