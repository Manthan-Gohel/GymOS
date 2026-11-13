"""VULN-004: KYC ID and health notes are not exposed to every staff role."""
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
        Role(id=3, gym_id=1, branch_id=1, name="trainer"),
        User(id=1, gym_id=1, branch_id=None, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="reception@example.com", full_name="Reception", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=3, gym_id=1, branch_id=1, email="trainer@example.com", full_name="Trainer", hashed_password=get_password_hash("secret123"), is_active=True),
    ])
    db.flush()
    db.add_all([
        UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
        UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2),
        UserRole(id=3, gym_id=1, branch_id=1, user_id=3, role_id=3),
    ])
    db.commit()


def auth(client, email):
    r = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_member(client, headers):
    r = client.post("/members", json={
        "full_name": "Rahul", "phone": "9999999999",
        "kyc_id_type": "aadhaar", "kyc_id_number": "1234-5678-9012",
        "health_notes": "Asthma",
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_reception_sees_masked_kyc_but_health_notes():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client, "reception@example.com")
    mid = create_member(client, h)

    r = client.get(f"/members/{mid}", headers=h)
    assert r.status_code == 200
    assert r.json()["kyc_id_number"] == "****9012"
    assert r.json()["health_notes"] == "Asthma"
    app.dependency_overrides.clear()


def test_trainer_gets_no_kyc_and_no_health_notes():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    hr = auth(client, "reception@example.com")
    mid = create_member(client, hr)
    ht = auth(client, "trainer@example.com")

    r = client.get(f"/members/{mid}", headers=ht)
    assert r.status_code == 200
    assert r.json()["kyc_id_number"] is None or str(r.json()["kyc_id_number"]).startswith("****")
    assert r.json()["health_notes"] is None
    app.dependency_overrides.clear()


def test_owner_sees_full_pii():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    hr = auth(client, "reception@example.com")
    mid = create_member(client, hr)
    ho = auth(client, "owner@example.com")

    r = client.get(f"/members/{mid}", headers=ho)
    assert r.status_code == 200
    assert r.json()["kyc_id_number"] == "1234-5678-9012"
    assert r.json()["health_notes"] == "Asthma"
    app.dependency_overrides.clear()
