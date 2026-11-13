from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MaintenanceSchedule
from app.models.message import OutboundMessage
from app.providers.messaging import MessagingProvider
from app.services.messaging import send_logged_message

REMINDER_WINDOW_DAYS = 3


def run_maintenance_reminders(
    db: Session,
    *,
    gym_id: int,
    today: date | None = None,
    provider: MessagingProvider | None = None,
) -> list[OutboundMessage]:
    """Notify staff about scheduled maintenance due within the reminder window. Idempotent per day."""
    day = today or date.today()
    horizon = day + timedelta(days=REMINDER_WINDOW_DAYS)
    schedules = (
        db.query(MaintenanceSchedule)
        .filter(
            MaintenanceSchedule.gym_id == gym_id,
            MaintenanceSchedule.status == "scheduled",
            MaintenanceSchedule.due_on <= horizon,
        )
        .order_by(MaintenanceSchedule.due_on)
        .all()
    )
    logs: list[OutboundMessage] = []
    for schedule in schedules:
        equipment = (
            db.query(Equipment)
            .filter(Equipment.id == schedule.equipment_id, Equipment.gym_id == gym_id)
            .first()
        )
        if equipment is None:
            continue
        why = f"maintenance:{schedule.id}:{day.isoformat()}"
        already = (
            db.query(OutboundMessage)
            .filter(OutboundMessage.gym_id == gym_id, OutboundMessage.why == why)
            .first()
        )
        if already is not None:
            continue
        body = (
            f"Maintenance due: {schedule.title} for {equipment.name} "
            f"on {schedule.due_on.isoformat()}."
        )
        logs.append(
            send_logged_message(
                db,
                gym_id=gym_id,
                branch_id=schedule.branch_id,
                phone="gym-staff",
                body=body,
                kind="maintenance_reminder",
                why=why,
                provider=provider,
            )
        )
    return logs
