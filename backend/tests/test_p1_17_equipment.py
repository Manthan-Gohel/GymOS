from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch, Gym, Role, User, UserRole
from app.providers.messaging import MockMessagingProvider
from app.services.maintenance import run_maintenance_reminders


def setup_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def seed(db):
    db.add_all([
        Gym(id=1, gym_id=1, branch_id=None, name="Gym A"),
        Branch(id=1, gym_id=1, branch_id=1, name="Main"),
        Role(id=1, gym_id=1, branch_id=1, name="owner"),
        Role(id=2, gym_id=1, branch_id=1, name="trainer"),
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="coach@example.com", full_name="Coach", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=3, gym_id=2, branch_id=9, email="other@example.com", full_name="Other", hashed_password=get_password_hash("secret123"), is_active=True),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.add(UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2))
    db.commit()


def auth(client, email="owner@example.com"):
    r = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_equipment_registry_and_tenant_isolation():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/equipment", json={
        "name": "Treadmill 1", "category": "cardio", "serial_number": "TR-001",
        "purchased_on": "2025-06-01", "notes": "belt replaced 2026-01",
    }, headers=h)
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    assert r.json()["status"] == "operational"

    r = client.get("/equipment?category=cardio", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.patch(f"/equipment/{eid}", json={"status": "under_maintenance"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "under_maintenance"

    r = client.patch(f"/equipment/{eid}", json={"status": "exploded"}, headers=h)
    assert r.status_code == 422
    r = client.get("/equipment/999", headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_maintenance_schedule_complete_and_due_list():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    eid = client.post("/equipment", json={"name": "Rack", "category": "strength"}, headers=h).json()["id"]

    r = client.post(f"/equipment/{eid}/maintenance", json={
        "title": "Quarterly bolt check", "due_on": "2026-01-10", "interval_days": 90,
    }, headers=h)
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    assert r.json()["status"] == "scheduled"

    r = client.get("/maintenance?due_on=2026-01-15", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.post(f"/maintenance/{mid}/complete", json={
        "completed_on": "2026-01-09", "notes": "all bolts torqued"
    }, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "done"
    assert body["completed_on"] == "2026-01-09"
    # recurring schedule spawns next occurrence
    assert body["next_schedule_id"] is not None

    r = client.get("/maintenance?due_on=2026-01-15", headers=h)
    assert r.json()["total"] == 0
    app.dependency_overrides.clear()


def test_maintenance_reminders_are_logged_and_idempotent():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    eid = client.post("/equipment", json={"name": "Bike 1", "category": "cardio"}, headers=h).json()["id"]
    client.post(f"/equipment/{eid}/maintenance", json={"title": "Chain lube", "due_on": "2026-01-12"}, headers=h)

    r = client.post("/maintenance/run-reminders", json={"today": "2026-01-10"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["sent"] == 1

    r = client.post("/maintenance/run-reminders", json={"today": "2026-01-10"}, headers=h)
    assert r.json()["sent"] == 0

    with SessionLocal() as db:
        provider = MockMessagingProvider()
        logs = run_maintenance_reminders(db, gym_id=1, today=date(2026, 1, 11), provider=provider)
        db.commit()
        assert len(logs) == 1
        assert logs[0].status == "sent"
        assert "Chain lube" in logs[0].body
        assert logs[0].why == "maintenance:1:2026-01-11"

    r = client.get("/messages?status=sent", headers=h)
    assert r.json()["total"] >= 2
    app.dependency_overrides.clear()


def test_trainer_cannot_manage_equipment():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client, "coach@example.com")
    r = client.post("/equipment", json={"name": "Bench", "category": "strength"}, headers=h)
    assert r.status_code == 403
    r = client.get("/equipment", headers=h)
    assert r.status_code == 200
    app.dependency_overrides.clear()
