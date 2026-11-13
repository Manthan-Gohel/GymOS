from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.equipment import Equipment, MaintenanceSchedule
from app.services.maintenance import run_maintenance_reminders

router = APIRouter(tags=["equipment"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]

EquipmentStatus = Literal["operational", "under_maintenance", "retired"]


class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=80)
    serial_number: str | None = None
    purchased_on: date | None = None
    notes: str | None = None


class EquipmentUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    serial_number: str | None = None
    purchased_on: date | None = None
    status: EquipmentStatus | None = None
    notes: str | None = None


class ScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    due_on: date
    interval_days: int | None = Field(default=None, ge=1)
    notes: str | None = None


class CompleteRequest(BaseModel):
    completed_on: date | None = None
    notes: str | None = None


class ReminderRunRequest(BaseModel):
    today: date | None = None


def _equipment_dict(e: Equipment) -> dict:
    return {
        "id": e.id,
        "gym_id": e.gym_id,
        "branch_id": e.branch_id,
        "name": e.name,
        "category": e.category,
        "serial_number": e.serial_number,
        "purchased_on": e.purchased_on.isoformat() if e.purchased_on else None,
        "status": e.status,
        "notes": e.notes,
    }


def _schedule_dict(s: MaintenanceSchedule) -> dict:
    return {
        "id": s.id,
        "gym_id": s.gym_id,
        "branch_id": s.branch_id,
        "equipment_id": s.equipment_id,
        "title": s.title,
        "due_on": s.due_on.isoformat(),
        "interval_days": s.interval_days,
        "status": s.status,
        "completed_on": s.completed_on.isoformat() if s.completed_on else None,
        "notes": s.notes,
    }


def _get_equipment(db: Session, gym_id: int, equipment_id: int) -> Equipment:
    e = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.gym_id == gym_id).first()
    if e is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return e


def _get_schedule(db: Session, gym_id: int, schedule_id: int) -> MaintenanceSchedule:
    s = (
        db.query(MaintenanceSchedule)
        .filter(MaintenanceSchedule.id == schedule_id, MaintenanceSchedule.gym_id == gym_id)
        .first()
    )
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance schedule not found")
    return s


@router.post("/equipment", status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    e = Equipment(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        status="operational",
        **payload.model_dump(),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _equipment_dict(e)


@router.get("/equipment")
def list_equipment(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    category: str | None = None,
    status_value: str | None = None,
):
    query = db.query(Equipment).filter(Equipment.gym_id == current_user.gym_id)
    if category is not None:
        query = query.filter(Equipment.category == category)
    if status_value is not None:
        query = query.filter(Equipment.status == status_value)
    items = query.order_by(Equipment.id).all()
    return {"items": [_equipment_dict(e) for e in items], "total": len(items)}


@router.get("/equipment/{equipment_id}")
def get_equipment(
    equipment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    return _equipment_dict(_get_equipment(db, current_user.gym_id, equipment_id))


@router.patch("/equipment/{equipment_id}")
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    e = _get_equipment(db, current_user.gym_id, equipment_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(e, key, value)
    db.commit()
    db.refresh(e)
    return _equipment_dict(e)


@router.post("/equipment/{equipment_id}/maintenance", status_code=status.HTTP_201_CREATED)
def schedule_maintenance(
    equipment_id: int,
    payload: ScheduleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    e = _get_equipment(db, current_user.gym_id, equipment_id)
    s = MaintenanceSchedule(
        gym_id=current_user.gym_id,
        branch_id=e.branch_id,
        equipment_id=e.id,
        status="scheduled",
        **payload.model_dump(),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _schedule_dict(s)


@router.get("/equipment/{equipment_id}/maintenance")
def list_equipment_maintenance(
    equipment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    e = _get_equipment(db, current_user.gym_id, equipment_id)
    items = (
        db.query(MaintenanceSchedule)
        .filter(MaintenanceSchedule.gym_id == current_user.gym_id, MaintenanceSchedule.equipment_id == e.id)
        .order_by(MaintenanceSchedule.due_on.desc())
        .all()
    )
    return {"items": [_schedule_dict(s) for s in items], "total": len(items)}


@router.get("/maintenance")
def list_due_maintenance(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    due_on: date | None = None,
    status_value: str | None = None,
):
    query = db.query(MaintenanceSchedule).filter(MaintenanceSchedule.gym_id == current_user.gym_id)
    if due_on is not None:
        query = query.filter(MaintenanceSchedule.due_on <= due_on)
    query = query.filter(MaintenanceSchedule.status == (status_value or "scheduled"))
    items = query.order_by(MaintenanceSchedule.due_on).all()
    return {"items": [_schedule_dict(s) for s in items], "total": len(items)}


@router.post("/maintenance/{schedule_id}/complete")
def complete_maintenance(
    schedule_id: int,
    payload: CompleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    s = _get_schedule(db, current_user.gym_id, schedule_id)
    if s.status == "done":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maintenance already completed")
    s.status = "done"
    s.completed_on = payload.completed_on or date.today()
    if payload.notes:
        s.notes = payload.notes
    s.recorded_by = current_user.id
    next_id = None
    if s.interval_days:
        next_schedule = MaintenanceSchedule(
            gym_id=s.gym_id,
            branch_id=s.branch_id,
            equipment_id=s.equipment_id,
            title=s.title,
            due_on=s.due_on + timedelta(days=s.interval_days),
            interval_days=s.interval_days,
            status="scheduled",
            notes=s.notes,
        )
        db.add(next_schedule)
        db.flush()
        next_id = next_schedule.id
    db.commit()
    db.refresh(s)
    return {**_schedule_dict(s), "next_schedule_id": next_id}


@router.post("/maintenance/run-reminders")
def run_reminders(
    payload: ReminderRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    logs = run_maintenance_reminders(db, gym_id=current_user.gym_id, today=payload.today)
    db.commit()
    return {
        "today": (payload.today or date.today()).isoformat(),
        "sent": sum(1 for log in logs if log.status == "sent"),
        "failed": sum(1 for log in logs if log.status == "failed"),
        "total": len(logs),
    }
