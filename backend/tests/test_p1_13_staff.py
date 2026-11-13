from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch, Gym, Role, User, UserRole


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
    db.add_all([
        UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
        UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2),
    ])
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_staff_attendance_manual_and_duplicate():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/staff-attendance", json={
        "user_id": 2, "on_date": "2026-01-05", "status": "present",
        "check_in": "06:00", "check_out": "10:00", "notes": "morning shift",
    }, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "present"

    r = client.post("/staff-attendance", json={"user_id": 2, "on_date": "2026-01-05", "status": "absent"}, headers=h)
    assert r.status_code == 409

    r = client.get("/staff-attendance?user_id=2&month=2026-01", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.post("/staff-attendance", json={"user_id": 3, "on_date": "2026-01-05", "status": "present"}, headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_payroll_calculation_and_finalize():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/payroll", json={
        "user_id": 2, "month": "2026-01",
        "base_paise": 2500000, "bonus_paise": 200000, "deductions_paise": 50000,
    }, headers=h)
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["net_paise"] == 2650000
    assert rec["status"] == "draft"

    r = client.post("/payroll", json={"user_id": 2, "month": "2026-01", "base_paise": 100}, headers=h)
    assert r.status_code == 409

    r = client.post(f"/payroll/{rec['id']}/finalize", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "finalized"

    r = client.get("/payroll?month=2026-01", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    app.dependency_overrides.clear()
