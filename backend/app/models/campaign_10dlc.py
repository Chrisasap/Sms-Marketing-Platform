import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Campaign10DLC(Base, TimestampMixin):
    __tablename__ = "campaigns_10dlc"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands_10dlc.id"), nullable=False
    )
    bandwidth_campaign_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    use_case: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sample_messages: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    subscriber_optin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    subscriber_optout: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    subscriber_help: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    number_pool: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedded_links: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    embedded_phone: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    age_gated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message_flow: Mapped[str] = mapped_column(Text, nullable=False, default="")
    help_message: Mapped[str] = mapped_column(String(320), nullable=False, default="Reply HELP for help.")
    help_keywords: Mapped[str] = mapped_column(String(255), nullable=False, default="HELP")
    optin_message: Mapped[str | None] = mapped_column(String(320), nullable=True)
    optin_keywords: Mapped[str | None] = mapped_column(String(255), nullable=True)
    optout_message: Mapped[str] = mapped_column(String(320), nullable=False, default="You have been unsubscribed. Reply START to resubscribe.")
    optout_keywords: Mapped[str] = mapped_column(String(255), nullable=False, default="STOP")
    direct_lending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    affiliate_marketing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sub_usecases: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    privacy_policy_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    terms_and_conditions_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mps_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )

    # Relationships
    tenant = relationship("Tenant", lazy="select")
    brand = relationship("Brand10DLC", back_populates="campaigns", lazy="select")

    def __repr__(self) -> str:
        return f"<Campaign10DLC(id={self.id}, use_case={self.use_case!r}, status={self.status!r})>"
