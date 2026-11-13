from __future__ import annotations

from datetime import UTC, date, datetime, time

from sqlalchemy import Date, DateTime, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StaffAttendance(Base):
    __tablename__ = "staff_attendance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    on_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="present")
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "on_date", name="uq_staff_attendance_user_date"),)


class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM

    base_paise: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus_paise: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deductions_paise: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_paise: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (UniqueConstraint("user_id", "month", name="uq_payroll_user_month"),)
