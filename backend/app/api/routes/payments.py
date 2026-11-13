from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.invoice import Invoice
from app.models.member import Member
from app.models.payment import Payment
from app.services.invoices import invoice_to_dict
from app.services.payments import member_dues, record_payment

router = APIRouter(prefix="/payments", tags=["payments"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


class PaymentCreate(BaseModel):
    member_id: int
    invoice_id: int | None = None
    membership_id: int | None = None
    amount_paise: int = Field(..., gt=0)
    method: Literal["cash", "upi", "card", "mock"]
    reference: str | None = None
    notes: str | None = None
    paid_at: date | None = None


def payment_to_dict(p: Payment) -> dict:
    return {
        "id": p.id,
        "gym_id": p.gym_id,
        "branch_id": p.branch_id,
        "member_id": p.member_id,
        "membership_id": p.membership_id,
        "invoice_id": p.invoice_id,
        "amount_paise": p.amount_paise,
        "method": p.method,
        "status": p.status,
        "reference": p.reference,
        "notes": p.notes,
        "paid_at": p.paid_at.isoformat(),
        "recorded_by": p.recorded_by,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.gym_id == current_user.gym_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    invoice: Invoice | None = None
    if payload.invoice_id is not None:
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == payload.invoice_id, Invoice.gym_id == current_user.gym_id)
            .first()
        )
        if invoice is None or invoice.member_id != member.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    payment = record_payment(
        db,
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or member.branch_id,
        member_id=member.id,
        amount_paise=payload.amount_paise,
        method=payload.method,
        invoice_id=payload.invoice_id,
        membership_id=payload.membership_id,
        reference=payload.reference,
        notes=payload.notes,
        paid_at=payload.paid_at,
        recorded_by=current_user.id,
    )
    db.commit()
    db.refresh(payment)
    if invoice is not None:
        db.refresh(invoice)
    return {
        "payment": payment_to_dict(payment),
        "invoice": invoice_to_dict(invoice) if invoice is not None else None,
        "dues": member_dues(db, gym_id=current_user.gym_id, member_id=member.id),
    }


@router.get("/dues")
def dues(
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
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return member_dues(db, gym_id=current_user.gym_id, member_id=member_id)
