from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.expense import Expense
from app.models.payment import Payment

router = APIRouter(tags=["finance"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]


class ExpenseCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=80)
    amount_paise: int = Field(..., gt=0)
    spent_on: date
    vendor: str | None = None
    notes: str | None = None


def _expense_dict(e: Expense) -> dict:
    return {
        "id": e.id,
        "gym_id": e.gym_id,
        "branch_id": e.branch_id,
        "category": e.category,
        "amount_paise": e.amount_paise,
        "spent_on": e.spent_on.isoformat(),
        "vendor": e.vendor,
        "notes": e.notes,
    }


def _revenue(db: Session, gym_id: int, start: date, end: date) -> tuple[int, int]:
    revenue, count = (
        db.query(func.coalesce(func.sum(Payment.amount_paise), 0), func.count(Payment.id))
        .filter(
            Payment.gym_id == gym_id,
            Payment.status == "paid",
            Payment.paid_at >= start,
            Payment.paid_at <= end,
        )
        .one()
    )
    return int(revenue or 0), int(count or 0)


def _expenses(db: Session, gym_id: int, start: date, end: date) -> int:
    total = (
        db.query(func.coalesce(func.sum(Expense.amount_paise), 0))
        .filter(Expense.gym_id == gym_id, Expense.spent_on >= start, Expense.spent_on <= end)
        .scalar()
    )
    return int(total or 0)


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    expense = Expense(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        category=payload.category,
        amount_paise=payload.amount_paise,
        spent_on=payload.spent_on,
        vendor=payload.vendor,
        notes=payload.notes,
        recorded_by=current_user.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return _expense_dict(expense)


@router.get("/expenses")
def list_expenses(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    month: str | None = None,
    on_date: date | None = None,
    category: str | None = None,
):
    query = db.query(Expense).filter(Expense.gym_id == current_user.gym_id)
    if month is not None:
        year, mon = (int(part) for part in month.split("-"))
        start = date(year, mon, 1)
        end = date(year + (mon == 12), 1 if mon == 12 else mon + 1, 1)
        query = query.filter(Expense.spent_on >= start, Expense.spent_on < end)
    if on_date is not None:
        query = query.filter(Expense.spent_on == on_date)
    if category is not None:
        query = query.filter(Expense.category == category)
    items = query.order_by(Expense.spent_on.desc(), Expense.id.desc()).all()
    return {"items": [_expense_dict(e) for e in items], "total": len(items)}


@router.get("/dashboard/daily")
def daily_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    on_date: date | None = None,
):
    target = on_date or date.today()
    revenue, count = _revenue(db, current_user.gym_id, target, target)
    expense = _expenses(db, current_user.gym_id, target, target)
    return {
        "on_date": target.isoformat(),
        "revenue_paise": revenue,
        "expense_paise": expense,
        "profit_paise": revenue - expense,
        "payments_count": count,
    }


@router.get("/dashboard/summary")
def summary_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    from_date: date,
    to_date: date,
):
    if to_date < from_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="to_date must be on/after from_date")
    revenue, count = _revenue(db, current_user.gym_id, from_date, to_date)
    expense = _expenses(db, current_user.gym_id, from_date, to_date)
    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "revenue_paise": revenue,
        "expense_paise": expense,
        "profit_paise": revenue - expense,
        "payments_count": count,
    }

