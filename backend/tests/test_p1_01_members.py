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


def seed(db, gym_id=1, branch_id=1, prefix="a"):
    gym = Gym(id=gym_id, gym_id=gym_id, branch_id=None, name=f"Gym {prefix}")
    branch = Branch(id=branch_id, gym_id=gym_id, branch_id=branch_id, name=f"Branch {prefix}")
    role = Role(id=gym_id * 10 + 1, gym_id=gym_id, branch_id=branch_id, name="reception")
    user = User(
        id=gym_id * 10 + 2,
        gym_id=gym_id,
        branch_id=branch_id,
        email=f"reception{prefix}@example.com",
        full_name="Reception",
        hashed_password=get_password_hash("secret123"),
        is_active=True,
    )
    ur = UserRole(id=gym_id * 10 + 3, gym_id=gym_id, branch_id=branch_id, user_id=user.id, role_id=role.id)
    db.add_all([gym, branch, role, user, ur])
    db.commit()


def login(client: TestClient, gym_id: int, email: str) -> str:
    resp = client.post("/auth/login", json={"gym_id": gym_id, "email": email, "password": "secret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def member_payload(**overrides):
    data = {
        "full_name": "Rahul Sharma",
        "phone": "9999999999",
        "email": "rahul@example.com",
        "photo_ref": "photos/rahul.jpg",
        "kyc_id_type": "aadhaar",
        "kyc_id_number": "1234-5678-9012",
        "address": "Mumbai",
        "emergency_contact_name": "Amit Sharma",
        "emergency_contact_phone": "8888888888",
        "health_notes": "None",
        "whatsapp_consent": True,
        "whatsapp_opt_out": False,
    }
    data.update(overrides)
    return data


def test_create_read_update_member_tenant_scoped():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db, gym_id=1, branch_id=1, prefix="a")
        seed(db, gym_id=2, branch_id=2, prefix="b")

    t1 = login(client, 1, "receptiona@example.com")
    t2 = login(client, 2, "receptionb@example.com")

    # create
    r = client.post("/members", json=member_payload(), headers=auth(t1))
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["gym_id"] == 1
    assert created["full_name"] == "Rahul Sharma"
    assert created["whatsapp_opt_out"] is False
    member_id = created["id"]

    # read
    r = client.get(f"/members/{member_id}", headers=auth(t1))
    assert r.status_code == 200
    assert r.json()["phone"] == "9999999999"

    # tenant isolation
    r = client.get(f"/members/{member_id}", headers=auth(t2))
    assert r.status_code == 404

    # update
    r = client.patch(f"/members/{member_id}", json={"health_notes": "Asthma", "whatsapp_opt_out": True}, headers=auth(t1))
    assert r.status_code == 200
    assert r.json()["health_notes"] == "Asthma"
    assert r.json()["whatsapp_opt_out"] is True

    app.dependency_overrides.clear()


def test_member_validation_requires_name_and_phone():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db, gym_id=1, branch_id=1, prefix="a")
    t1 = login(client, 1, "receptiona@example.com")

    r = client.post("/members", json=member_payload(full_name="", phone=""), headers=auth(t1))
    assert r.status_code == 422
    app.dependency_overrides.clear()
