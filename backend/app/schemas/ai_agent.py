from pydantic import BaseModel
from typing import Any
from datetime import datetime
from uuid import UUID


class AIAgentCreate(BaseModel):
    name: str
    phone_number_ids: list[UUID] = []
    system_prompt: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 500
    knowledge_base: dict[str, Any] = {}
    escalation_rules: dict[str, Any] = {}


class AIAgentUpdate(BaseModel):
    name: str | None = None
    phone_number_ids: list[UUID] | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    knowledge_base: dict[str, Any] | None = None
    escalation_rules: dict[str, Any] | None = None
    is_active: bool | None = None


class AIAgentResponse(BaseModel):
    id: UUID
    name: str
    phone_number_ids: list[UUID]
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    knowledge_base: dict[str, Any]
    escalation_rules: dict[str, Any]
    is_active: bool
    conversation_count: int
    avg_response_time_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AIAgentLogResponse(BaseModel):
    id: UUID
    agent_id: UUID
    conversation_id: UUID
    inbound_message: str
    ai_response: str
    model_used: str
    tokens_used: int
    latency_ms: int
    escalated: bool
    created_at: datetime

    model_config = {"from_attributes": True}
