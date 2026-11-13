from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    trainer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class TrainerAttendance(Base):
    __tablename__ = "trainer_attendance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    trainer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
