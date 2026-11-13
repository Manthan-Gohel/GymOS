from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session


class TenantScopeError(ValueError):
    """Raised when an operation violates tenant scope."""


def scoped_query(db: Session, model: type[Any], *, gym_id: int, branch_id: int | None = None):
    """Return a tenant-scoped select for the given model (composable)."""
    _ = db  # kept for API consistency; execution via db.scalars/db.execute
    if not hasattr(model, "gym_id"):
        raise TenantScopeError(f"{model.__name__} is not tenant-scoped (missing gym_id)")
    stmt = select(model).where(model.gym_id == gym_id)
    if branch_id is not None and hasattr(model, "branch_id"):
        stmt = stmt.where(model.branch_id == branch_id)
    return stmt


def assert_tenant_match(obj: Any, *, gym_id: int, branch_id: int | None = None) -> None:
    obj_gym = getattr(obj, "gym_id", None)
    if obj_gym != gym_id:
        raise TenantScopeError(f"gym_id mismatch: expected {gym_id}, got {obj_gym}")
    if branch_id is not None:
        obj_branch = getattr(obj, "branch_id", None)
        if obj_branch != branch_id:
            raise TenantScopeError(f"branch_id mismatch: expected {branch_id}, got {obj_branch}")


def tenant_add(db: Session, obj: Any, *, gym_id: int, branch_id: int | None = None) -> Any:
    """Add object to session only if it matches tenant scope."""
    assert_tenant_match(obj, gym_id=gym_id, branch_id=branch_id)
    db.add(obj)
    return obj
