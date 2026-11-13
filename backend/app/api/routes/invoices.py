from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.invoice import Invoice
from app.services.invoices import generate_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])

StaffWrite = Annotated[User, Depends(require_roles(["owner", "admin", "reception"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


class InvoiceCreate(BaseModel):
    member_id: int
    membership_id: int | None = None
    payment_id: int | None = None
    taxable_value_paise: int = Field(..., ge=0)
    gst_rate: float = 0.0
    gst_mode: str = "intra"  # intra => CGST+SGST, inter => IGST
    currency: str = "INR"
    seller_gstin: str | None = None
    buyer_name: str | None = None
    buyer_gstin: str | None = None
    notes: str | None = None
    meta: dict[str, Any] | None = None


def _to_dict(inv: Invoice) -> dict:
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
        "total_paise": inv.total_paise,
        "currency": inv.currency,
        "seller_gstin": inv.seller_gstin,
        "buyer_name": inv.buyer_name,
        "buyer_gstin": inv.buyer_gstin,
        "notes": inv.notes,
        "meta": inv.meta,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    inv = generate_invoice(
        db,
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        **payload.model_dump(),
    )
    db.commit()
    db.refresh(inv)
    return _to_dict(inv)


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.gym_id == current_user.gym_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return _to_dict(inv)
