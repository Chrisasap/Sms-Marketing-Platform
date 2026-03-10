import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class AIAgent(Base, TimestampMixin):
    __tablename__ = "ai_agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(
        String(50), nullable=False, default="gpt-4o"
    )
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    knowledge_base: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    escalation_rules: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    conversation_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    avg_response_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="ai_agents", lazy="select")
    logs = relationship(
        "AIAgentLog", back_populates="agent", lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AIAgent(id={self.id}, name={self.name!r}, model={self.model!r})>"
