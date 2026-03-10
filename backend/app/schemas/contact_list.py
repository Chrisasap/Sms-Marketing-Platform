from pydantic import BaseModel
from typing import Any
from datetime import datetime
from uuid import UUID


class ListCreate(BaseModel):
    name: str
    description: str = ""
    tag_color: str = "#3b82f6"
    is_smart: bool = False
    smart_filter: dict[str, Any] | None = None


class ListUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tag_color: str | None = None
    smart_filter: dict[str, Any] | None = None


class ListResponse(BaseModel):
    id: UUID
    name: str
    description: str
    tag_color: str
    contact_count: int
    is_smart: bool
    smart_filter: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}
