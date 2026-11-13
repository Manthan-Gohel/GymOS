from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.core import Role, User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    gym_id: int
    email: EmailStr
    password: str


@router.post("/login")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = (
        db.query(User)
        .filter(User.gym_id == payload.gym_id, User.email == str(payload.email))
        .first()
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    roles = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id, UserRole.gym_id == user.gym_id)
        .all()
    )
    role_names = [r[0] for r in roles]
    token = create_access_token({"sub": str(user.id), "gym_id": user.gym_id, "roles": role_names})
    return {"access_token": token, "token_type": "bearer"}


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
