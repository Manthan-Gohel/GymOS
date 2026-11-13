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
    roles = {}
    for i, name in enumerate(["owner", "reception"], start=1):
        r = Role(id=gym_id * 100 + i, gym_id=gym_id, branch_id=branch_id, name=name)
        db.add(r)
        roles[name] = r
    db.flush()
    users = {}
    for i, name in enumerate(["owner", "reception"], start=1):
        u = User(
            id=gym_id * 100 + 10 + i,
            gym_id=gym_id,
            branch_id=branch_id,
            email=f"{name}{prefix}@example.com",
            full_name=name,
            hashed_password=get_password_hash("secret123"),
            is_active=True,
        )
        db.add(u)
        db.flush()
        db.add(UserRole(id=gym_id * 100 + 20 + i, gym_id=gym_id, branch_id=branch_id, user_id=u.id, role_id=roles[name].id))
        users[name] = u
    db.add_all([gym, branch])
    db.commit()


def login(client, gym_id, email):
    r = client.post("/auth/login", json={"gym_id": gym_id, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def plan_payload(**overrides):
    data = {
        "name": "Monthly",
        "duration_days": 30,
        "price_paise": 150000,
        "currency": "INR",
        "terms": {"access": "gym", "freeze_allowed": True},
        "is_active": True,
    }
    data.update(overrides)
    return data


def test_plan_crud_and_tenant_scoping():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db, 1, 1, "a")
        seed(db, 2, 2, "b")
    owner1 = login(client, 1, "ownera@example.com")
    owner2 = login(client, 2, "ownerb@example.com")

    r = client.post("/plans", json=plan_payload(), headers=owner1)
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["gym_id"] == 1
    assert plan["name"] == "Monthly"
    pid = plan["id"]

    r = client.get("/plans", headers=owner1)
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    r = client.get(f"/plans/{pid}", headers=owner2)
    assert r.status_code == 404  # tenant isolation

    r = client.patch(f"/plans/{pid}", json={"price_paise": 175000, "name": "Monthly Plus"}, headers=owner1)
    assert r.status_code == 200
    assert r.json()["price_paise"] == 175000
    assert r.json()["name"] == "Monthly Plus"

    app.dependency_overrides.clear()


def test_plan_rbac_write_denied_for_reception():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db, 1, 1, "a")
    reception = login(client, 1, "receptiona@example.com")
    r = client.post("/plans", json=plan_payload(), headers=reception)
    assert r.status_code == 403
    app.dependency_overrides.clear()
