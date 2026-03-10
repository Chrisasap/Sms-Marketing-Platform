import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class CampaignMessage(Base, TimestampMixin):
    __tablename__ = "campaign_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), index=True, nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    message_body: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    bandwidth_message_id: Mapped[str | None] = mapped_column(
        String(255), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_messages", lazy="select")
    contact = relationship("Contact", lazy="select")
    tenant = relationship("Tenant", lazy="select")

    def __repr__(self) -> str:
        return f"<CampaignMessage(id={self.id}, status={self.status!r})>"
