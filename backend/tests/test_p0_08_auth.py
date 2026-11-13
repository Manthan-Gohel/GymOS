from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch, Gym, Role, User, UserRole


def setup_test_app():
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
    return engine, TestingSessionLocal


def seed(session: Session):
    gym = Gym(id=1, gym_id=1, branch_id=None, name="Gym A")
    branch = Branch(id=1, gym_id=1, branch_id=1, name="Main")
    user = User(
        id=1,
        gym_id=1,
        branch_id=1,
        email="owner@example.com",
        full_name="Owner",
        hashed_password=get_password_hash("secret123"),
        is_active=True,
    )
    role = Role(id=1, gym_id=1, branch_id=1, name="owner")
    ur = UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1)
    session.add_all([gym, branch, user, role, ur])
    session.commit()


def test_login_success_returns_jwt_with_claims():
    _, SessionLocal = setup_test_app()
    with SessionLocal() as db:
        seed(db)
    client = TestClient(app)
    resp = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]
    # decode via app logic endpoint/me-like check
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["email"] == "owner@example.com"
    assert me_data["gym_id"] == 1
    assert "owner" in me_data.get("roles", [])
    app.dependency_overrides.clear()


def test_login_failure_wrong_password():
    _, SessionLocal = setup_test_app()
    with SessionLocal() as db:
        seed(db)
    client = TestClient(app)
    resp = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "wrong"})
    assert resp.status_code == 401
    app.dependency_overrides.clear()


def test_expired_token_rejected():
    _, SessionLocal = setup_test_app()
    with SessionLocal() as db:
        seed(db)
    token = create_access_token({"sub": "1", "gym_id": 1, "roles": ["owner"]}, expires_delta=timedelta(seconds=-1))
    client = TestClient(app)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    app.dependency_overrides.clear()
