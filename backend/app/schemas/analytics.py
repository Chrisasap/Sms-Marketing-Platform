from pydantic import BaseModel
from datetime import datetime, date
from typing import Any


class DashboardStats(BaseModel):
    messages_sent_today: int
    messages_delivered_today: int
    messages_failed_today: int
    responses_today: int
    delivery_rate: float
    active_contacts: int
    active_numbers: int
    spend_today: float


class CampaignAnalytics(BaseModel):
    campaign_id: str
    name: str
    sent: int
    delivered: int
    failed: int
    opted_out: int
    responses: int
    delivery_rate: float
    response_rate: float
    click_through_rate: float
    cost: float


class VolumeDataPoint(BaseModel):
    date: date
    sent: int
    delivered: int
    failed: int


class AnalyticsResponse(BaseModel):
    dashboard: DashboardStats
    volume_chart: list[VolumeDataPoint]
    top_campaigns: list[CampaignAnalytics]
