from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class TemplateCreate(BaseModel):
    name: str
    category: str = "custom"
    body: str
    media_urls: list[str] = []
    is_shared: bool = True


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    body: str | None = None
    media_urls: list[str] | None = None
    is_shared: bool | None = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    category: str
    body: str
    media_urls: list[str]
    is_shared: bool
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
