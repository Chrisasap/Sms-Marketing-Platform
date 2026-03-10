import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ContactListMember(Base):
    __tablename__ = "contact_list_members"
    __table_args__ = (
        UniqueConstraint(
            "contact_id", "list_id", name="uq_contact_list_membership"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contact_lists.id"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    contact = relationship("Contact", lazy="select")
    contact_list = relationship(
        "ContactList", back_populates="members", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ContactListMember(contact_id={self.contact_id}, list_id={self.list_id})>"
