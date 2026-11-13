from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.invoice import Invoice
from app.services.invoices import generate_invoice, invoice_to_dict
from app.services.payments import apply_late_fee, invoice_due_paise

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


class LateFeeRequest(BaseModel):
    late_fee_paise: int = Field(..., ge=0)


def _get_invoice(db: Session, gym_id: int, invoice_id: int) -> Invoice:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.gym_id == gym_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return inv


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
    return invoice_to_dict(inv)


@router.get("")
def list_invoices(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    member_id: int | None = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
    limit: int = 100,
):
    query = db.query(Invoice).filter(Invoice.gym_id == current_user.gym_id)
    if member_id is not None:
        query = query.filter(Invoice.member_id == member_id)
    if status_value is not None:
        query = query.filter(Invoice.status == status_value)
    items = query.order_by(Invoice.id.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [invoice_to_dict(i) for i in items], "total": len(items)}


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    return invoice_to_dict(_get_invoice(db, current_user.gym_id, invoice_id))


@router.post("/{invoice_id}/late-fee")
def set_late_fee(
    invoice_id: int,
    payload: LateFeeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffWrite,
    db: Annotated[Session, Depends(get_db)],
):
    inv = _get_invoice(db, current_user.gym_id, invoice_id)
    apply_late_fee(db, gym_id=current_user.gym_id, invoice_id=inv.id, late_fee_paise=payload.late_fee_paise)
    db.commit()
    db.refresh(inv)
    return {**invoice_to_dict(inv), "total_due_paise": invoice_due_paise(db, inv)}
