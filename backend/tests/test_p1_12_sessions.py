from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch, Gym, Role, User, UserRole
from app.models.member import Member
from app.models.trainer import Trainer, TrainerAvailability


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
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999"),
        Member(id=2, gym_id=1, branch_id=1, full_name="Anita", phone="88888"),
        Trainer(id=1, gym_id=1, branch_id=1, full_name="Coach A", phone="77777"),
        TrainerAvailability(id=1, gym_id=1, branch_id=1, trainer_id=1, weekday=0, start_time=__import__("datetime").time(6, 0), end_time=__import__("datetime").time(10, 0)),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def book(client, h, trainer_id=1, member_id=1, start="2026-01-05T06:00:00", end="2026-01-05T07:00:00"):
    return client.post("/sessions", json={
        "trainer_id": trainer_id, "member_id": member_id, "start_at": start, "end_at": end
    }, headers=h)


def test_book_within_availability_and_reject_outside_and_overlap():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    # 2026-01-05 is a Monday
    r = book(client, h)
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert r.json()["status"] == "scheduled"

    # outside 06:00-10:00 Monday
    r = book(client, h, member_id=2, start="2026-01-05T11:00:00", end="2026-01-05T12:00:00")
    assert r.status_code == 409

    # overlap same trainer
    r = book(client, h, member_id=2)
    assert r.status_code == 409

    # different trainer has no availability restrictions -> allowed
    client.post("/trainers", json={"full_name": "Coach B", "phone": "66666"}, headers=h)
    r = book(client, h, trainer_id=2, member_id=2)
    assert r.status_code == 201

    # list and reschedule
    r = client.get("/sessions?trainer_id=1", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    r = client.post(f"/sessions/{sid}/reschedule", json={"start_at": "2026-01-05T08:00:00", "end_at": "2026-01-05T09:00:00"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["start_at"].startswith("2026-01-05T08:00")
    app.dependency_overrides.clear()


def test_cancel_and_trainer_attendance():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    sid = book(client, h).json()["id"]

    r = client.post(f"/sessions/{sid}/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # cancelled session frees the slot
    r = book(client, h, member_id=2)
    assert r.status_code == 201
    sid2 = r.json()["id"]

    r = client.post(f"/sessions/{sid2}/attendance", json={
        "checked_in_at": "2026-01-05T05:55:00", "checked_out_at": "2026-01-05T07:05:00"
    }, headers=h)
    assert r.status_code == 201, r.text
    att = r.json()
    assert att["session_id"] == sid2
    r = client.get(f"/sessions/{sid2}/attendance", headers=h)
    assert r.status_code == 200
    assert r.json()["items"][0]["checked_out_at"].startswith("2026-01-05T07:05")
    r = client.get(f"/sessions/{sid2}", headers=h)
    assert r.json()["status"] == "completed"
    app.dependency_overrides.clear()


def test_session_tenant_isolation():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add_all([
            Gym(id=2, gym_id=2, branch_id=None, name="Gym B"),
            Member(id=3, gym_id=2, branch_id=9, full_name="Other", phone="111"),
        ])
        db.commit()
    h = auth(client)
    r = book(client, h, member_id=3)
    assert r.status_code == 404
    r = client.get("/sessions/999", headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()
