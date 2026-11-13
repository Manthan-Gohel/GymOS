from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.message import OutboundMessage
from app.models.template import MessageTemplate
from app.providers.messaging import MessagingProvider, get_messaging_provider


class OptOutError(Exception):
    """Raised when a member has not consented or has opted out of WhatsApp messages."""


def render_template(body: str, params: dict[str, Any] | None = None) -> str:
    try:
        return body.format(**(params or {}))
    except KeyError as exc:
        raise ValueError(f"missing template parameter: {exc.args[0]}") from exc


def send_template_to_member(
    db: Session,
    *,
    member: Member,
    template: MessageTemplate,
    params: dict[str, Any] | None = None,
    provider: MessagingProvider | None = None,
    why: str | None = None,
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    if not template.is_active:
        raise ValueError("template is inactive")
    if template.gym_id != member.gym_id:
        raise ValueError("template and member belong to different tenants")
    if member.whatsapp_opt_out or not member.whatsapp_consent:
        raise OptOutError("member has not consented or has opted out of WhatsApp messages")
    body = render_template(template.body, params)
    provider = provider or get_messaging_provider()
    return provider.send_message(
        to=member.phone,
        body=body,
        who=f"user:{actor_user_id}" if actor_user_id is not None else "system",
        what="template_message",
        why=why or template.category,
        template_name=template.name,
    )


def send_logged_template(
    db: Session,
    *,
    member: Member,
    template: MessageTemplate,
    params: dict[str, Any] | None = None,
    provider: MessagingProvider | None = None,
    why: str | None = None,
    actor_user_id: int | None = None,
) -> OutboundMessage:
    """Attempt a templated send and persist an audit row for every outcome."""
    who = f"user:{actor_user_id}" if actor_user_id is not None else "system"
    try:
        rendered = render_template(template.body, params)
    except ValueError as exc:
        log = OutboundMessage(
            gym_id=member.gym_id,
            branch_id=member.branch_id,
            member_id=member.id,
            phone=member.phone,
            template_name=template.name,
            body=template.body,
            kind="template_message",
            status="failed",
            provider="none",
            who=who,
            why=why or template.category,
            error=str(exc),
        )
        db.add(log)
        db.flush()
        return log

    try:
        result = send_template_to_member(
            db,
            member=member,
            template=template,
            params=params,
            provider=provider,
            why=why,
            actor_user_id=actor_user_id,
        )
    except OptOutError as exc:
        log = OutboundMessage(
            gym_id=member.gym_id,
            branch_id=member.branch_id,
            member_id=member.id,
            phone=member.phone,
            template_name=template.name,
            body=rendered,
            kind="template_message",
            status="blocked",
            provider="none",
            who=who,
            why=why or template.category,
            error=str(exc),
        )
        db.add(log)
        db.flush()
        return log
    except Exception as exc:  # provider/transport errors must be auditable, not silent
        log = OutboundMessage(
            gym_id=member.gym_id,
            branch_id=member.branch_id,
            member_id=member.id,
            phone=member.phone,
            template_name=template.name,
            body=rendered,
            kind="template_message",
            status="failed",
            provider="unknown",
            who=who,
            why=why or template.category,
            error=str(exc),
        )
        db.add(log)
        db.flush()
        return log

    log = OutboundMessage(
        gym_id=member.gym_id,
        branch_id=member.branch_id,
        member_id=member.id,
        phone=member.phone,
        template_name=template.name,
        body=result.get("body", rendered),
        kind=result.get("kind", "template_message"),
        status="sent",
        provider=result.get("provider", "unknown"),
        who=who,
        why=why or template.category,
        error=None,
    )
    db.add(log)
    db.flush()
    return log

def send_logged_message(
    db: Session,
    *,
    gym_id: int,
    branch_id: int,
    phone: str,
    body: str,
    kind: str = "internal_notice",
    why: str | None = None,
    template_name: str | None = None,
    provider: MessagingProvider | None = None,
) -> OutboundMessage:
    """Send a non-member/internal notice through the provider and log the attempt."""
    provider = provider or get_messaging_provider()
    try:
        result = provider.send_message(
            to=phone, body=body, who="system", what=kind, why=why, template_name=template_name
        )
        status_value = "sent"
        error = None
        provider_name = result.get("provider", "unknown")
    except Exception as exc:  # transport errors must be auditable, not silent
        status_value = "failed"
        error = str(exc)
        provider_name = "unknown"
    log = OutboundMessage(
        gym_id=gym_id,
        branch_id=branch_id,
        member_id=None,
        phone=phone,
        template_name=template_name,
        body=body,
        kind=kind,
        status=status_value,
        provider=provider_name,
        who="system",
        why=why,
        error=error,
    )
    db.add(log)
    db.flush()
    return log
