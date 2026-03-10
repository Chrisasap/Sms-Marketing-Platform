from pydantic import BaseModel
from typing import Any
from datetime import datetime
from uuid import UUID


class AutoReplyCreate(BaseModel):
    phone_number_id: UUID | None = None
    trigger_type: str
    trigger_value: str | None = None
    response_body: str
    media_urls: list[str] = []
    is_active: bool = True
    priority: int = 0


class AutoReplyUpdate(BaseModel):
    trigger_type: str | None = None
    trigger_value: str | None = None
    response_body: str | None = None
    media_urls: list[str] | None = None
    is_active: bool | None = None
    priority: int | None = None


class AutoReplyResponse(BaseModel):
    id: UUID
    phone_number_id: UUID | None
    trigger_type: str
    trigger_value: str | None
    response_body: str
    media_urls: list[str]
    is_active: bool
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DripSequenceCreate(BaseModel):
    name: str
    trigger_event: str
    steps: list["DripStepCreate"] = []


class DripStepCreate(BaseModel):
    step_order: int
    delay_minutes: int
    message_template: str
    media_urls: list[str] = []
    condition: dict[str, Any] | None = None


class DripSequenceResponse(BaseModel):
    id: UUID
    name: str
    trigger_event: str
    is_active: bool
    steps: list["DripStepResponse"] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class DripStepResponse(BaseModel):
    id: UUID
    step_order: int
    delay_minutes: int
    message_template: str
    media_urls: list[str]
    condition: dict[str, Any] | None

    model_config = {"from_attributes": True}
