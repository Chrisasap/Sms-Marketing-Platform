import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Brand10DLC(Base, TimestampMixin):
    __tablename__ = "brands_10dlc"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    bandwidth_brand_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dba_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ein: Mapped[str] = mapped_column(String(20), nullable=False)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vertical: Mapped[str] = mapped_column(String(100), nullable=False)
    stock_symbol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    stock_exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vetting_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    registration_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    brand_relationship: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alt_business_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alt_business_id_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    business_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    tenant = relationship("Tenant", lazy="select")
    campaigns = relationship("Campaign10DLC", back_populates="brand", lazy="select")

    def __repr__(self) -> str:
        return f"<Brand10DLC(id={self.id}, legal_name={self.legal_name!r})>"
