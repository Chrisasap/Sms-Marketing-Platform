import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ContactList(Base, TimestampMixin):
    __tablename__ = "contact_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tag_color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#3b82f6"
    )
    contact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_smart: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smart_filter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="contact_lists", lazy="select")
    members = relationship(
        "ContactListMember", back_populates="contact_list", lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ContactList(id={self.id}, name={self.name!r}, count={self.contact_count})>"
