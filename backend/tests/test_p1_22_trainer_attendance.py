from datetime import time

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
        Role(id=2, gym_id=1, branch_id=1, name="trainer"),
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="coach@example.com", full_name="Coach A", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=3, gym_id=1, branch_id=1, email="coach2@example.com", full_name="Coach B", hashed_password=get_password_hash("secret123"), is_active=True),
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999"),
        Trainer(id=1, gym_id=1, branch_id=1, full_name="Coach A", phone="77777", user_id=2),
        Trainer(id=2, gym_id=1, branch_id=1, full_name="Coach B", phone="66666", user_id=3),
        TrainerAvailability(id=1, gym_id=1, branch_id=1, trainer_id=1, weekday=0, start_time=time(6, 0), end_time=time(10, 0)),
        TrainerAvailability(id=2, gym_id=1, branch_id=1, trainer_id=2, weekday=0, start_time=time(6, 0), end_time=time(10, 0)),
    ])
    db.flush()
    db.add_all([
        UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
        UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2),
        UserRole(id=3, gym_id=1, branch_id=1, user_id=3, role_id=2),
    ])
    db.commit()


def auth(client, email="owner@example.com"):
    r = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def book(client, h, trainer_id=1):
    return client.post("/sessions", json={
        "trainer_id": trainer_id,
        "member_id": 1,
        "start_at": "2026-01-05T06:00:00",
        "end_at": "2026-01-05T07:00:00",
    }, headers=h)


def test_trainer_records_own_session_and_cannot_record_other_trainers():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    owner = auth(client)
    session_id = book(client, owner).json()["id"]

    other = auth(client, "coach2@example.com")
    r = client.post(f"/sessions/{session_id}/attendance", json={
        "checked_in_at": "2026-01-05T06:05:00"
    }, headers=other)
    assert r.status_code == 403

    own = auth(client, "coach@example.com")
    r = client.post(f"/sessions/{session_id}/attendance", json={
        "checked_in_at": "2026-01-05T06:05:00"
    }, headers=own)
    assert r.status_code == 201, r.text

    r = client.get("/sessions?trainer_id=1", headers=own)
    assert r.status_code == 200
    app.dependency_overrides.clear()


def test_reception_can_still_record_attendance():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    owner = auth(client)
    session_id = book(client, owner).json()["id"]
    r = client.post(f"/sessions/{session_id}/attendance", json={
        "checked_in_at": "2026-01-05T06:05:00"
    }, headers=owner)
    assert r.status_code == 201, r.text
    app.dependency_overrides.clear()
