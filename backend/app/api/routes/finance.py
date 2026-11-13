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


def _revenue(db: Session, gym_id: int, start: date, end: date, branch_id: int | None = None) -> tuple[int, int]:
    query = (
        db.query(func.coalesce(func.sum(Payment.amount_paise), 0), func.count(Payment.id))
        .filter(
            Payment.gym_id == gym_id,
            Payment.status == "paid",
            Payment.paid_at >= start,
            Payment.paid_at <= end,
        )
    )
    if branch_id is not None:
        query = query.filter(Payment.branch_id == branch_id)
    revenue, count = query.one()
    return int(revenue or 0), int(count or 0)


def _expenses(db: Session, gym_id: int, start: date, end: date, branch_id: int | None = None) -> int:
    query = (
        db.query(func.coalesce(func.sum(Expense.amount_paise), 0))
        .filter(Expense.gym_id == gym_id, Expense.spent_on >= start, Expense.spent_on <= end)
    )
    if branch_id is not None:
        query = query.filter(Expense.branch_id == branch_id)
    total = query.scalar()
    return int(total or 0)


def _branch_aggregates(
    db: Session,
    gym_id: int,
    start: date,
    end: date,
) -> list[dict]:
    """Revenue, expenses, profit per branch for comparison."""
    from app.models.core import Branch

    branches = db.query(Branch).filter(Branch.gym_id == gym_id).all()
    result = []
    for branch in branches:
        revenue, count = _revenue(db, gym_id, start, end, branch_id=branch.id)
        expense = _expenses(db, gym_id, start, end, branch_id=branch.id)
        result.append({
            "branch_id": branch.id,
            "branch_name": branch.name,
            "revenue_paise": revenue,
            "expense_paise": expense,
            "profit_paise": revenue - expense,
            "payments_count": count,
        })
    return result


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
def daily_dashboard_branch(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    on_date: date | None = None,
    branch_id: int | None = None,
):
    """Daily dashboard with optional branch filter.

    - Owner/admin: sees all branches if branch_id not provided,
      or specific branch if branch_id provided.
    - Non-owner staff: automatically scoped to their assigned branch.
    """
    target = on_date or date.today()

    # If no branch_id provided and user is not owner, use their assigned branch
    if branch_id is None and current_user.branch_id is not None:
        branch_id = current_user.branch_id

    # For non-owner users, verify they have access to this branch
    if branch_id is not None and current_user.branch_id is not None:
        from app.core.rbac import check_branch_access
        check_branch_access(current_user, branch_id)

    revenue, count = _revenue(db, current_user.gym_id, target, target, branch_id=branch_id)
    expense = _expenses(db, current_user.gym_id, target, target, branch_id=branch_id)
    return {
        "on_date": target.isoformat(),
        "branch_id": branch_id,
        "revenue_paise": revenue,
        "expense_paise": expense,
        "profit_paise": revenue - expense,
        "payments_count": count,
    }


@router.get("/dashboard/summary")
def summary_dashboard_branch(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    from_date: date,
    to_date: date,
    branch_id: int | None = None,
):
    if to_date < from_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="to_date must be on/after from_date")

    # If no branch_id provided and user is not owner, use their assigned branch
    if branch_id is None and current_user.branch_id is not None:
        branch_id = current_user.branch_id

    # For non-owner users, verify they have access to this branch
    if branch_id is not None and current_user.branch_id is not None:
        from app.core.rbac import check_branch_access
        check_branch_access(current_user, branch_id)

    revenue, count = _revenue(db, current_user.gym_id, from_date, to_date, branch_id=branch_id)
    expense = _expenses(db, current_user.gym_id, from_date, to_date, branch_id=branch_id)
    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "branch_id": branch_id,
        "revenue_paise": revenue,
        "expense_paise": expense,
        "profit_paise": revenue - expense,
        "payments_count": count,
    }


@router.get("/dashboard/branch-comparison")
def branch_comparison(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    from_date: date,
    to_date: date,
):
    """Cross-branch comparison for owner/admin. Returns per-branch aggregates.

    Owner can see all branches. Non-owner staff will be denied (403).
    """
    if to_date < from_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="to_date must be on/after from_date")

    branches = _branch_aggregates(db, current_user.gym_id, from_date, to_date)
    # Totals
    total_revenue = sum(b["revenue_paise"] for b in branches)
    total_expense = sum(b["expense_paise"] for b in branches)
    total_profit = total_revenue - total_expense
    total_payments = sum(b["payments_count"] for b in branches)
    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "branches": branches,
        "totals": {
            "revenue_paise": total_revenue,
            "expense_paise": total_expense,
            "profit_paise": total_profit,
            "payments_count": total_payments,
        },
    }