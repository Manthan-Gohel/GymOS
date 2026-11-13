from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.invoice import Invoice


def invoice_to_dict(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "gym_id": inv.gym_id,
        "branch_id": inv.branch_id,
        "member_id": inv.member_id,
        "membership_id": inv.membership_id,
        "payment_id": inv.payment_id,
        "invoice_number": inv.invoice_number,
        "status": inv.status,
        "taxable_value_paise": inv.taxable_value_paise,
        "gst_rate": inv.gst_rate,
        "cgst_paise": inv.cgst_paise,
        "sgst_paise": inv.sgst_paise,
        "igst_paise": inv.igst_paise,
        "late_fee_paise": inv.late_fee_paise,
        "total_paise": inv.total_paise,
        "currency": inv.currency,
        "seller_gstin": inv.seller_gstin,
        "buyer_name": inv.buyer_name,
        "buyer_gstin": inv.buyer_gstin,
        "notes": inv.notes,
        "meta": inv.meta,
    }


def _next_invoice_number(db: Session, gym_id: int) -> str:
    count = db.query(Invoice).filter(Invoice.gym_id == gym_id).count()
    return f"INV-{gym_id}-{count + 1:06d}"


def generate_invoice(
    db: Session,
    *,
    gym_id: int,
    branch_id: int,
    member_id: int,
    taxable_value_paise: int,
    gst_rate: float = 0.0,
    gst_mode: str = "intra",
    membership_id: int | None = None,
    payment_id: int | None = None,
    currency: str = "INR",
    seller_gstin: str | None = None,
    buyer_name: str | None = None,
    buyer_gstin: str | None = None,
    notes: str | None = None,
    meta: dict | None = None,
) -> Invoice:
    total_tax = round(taxable_value_paise * (gst_rate / 100.0))
    if gst_mode == "inter":
        cgst = 0
        sgst = 0
        igst = total_tax
    else:
        # intra-state: split CGST/SGST (half-half)
        cgst = total_tax // 2
        sgst = total_tax - cgst
        igst = 0
    total = taxable_value_paise + cgst + sgst + igst
    inv = Invoice(
        gym_id=gym_id,
        branch_id=branch_id,
        member_id=member_id,
        membership_id=membership_id,
        payment_id=payment_id,
        invoice_number=_next_invoice_number(db, gym_id),
        status="issued",
        taxable_value_paise=taxable_value_paise,
        gst_rate=gst_rate,
        cgst_paise=cgst,
        sgst_paise=sgst,
        igst_paise=igst,
        total_paise=total,
        currency=currency,
        seller_gstin=seller_gstin,
        buyer_name=buyer_name,
        buyer_gstin=buyer_gstin,
        notes=notes,
        meta=meta,
    )
    db.add(inv)
    db.flush()
    return inv
