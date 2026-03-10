import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class DLCApplication(Base, TimestampMixin):
    """Tracks 10DLC brand and campaign registration applications through the review queue.

    Workflow: draft -> pending_review -> approved -> submitted -> registered
                                      -> rejected (terminal, can resubmit)
    """
    __tablename__ = "dlc_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    # "brand" or "campaign"
    application_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Reference to the brand or campaign record
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands_10dlc.id"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns_10dlc.id"), nullable=True
    )
    # The full form data as submitted by the tenant
    form_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Workflow status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )
    # Submitted by (tenant user)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Reviewed by (superadmin)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Admin notes / rejection reason
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bandwidth response data after submission
    bandwidth_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", lazy="select")
    brand = relationship("Brand10DLC", lazy="select")
    campaign = relationship("Campaign10DLC", lazy="select")
    submitter = relationship("User", foreign_keys=[submitted_by], lazy="select")
    reviewer = relationship("User", foreign_keys=[reviewed_by], lazy="select")

    def __repr__(self) -> str:
        return f"<DLCApplication(id={self.id}, type={self.application_type}, status={self.status})>"
