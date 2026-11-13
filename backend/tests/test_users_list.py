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
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="front@example.com", full_name="Front Desk", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=3, gym_id=2, branch_id=9, email="other@example.com", full_name="Other", hashed_password=get_password_hash("secret123"), is_active=True),
    ])
    db.flush()
    db.add_all([
        UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
        UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2),
    ])
    db.commit()


def auth(client, email="owner@example.com"):
    r = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_list_users_tenant_scoped_with_roles():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.get("/users", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    by_email = {u["email"]: u for u in body["items"]}
    assert by_email["owner@example.com"]["roles"] == ["owner"]
    assert by_email["front@example.com"]["roles"] == ["reception"]

    r = client.get("/users?is_active=false", headers=h)
    assert r.json()["total"] == 0
    app.dependency_overrides.clear()


def test_reception_cannot_list_users():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client, "front@example.com")
    r = client.get("/users", headers=h)
    assert r.status_code == 403
    app.dependency_overrides.clear()
