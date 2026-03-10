from pydantic import BaseModel
from typing import Any
from datetime import datetime, time
from uuid import UUID


class CampaignCreate(BaseModel):
    name: str
    campaign_type: str = "blast"
    from_number_id: UUID | None = None
    number_pool_ids: list[UUID] = []
    message_template: str
    media_urls: list[str] = []
    target_list_ids: list[UUID] = []
    exclude_list_ids: list[UUID] = []
    segment_filter: dict[str, Any] | None = None
    scheduled_at: datetime | None = None
    send_window_start: str | None = None  # HH:MM
    send_window_end: str | None = None
    send_window_timezone: str = "America/New_York"
    throttle_mps: int | None = None
    ab_variants: list[dict[str, Any]] | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    message_template: str | None = None
    media_urls: list[str] | None = None
    scheduled_at: datetime | None = None
    status: str | None = None


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    campaign_type: str
    status: str
    from_number_id: UUID | None
    message_template: str
    media_urls: list[str]
    total_recipients: int
    sent_count: int
    delivered_count: int
    failed_count: int
    opted_out_count: int
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignStats(BaseModel):
    total_recipients: int
    sent: int
    delivered: int
    failed: int
    opted_out: int
    delivery_rate: float
    response_rate: float
    cost: float
