from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.core import Role, User, UserRole
from app.services import ratelimit as rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "gymos_token"

# ponytail: one-time bcrypt hash (~200ms at import) so unknown-user logins take
# the same time as wrong-password logins, preventing user enumeration by timing.
_DUMMY_HASH = get_password_hash("gymos-dummy-password")


class LoginRequest(BaseModel):
    gym_id: int
    email: EmailStr
    password: str


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Annotated[Session, Depends(get_db)]):
    ip = request.client.host if request.client else "unknown"

    # Rate limit login attempts per IP+account unless in the dev environment.
    # ponytail: dev/test bypass; enforced in staging/production.
    if settings.app_env.lower() not in {"development", "test"}:
        allowed, _remaining = rate_limiter.allow(
            f"login:{ip}:{payload.gym_id}:{payload.email}",
            limit=settings.login_rate_limit_per_minute,
            window_seconds=60,
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    user = (
        db.query(User)
        .filter(User.gym_id == payload.gym_id, User.email == str(payload.email))
        .first()
    )
    if user is None:
        # Constant-time-ish: run a dummy verify so unknown users cost the same as wrong passwords.
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    roles = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id, UserRole.gym_id == user.gym_id)
        .all()
    )
    role_names = [r[0] for r in roles]
    token = create_access_token({"sub": str(user.id), "gym_id": user.gym_id, "roles": role_names})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@router.get("/me")
def me(current_user: Annotated[User, Depends(get_current_user)]):
    roles = getattr(current_user, "role_names", [])
    return {
        "id": current_user.id,
        "email": current_user.email,
        "gym_id": current_user.gym_id,
        "branch_id": current_user.branch_id,
        "roles": roles,
    }
