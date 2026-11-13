from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.complaint import Complaint
from app.models.core import User
from app.models.member import Member

router = APIRouter(prefix="/complaints", tags=["complaints"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]

ComplaintStatus = Literal["open", "in_progress", "resolved", "closed"]


class ComplaintCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=80)
    description: str = Field(..., min_length=1)
    member_id: int | None = None
    assigned_to: int | None = None


class ComplaintUpdate(BaseModel):
    status: ComplaintStatus | None = None
    assigned_to: int | None = None
    resolution_notes: str | None = None


def _to_dict(c: Complaint) -> dict:
    return {
        "id": c.id,
        "gym_id": c.gym_id,
        "branch_id": c.branch_id,
        "member_id": c.member_id,
        "category": c.category,
        "description": c.description,
        "status": c.status,
        "assigned_to": c.assigned_to,
        "resolution_notes": c.resolution_notes,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _get_complaint(db: Session, gym_id: int, complaint_id: int) -> Complaint:
    c = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.gym_id == gym_id).first()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    return c


@router.post("", status_code=status.HTTP_201_CREATED)
def create_complaint(
    payload: ComplaintCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    if payload.member_id is not None:
        member = (
            db.query(Member)
            .filter(Member.id == payload.member_id, Member.gym_id == current_user.gym_id)
            .first()
        )
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    complaint = Complaint(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        status="open",
        **payload.model_dump(),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return _to_dict(complaint)


@router.get("")
def list_complaints(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    status_value: Annotated[str | None, Query(alias="status")] = None,
    limit: int = 100,
):
    query = db.query(Complaint).filter(Complaint.gym_id == current_user.gym_id)
    if status_value is not None:
        query = query.filter(Complaint.status == status_value)
    items = query.order_by(Complaint.id.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [_to_dict(c) for c in items], "total": len(items)}


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    return _to_dict(_get_complaint(db, current_user.gym_id, complaint_id))


@router.patch("/{complaint_id}")
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    complaint = _get_complaint(db, current_user.gym_id, complaint_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") in ("resolved", "closed") and not (
        data.get("resolution_notes") or complaint.resolution_notes
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="resolution_notes required to resolve or close a complaint",
        )
    for key, value in data.items():
        setattr(complaint, key, value)
    complaint.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(complaint)
    return _to_dict(complaint)
