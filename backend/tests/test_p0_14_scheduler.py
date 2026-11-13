from app.worker import celery_app, sample_reminder_task


def test_sample_reminder_task_runs_in_eager_mode():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    result = sample_reminder_task.delay(gym_id=1, message="expiry reminder")
    assert result.get(timeout=5) == {"status": "queued", "gym_id": 1, "message": "expiry reminder"}


def test_celery_app_configured():
    assert celery_app.main == "gymos"
    assert "sample_reminder_task" in celery_app.tasks or any(
        name.endswith("sample_reminder_task") for name in celery_app.tasks
    )
