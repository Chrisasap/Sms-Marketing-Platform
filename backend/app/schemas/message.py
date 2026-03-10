from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class SendMessageRequest(BaseModel):
    to: str
    from_number_id: UUID | None = None
    text: str
    media_urls: list[str] = []


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID | None
    direction: str
    sender_type: str
    body: str
    media_urls: list[str]
    status: str
    error_code: str | None
    segments: int
    cost: float
    created_at: datetime

    model_config = {"from_attributes": True}
