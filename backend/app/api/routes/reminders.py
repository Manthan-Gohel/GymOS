from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services.reminders import run_reminders

router = APIRouter(prefix="/reminders", tags=["reminders"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]


class ReminderRunRequest(BaseModel):
    today: date | None = None


@router.post("/run")
def run(
    payload: ReminderRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    logs = run_reminders(db, gym_id=current_user.gym_id, today=payload.today)
    db.commit()
    return {
        "today": (payload.today or date.today()).isoformat(),
        "sent": sum(1 for log in logs if log.status == "sent"),
        "blocked": sum(1 for log in logs if log.status == "blocked"),
        "failed": sum(1 for log in logs if log.status == "failed"),
        "total": len(logs),
    }
