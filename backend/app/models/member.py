from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(nullable=False, index=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    photo_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kyc_id_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kyc_id_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    emergency_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    health_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    whatsapp_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
