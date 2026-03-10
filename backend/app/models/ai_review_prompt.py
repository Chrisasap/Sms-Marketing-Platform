import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AIReviewPrompt(Base):
    """Stores configurable prompts for AI-powered 10DLC application review."""
    __tablename__ = "ai_review_prompts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    prompt_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # "brand_review" or "campaign_review"
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="gpt-4o")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    creator = relationship("User", lazy="select")

    def __repr__(self) -> str:
        return f"<AIReviewPrompt(id={self.id}, name={self.name!r}, type={self.prompt_type!r}, v{self.version})>"
