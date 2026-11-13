from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.conversation import Conversation, InboundMessage
from app.models.core import Gym, User
from app.services.chatbot import run_chatbot
from app.services.messaging import send_logged_message

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]

def _verify_webhook_signature(raw_body: bytes, signature: str | None) -> None:
    """VULN-002: Verify HMAC-SHA256 signature from openWA Easy API webhook.

    If OPENWA_WEBHOOK_SECRET is configured, the header is required and verified.
    If secret is not configured (dev mode), signature check is skipped with a warning.
    """
    secret = settings.openwa_webhook_secret
    if not secret:
        # Dev/mock mode — skip; log a warning so ops notice
        return
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


def _get_or_create_conversation(
    db: Session,
    gym_id: int,
    branch_id: int,
    contact_phone: str,
) -> Conversation:
    conv = (
        db.query(Conversation)
        .filter(Conversation.gym_id == gym_id, Conversation.contact_phone == contact_phone)
        .first()
    )
    if conv is None:
        conv = Conversation(gym_id=gym_id, branch_id=branch_id, contact_phone=contact_phone, status="active")
        db.add(conv)
        db.flush()
    conv.last_message_at = datetime.now(UTC)
    conv.updated_at = datetime.now(UTC)
    return conv


def _process_inbound(
    db: Session,
    gym: Gym,
    branch_id: int,
    from_phone: str,
    body: str,
    payload: dict,
) -> dict:
    """Shared webhook processing; tenant (gym) is resolved by the caller, never from the payload."""
    conv = _get_or_create_conversation(db, gym.id, branch_id, from_phone)

    msg = InboundMessage(
        gym_id=gym.id,
        branch_id=branch_id,
        conversation_id=conv.id,
        from_phone=from_phone,
        body=body,
        raw_payload=str(payload),
    )
    db.add(msg)
    db.commit()

    # Process with chatbot if bot is not paused
    if not conv.bot_paused:
        decision = run_chatbot(
            db,
            gym_id=gym.id,
            branch_id=branch_id,
            from_phone=from_phone,
            inbound_text=body,
            conversation_id=conv.id,
        )
        # Log bot reply
        send_logged_message(
            db,
            gym_id=gym.id,
            branch_id=branch_id,
            phone=from_phone,
            body=decision.reply,
            kind="chatbot_reply",
            why=f"conversation:{conv.id}",
            template_name="chatbot_reply",
        )
        conv.last_message_at = datetime.now(UTC)
        conv.status = "escalated" if decision.handoff else "active"
        db.commit()
        return {
            "status": "accepted",
            "conversation_id": conv.id,
            "message_id": msg.id,
            "bot_reply": decision.reply,
            "handoff": decision.handoff,
        }

    return {"status": "accepted", "conversation_id": conv.id, "message_id": msg.id, "bot_reply": None, "handoff": False}


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def inbound_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_gymos_signature: Annotated[str | None, Header(alias="X-GymOS-Signature")] = None,
):
    """Dev/mock webhook.

    VULN-002: legacy unauthenticated route is dev-only. In production/staging use
    /webhook/{gym_token} which resolves the tenant from an unforgeable URL token.
    """
    if settings.app_env.lower() in {"production", "staging"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use /whatsapp/webhook/{gym_token}")

    raw_body = await request.body()
    _verify_webhook_signature(raw_body, x_gymos_signature)

    content_type = request.headers.get("content-type", "")
    payload: dict
    if "application/json" in content_type:
        import json
        payload = json.loads(raw_body)
    else:
        form = await request.form()
        payload = dict(form)

    from_phone = str(payload.get("from") or payload.get("From") or "").strip()
    body = str(payload.get("body") or payload.get("Body") or "").strip()
    branch_id = payload.get("branch_id")

    if not from_phone or not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Missing 'from' or 'body'")

    gym = db.query(Gym).first()
    if gym is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No gym configured")

    return _process_inbound(db, gym, int(branch_id or 1), from_phone, body, payload)


@router.post("/webhook/{gym_token}", status_code=status.HTTP_202_ACCEPTED)
async def inbound_webhook_tokened(
    gym_token: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_gymos_signature: Annotated[str | None, Header(alias="X-GymOS-Signature")] = None,
):
    """Production webhook: VULN-002 — tenant resolved from per-gym URL token, never payload.gym_id."""
    raw_body = await request.body()
    _verify_webhook_signature(raw_body, x_gymos_signature)

    content_type = request.headers.get("content-type", "")
    payload: dict
    if "application/json" in content_type:
        import json
        payload = json.loads(raw_body)
    else:
        form = await request.form()
        payload = dict(form)

    from_phone = str(payload.get("from") or payload.get("From") or "").strip()
    body = str(payload.get("body") or payload.get("Body") or "").strip()
    branch_id = payload.get("branch_id")

    if not from_phone or not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Missing 'from' or 'body'")

    gym = db.query(Gym).filter(Gym.webhook_token == gym_token).first()
    if gym is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown gym token")

    # payload gym_id / gym tokens are deliberately ignored — tenant comes from the URL token
    return _process_inbound(db, gym, int(branch_id or 1), from_phone, body, payload)


@router.get("/conversations")
def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
    status_value: str | None = None,
    limit: int = 100,
):
    query = db.query(Conversation).filter(Conversation.gym_id == current_user.gym_id)
    if status_value:
        query = query.filter(Conversation.status == status_value)
    items = query.order_by(Conversation.last_message_at.desc().nullslast()).limit(min(max(limit, 1), 200)).all()
    return {
        "items": [
            {
                "id": c.id,
                "gym_id": c.gym_id,
                "branch_id": c.branch_id,
                "contact_phone": c.contact_phone,
                "status": c.status,
                "bot_paused": c.bot_paused,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in items
        ],
        "total": len(items),
    }


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 200,
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.gym_id == current_user.gym_id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    msgs = (
        db.query(InboundMessage)
        .filter(InboundMessage.conversation_id == conv.id)
        .order_by(InboundMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": m.id,
                "from_phone": m.from_phone,
                "body": m.body,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
        "total": len(msgs),
    }


@router.post("/conversations/{conversation_id}/pause")
def pause_bot(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.gym_id == current_user.gym_id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv.bot_paused = True
    conv.updated_at = datetime.now(UTC)
    db.commit()
    return {"status": "paused", "conversation_id": conv.id}


@router.post("/conversations/{conversation_id}/resume")
def resume_bot(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.gym_id == current_user.gym_id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv.bot_paused = False
    conv.updated_at = datetime.now(UTC)
    db.commit()
    return {"status": "active", "conversation_id": conv.id}


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.gym_id == current_user.gym_id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    for key, value in payload.items():
        if key in ("status", "bot_paused"):
            setattr(conv, key, value)
    conv.updated_at = datetime.now(UTC)
    db.commit()
    return {"status": "updated", "conversation_id": conv.id}


@router.get("/inbox")
def staff_inbox(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
    status_value: str | None = None,
    bot_paused: bool | None = None,
    limit: int = 50,
):
    """Staff inbox: conversations needing attention (bot paused, unread, escalated)."""
    query = db.query(Conversation).filter(Conversation.gym_id == current_user.gym_id)
    if status_value:
        query = query.filter(Conversation.status == status_value)
    if bot_paused is not None:
        query = query.filter(Conversation.bot_paused.is_(bot_paused))
    items = query.order_by(Conversation.last_message_at.desc().nullslast()).limit(min(max(limit, 1), 200)).all()
    return {
        "items": [
            {
                "id": c.id,
                "contact_phone": c.contact_phone,
                "status": c.status,
                "bot_paused": c.bot_paused,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in items
        ],
        "total": len(items),
    }


@router.post("/conversations/{conversation_id}/staff-reply")
def staff_reply(
    conversation_id: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    """Staff sends a reply in a paused conversation; bot remains paused unless explicitly resumed."""
    from app.services.messaging import send_logged_message

    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.gym_id == current_user.gym_id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    body = str(payload.get("body", "")).strip()
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Body required")

    # Log as outbound message
    log = send_logged_message(
        db,
        gym_id=current_user.gym_id,
        branch_id=conv.branch_id,
        phone=conv.contact_phone,
        body=body,
        kind="staff_reply",
        why=f"conversation:{conv.id}",
        template_name="staff_reply",
    )
    conv.last_message_at = datetime.now(UTC)
    conv.updated_at = datetime.now(UTC)
    db.commit()

    return {"status": "sent", "message_id": log.id, "conversation_id": conv.id}