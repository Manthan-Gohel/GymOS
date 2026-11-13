from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment


def invoice_paid_paise(db: Session, invoice_id: int) -> int:
    total = (
        db.query(func.coalesce(func.sum(Payment.amount_paise), 0))
        .filter(Payment.invoice_id == invoice_id, Payment.status == "paid")
        .scalar()
    )
    return int(total or 0)


def invoice_due_paise(db: Session, invoice: Invoice) -> int:
    paid = invoice_paid_paise(db, invoice.id)
    return max(0, invoice.total_paise + invoice.late_fee_paise - paid)


def sync_invoice_status(db: Session, invoice: Invoice) -> None:
    due = invoice_due_paise(db, invoice)
    paid = invoice_paid_paise(db, invoice.id)
    if due <= 0:
        invoice.status = "paid"
    elif paid > 0:
        invoice.status = "partial"
    else:
        invoice.status = "issued"


def record_payment(
    db: Session,
    *,
    gym_id: int,
    branch_id: int,
    member_id: int,
    amount_paise: int,
    method: str,
    invoice_id: int | None = None,
    membership_id: int | None = None,
    reference: str | None = None,
    notes: str | None = None,
    paid_at: date | None = None,
    recorded_by: int | None = None,
    status: str = "paid",
) -> Payment:
    if amount_paise <= 0:
        raise ValueError("amount_paise must be positive")
    if method not in ("cash", "upi", "card", "mock"):
        raise ValueError("unsupported payment method")
    payment = Payment(
        gym_id=gym_id,
        branch_id=branch_id,
        member_id=member_id,
        membership_id=membership_id,
        invoice_id=invoice_id,
        amount_paise=amount_paise,
        method=method,
        status=status,
        reference=reference,
        notes=notes,
        paid_at=paid_at or date.today(),
        recorded_by=recorded_by,
    )
    db.add(payment)
    db.flush()
    if invoice_id is not None:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.gym_id == gym_id).first()
        if invoice is None:
            raise ValueError("invoice not found for tenant")
        sync_invoice_status(db, invoice)
    return payment


def apply_late_fee(db: Session, *, gym_id: int, invoice_id: int, late_fee_paise: int) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.gym_id == gym_id).first()
    if invoice is None:
        raise ValueError("invoice not found")
    invoice.late_fee_paise = max(0, late_fee_paise)
    sync_invoice_status(db, invoice)
    return invoice


def update_payment_status(db: Session, *, gym_id: int, payment_id: int, status: str) -> Payment:
    if status not in ("paid", "failed", "refunded", "pending"):
        raise ValueError("unsupported payment status")
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.gym_id == gym_id).first()
    if payment is None:
        raise ValueError("payment not found")
    payment.status = status
    db.flush()
    if payment.invoice_id is not None:
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id, Invoice.gym_id == gym_id).first()
        if invoice is not None:
            sync_invoice_status(db, invoice)
    return payment


def member_dues(db: Session, *, gym_id: int, member_id: int) -> dict:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.gym_id == gym_id, Invoice.member_id == member_id)
        .order_by(Invoice.id)
        .all()
    )
    rows = []
    total_due = 0
    for inv in invoices:
        due = invoice_due_paise(db, inv)
        total_due += due
        rows.append({"invoice_id": inv.id, "invoice_number": inv.invoice_number, "status": inv.status, "due_paise": due})
    return {"member_id": member_id, "total_due_paise": total_due, "invoices": rows}
