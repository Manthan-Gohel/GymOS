from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.plan import MembershipPlan

router = APIRouter(prefix="/plans", tags=["plans"])

StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]
StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin"]))]


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1)
    duration_days: int = Field(..., gt=0)
    price_paise: int = Field(..., ge=0)
    currency: str = "INR"
    terms: dict[str, Any] | None = None
    is_active: bool = True


class PlanUpdate(BaseModel):
    name: str | None = None
    duration_days: int | None = Field(default=None, gt=0)
    price_paise: int | None = Field(default=None, ge=0)
    currency: str | None = None
    terms: dict[str, Any] | None = None
    is_active: bool | None = None


def _to_dict(p: MembershipPlan) -> dict:
    return {
        "id": p.id,
        "gym_id": p.gym_id,
        "branch_id": p.branch_id,
        "name": p.name,
        "duration_days": p.duration_days,
        "price_paise": p.price_paise,
        "currency": p.currency,
        "terms": p.terms,
        "is_active": p.is_active,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    plan = MembershipPlan(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        **payload.model_dump(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _to_dict(plan)


@router.get("")
def list_plans(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    plans = db.query(MembershipPlan).filter(MembershipPlan.gym_id == current_user.gym_id).all()
    return [_to_dict(p) for p in plans]


@router.get("/{plan_id}")
def get_plan(
    plan_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    plan = (
        db.query(MembershipPlan)
        .filter(MembershipPlan.id == plan_id, MembershipPlan.gym_id == current_user.gym_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _to_dict(plan)


@router.patch("/{plan_id}")
def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    plan = (
        db.query(MembershipPlan)
        .filter(MembershipPlan.id == plan_id, MembershipPlan.gym_id == current_user.gym_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return _to_dict(plan)
