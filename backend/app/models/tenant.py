import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", use_alter=True, name="fk_tenant_owner_user"),
        nullable=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    stripe_subscription_item_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    plan_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free_trial"
    )
    credit_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=0
    )
    bandwidth_site_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bandwidth_location_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    bandwidth_application_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )

    # Relationships
    users = relationship(
        "User", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan", foreign_keys="[User.tenant_id]",
    )
    phone_numbers = relationship(
        "PhoneNumber", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    contacts = relationship(
        "Contact", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    campaigns = relationship(
        "Campaign", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    contact_lists = relationship(
        "ContactList", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    ai_agents = relationship(
        "AIAgent", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    drip_sequences = relationship(
        "DripSequence", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    templates = relationship(
        "Template", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    auto_replies = relationship(
        "AutoReply", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    api_keys = relationship(
        "ApiKey", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name!r}, slug={self.slug!r})>"
