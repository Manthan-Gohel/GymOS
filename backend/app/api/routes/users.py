from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import Role, User, UserRole

router = APIRouter(prefix="/users", tags=["users"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]


@router.get("")
def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
    is_active: bool | None = None,
):
    query = db.query(User).filter(User.gym_id == current_user.gym_id)
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    users = query.order_by(User.id).all()

    role_rows = (
        db.query(UserRole.user_id, Role.name)
        .join(Role, Role.id == UserRole.role_id)
        .filter(UserRole.gym_id == current_user.gym_id)
        .all()
    )
    roles_by_user: dict[int, list[str]] = {}
    for user_id, role_name in role_rows:
        roles_by_user.setdefault(user_id, []).append(role_name)

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "branch_id": u.branch_id,
                "is_active": u.is_active,
                "roles": roles_by_user.get(u.id, []),
            }
            for u in users
        ],
        "total": len(users),
    }
