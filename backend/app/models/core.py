from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Gym(Base):
    __tablename__ = "gyms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # VULN-002: unforgeable per-gym token used in the webhook URL path
    webhook_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id"), nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    __table_args__ = (UniqueConstraint("gym_id", "email", name="uq_users_gym_email"),)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id"), nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # owner/admin/reception/trainer

    __table_args__ = (UniqueConstraint("gym_id", "branch_id", "name", name="uq_roles_scope_name"),)


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id"), nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)
