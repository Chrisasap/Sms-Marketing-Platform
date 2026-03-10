import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class DripSequence(Base, TimestampMixin):
    __tablename__ = "drip_sequences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="drip_sequences", lazy="select")
    steps = relationship(
        "DripStep", back_populates="sequence", lazy="select",
        order_by="DripStep.step_order",
        cascade="all, delete-orphan",
    )
    enrollments = relationship(
        "DripEnrollment", back_populates="sequence", lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DripSequence(id={self.id}, name={self.name!r}, active={self.is_active})>"


class DripStep(Base):
    __tablename__ = "drip_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drip_sequences.id"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    condition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    sequence = relationship("DripSequence", back_populates="steps", lazy="select")

    def __repr__(self) -> str:
        return f"<DripStep(id={self.id}, order={self.step_order}, delay={self.delay_minutes}m)>"


class DripEnrollment(Base):
    __tablename__ = "drip_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drip_sequences.id"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    next_step_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    sequence = relationship("DripSequence", back_populates="enrollments", lazy="select")
    contact = relationship("Contact", lazy="select")
    tenant = relationship("Tenant", lazy="select")

    def __repr__(self) -> str:
        return f"<DripEnrollment(id={self.id}, step={self.current_step}, status={self.status!r})>"
