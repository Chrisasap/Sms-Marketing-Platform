from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class PlanInfo(BaseModel):
    tier: str
    name: str
    price: Decimal
    included_sms: int
    included_mms: int
    max_numbers: int
    max_users: int
    max_contacts: int
    max_ai_agents: int


class CreditPurchaseRequest(BaseModel):
    amount: Decimal  # dollar amount


class BillingOverview(BaseModel):
    plan_tier: str
    credit_balance: Decimal
    current_period_sms: int
    current_period_mms: int
    included_sms: int
    included_mms: int
    overage_cost: Decimal
    next_invoice_date: datetime | None


class BillingEventResponse(BaseModel):
    id: UUID
    event_type: str
    quantity: int
    unit_cost: Decimal
    total_cost: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
