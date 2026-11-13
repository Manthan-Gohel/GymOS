from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.conversation import Conversation, InboundMessage
from app.models.core import Gym, User
from app.services.chatbot import run_chatbot
from app.services.messaging import send_logged_message

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]

# Mock provider signature for dev; real openWA service will send JSON with these fields
class InboundWebhookPayload(BaseModel):
    from_phone: str = Field(..., alias="from")
    body: str
    gym_id: int | None = None
    branch_id: int | None = None


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


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def inbound_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_gymos_signature: Annotated[str | None, Header(alias="X-GymOS-Signature")] = None,
):
    """Receive inbound WhatsApp message from openWA service (or mock).

    In production the openWA service should sign the payload; here we accept
    an optional header for future validation. Body can be raw text or JSON.
    """
    content_type = request.headers.get("content-type", "")
    payload: dict
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    from_phone = str(payload.get("from") or payload.get("From") or "").strip()
    body = str(payload.get("body") or payload.get("Body") or "").strip()
    gym_id = payload.get("gym_id")
    branch_id = payload.get("branch_id")

    if not from_phone or not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Missing 'from' or 'body'")

    if gym_id is None:
        gym = db.query(Gym).first()
        if gym is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No gym configured")
        gym_id = gym.gym_id
        branch_id = branch_id or 1

    conv = _get_or_create_conversation(db, int(gym_id), int(branch_id or 1), from_phone)

    msg = InboundMessage(
        gym_id=gym_id,
        branch_id=branch_id or 1,
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
            gym_id=gym_id,
            branch_id=branch_id or 1,
            from_phone=from_phone,
            inbound_text=body,
            conversation_id=conv.id,
        )
        # Log bot reply
        send_logged_message(
            db,
            gym_id=gym_id,
            branch_id=branch_id or 1,
            phone=from_phone,
            body=decision.reply,
            kind="chatbot_reply",
            why=f"conversation:{conv.id}",
            template_name="chatbot_reply",
        )
        conv.last_message_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
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