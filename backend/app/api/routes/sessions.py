from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.member import Member
from app.models.session import TrainerAttendance, TrainingSession
from app.models.trainer import Trainer, TrainerAvailability

router = APIRouter(prefix="/sessions", tags=["sessions"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


class SessionCreate(BaseModel):
    trainer_id: int
    member_id: int
    start_at: datetime
    end_at: datetime
    notes: str | None = None


class SessionReschedule(BaseModel):
    start_at: datetime
    end_at: datetime


class AttendanceCreate(BaseModel):
    checked_in_at: datetime
    checked_out_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


def _session_dict(s: TrainingSession) -> dict:
    return {
        "id": s.id,
        "gym_id": s.gym_id,
        "branch_id": s.branch_id,
        "trainer_id": s.trainer_id,
        "member_id": s.member_id,
        "start_at": s.start_at.isoformat(),
        "end_at": s.end_at.isoformat(),
        "status": s.status,
        "notes": s.notes,
    }


def _attendance_dict(a: TrainerAttendance) -> dict:
    return {
        "id": a.id,
        "trainer_id": a.trainer_id,
        "session_id": a.session_id,
        "checked_in_at": a.checked_in_at.isoformat(),
        "checked_out_at": a.checked_out_at.isoformat() if a.checked_out_at else None,
        "notes": a.notes,
    }


def _get_session(db: Session, gym_id: int, session_id: int) -> TrainingSession:
    s = db.query(TrainingSession).filter(TrainingSession.id == session_id, TrainingSession.gym_id == gym_id).first()
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return s


def _validate_window(db: Session, *, gym_id: int, trainer_id: int, start_at: datetime, end_at: datetime, exclude_id: int | None = None) -> None:
    if end_at <= start_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="end_at must be after start_at")

    slots = (
        db.query(TrainerAvailability)
        .filter(TrainerAvailability.gym_id == gym_id, TrainerAvailability.trainer_id == trainer_id)
        .all()
    )
    if slots:
        weekday = start_at.weekday()
        covered = any(
            slot.weekday == weekday and slot.start_time <= start_at.time() and slot.end_time >= end_at.time()
            for slot in slots
        )
        if not covered:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is outside trainer availability")

    conflict_query = db.query(TrainingSession).filter(
        TrainingSession.gym_id == gym_id,
        TrainingSession.status == "scheduled",
        TrainingSession.trainer_id == trainer_id,
        TrainingSession.start_at < end_at,
        TrainingSession.end_at > start_at,
    )
    if exclude_id is not None:
        conflict_query = conflict_query.filter(TrainingSession.id != exclude_id)
    if conflict_query.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trainer has an overlapping session")


def _validate_member_window(db: Session, *, gym_id: int, member_id: int, start_at: datetime, end_at: datetime, exclude_id: int | None = None) -> None:
    conflict_query = db.query(TrainingSession).filter(
        TrainingSession.gym_id == gym_id,
        TrainingSession.status == "scheduled",
        TrainingSession.member_id == member_id,
        TrainingSession.start_at < end_at,
        TrainingSession.end_at > start_at,
    )
    if exclude_id is not None:
        conflict_query = conflict_query.filter(TrainingSession.id != exclude_id)
    if conflict_query.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member has an overlapping session")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    trainer = db.query(Trainer).filter(Trainer.id == payload.trainer_id, Trainer.gym_id == current_user.gym_id).first()
    member = db.query(Member).filter(Member.id == payload.member_id, Member.gym_id == current_user.gym_id).first()
    if trainer is None or member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer or member not found")
    _validate_window(db, gym_id=current_user.gym_id, trainer_id=trainer.id, start_at=payload.start_at, end_at=payload.end_at)
    _validate_member_window(db, gym_id=current_user.gym_id, member_id=member.id, start_at=payload.start_at, end_at=payload.end_at)
    s = TrainingSession(
        gym_id=current_user.gym_id,
        branch_id=trainer.branch_id,
        trainer_id=trainer.id,
        member_id=member.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status="scheduled",
        notes=payload.notes,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _session_dict(s)


@router.get("")
def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    trainer_id: int | None = None,
    member_id: int | None = None,
    on_date: date | None = None,
    limit: int = 100,
):
    query = db.query(TrainingSession).filter(TrainingSession.gym_id == current_user.gym_id)
    if trainer_id is not None:
        query = query.filter(TrainingSession.trainer_id == trainer_id)
    if member_id is not None:
        query = query.filter(TrainingSession.member_id == member_id)
    if on_date is not None:
        query = query.filter(
            TrainingSession.start_at >= datetime.combine(on_date, datetime.min.time()),
            TrainingSession.start_at < datetime.combine(on_date, datetime.max.time()),
        )
    items = query.order_by(TrainingSession.start_at.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [_session_dict(s) for s in items], "total": len(items)}


@router.get("/{session_id}")
def get_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    return _session_dict(_get_session(db, current_user.gym_id, session_id))


@router.post("/{session_id}/reschedule")
def reschedule_session(
    session_id: int,
    payload: SessionReschedule,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    s = _get_session(db, current_user.gym_id, session_id)
    if s.status != "scheduled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only scheduled sessions can be rescheduled")
    _validate_window(db, gym_id=current_user.gym_id, trainer_id=s.trainer_id, start_at=payload.start_at, end_at=payload.end_at, exclude_id=s.id)
    _validate_member_window(db, gym_id=current_user.gym_id, member_id=s.member_id, start_at=payload.start_at, end_at=payload.end_at, exclude_id=s.id)
    s.start_at = payload.start_at
    s.end_at = payload.end_at
    db.commit()
    db.refresh(s)
    return _session_dict(s)


@router.post("/{session_id}/cancel")
def cancel_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    s = _get_session(db, current_user.gym_id, session_id)
    if s.status != "scheduled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only scheduled sessions can be cancelled")
    s.status = "cancelled"
    db.commit()
    db.refresh(s)
    return _session_dict(s)


@router.post("/{session_id}/attendance", status_code=status.HTTP_201_CREATED)
def record_attendance(
    session_id: int,
    payload: AttendanceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    s = _get_session(db, current_user.gym_id, session_id)
    roles = set(getattr(current_user, "role_names", []) or [])
    if not roles.intersection({"owner", "admin", "reception"}):
        trainer = (
            db.query(Trainer)
            .filter(Trainer.id == s.trainer_id, Trainer.gym_id == current_user.gym_id)
            .first()
        )
        if trainer is None or trainer.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if payload.checked_out_at is not None and payload.checked_out_at < payload.checked_in_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="checked_out_at must be after checked_in_at")
    attendance = TrainerAttendance(
        gym_id=current_user.gym_id,
        branch_id=s.branch_id,
        trainer_id=s.trainer_id,
        session_id=s.id,
        checked_in_at=payload.checked_in_at,
        checked_out_at=payload.checked_out_at,
        notes=payload.notes,
    )
    s.status = "completed"
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return _attendance_dict(attendance)


@router.get("/{session_id}/attendance")
def list_attendance(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    _get_session(db, current_user.gym_id, session_id)
    items = (
        db.query(TrainerAttendance)
        .filter(TrainerAttendance.gym_id == current_user.gym_id, TrainerAttendance.session_id == session_id)
        .all()
    )
    return {"items": [_attendance_dict(a) for a in items], "total": len(items)}
