from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.member import Member
from app.models.membership import Membership
from app.models.message import OutboundMessage
from app.models.template import MessageTemplate
from app.providers.messaging import MessagingProvider
from app.services.messaging import send_logged_template
from app.services.payments import invoice_due_paise

EXPIRY_WINDOWS = (7, 3, 1)


def _template(db: Session, gym_id: int, name: str) -> MessageTemplate | None:
    return (
        db.query(MessageTemplate)
        .filter(
            MessageTemplate.gym_id == gym_id,
            MessageTemplate.name == name,
            MessageTemplate.is_active.is_(True),
        )
        .first()
    )


def _already_logged(db: Session, *, gym_id: int, member_id: int, why: str) -> bool:
    return (
        db.query(OutboundMessage)
        .filter(
            OutboundMessage.gym_id == gym_id,
            OutboundMessage.member_id == member_id,
            OutboundMessage.why == why,
        )
        .first()
        is not None
    )


def run_reminders(
    db: Session,
    *,
    gym_id: int,
    today: date | None = None,
    provider: MessagingProvider | None = None,
) -> list[OutboundMessage]:
    """Send due welcome/expiry/payment reminders for one tenant. Idempotent per day."""
    day = today or date.today()
    logs: list[OutboundMessage] = []

    welcome = _template(db, gym_id, "welcome")
    expiry = _template(db, gym_id, "expiry_reminder")
    payment_due = _template(db, gym_id, "payment_due")

    def member_for(membership: Membership) -> Member | None:
        return db.query(Member).filter(Member.id == membership.member_id, Member.gym_id == gym_id).first()

    if welcome is not None:
        for membership in (
            db.query(Membership)
            .filter(Membership.gym_id == gym_id, Membership.status == "active", Membership.start_date == day)
            .all()
        ):
            member = member_for(membership)
            why = f"welcome:{membership.id}:{day.isoformat()}"
            if member is None or _already_logged(db, gym_id=gym_id, member_id=member.id, why=why):
                continue
            logs.append(
                send_logged_template(
                    db, member=member, template=welcome, params={"name": member.full_name}, why=why, provider=provider
                )
            )

    if expiry is not None:
        for days in EXPIRY_WINDOWS:
            target = day + timedelta(days=days)
            for membership in (
                db.query(Membership)
                .filter(Membership.gym_id == gym_id, Membership.status == "active", Membership.end_date == target)
                .all()
            ):
                member = member_for(membership)
                why = f"expiry_{days}d:{membership.id}:{day.isoformat()}"
                if member is None or _already_logged(db, gym_id=gym_id, member_id=member.id, why=why):
                    continue
                logs.append(
                    send_logged_template(
                        db,
                        member=member,
                        template=expiry,
                        params={"name": member.full_name, "days": days, "date": target.isoformat()},
                        why=why,
                        provider=provider,
                    )
                )

    if payment_due is not None:
        invoices = (
            db.query(Invoice)
            .filter(Invoice.gym_id == gym_id, Invoice.status.in_(("issued", "partial")))
            .all()
        )
        for invoice in invoices:
            due = invoice_due_paise(db, invoice)
            if due <= 0:
                continue
            member = db.query(Member).filter(Member.id == invoice.member_id, Member.gym_id == gym_id).first()
            why = f"payment_due:{invoice.id}:{day.isoformat()}"
            if member is None or _already_logged(db, gym_id=gym_id, member_id=member.id, why=why):
                continue
            logs.append(
                send_logged_template(
                    db,
                    member=member,
                    template=payment_due,
                    params={"name": member.full_name, "amount": f"{due / 100:.2f}"},
                    why=why,
                    provider=provider,
                )
            )

    return logs

