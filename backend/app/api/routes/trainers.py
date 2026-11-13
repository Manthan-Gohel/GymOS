from __future__ import annotations

from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.member import Member
from app.models.trainer import Trainer, TrainerAssignment, TrainerAvailability

router = APIRouter(prefix="/trainers", tags=["trainers"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


class TrainerCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    specialty: str | None = None
    bio: str | None = None
    user_id: int | None = None
    is_active: bool = True


class TrainerUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    specialty: str | None = None
    bio: str | None = None
    user_id: int | None = None
    is_active: bool | None = None


class AvailabilityCreate(BaseModel):
    weekday: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time


class AssignmentCreate(BaseModel):
    member_id: int


def _trainer_dict(t: Trainer) -> dict:
    return {
        "id": t.id,
        "gym_id": t.gym_id,
        "branch_id": t.branch_id,
        "user_id": t.user_id,
        "full_name": t.full_name,
        "phone": t.phone,
        "specialty": t.specialty,
        "bio": t.bio,
        "is_active": t.is_active,
    }


def _slot_dict(s: TrainerAvailability) -> dict:
    return {
        "id": s.id,
        "trainer_id": s.trainer_id,
        "weekday": s.weekday,
        "start_time": s.start_time.strftime("%H:%M"),
        "end_time": s.end_time.strftime("%H:%M"),
    }


def _get_trainer(db: Session, gym_id: int, trainer_id: int) -> Trainer:
    t = db.query(Trainer).filter(Trainer.id == trainer_id, Trainer.gym_id == gym_id).first()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer not found")
    return t


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trainer(
    payload: TrainerCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    t = Trainer(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        **payload.model_dump(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _trainer_dict(t)


@router.get("")
def list_trainers(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    items = (
        db.query(Trainer)
        .filter(Trainer.gym_id == current_user.gym_id)
        .order_by(Trainer.id)
        .all()
    )
    return {"items": [_trainer_dict(t) for t in items], "total": len(items)}


@router.get("/{trainer_id}")
def get_trainer(
    trainer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    return _trainer_dict(_get_trainer(db, current_user.gym_id, trainer_id))


@router.patch("/{trainer_id}")
def update_trainer(
    trainer_id: int,
    payload: TrainerUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    t = _get_trainer(db, current_user.gym_id, trainer_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return _trainer_dict(t)


@router.post("/{trainer_id}/availability", status_code=status.HTTP_201_CREATED)
def add_availability(
    trainer_id: int,
    payload: AvailabilityCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    trainer = _get_trainer(db, current_user.gym_id, trainer_id)
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_time must be before end_time")
    slot = TrainerAvailability(
        gym_id=current_user.gym_id,
        branch_id=trainer.branch_id,
        trainer_id=trainer.id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _slot_dict(slot)


@router.get("/{trainer_id}/availability")
def list_availability(
    trainer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    _get_trainer(db, current_user.gym_id, trainer_id)
    items = (
        db.query(TrainerAvailability)
        .filter(TrainerAvailability.gym_id == current_user.gym_id, TrainerAvailability.trainer_id == trainer_id)
        .order_by(TrainerAvailability.weekday, TrainerAvailability.start_time)
        .all()
    )
    return {"items": [_slot_dict(s) for s in items], "total": len(items)}


@router.delete("/{trainer_id}/availability/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(
    trainer_id: int,
    slot_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    _get_trainer(db, current_user.gym_id, trainer_id)
    slot = (
        db.query(TrainerAvailability)
        .filter(
            TrainerAvailability.id == slot_id,
            TrainerAvailability.gym_id == current_user.gym_id,
            TrainerAvailability.trainer_id == trainer_id,
        )
        .first()
    )
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability slot not found")
    db.delete(slot)
    db.commit()
    return None


@router.post("/{trainer_id}/assign", status_code=status.HTTP_201_CREATED)
def assign_member(
    trainer_id: int,
    payload: AssignmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    trainer = _get_trainer(db, current_user.gym_id, trainer_id)
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.gym_id == current_user.gym_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    existing = (
        db.query(TrainerAssignment)
        .filter(
            TrainerAssignment.gym_id == current_user.gym_id,
            TrainerAssignment.trainer_id == trainer.id,
            TrainerAssignment.member_id == member.id,
            TrainerAssignment.is_active.is_(True),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already assigned")
    assignment = TrainerAssignment(
        gym_id=current_user.gym_id,
        branch_id=trainer.branch_id,
        trainer_id=trainer.id,
        member_id=member.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"id": assignment.id, "trainer_id": trainer.id, "member_id": member.id, "is_active": assignment.is_active}


@router.get("/{trainer_id}/members")
def list_assigned_members(
    trainer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    _get_trainer(db, current_user.gym_id, trainer_id)
    items = (
        db.query(TrainerAssignment)
        .filter(
            TrainerAssignment.gym_id == current_user.gym_id,
            TrainerAssignment.trainer_id == trainer_id,
            TrainerAssignment.is_active.is_(True),
        )
        .all()
    )
    return {
        "items": [
            {"id": a.id, "trainer_id": a.trainer_id, "member_id": a.member_id, "is_active": a.is_active}
            for a in items
        ],
        "total": len(items),
    }


@router.delete("/{trainer_id}/assign/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_member(
    trainer_id: int,
    member_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    _get_trainer(db, current_user.gym_id, trainer_id)
    assignment = (
        db.query(TrainerAssignment)
        .filter(
            TrainerAssignment.gym_id == current_user.gym_id,
            TrainerAssignment.trainer_id == trainer_id,
            TrainerAssignment.member_id == member_id,
            TrainerAssignment.is_active.is_(True),
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    assignment.is_active = False
    db.commit()
    return None
