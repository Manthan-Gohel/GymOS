from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rbac import require_roles
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.models.core import Branch, Gym, Role, User, UserRole


def make_app():
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

    app = FastAPI()
    app.dependency_overrides[get_db] = override_get_db

    router = APIRouter()

    @router.get("/owner-only")
    def owner_only(user: Annotated[object, Depends(require_roles(["owner"]))]):
        return {"ok": True}

    @router.get("/staff")
    def staff(user: Annotated[object, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]):
        return {"ok": True}

    # include auth-like login/me? easier: mint token via login endpoint by mounting auth router
    from app.api.routes.auth import router as auth_router

    app.include_router(auth_router)
    app.include_router(router)
    return app, TestingSessionLocal


def seed_user(db, user_id: int, email: str, role_name: str):
    if db.get(Gym, 1) is None:
        db.add_all([
            Gym(id=1, gym_id=1, branch_id=None, name="Gym A"),
            Branch(id=1, gym_id=1, branch_id=1, name="Main"),
        ])
    user = User(
        id=user_id,
        gym_id=1,
        branch_id=1,
        email=email,
        full_name=role_name,
        hashed_password=get_password_hash("secret123"),
        is_active=True,
    )
    role = db.query(Role).filter(Role.gym_id == 1, Role.name == role_name).first()
    if not role:
        role = Role(id=user_id + 100, gym_id=1, branch_id=1, name=role_name)
        db.add(role)
        db.flush()
    db.add(user)
    db.flush()
    db.add(UserRole(id=user_id + 200, gym_id=1, branch_id=1, user_id=user.id, role_id=role.id))
    db.commit()


def token_for(client: TestClient, email: str) -> str:
    resp = client.post("/auth/login", json={"gym_id": 1, "email": email, "password": "secret123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_owner_allowed_admin_denied_on_owner_only():
    app, SessionLocal = make_app()
    with SessionLocal() as db:
        seed_user(db, 1, "owner@example.com", "owner")
        seed_user(db, 2, "admin@example.com", "admin")
    client = TestClient(app)
    owner_token = token_for(client, "owner@example.com")
    admin_token = token_for(client, "admin@example.com")
    assert client.get("/owner-only", headers={"Authorization": f"Bearer {owner_token}"}).status_code == 200
    assert client.get("/owner-only", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 403


def test_all_staff_roles_allowed_on_staff_endpoint():
    app, SessionLocal = make_app()
    with SessionLocal() as db:
        for i, role in enumerate(["owner", "admin", "reception", "trainer"], start=1):
            seed_user(db, i, f"{role}@example.com", role)
    client = TestClient(app)
    for role in ["owner", "admin", "reception", "trainer"]:
        tok = token_for(client, f"{role}@example.com")
        resp = client.get("/staff", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200, role


def test_unauthenticated_denied():
    app, _ = make_app()
    client = TestClient(app)
    assert client.get("/staff").status_code == 401
