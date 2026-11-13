from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.core import User


def require_roles(allowed_roles: list[str]) -> Callable:
    allowed = set(allowed_roles)

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        user_roles = set(getattr(current_user, "role_names", []) or [])
        if not user_roles.intersection(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return dependency
