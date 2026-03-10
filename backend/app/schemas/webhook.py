from pydantic import BaseModel
from typing import Any
from datetime import datetime


class BandwidthCallback(BaseModel):
    type: str
    time: str
    description: str | None = None
    to: str | None = None
    message: dict[str, Any] = {}

    model_config = {"extra": "allow"}


class OutboundWebhookCreate(BaseModel):
    url: str
    events: list[str]
    is_active: bool = True


class OutboundWebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime
