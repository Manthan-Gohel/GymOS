from __future__ import annotations

import os
from datetime import date

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

celery_app = Celery("gymos", broker=broker_url, backend=result_backend)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "daily-reminders-all-gyms": {
            "task": "app.worker.run_all_gyms_reminders_task",
            "schedule": 60 * 60 * 24,
        },
        "daily-expiry-all-gyms": {
            "task": "app.worker.expire_all_gyms_task",
            "schedule": 60 * 60 * 24,
        },
    },
)


@celery_app.task(name="app.worker.sample_reminder_task")
def sample_reminder_task(gym_id: int, message: str) -> dict:
    """Sample scheduled/reminder task for dev/test validation."""
    return {"status": "queued", "gym_id": gym_id, "message": message}


@celery_app.task(name="app.worker.run_reminders_task")
def run_reminders_task(gym_id: int, today: str | None = None) -> dict:
    """Scheduled reminder batch for one tenant (welcome/expiry/payment due)."""
    from app.db.session import SessionLocal
    from app.services.reminders import run_reminders

    with SessionLocal() as db:
        logs = run_reminders(db, gym_id=gym_id, today=date.fromisoformat(today) if today else None)
        db.commit()
        return {
            "gym_id": gym_id,
            "sent": sum(1 for log in logs if log.status == "sent"),
            "blocked": sum(1 for log in logs if log.status == "blocked"),
            "failed": sum(1 for log in logs if log.status == "failed"),
        }


@celery_app.task(name="app.worker.run_all_gyms_reminders_task")
def run_all_gyms_reminders_task(today: str | None = None) -> dict:
    """Daily beat task: run reminders for every tenant."""
    from app.db.session import SessionLocal
    from app.models.core import Gym
    from app.services.reminders import run_reminders

    totals = {"sent": 0, "blocked": 0, "failed": 0, "gyms": 0}
    target = date.fromisoformat(today) if today else None
    with SessionLocal() as db:
        for gym in db.query(Gym).all():
            logs = run_reminders(db, gym_id=gym.gym_id, today=target)
            totals["sent"] += sum(1 for log in logs if log.status == "sent")
            totals["blocked"] += sum(1 for log in logs if log.status == "blocked")
            totals["failed"] += sum(1 for log in logs if log.status == "failed")
            totals["gyms"] += 1
        db.commit()
    return totals


@celery_app.task(name="app.worker.expire_all_gyms_task")
def expire_all_gyms_task() -> dict:
    """Daily beat task: expire lapsed memberships for every tenant."""
    from app.db.session import SessionLocal
    from app.models.core import Gym
    from app.services.memberships import expire_due_memberships

    expired = 0
    with SessionLocal() as db:
        for gym in db.query(Gym).all():
            expired += expire_due_memberships(db, gym_id=gym.gym_id, today=date.today())
        db.commit()
    return {"expired": expired}
