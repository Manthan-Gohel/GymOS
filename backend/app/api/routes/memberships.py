from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.member import Member
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.services.memberships import expire_due_memberships

router = APIRouter(prefix="/memberships", tags=["memberships"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


class PurchaseRequest(BaseModel):
    member_id: int
    plan_id: int
    start_date: date


class FreezeRequest(BaseModel):
    frozen_on: date


class UnfreezeRequest(BaseModel):
    unfrozen_on: date


class UpgradeRequest(BaseModel):
    new_plan_id: int
    start_date: date | None = None


def _to_dict(m: Membership) -> dict:
    return {
        "id": m.id,
        "gym_id": m.gym_id,
        "branch_id": m.branch_id,
        "member_id": m.member_id,
        "plan_id": m.plan_id,
        "status": m.status,
        "start_date": m.start_date.isoformat(),
        "end_date": m.end_date.isoformat(),
        "frozen_on": m.frozen_on.isoformat() if m.frozen_on else None,
        "upgraded_to_id": m.upgraded_to_id,
    }


def _get_membership(db: Session, gym_id: int, membership_id: int) -> Membership:
    m = db.query(Membership).filter(Membership.id == membership_id, Membership.gym_id == gym_id).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    return m


@router.post("/purchase", status_code=status.HTTP_201_CREATED)
def purchase(
    payload: PurchaseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    member = db.query(Member).filter(Member.id == payload.member_id, Member.gym_id == current_user.gym_id).first()
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == payload.plan_id, MembershipPlan.gym_id == current_user.gym_id).first()
    if not member or not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member or plan not found")
    end_date = payload.start_date + timedelta(days=plan.duration_days)
    m = Membership(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or member.branch_id,
        member_id=member.id,
        plan_id=plan.id,
        status="active",
        start_date=payload.start_date,
        end_date=end_date,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _to_dict(m)


@router.get("/{membership_id}")
def get_membership(
    membership_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    return _to_dict(_get_membership(db, current_user.gym_id, membership_id))


@router.post("/{membership_id}/freeze")
def freeze(
    membership_id: int,
    payload: FreezeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    m = _get_membership(db, current_user.gym_id, membership_id)
    if m.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only active memberships can be frozen")
    m.status = "frozen"
    m.frozen_on = payload.frozen_on
    db.commit()
    db.refresh(m)
    return _to_dict(m)


@router.post("/{membership_id}/unfreeze")
def unfreeze(
    membership_id: int,
    payload: UnfreezeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    m = _get_membership(db, current_user.gym_id, membership_id)
    if m.status != "frozen" or m.frozen_on is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only frozen memberships can be unfrozen")
    freeze_days = (payload.unfrozen_on - m.frozen_on).days
    if freeze_days < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid unfreeze date")
    m.end_date = m.end_date + timedelta(days=freeze_days)
    m.status = "active"
    m.frozen_on = None
    db.commit()
    db.refresh(m)
    return _to_dict(m)


@router.post("/{membership_id}/upgrade")
def upgrade(
    membership_id: int,
    payload: UpgradeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    old = _get_membership(db, current_user.gym_id, membership_id)
    if old.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only active memberships can be upgraded")
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == payload.new_plan_id, MembershipPlan.gym_id == current_user.gym_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    start_date = payload.start_date or date.today()
    new_end = start_date + timedelta(days=plan.duration_days)
    new_m = Membership(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or old.branch_id,
        member_id=old.member_id,
        plan_id=plan.id,
        status="active",
        start_date=start_date,
        end_date=new_end,
    )
    db.add(new_m)
    db.flush()
    old.status = "upgraded"
    old.upgraded_to_id = new_m.id
    db.commit()
    db.refresh(old)
    db.refresh(new_m)
    return {"old_membership": _to_dict(old), "new_membership": _to_dict(new_m)}


class ExpiryRunRequest(BaseModel):
    today: date | None = None


@router.post("/expire/run")
def run_expiry(
    payload: ExpiryRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    target_day = payload.today or date.today()
    count = expire_due_memberships(db, gym_id=current_user.gym_id, today=target_day)
    db.commit()
    return {"expired": count, "today": target_day.isoformat()}
