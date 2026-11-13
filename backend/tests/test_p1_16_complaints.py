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
        Role(id=2, gym_id=1, branch_id=1, name="reception"),
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="front@example.com", full_name="Front Desk", hashed_password=get_password_hash("secret123"), is_active=True),
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999"),
        Member(id=2, gym_id=2, branch_id=9, full_name="Other", phone="111"),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.add(UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2))
    db.commit()


def auth(client, email="owner@example.com"):
    r = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_complaint_intake_assign_resolve():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client, "front@example.com")
    r = client.post("/complaints", json={
        "member_id": 1, "category": "equipment", "description": "Treadmill belt slipping"
    }, headers=h)
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["status"] == "open"
    cid = c["id"]

    r = client.get("/complaints?status=open", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.patch(f"/complaints/{cid}", json={
        "status": "resolved", "assigned_to": 1, "resolution_notes": "Belt replaced"
    }, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "resolved"
    assert r.json()["assigned_to"] == 1
    assert r.json()["resolution_notes"] == "Belt replaced"

    r = client.get("/complaints?status=open", headers=h)
    assert r.json()["total"] == 0

    r = client.patch(f"/complaints/{cid}", json={"status": "bogus"}, headers=h)
    assert r.status_code == 422
    app.dependency_overrides.clear()


def test_complaint_validation_and_tenant_isolation():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/complaints", json={"category": "noise", "description": ""}, headers=h)
    assert r.status_code == 422

    r = client.post("/complaints", json={"member_id": 2, "category": "noise", "description": "too loud"}, headers=h)
    assert r.status_code == 404

    r = client.get("/complaints/999", headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()
