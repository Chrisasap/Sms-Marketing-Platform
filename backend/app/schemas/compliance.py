"""Schemas for 10DLC brand/campaign registration with full TCR/Bandwidth field coverage."""

from pydantic import BaseModel, Field, field_validator
from typing import Any
from datetime import datetime
from uuid import UUID


# ---------------------------------------------------------------------------
# Enums / Constants (for validation)
# ---------------------------------------------------------------------------

ENTITY_TYPES = {
    "PRIVATE_PROFIT", "PUBLIC_PROFIT", "NON_PROFIT", "GOVERNMENT", "SOLE_PROPRIETOR"
}

VERTICALS = {
    "PROFESSIONAL", "REAL_ESTATE", "HEALTHCARE", "HUMAN_RESOURCES", "ENERGY",
    "ENTERTAINMENT", "RETAIL", "TRANSPORTATION", "AGRICULTURE", "INSURANCE",
    "POSTAL", "EDUCATION", "HOSPITALITY", "FINANCIAL", "POLITICAL", "GAMBLING",
    "LEGAL", "CONSTRUCTION", "NGO", "MANUFACTURING", "GOVERNMENT", "TECHNOLOGY",
    "COMMUNICATION",
}

BRAND_RELATIONSHIPS = {
    "BASIC_ACCOUNT", "SMALL_ACCOUNT", "MEDIUM_ACCOUNT", "LARGE_ACCOUNT", "KEY_ACCOUNT"
}

STOCK_EXCHANGES = {
    "NASDAQ", "NYSE", "AMEX", "AMX", "ASX", "B3", "BME", "BSE", "FRA",
    "ICEX", "JPX", "JSE", "KRX", "LON", "NSE", "OMX", "SEHK", "SGX",
    "SSE", "STO", "SWX", "SZSE", "TSX", "TWSE", "VSE", "OTHER",
}

USE_CASES = {
    "2FA", "ACCOUNT_NOTIFICATION", "CUSTOMER_CARE", "DELIVERY_NOTIFICATION",
    "FRAUD_ALERT", "HIGHER_EDUCATION", "LOW_VOLUME", "MARKETING", "MIXED",
    "POLLING_VOTING", "PUBLIC_SERVICE_ANNOUNCEMENT", "SECURITY_ALERT", "STARTER",
    "CHARITY", "EMERGENCY", "POLITICAL", "SWEEPSTAKE", "PROXY",
    "AGENTS_FRANCHISES", "CARRIER_EXEMPT", "SOCIAL",
}

SUB_USECASES = {
    "2FA", "ACCOUNT_NOTIFICATION", "CUSTOMER_CARE", "DELIVERY_NOTIFICATION",
    "FRAUD_ALERT", "HIGHER_EDUCATION", "MARKETING", "POLLING_VOTING",
    "PUBLIC_SERVICE_ANNOUNCEMENT", "SECURITY_ALERT",
}

ALT_BUSINESS_ID_TYPES = {"NONE", "DUNS", "GIIN", "LEI"}


# ---------------------------------------------------------------------------
# Brand Schemas
# ---------------------------------------------------------------------------

class BrandCreate(BaseModel):
    """Full brand registration form matching TCR/Bandwidth requirements."""
    entity_type: str = Field(..., description="PRIVATE_PROFIT, PUBLIC_PROFIT, NON_PROFIT, GOVERNMENT, SOLE_PROPRIETOR")
    legal_name: str = Field(..., min_length=1, max_length=255)
    dba_name: str | None = Field(None, max_length=255, description="Display/DBA name")
    ein: str = Field(..., max_length=21, description="9-digit EIN (XX-XXXXXXX)")
    phone: str = Field(..., max_length=20, description="E.164 support contact phone")
    email: str = Field(..., max_length=100, description="Support contact email")
    street: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=20, description="2-letter US state code")
    zip_code: str = Field(..., max_length=10)
    country: str = Field("US", max_length=2)
    website: str | None = Field(None, max_length=255)
    vertical: str = Field(..., description="Business vertical from TCR list")
    brand_relationship: str | None = Field(None, description="Account size: BASIC_ACCOUNT through KEY_ACCOUNT")
    is_main: bool = Field(True, description="True=your brand, False=customer's brand")
    stock_symbol: str | None = Field(None, max_length=10)
    stock_exchange: str | None = Field(None, max_length=20)
    business_contact_email: str | None = Field(None, max_length=255)
    alt_business_id: str | None = Field(None, max_length=50)
    alt_business_id_type: str | None = Field(None, description="NONE, DUNS, GIIN, LEI")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of: {', '.join(sorted(ENTITY_TYPES))}")
        return v

    @field_validator("vertical")
    @classmethod
    def validate_vertical(cls, v: str) -> str:
        if v not in VERTICALS:
            raise ValueError(f"vertical must be one of: {', '.join(sorted(VERTICALS))}")
        return v

    @field_validator("ein")
    @classmethod
    def validate_ein(cls, v: str) -> str:
        clean = v.replace("-", "")
        if not clean.isdigit() or len(clean) != 9:
            raise ValueError("EIN must be 9 digits (XX-XXXXXXX)")
        return v


class BrandResponse(BaseModel):
    id: UUID
    bandwidth_brand_id: str | None
    entity_type: str
    legal_name: str
    dba_name: str | None
    ein: str
    phone: str
    email: str
    vertical: str
    brand_relationship: str | None
    trust_score: int | None
    identity_status: str | None
    vetting_status: str
    registration_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Campaign Schemas
# ---------------------------------------------------------------------------

class CampaignRegistrationCreate(BaseModel):
    """Full campaign registration form matching TCR/Bandwidth requirements."""
    brand_id: UUID
    use_case: str = Field(..., description="Campaign use case type")
    sub_usecases: list[str] | None = Field(None, description="Required for MIXED, LOW_VOLUME, STARTER (2-5 items)")
    description: str = Field(..., min_length=40, max_length=4096, description="Campaign purpose (min 40 chars)")
    message_flow: str = Field(..., min_length=40, max_length=2048, description="How subscribers opt in (min 40 chars)")
    sample_messages: list[str] = Field(..., min_length=1, max_length=5, description="1-5 sample messages (each min 20 chars)")
    help_message: str = Field(..., min_length=20, max_length=320, description="Response to HELP keyword")
    help_keywords: str = Field("HELP", max_length=255)
    optin_message: str | None = Field(None, max_length=320)
    optin_keywords: str | None = Field(None, max_length=255)
    optout_message: str = Field(..., min_length=20, max_length=320, description="Response to STOP keyword")
    optout_keywords: str = Field("STOP", max_length=255)
    subscriber_optin: bool = True
    subscriber_optout: bool = True
    subscriber_help: bool = True
    number_pool: bool = False
    direct_lending: bool = False
    embedded_links: bool = False
    embedded_phone: bool = False
    affiliate_marketing: bool = False
    age_gated: bool = False
    auto_renewal: bool = True
    privacy_policy_link: str | None = Field(None, max_length=255)
    terms_and_conditions_link: str | None = Field(None, max_length=255)

    @field_validator("use_case")
    @classmethod
    def validate_use_case(cls, v: str) -> str:
        if v not in USE_CASES:
            raise ValueError(f"use_case must be one of: {', '.join(sorted(USE_CASES))}")
        return v

    @field_validator("sample_messages")
    @classmethod
    def validate_samples(cls, v: list[str]) -> list[str]:
        for i, msg in enumerate(v):
            if len(msg) < 20:
                raise ValueError(f"Sample message {i+1} must be at least 20 characters")
            if len(msg) > 1024:
                raise ValueError(f"Sample message {i+1} must be at most 1024 characters")
        return v


class CampaignRegistrationResponse(BaseModel):
    id: UUID
    brand_id: UUID
    bandwidth_campaign_id: str | None
    use_case: str
    description: str
    message_flow: str
    help_message: str
    optout_message: str
    sub_usecases: list[str] | None
    mps_limit: int
    daily_limit: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# DLC Application (review queue) Schemas
# ---------------------------------------------------------------------------

class DLCApplicationSubmit(BaseModel):
    """Submit a brand or campaign for admin review."""
    application_type: str = Field(..., description="'brand' or 'campaign'")
    form_data: dict = Field(..., description="Full registration form data")

    @field_validator("application_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("brand", "campaign"):
            raise ValueError("application_type must be 'brand' or 'campaign'")
        return v


class DLCApplicationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    application_type: str
    brand_id: UUID | None
    campaign_id: UUID | None
    form_data: dict
    status: str
    submitted_by: UUID | None
    submitted_at: datetime | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    admin_notes: str | None
    rejection_reason: str | None
    bandwidth_response: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DLCReviewAction(BaseModel):
    """Admin action on a DLC application."""
    action: str = Field(..., description="'approve' or 'reject'")
    admin_notes: str | None = None
    rejection_reason: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v
