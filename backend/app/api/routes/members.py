from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.member import Member
from app.services.audit import write_audit_log

router = APIRouter(prefix="/members", tags=["members"])

StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]
StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]


class MemberCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    email: EmailStr | None = None
    photo_ref: str | None = None
    kyc_id_type: str | None = None
    kyc_id_number: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    whatsapp_consent: bool = False
    whatsapp_opt_out: bool = False

    @field_validator("full_name", "phone")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class MemberUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    photo_ref: str | None = None
    kyc_id_type: str | None = None
    kyc_id_number: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    whatsapp_consent: bool | None = None
    whatsapp_opt_out: bool | None = None
    is_active: bool | None = None

    @field_validator("full_name", "phone")
    @classmethod
    def not_blank_if_present(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v.strip() if isinstance(v, str) else v


def _mask_kyc(number: str | None) -> str | None:
    if number is None:
        return None
    return "****" + number[-4:] if len(number) > 4 else "****"


def _to_dict(m: Member, roles: set[str] | None = None) -> dict:
    # VULN-004: KYC ID is owner/admin-only; health notes hidden from trainer.
    # reception keeps health_notes (front desk needs it) but never sees raw KYC IDs.
    roles = roles or set()
    full_pii = bool(roles & {"owner", "admin"})
    return {
        "id": m.id,
        "gym_id": m.gym_id,
        "branch_id": m.branch_id,
        "full_name": m.full_name,
        "phone": m.phone,
        "email": m.email,
        "photo_ref": m.photo_ref,
        "kyc_id_type": m.kyc_id_type,
        "kyc_id_number": m.kyc_id_number if full_pii else _mask_kyc(m.kyc_id_number),
        "address": m.address,
        "emergency_contact_name": m.emergency_contact_name,
        "emergency_contact_phone": m.emergency_contact_phone,
        "health_notes": m.health_notes if (full_pii or "reception" in roles) else None,
        "whatsapp_consent": m.whatsapp_consent,
        "whatsapp_opt_out": m.whatsapp_opt_out,
        "is_active": m.is_active,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    member = Member(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        **payload.model_dump(),
    )
    db.add(member)
    db.flush()
    write_audit_log(
        db,
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id,
        actor_user_id=current_user.id,
        action="member.create",
        entity_type="member",
        entity_id=member.id,
        why="staff_entered_member_record",
    )
    db.commit()
    db.refresh(member)
    return _to_dict(member, set(getattr(current_user, "role_names", []) or []))


@router.get("")
def list_members(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    is_active: bool | None = None,
    limit: int = 100,
):
    query = db.query(Member).filter(Member.gym_id == current_user.gym_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Member.full_name.ilike(like), Member.phone.ilike(like)))
    if is_active is not None:
        query = query.filter(Member.is_active.is_(is_active))
    items = query.order_by(Member.id.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [_to_dict(m, set(getattr(current_user, "role_names", []) or [])) for m in items], "total": len(items)}


@router.get("/{member_id}")
def get_member(
    member_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.gym_id == current_user.gym_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return _to_dict(member, set(getattr(current_user, "role_names", []) or []))


@router.patch("/{member_id}")
def update_member(
    member_id: int,
    payload: MemberUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.gym_id == current_user.gym_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    changed = list(payload.model_dump(exclude_unset=True).keys())
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    write_audit_log(
        db,
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id,
        actor_user_id=current_user.id,
        action="member.update",
        entity_type="member",
        entity_id=member.id,
        why="staff_updated_member_record",
        metadata={"changed_fields": changed},
    )
    db.commit()
    db.refresh(member)
    return _to_dict(member, set(getattr(current_user, "role_names", []) or []))
