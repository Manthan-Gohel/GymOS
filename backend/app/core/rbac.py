from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.core import User


def require_roles(
    allowed_roles: list[str],
    *,
    branch_scoped: bool = False,
) -> Callable:
    """
    Dependency that checks if the current user has one of the allowed roles.

    If branch_scoped=True, the user can only access data for their assigned branch.
    The caller must also pass branch_id via a kwarg or the function must handle
    branch filtering at the route level.

    Usage:
        - require_roles(["owner", "admin"])  - standard role check
        - require_roles(["reception"], branch_scoped=True) - reception scoped to user's branch
    """
    allowed = set(allowed_roles)

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        user_roles = set(getattr(current_user, "role_names", []) or [])
        if not user_roles.intersection(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return dependency


def check_branch_access(
    current_user: Annotated[User, Depends(get_current_user)],
    target_branch_id: int,
) -> User:
    """
    Verify that the current user has access to the target branch.

    - Users with branch_id == target_branch_id always have access
    - Users with branch_id == None (owner) have access to all branches
    - Others are denied

    Raises 403 if access is denied.
    """
    # Owner (branch_id is None) can access all branches
    if current_user.branch_id is None:
        return current_user

    # Staff can only access their assigned branch
    if current_user.branch_id == target_branch_id:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: this endpoint is scoped to branch {target_branch_id}, "
               f"but user is assigned to branch {current_user.branch_id}",
    )