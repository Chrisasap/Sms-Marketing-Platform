from pydantic import BaseModel
from typing import Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class NumberSearchRequest(BaseModel):
    area_code: str | None = None
    state: str | None = None
    city: str | None = None
    zip_code: str | None = None
    quantity: int = 10
    number_type: str = "local"  # local, toll_free


class AvailableNumber(BaseModel):
    number: str
    city: str | None
    state: str | None
    rate_center: str | None
    monthly_cost: Decimal


class NumberOrderRequest(BaseModel):
    numbers: list[str]


class NumberResponse(BaseModel):
    id: UUID
    number: str
    number_type: str
    status: str
    capabilities: list[str]
    monthly_cost: Decimal
    campaign_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
