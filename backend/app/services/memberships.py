from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.membership import Membership


def expire_due_memberships(db: Session, *, gym_id: int, today: date) -> int:
    """Mark active memberships with end_date < today as expired. Returns count."""
    rows = (
        db.query(Membership)
        .filter(
            Membership.gym_id == gym_id,
            Membership.status == "active",
            Membership.end_date < today,
        )
        .all()
    )
    for m in rows:
        m.status = "expired"
    return len(rows)
