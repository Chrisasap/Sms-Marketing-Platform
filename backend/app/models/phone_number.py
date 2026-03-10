import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class PhoneNumber(Base, TimestampMixin):
    __tablename__ = "phone_numbers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_phone_number_tenant_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    number_type: Mapped[str] = mapped_column(String(20), nullable=False)
    bandwidth_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns_10dlc.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    capabilities: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default='["sms"]'
    )
    monthly_cost: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=0
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="phone_numbers", lazy="select")
    campaign_10dlc = relationship("Campaign10DLC", lazy="select")

    def __repr__(self) -> str:
        return f"<PhoneNumber(id={self.id}, number={self.number!r}, status={self.status!r})>"
