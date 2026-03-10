from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class TenantCreate(BaseModel):
    name: str
    slug: str | None = None


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan_tier: str
    credit_balance: Decimal
    status: str
    settings: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    settings: dict[str, Any] | None = None
