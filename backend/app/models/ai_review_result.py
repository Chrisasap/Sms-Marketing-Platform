import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AIReviewResult(Base):
    """Stores AI-generated review analysis of 10DLC applications."""
    __tablename__ = "ai_review_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dlc_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dlc_applications.id"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verdict: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    issues: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    enhanced_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    compliance_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False, default="gpt-4o")
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    application = relationship("DLCApplication", lazy="select")

    def __repr__(self) -> str:
        return f"<AIReviewResult(id={self.id}, score={self.score}, verdict={self.verdict!r})>"
