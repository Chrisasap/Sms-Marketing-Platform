"""Celery task for AI-powered 10DLC application review.

Analyzes brand and campaign submissions using OpenAI to score, flag issues,
and suggest improvements that maximize TCR approval rates.
"""
import json
import logging
import time
import uuid

import httpx
from celery import shared_task

from app.database import get_sync_session
from app.config import get_settings
from app.models.dlc_application import DLCApplication
from app.models.ai_review_result import AIReviewResult
from app.models.ai_review_prompt import AIReviewPrompt

logger = logging.getLogger(__name__)

# Default prompts (used if no active prompt in DB)
DEFAULT_BRAND_PROMPT = """You are a 10DLC compliance expert reviewing brand registrations for The Campaign Registry (TCR).
Your job is to evaluate brand submissions and maximize their approval probability.

Evaluate the following brand registration data:
{form_data}

Analyze for:
1. LEGAL NAME: Does it match what would appear on IRS records? Flag if informal or uses DBA-style names without proper entity suffix (LLC, Inc, Corp, etc).
2. EIN FORMAT: Is the EIN in valid XX-XXXXXXX format? Flag if missing or malformed.
3. WEBSITE: Does the domain look legitimate? Flag if no website, parked domain indicators, or mismatch with brand name.
4. VERTICAL: Is the selected vertical appropriate for the described business? Flag mismatches.
5. ENTITY TYPE: Does the entity type match the business description?
6. DESCRIPTION: Is the business description clear, professional, and specific enough for TCR review?
7. CONTACT INFO: Are phone, email, and address complete and professional?

For each issue found, provide:
- severity: "CRITICAL" (will cause rejection), "WARNING" (may cause rejection), "INFO" (could be improved)
- field: which field has the issue
- issue: what's wrong
- suggestion: exact replacement text or action to fix

Return ONLY a valid JSON object (no markdown, no code fences):
{
  "score": <0-100 integer>,
  "verdict": "LIKELY_APPROVED" or "NEEDS_CHANGES" or "HIGH_RISK",
  "issues": [{"severity": "...", "field": "...", "issue": "...", "suggestion": "..."}],
  "enhanced_fields": {"field_name": "suggested_value", ...},
  "compliance_flags": [],
  "summary": "One paragraph summary of the review"
}"""

DEFAULT_CAMPAIGN_PROMPT = """You are a 10DLC compliance expert reviewing campaign registrations for The Campaign Registry (TCR).
Your goal is to maximize approval rates while ensuring full TCPA/CTIA compliance.

Evaluate the following campaign registration data:
{form_data}

TCR APPROVAL CRITERIA (evaluate against ALL of these):

1. USE CASE MATCH: Does the description accurately match the selected use case category? TCR rejects mismatched use cases immediately.

2. SAMPLE MESSAGES (most common rejection reason):
   - Must include opt-out language like "Reply STOP to unsubscribe"
   - Must include business name/identifier
   - Must be realistic examples of what will actually be sent
   - Must match the declared use case
   - Need at minimum 2 distinct sample messages
   - Marketing messages must clearly identify as promotional

3. MESSAGE FLOW / CONSENT:
   - Must clearly describe HOW consumers opt in (web form, point of sale, text keyword, etc.)
   - Must describe WHAT consumers are opting into (type + frequency)
   - Must not imply purchased lists or shared consent
   - "Customers opt in on our website" is TOO VAGUE — needs specifics

4. OPT-OUT HANDLING:
   - STOP must be a supported keyword (minimum)
   - Should support: STOP, CANCEL, UNSUBSCRIBE, END, QUIT
   - Help keyword should return contact information

5. DESCRIPTION:
   - Must be specific about message content and purpose
   - Generic descriptions like "marketing messages" get rejected
   - Should specify frequency (e.g., "up to 4 messages per month")

6. COMPLIANCE FLAGS:
   - SHAFT content (Sex, Hate, Alcohol, Firearms, Tobacco) requires special use case
   - Loan/lending requires specific compliance language
   - Cannabis/CBD is prohibited on most carrier paths
   - Gambling requires age verification disclosure

For each issue, provide severity, field, issue description, and EXACT replacement text.
If sample messages need improvement, rewrite them to be compliant while preserving business intent.

Return ONLY a valid JSON object (no markdown, no code fences):
{
  "score": <0-100 integer>,
  "verdict": "LIKELY_APPROVED" or "NEEDS_CHANGES" or "HIGH_RISK",
  "issues": [{"severity": "...", "field": "...", "issue": "...", "suggestion": "..."}],
  "enhanced_fields": {"description": "improved", "sample_messages": ["msg1", "msg2"], ...},
  "compliance_flags": ["any SHAFT or restricted content flags"],
  "summary": "One paragraph summary"
}"""


def _get_prompt(session, prompt_type: str) -> tuple[str, str, float]:
    """Get active prompt from DB, falling back to defaults.
    Returns (system_prompt, model, temperature)."""
    prompt = session.query(AIReviewPrompt).filter(
        AIReviewPrompt.prompt_type == prompt_type,
        AIReviewPrompt.is_active == True,
    ).order_by(AIReviewPrompt.version.desc()).first()

    if prompt:
        return prompt.system_prompt, prompt.model, prompt.temperature

    defaults = {
        "brand_review": DEFAULT_BRAND_PROMPT,
        "campaign_review": DEFAULT_CAMPAIGN_PROMPT,
    }
    return defaults.get(prompt_type, DEFAULT_BRAND_PROMPT), "gpt-4o", 0.3


def _call_openai(api_key: str, system_prompt: str, model: str, temperature: float) -> tuple[str, int]:
    """Call OpenAI API synchronously. Returns (response_text, total_tokens)."""
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": "You are a 10DLC compliance expert. Always respond with valid JSON only."},
                    {"role": "user", "content": system_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


def _parse_ai_response(text: str) -> dict:
    """Parse AI response JSON, handling common formatting issues."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "score": 0,
            "verdict": "ERROR",
            "issues": [],
            "enhanced_fields": {},
            "compliance_flags": [],
            "summary": f"Failed to parse AI response: {cleaned[:200]}",
        }

    # Ensure required fields
    result.setdefault("score", 0)
    result.setdefault("verdict", "NEEDS_CHANGES")
    result.setdefault("issues", [])
    result.setdefault("enhanced_fields", {})
    result.setdefault("compliance_flags", [])
    result.setdefault("summary", "")

    # Clamp score
    result["score"] = max(0, min(100, int(result["score"])))

    return result


@shared_task(name="run_ai_dlc_review", bind=True, max_retries=2, queue="ai")
def run_ai_dlc_review(self, application_id: str):
    """Run AI review on a DLC application.

    Loads the application from DB, selects the appropriate prompt,
    calls OpenAI, parses the response, and saves the result.
    """
    settings = get_settings()
    api_key = settings.openai_api_key

    if not api_key:
        logger.warning("OpenAI API key not configured, skipping AI review for %s", application_id)
        return {"status": "skipped", "reason": "no_api_key"}

    with get_sync_session() as db:
        app = db.query(DLCApplication).filter(DLCApplication.id == uuid.UUID(application_id)).first()
        if not app:
            logger.error("DLC application %s not found", application_id)
            return {"status": "error", "reason": "not_found"}

        # Determine prompt type
        prompt_type = "brand_review" if app.application_type == "brand" else "campaign_review"
        system_prompt_template, model, temperature = _get_prompt(db, prompt_type)

        # Format prompt with application data
        form_data_str = json.dumps(app.form_data, indent=2, default=str)
        system_prompt = system_prompt_template.replace("{form_data}", form_data_str)

        start_time = time.time()
        try:
            response_text, tokens_used = _call_openai(api_key, system_prompt, model, temperature)
            latency_ms = int((time.time() - start_time) * 1000)
            parsed = _parse_ai_response(response_text)

            review = AIReviewResult(
                dlc_application_id=app.id,
                score=parsed["score"],
                verdict=parsed["verdict"],
                issues=parsed["issues"],
                enhanced_fields=parsed["enhanced_fields"],
                compliance_flags=parsed["compliance_flags"],
                summary=parsed["summary"],
                model_used=model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
            )
            db.add(review)
            db.commit()

            logger.info(
                "AI review complete for %s: score=%d, verdict=%s, %d issues",
                application_id, parsed["score"], parsed["verdict"], len(parsed["issues"]),
            )
            return {
                "status": "completed",
                "review_id": str(review.id),
                "score": parsed["score"],
                "verdict": parsed["verdict"],
            }

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"OpenAI API error: {e.response.status_code} - {e.response.text[:200]}"
            logger.error("AI review failed for %s: %s", application_id, error_msg)

            # Save error result
            review = AIReviewResult(
                dlc_application_id=app.id,
                score=0,
                verdict="ERROR",
                issues=[],
                enhanced_fields={},
                compliance_flags=[],
                summary=error_msg,
                model_used=model,
                tokens_used=0,
                latency_ms=latency_ms,
                error=error_msg,
            )
            db.add(review)
            db.commit()

            # Retry on 5xx errors
            if e.response.status_code >= 500:
                raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
            return {"status": "error", "reason": error_msg}

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.exception("AI review failed for %s", application_id)

            review = AIReviewResult(
                dlc_application_id=app.id,
                score=0,
                verdict="ERROR",
                issues=[],
                enhanced_fields={},
                compliance_flags=[],
                model_used=model,
                tokens_used=0,
                latency_ms=latency_ms,
                error=error_msg,
            )
            db.add(review)
            db.commit()

            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
