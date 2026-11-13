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
from app.services.payments import member_dues, record_payment, update_payment_status

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


class PaymentStatusUpdate(BaseModel):
    status: Literal["paid", "pending", "failed", "refunded"]


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


@router.get("")
def list_payments(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    member_id: int | None = None,
    limit: int = 50,
):
    query = db.query(Payment).filter(Payment.gym_id == current_user.gym_id)
    if member_id is not None:
        query = query.filter(Payment.member_id == member_id)
    items = query.order_by(Payment.id.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [payment_to_dict(p) for p in items], "total": len(items)}


def _get_payment(db: Session, gym_id: int, payment_id: int) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.gym_id == gym_id).first()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.get("/{payment_id}/receipt")
def get_receipt(
    payment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    payment = _get_payment(db, current_user.gym_id, payment_id)
    member = db.query(Member).filter(Member.id == payment.member_id, Member.gym_id == current_user.gym_id).first()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    invoice = None
    if payment.invoice_id is not None:
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id, Invoice.gym_id == current_user.gym_id).first()
    return {
        "receipt_number": f"RCPT-{current_user.gym_id}-{payment.id:06d}",
        "payment": payment_to_dict(payment),
        "invoice": invoice_to_dict(invoice) if invoice is not None else None,
        "member": {"id": member.id, "full_name": member.full_name, "phone": member.phone},
    }


@router.post("/{payment_id}/status")
def set_payment_status(
    payment_id: int,
    payload: PaymentStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    payment = _get_payment(db, current_user.gym_id, payment_id)
    update_payment_status(db, gym_id=current_user.gym_id, payment_id=payment.id, status=payload.status)
    db.commit()
    db.refresh(payment)
    invoice = None
    if payment.invoice_id is not None:
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id, Invoice.gym_id == current_user.gym_id).first()
    return {
        "payment": payment_to_dict(payment),
        "invoice": invoice_to_dict(invoice) if invoice is not None else None,
        "dues": member_dues(db, gym_id=current_user.gym_id, member_id=payment.member_id),
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
