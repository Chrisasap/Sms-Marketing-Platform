import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class AutoReply(Base, TimestampMixin):
    __tablename__ = "auto_replies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    phone_number_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("phone_numbers.id"), nullable=True
    )
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    tenant = relationship("Tenant", back_populates="auto_replies", lazy="select")
    phone_number = relationship("PhoneNumber", lazy="select")

    def __repr__(self) -> str:
        return f"<AutoReply(id={self.id}, trigger_type={self.trigger_type!r})>"
