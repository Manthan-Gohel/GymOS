from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.conversation import Conversation, InboundMessage
from app.models.core import User
from app.models.message import OutboundMessage

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]


class RateLimitConfig(BaseModel):
    window_seconds: int = Field(default=60, ge=1)
    max_messages: int = Field(default=10, ge=1)


# In-memory rate limit store (for dev/tests; replace with Redis in production)
_rate_limit_store: dict[str, list[float]] = {}


_DEFAULT_RATE_LIMIT_CONFIG = RateLimitConfig()


def check_rate_limit(phone: str, config: RateLimitConfig = _DEFAULT_RATE_LIMIT_CONFIG) -> tuple[bool, int]:
    """Check if phone has exceeded rate limit. Returns (allowed, remaining)."""
    now = datetime.now(UTC).timestamp()
    window_start = now - config.window_seconds

    if phone not in _rate_limit_store:
        _rate_limit_store[phone] = []

    # Clean old entries
    _rate_limit_store[phone] = [ts for ts in _rate_limit_store[phone] if ts > window_start]

    if len(_rate_limit_store[phone]) >= config.max_messages:
        return False, 0

    _rate_limit_store[phone].append(now)
    return True, config.max_messages - len(_rate_limit_store[phone])


def clear_rate_limit(phone: str) -> None:
    """Clear rate limit for a phone (e.g., after staff intervention)."""
    _rate_limit_store.pop(phone, None)


@router.get("/conversations/{conversation_id}/audit")
def conversation_audit(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    """Full audit trail for a conversation: inbound, outbound, handoffs, bot pauses."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.gym_id == current_user.gym_id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    inbound = (
        db.query(InboundMessage)
        .filter(InboundMessage.conversation_id == conv.id)
        .order_by(InboundMessage.created_at.asc())
        .all()
    )

    outbound = (
        db.query(OutboundMessage)
        .filter(OutboundMessage.gym_id == current_user.gym_id)
        .filter(OutboundMessage.why.like(f"%conversation:{conv.id}%"))
        .order_by(OutboundMessage.created_at.asc())
        .all()
    )

    events: list[dict[str, Any]] = []
    for im in inbound:
        events.append({
            "type": "inbound",
            "timestamp": im.created_at.isoformat(),
            "from_phone": im.from_phone,
            "body": im.body,
            "raw_payload": im.raw_payload,
        })
    for om in outbound:
        events.append({
            "type": "outbound",
            "timestamp": om.created_at.isoformat(),
            "to_phone": om.phone,
            "body": om.body,
            "kind": om.kind,
            "template_name": om.template_name,
            "provider": om.provider,
            "who": om.who,
            "why": om.why,
            "status": om.status,
            "error": om.error,
        })

    events.sort(key=lambda e: e.get("timestamp", ""))

    return {
        "conversation_id": conv.id,
        "contact_phone": conv.contact_phone,
        "status": conv.status,
        "bot_paused": conv.bot_paused,
        "created_at": conv.created_at.isoformat(),
        "events": events,
    }


@router.get("/rate-limits/{phone}")
def get_rate_limit_status(
    phone: str,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
    window_seconds: int = 60,
    max_messages: int = 10,
):
    """Get current rate limit status for a phone number."""
    config = RateLimitConfig(window_seconds=window_seconds, max_messages=max_messages)
    allowed, remaining = check_rate_limit(phone, config)
    return {
        "phone": phone,
        "allowed": allowed,
        "remaining": remaining,
        "window_seconds": config.window_seconds,
        "max_messages": config.max_messages,
    }


@router.post("/rate-limits/{phone}/reset")
def reset_rate_limit(
    phone: str,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    """Reset rate limit for a phone number."""
    clear_rate_limit(phone)
    return {"status": "cleared", "phone": phone}


@router.get("/guardrails/test")
def test_guardrails(
    text: str,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    """Test guardrail detection on arbitrary text (admin tool)."""
    from app.services.chatbot import HANDOFF_KEYWORDS, _detect_intent, _should_handoff

    handoff, reason = _should_handoff(text)
    intents = _detect_intent(text)
    return {
        "text": text,
        "handoff_triggered": handoff,
        "reason": reason,
        "intents": intents,
        "guardrail_keywords": HANDOFF_KEYWORDS,
    }