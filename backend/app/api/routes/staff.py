from __future__ import annotations

from datetime import date, time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.staff import PayrollRecord, StaffAttendance

router = APIRouter(tags=["staff"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class AttendanceCreate(BaseModel):
    user_id: int
    on_date: date
    status: Literal["present", "absent", "half_day", "leave"] = "present"
    check_in: time | None = None
    check_out: time | None = None
    notes: str | None = Field(default=None, max_length=500)


class PayrollCreate(BaseModel):
    user_id: int
    month: str = Field(..., pattern=MONTH_PATTERN)
    base_paise: int = Field(..., ge=0)
    bonus_paise: int = Field(default=0, ge=0)
    deductions_paise: int = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=500)


def _attendance_dict(a: StaffAttendance) -> dict:
    return {
        "id": a.id,
        "gym_id": a.gym_id,
        "branch_id": a.branch_id,
        "user_id": a.user_id,
        "on_date": a.on_date.isoformat(),
        "status": a.status,
        "check_in": a.check_in.strftime("%H:%M") if a.check_in else None,
        "check_out": a.check_out.strftime("%H:%M") if a.check_out else None,
        "notes": a.notes,
    }


def _payroll_dict(p: PayrollRecord) -> dict:
    return {
        "id": p.id,
        "gym_id": p.gym_id,
        "branch_id": p.branch_id,
        "user_id": p.user_id,
        "month": p.month,
        "base_paise": p.base_paise,
        "bonus_paise": p.bonus_paise,
        "deductions_paise": p.deductions_paise,
        "net_paise": p.net_paise,
        "status": p.status,
        "notes": p.notes,
    }


def _get_staff_user(db: Session, gym_id: int, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.gym_id == gym_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found")
    return user


@router.post("/staff-attendance", status_code=status.HTTP_201_CREATED)
def record_attendance(
    payload: AttendanceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    user = _get_staff_user(db, current_user.gym_id, payload.user_id)
    existing = (
        db.query(StaffAttendance)
        .filter(StaffAttendance.user_id == user.id, StaffAttendance.on_date == payload.on_date)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance already recorded for this date")
    if payload.check_in and payload.check_out and payload.check_out < payload.check_in:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="check_out must be after check_in")
    entry = StaffAttendance(
        gym_id=current_user.gym_id,
        branch_id=user.branch_id or current_user.branch_id or 0,
        user_id=user.id,
        on_date=payload.on_date,
        status=payload.status,
        check_in=payload.check_in,
        check_out=payload.check_out,
        notes=payload.notes,
        recorded_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _attendance_dict(entry)


@router.get("/staff-attendance")
def list_attendance(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    user_id: int | None = None,
    month: str | None = None,
):
    query = db.query(StaffAttendance).filter(StaffAttendance.gym_id == current_user.gym_id)
    if user_id is not None:
        query = query.filter(StaffAttendance.user_id == user_id)
    if month is not None:
        query = query.filter(StaffAttendance.on_date >= date.fromisoformat(f"{month}-01"))
        year, mon = (int(part) for part in month.split("-"))
        next_month = date(year + (mon == 12), 1 if mon == 12 else mon + 1, 1)
        query = query.filter(StaffAttendance.on_date < next_month)
    items = query.order_by(StaffAttendance.on_date.desc()).all()
    return {"items": [_attendance_dict(a) for a in items], "total": len(items)}


@router.post("/payroll", status_code=status.HTTP_201_CREATED)
def create_payroll(
    payload: PayrollCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    user = _get_staff_user(db, current_user.gym_id, payload.user_id)
    existing = (
        db.query(PayrollRecord)
        .filter(PayrollRecord.user_id == user.id, PayrollRecord.month == payload.month)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payroll already exists for this month")
    record = PayrollRecord(
        gym_id=current_user.gym_id,
        branch_id=user.branch_id or current_user.branch_id or 0,
        user_id=user.id,
        month=payload.month,
        base_paise=payload.base_paise,
        bonus_paise=payload.bonus_paise,
        deductions_paise=payload.deductions_paise,
        net_paise=payload.base_paise + payload.bonus_paise - payload.deductions_paise,
        status="draft",
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _payroll_dict(record)


@router.get("/payroll")
def list_payroll(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    month: str | None = None,
    user_id: int | None = None,
):
    query = db.query(PayrollRecord).filter(PayrollRecord.gym_id == current_user.gym_id)
    if month is not None:
        query = query.filter(PayrollRecord.month == month)
    if user_id is not None:
        query = query.filter(PayrollRecord.user_id == user_id)
    items = query.order_by(PayrollRecord.month.desc(), PayrollRecord.id).all()
    return {"items": [_payroll_dict(p) for p in items], "total": len(items)}


@router.post("/payroll/{payroll_id}/finalize")
def finalize_payroll(
    payroll_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    record = (
        db.query(PayrollRecord)
        .filter(PayrollRecord.id == payroll_id, PayrollRecord.gym_id == current_user.gym_id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll record not found")
    if record.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft payroll can be finalized")
    record.status = "finalized"
    db.commit()
    db.refresh(record)
    return _payroll_dict(record)
