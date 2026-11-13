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
        Member(id=2, gym_id=2, branch_id=9, full_name="Other", phone="111"),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_trainer_crud_and_availability():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/trainers", json={"full_name": "Coach Vikram", "phone": "77777", "specialty": "Strength"}, headers=h)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = client.post(f"/trainers/{tid}/availability", json={"weekday": 1, "start_time": "06:00", "end_time": "09:00"}, headers=h)
    assert r.status_code == 201, r.text
    slot = r.json()["id"]

    r = client.post(f"/trainers/{tid}/availability", json={"weekday": 1, "start_time": "09:00", "end_time": "08:00"}, headers=h)
    assert r.status_code == 422

    r = client.get(f"/trainers/{tid}/availability", headers=h)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["start_time"] == "06:00"

    r = client.delete(f"/trainers/{tid}/availability/{slot}", headers=h)
    assert r.status_code == 204
    r = client.get(f"/trainers/{tid}/availability", headers=h)
    assert r.json()["items"] == []

    r = client.patch(f"/trainers/{tid}", json={"specialty": "Powerlifting", "is_active": False}, headers=h)
    assert r.status_code == 200
    assert r.json()["specialty"] == "Powerlifting"
    assert r.json()["is_active"] is False
    app.dependency_overrides.clear()


def test_member_assignment_and_tenant_isolation():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    tid = client.post("/trainers", json={"full_name": "Coach A", "phone": "77777"}, headers=h).json()["id"]

    r = client.post(f"/trainers/{tid}/assign", json={"member_id": 1}, headers=h)
    assert r.status_code == 201, r.text
    r = client.post(f"/trainers/{tid}/assign", json={"member_id": 1}, headers=h)
    assert r.status_code == 409

    r = client.get(f"/trainers/{tid}/members", headers=h)
    assert r.status_code == 200
    assert [m["member_id"] for m in r.json()["items"]] == [1]

    r = client.post(f"/trainers/{tid}/assign", json={"member_id": 2}, headers=h)
    assert r.status_code == 404

    r = client.delete(f"/trainers/{tid}/assign/1", headers=h)
    assert r.status_code == 204
    r = client.get(f"/trainers/{tid}/members", headers=h)
    assert r.json()["items"] == []
    app.dependency_overrides.clear()
