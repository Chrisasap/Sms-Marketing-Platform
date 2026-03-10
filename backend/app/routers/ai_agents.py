"""AI agent management router.

Provides CRUD for AI-powered conversation agents, test chat, and
interaction logs -- all tenant-scoped.
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.ai_agent import AIAgent
from app.models.ai_agent_log import AIAgentLog
from app.schemas.ai_agent import (
    AIAgentCreate,
    AIAgentUpdate,
    AIAgentResponse,
    AIAgentLogResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET / -- List AI agents
# ---------------------------------------------------------------------------

@router.get("/")
async def list_ai_agents(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all AI agents for the tenant."""
    tenant_id = user.tenant_id

    base_filter = [AIAgent.tenant_id == tenant_id]
    if is_active is not None:
        base_filter.append(AIAgent.is_active == is_active)

    count_q = select(func.count(AIAgent.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(AIAgent)
        .where(*base_filter)
        .order_by(AIAgent.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    agents = result.scalars().all()

    return {
        "agents": [
            {
                "id": str(a.id),
                "name": a.name,
                "phone_number_ids": [str(pid) for pid in (a.phone_number_ids or [])],
                "system_prompt": a.system_prompt[:200] + "..." if len(a.system_prompt) > 200 else a.system_prompt,
                "model": a.model,
                "temperature": a.temperature,
                "max_tokens": a.max_tokens,
                "is_active": a.is_active,
                "conversation_count": a.conversation_count,
                "avg_response_time_ms": a.avg_response_time_ms,
                "created_at": a.created_at.isoformat(),
            }
            for a in agents
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST / -- Create AI agent
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_ai_agent(
    body: AIAgentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Create a new AI agent with a system prompt and configuration.

    The agent starts as active and can be assigned to specific phone numbers
    to handle inbound conversations automatically.
    """
    # Check plan limits
    from app.models.tenant import Tenant

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    # Count existing agents
    agent_count_q = select(func.count(AIAgent.id)).where(
        AIAgent.tenant_id == user.tenant_id
    )
    count_result = await db.execute(agent_count_q)
    current_count = count_result.scalar() or 0

    # Plan limit check (basic enforcement)
    from app.routers.billing import PLANS

    plan = PLANS.get(tenant.plan_tier, PLANS["free_trial"]) if tenant else PLANS["free_trial"]
    if current_count >= plan["max_ai_agents"]:
        raise HTTPException(
            status_code=400,
            detail=f"Plan limit reached. Your {plan['name']} plan allows "
                   f"{plan['max_ai_agents']} AI agent(s). Upgrade to add more.",
        )

    agent = AIAgent(
        tenant_id=user.tenant_id,
        name=body.name,
        phone_number_ids=body.phone_number_ids or [],
        system_prompt=body.system_prompt,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        knowledge_base=body.knowledge_base or {},
        escalation_rules=body.escalation_rules or {},
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return {
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "phone_number_ids": [str(pid) for pid in (agent.phone_number_ids or [])],
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "knowledge_base": agent.knowledge_base,
            "escalation_rules": agent.escalation_rules,
            "is_active": agent.is_active,
            "conversation_count": agent.conversation_count,
            "avg_response_time_ms": agent.avg_response_time_ms,
            "created_at": agent.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# GET /{agent_id} -- Get agent detail
# ---------------------------------------------------------------------------

@router.get("/{agent_id}")
async def get_ai_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full AI agent details including knowledge base and escalation rules."""
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.id == agent_id,
            AIAgent.tenant_id == user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="AI agent not found")

    # Get interaction stats
    log_stats_q = select(
        func.count(AIAgentLog.id).label("total_interactions"),
        func.avg(AIAgentLog.latency_ms).label("avg_latency"),
        func.sum(AIAgentLog.tokens_used).label("total_tokens"),
        func.count(
            func.nullif(AIAgentLog.escalated, False)
        ).label("escalations"),
    ).where(AIAgentLog.agent_id == agent.id)
    stats_result = await db.execute(log_stats_q)
    stats = stats_result.one()

    total_interactions = stats.total_interactions or 0
    escalation_rate = (
        round((stats.escalations or 0) / total_interactions * 100, 2)
        if total_interactions > 0 else 0.0
    )

    return {
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "phone_number_ids": [str(pid) for pid in (agent.phone_number_ids or [])],
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "knowledge_base": agent.knowledge_base,
            "escalation_rules": agent.escalation_rules,
            "is_active": agent.is_active,
            "conversation_count": agent.conversation_count,
            "avg_response_time_ms": agent.avg_response_time_ms,
            "created_at": agent.created_at.isoformat(),
        },
        "stats": {
            "total_interactions": total_interactions,
            "avg_latency_ms": round(float(stats.avg_latency or 0), 1),
            "total_tokens_used": int(stats.total_tokens or 0),
            "escalation_count": stats.escalations or 0,
            "escalation_rate": escalation_rate,
        },
    }


# ---------------------------------------------------------------------------
# PUT /{agent_id} -- Update agent
# ---------------------------------------------------------------------------

@router.put("/{agent_id}")
async def update_ai_agent(
    agent_id: uuid.UUID,
    body: AIAgentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Update an AI agent's configuration."""
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.id == agent_id,
            AIAgent.tenant_id == user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="AI agent not found")

    if body.name is not None:
        agent.name = body.name
    if body.phone_number_ids is not None:
        agent.phone_number_ids = body.phone_number_ids
    if body.system_prompt is not None:
        agent.system_prompt = body.system_prompt
    if body.model is not None:
        agent.model = body.model
    if body.temperature is not None:
        if body.temperature < 0 or body.temperature > 2:
            raise HTTPException(
                status_code=400, detail="Temperature must be between 0 and 2"
            )
        agent.temperature = body.temperature
    if body.max_tokens is not None:
        if body.max_tokens < 1 or body.max_tokens > 4096:
            raise HTTPException(
                status_code=400, detail="max_tokens must be between 1 and 4096"
            )
        agent.max_tokens = body.max_tokens
    if body.knowledge_base is not None:
        agent.knowledge_base = body.knowledge_base
    if body.escalation_rules is not None:
        agent.escalation_rules = body.escalation_rules
    if body.is_active is not None:
        agent.is_active = body.is_active

    await db.commit()
    await db.refresh(agent)

    return {
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "phone_number_ids": [str(pid) for pid in (agent.phone_number_ids or [])],
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "knowledge_base": agent.knowledge_base,
            "escalation_rules": agent.escalation_rules,
            "is_active": agent.is_active,
            "created_at": agent.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# DELETE /{agent_id} -- Delete agent
# ---------------------------------------------------------------------------

@router.delete("/{agent_id}")
async def delete_ai_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Delete an AI agent. Logs are preserved for audit purposes."""
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.id == agent_id,
            AIAgent.tenant_id == user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="AI agent not found")

    await db.delete(agent)
    await db.commit()

    return {"message": "AI agent deleted", "id": str(agent_id)}


# ---------------------------------------------------------------------------
# POST /{agent_id}/test -- Test chat
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/test")
async def test_ai_agent(
    agent_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Send a test message to the AI agent and get a response.

    Body: ``{"message": "Hello, I need help with my order"}``

    Uses the agent's system prompt and model configuration to generate
    a response via the configured LLM provider.
    """
    result = await db.execute(
        select(AIAgent).where(
            AIAgent.id == agent_id,
            AIAgent.tenant_id == user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="AI agent not found")

    test_message = body.get("message", "").strip()
    if not test_message:
        raise HTTPException(status_code=400, detail="Message is required")

    from app.config import get_settings

    settings = get_settings()

    # Attempt to call the LLM
    import time

    start_time = time.time()
    ai_response = ""
    tokens_used = 0

    try:
        if "gpt" in agent.model or "openai" in agent.model.lower():
            # OpenAI-compatible
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": agent.model,
                        "messages": [
                            {"role": "system", "content": agent.system_prompt},
                            {"role": "user", "content": test_message},
                        ],
                        "temperature": agent.temperature,
                        "max_tokens": agent.max_tokens,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    ai_response = (
                        data["choices"][0]["message"]["content"]
                        if data.get("choices") else "No response generated"
                    )
                    tokens_used = data.get("usage", {}).get("total_tokens", 0)
                else:
                    ai_response = f"[LLM Error {resp.status_code}] Unable to generate response. Check API key and model configuration."

        elif "claude" in agent.model.lower():
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": agent.model,
                        "system": agent.system_prompt,
                        "messages": [
                            {"role": "user", "content": test_message},
                        ],
                        "max_tokens": agent.max_tokens,
                        "temperature": agent.temperature,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    ai_response = (
                        data["content"][0]["text"]
                        if data.get("content") else "No response generated"
                    )
                    usage = data.get("usage", {})
                    tokens_used = (
                        usage.get("input_tokens", 0)
                        + usage.get("output_tokens", 0)
                    )
                else:
                    ai_response = f"[LLM Error {resp.status_code}] Unable to generate response. Check API key and model configuration."
        else:
            ai_response = (
                f"[Test Mode] Model '{agent.model}' is not directly supported for test chat. "
                f"The agent would respond using the system prompt: \"{agent.system_prompt[:100]}...\""
            )

    except Exception as e:
        logger.warning("AI test chat failed: %s", e)
        ai_response = (
            f"[Test Mode] Could not reach LLM API. "
            f"Simulated response based on system prompt: \"{agent.system_prompt[:150]}...\""
        )

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "test_message": test_message,
        "ai_response": ai_response,
        "model": agent.model,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
    }


# ---------------------------------------------------------------------------
# GET /{agent_id}/logs -- Agent interaction logs
# ---------------------------------------------------------------------------

@router.get("/{agent_id}/logs")
async def list_agent_logs(
    agent_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    escalated_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List interaction logs for an AI agent.

    Optionally filter to only escalated conversations.
    """
    # Verify agent belongs to tenant
    agent_result = await db.execute(
        select(AIAgent.id).where(
            AIAgent.id == agent_id,
            AIAgent.tenant_id == user.tenant_id,
        )
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="AI agent not found")

    base_filter = [
        AIAgentLog.agent_id == agent_id,
        AIAgentLog.tenant_id == user.tenant_id,
    ]
    if escalated_only:
        base_filter.append(AIAgentLog.escalated == True)

    count_q = select(func.count(AIAgentLog.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(AIAgentLog)
        .where(*base_filter)
        .order_by(AIAgentLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "agent_id": str(log.agent_id),
                "conversation_id": str(log.conversation_id),
                "inbound_message": log.inbound_message,
                "ai_response": log.ai_response,
                "model_used": log.model_used,
                "tokens_used": log.tokens_used,
                "latency_ms": log.latency_ms,
                "escalated": log.escalated,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
