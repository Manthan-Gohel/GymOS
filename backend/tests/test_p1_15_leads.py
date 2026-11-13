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
        Role(id=2, gym_id=1, branch_id=1, name="reception"),
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="front@example.com", full_name="Front Desk", hashed_password=get_password_hash("secret123"), is_active=True),
    ])
    db.flush()
    db.add_all([
        UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
        UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2),
    ])
    db.commit()


def login(client, email):
    r = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_lead_capture_trial_and_conversion_pipeline():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = login(client, "front@example.com")
    r = client.post("/leads", json={"full_name": "Priya", "phone": "90000", "source": "walk_in"}, headers=h)
    assert r.status_code == 201, r.text
    lead = r.json()
    assert lead["status"] == "new"
    lid = lead["id"]

    r = client.post("/leads", json={"full_name": "Amit", "phone": "91111", "source": "instagram"}, headers=h)
    assert r.status_code == 201

    r = client.get("/leads?status=new", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    r = client.patch(f"/leads/{lid}", json={
        "status": "trial_booked", "trial_date": "2026-01-10", "notes": "wants morning slot", "assigned_to": 2
    }, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "trial_booked"
    assert r.json()["trial_date"] == "2026-01-10"

    r = client.patch(f"/leads/{lid}", json={"status": "converted"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "converted"

    r = client.patch(f"/leads/{lid}", json={"status": "bogus"}, headers=h)
    assert r.status_code == 422
    app.dependency_overrides.clear()


def test_lead_tenant_isolation():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add_all([Gym(id=2, gym_id=2, branch_id=None, name="Gym B")])
        db.commit()
    h = login(client, "front@example.com")
    client.post("/leads", json={"full_name": "Local", "phone": "1"}, headers=h)
    r = client.get("/leads/999", headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()
