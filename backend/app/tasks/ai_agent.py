"""Celery tasks for AI agent message processing."""
from app.celery_app import celery_app
import logging
import time

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.ai_agent.process_inbound_for_ai", bind=True, max_retries=2)
def process_inbound_for_ai(self, conversation_id: str, message_text: str, tenant_id: str):
    """Process an inbound message through the AI agent pipeline."""
    from sqlalchemy import select, update
    from app.config import get_settings
    from app.database import get_sync_session
    from app.models.ai_agent import AIAgent
    from app.models.ai_agent_log import AIAgentLog
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.phone_number import PhoneNumber
    from app.models.tenant import Tenant
    from app.models.billing_event import BillingEvent
    from app.services.message_sender import calculate_segments, calculate_cost, SMS_SEGMENT_COST, MMS_MESSAGE_COST
    import uuid
    import httpx

    settings = get_settings()

    with get_sync_session() as db:
        conversation = db.get(Conversation, uuid.UUID(conversation_id))
        if not conversation:
            return

        # Find an AI agent assigned to this phone number
        phone = db.get(PhoneNumber, conversation.phone_number_id)
        if not phone:
            return

        # Check all active AI agents for this tenant
        agents = db.execute(
            select(AIAgent).where(
                AIAgent.tenant_id == uuid.UUID(tenant_id),
                AIAgent.is_active == True,
            )
        ).scalars().all()

        agent = None
        for a in agents:
            if a.phone_number_ids and uuid.UUID(str(phone.id)) in [uuid.UUID(str(pid)) for pid in a.phone_number_ids]:
                agent = a
                break

        if not agent:
            return  # No AI agent assigned to this number

        # Build conversation context
        recent_messages = db.execute(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc()).limit(20)
        ).scalars().all()

        context_messages = []
        for msg in reversed(list(recent_messages)):
            role = "user" if msg.direction == "inbound" else "assistant"
            context_messages.append({"role": role, "content": msg.body})

        # Call AI
        start_time = time.time()
        ai_response = None
        tokens_used = 0

        try:
            if agent.model.startswith("gpt"):
                ai_response, tokens_used = _call_openai(
                    settings.openai_api_key, agent, context_messages
                )
            else:
                ai_response, tokens_used = _call_anthropic(
                    settings.anthropic_api_key, agent, context_messages
                )
        except Exception as e:
            logger.error(f"AI agent error: {e}")
            return

        latency_ms = int((time.time() - start_time) * 1000)

        if not ai_response:
            return

        # Check escalation rules
        escalated = _check_escalation(agent.escalation_rules, message_text, ai_response)

        # Log the interaction
        log = AIAgentLog(
            agent_id=agent.id,
            conversation_id=conversation.id,
            tenant_id=uuid.UUID(tenant_id),
            inbound_message=message_text,
            ai_response=ai_response,
            model_used=agent.model,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            escalated=escalated,
        )
        db.add(log)

        if escalated:
            logger.info(f"AI escalated conversation {conversation_id}")
            db.commit()
            return

        # Calculate cost for the AI response
        segments = calculate_segments(ai_response)
        is_mms = False
        cost = calculate_cost(segments, is_mms)

        # Check tenant has credits before sending
        tenant = db.get(Tenant, uuid.UUID(tenant_id))
        if tenant and tenant.plan_tier == "free_trial" and tenant.credit_balance < cost:
            logger.warning(f"Tenant {tenant_id} has insufficient credits for AI response")
            db.commit()  # commit the log entry
            return

        # Send the response via Bandwidth
        # Add a small delay to seem more natural
        time.sleep(min(agent.temperature * 5, 10))

        bw_url = f"https://messaging.bandwidth.com/api/v2/users/{settings.bandwidth_account_id}/messages"
        payload = {
            "applicationId": settings.bandwidth_application_id,
            "to": [conversation.contact_phone],
            "from": phone.number,
            "text": ai_response,
        }

        with httpx.Client(
            auth=(settings.bandwidth_api_token, settings.bandwidth_api_secret),
            timeout=30.0,
        ) as client:
            resp = client.post(bw_url, json=payload)
            bw_data = resp.json() if resp.status_code < 400 else {}

        # Deduct credits atomically after successful send
        db.execute(
            update(Tenant)
            .where(Tenant.id == uuid.UUID(tenant_id), Tenant.credit_balance >= cost)
            .values(credit_balance=Tenant.credit_balance - cost)
        )

        # Record billing event
        billing_event = BillingEvent(
            tenant_id=uuid.UUID(tenant_id),
            event_type="sms_sent",
            quantity=segments,
            unit_cost=SMS_SEGMENT_COST,
            total_cost=cost,
        )
        db.add(billing_event)

        # Record outbound message
        outbound = Message(
            conversation_id=conversation.id,
            tenant_id=uuid.UUID(tenant_id),
            direction="outbound",
            sender_type="ai_agent",
            sender_id=agent.id,
            body=ai_response,
            media_urls=[],
            bandwidth_message_id=bw_data.get("id"),
            status="sending",
            segments=segments,
        )
        db.add(outbound)

        # Update agent stats
        agent.conversation_count += 1
        total = agent.conversation_count
        agent.avg_response_time_ms = int(
            (agent.avg_response_time_ms * (total - 1) + latency_ms) / total
        )

        conversation.last_message_at = outbound.created_at
        db.commit()


def _call_openai(api_key: str, agent, messages: list[dict]) -> tuple[str, int]:
    """Call OpenAI API."""
    import httpx
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": agent.model,
                "messages": [{"role": "system", "content": agent.system_prompt}] + messages,
                "temperature": agent.temperature,
                "max_tokens": agent.max_tokens,
            },
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return content, tokens


def _call_anthropic(api_key: str, agent, messages: list[dict]) -> tuple[str, int]:
    """Call Anthropic API."""
    import httpx
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": agent.model if "claude" in agent.model else "claude-sonnet-4-20250514",
                "system": agent.system_prompt,
                "messages": messages,
                "temperature": agent.temperature,
                "max_tokens": agent.max_tokens,
            },
        )
        data = resp.json()
        content = data["content"][0]["text"]
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
        return content, tokens


def _check_escalation(rules: dict, inbound: str, response: str) -> bool:
    """Check if the conversation should be escalated to a human."""
    if not rules:
        return False
    keywords = rules.get("escalation_keywords", [])
    if any(kw.lower() in inbound.lower() for kw in keywords):
        return True
    confidence_phrases = rules.get("low_confidence_phrases", ["I'm not sure", "I don't know", "let me check"])
    if any(phrase.lower() in response.lower() for phrase in confidence_phrases):
        return True
    return False
