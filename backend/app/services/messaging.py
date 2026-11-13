from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.member import Member
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
