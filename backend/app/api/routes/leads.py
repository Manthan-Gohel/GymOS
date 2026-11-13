from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.lead import Lead

router = APIRouter(prefix="/leads", tags=["leads"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]

LeadStatus = Literal["new", "contacted", "trial_booked", "converted", "lost"]


class LeadCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    email: str | None = None
    source: str | None = None
    notes: str | None = None
    trial_date: date | None = None
    assigned_to: int | None = None


class LeadUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    status: LeadStatus | None = None
    notes: str | None = None
    trial_date: date | None = None
    assigned_to: int | None = None


def _to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "gym_id": lead.gym_id,
        "branch_id": lead.branch_id,
        "full_name": lead.full_name,
        "phone": lead.phone,
        "email": lead.email,
        "source": lead.source,
        "status": lead.status,
        "trial_date": lead.trial_date.isoformat() if lead.trial_date else None,
        "assigned_to": lead.assigned_to,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    lead = Lead(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        **payload.model_dump(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _to_dict(lead)


@router.get("")
def list_leads(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    status_value: Annotated[str | None, Query(alias="status")] = None,
    limit: int = 100,
):
    query = db.query(Lead).filter(Lead.gym_id == current_user.gym_id)
    if status_value is not None:
        query = query.filter(Lead.status == status_value)
    items = query.order_by(Lead.id.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [_to_dict(lead) for lead in items], "total": len(items)}


@router.get("/{lead_id}")
def get_lead(
    lead_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.gym_id == current_user.gym_id).first()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return _to_dict(lead)


@router.patch("/{lead_id}")
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.gym_id == current_user.gym_id).first()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, key, value)
    lead.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(lead)
    return _to_dict(lead)
