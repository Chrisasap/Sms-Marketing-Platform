from pydantic import BaseModel
from typing import Any
from datetime import datetime
from uuid import UUID


class ConversationResponse(BaseModel):
    id: UUID
    contact_id: UUID
    contact_phone: str
    contact_name: str | None = None
    phone_number_id: UUID
    status: str
    assigned_to: UUID | None
    last_message_at: datetime | None
    unread_count: int
    tags: list[str]
    last_message_preview: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    status: str | None = None
    assigned_to: UUID | None = None
    tags: list[str] | None = None


class ReplyRequest(BaseModel):
    body: str
    media_urls: list[str] = []
