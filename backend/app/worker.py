from __future__ import annotations

import os

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
)


@celery_app.task(name="app.worker.sample_reminder_task")
def sample_reminder_task(gym_id: int, message: str) -> dict:
    """Sample scheduled/reminder task for dev/test validation."""
    return {"status": "queued", "gym_id": gym_id, "message": message}
