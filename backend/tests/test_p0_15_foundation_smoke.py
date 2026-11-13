from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import router as auth_router
from app.core.rbac import require_roles
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.db.tenant import scoped_query
from app.models.core import Branch, Gym, Role, User, UserRole
from app.providers.llm import CannedFallbackLLMProvider, get_llm_provider
from app.providers.messaging import MockMessagingProvider, get_messaging_provider
from app.providers.payments import MockPaymentsProvider, get_payments_provider
from app.services.audit import write_audit_log


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
    app.include_router(auth_router)

    router = APIRouter()

    @router.get("/owner-only")
    def owner_only(user: Annotated[object, Depends(require_roles(["owner"]))]):
        return {"ok": True}

    app.include_router(router)
    return app, TestingSessionLocal


def seed(SessionLocal):
    with SessionLocal() as db:
        gym = Gym(id=1, gym_id=1, branch_id=None, name="Gym A")
        branch = Branch(id=1, gym_id=1, branch_id=1, name="Main")
        owner = User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True)
        reception = User(id=2, gym_id=1, branch_id=1, email="reception@example.com", full_name="Reception", hashed_password=get_password_hash("secret123"), is_active=True)
        r_owner = Role(id=1, gym_id=1, branch_id=1, name="owner")
        r_rec = Role(id=2, gym_id=1, branch_id=1, name="reception")
        db.add_all([gym, branch, owner, reception, r_owner, r_rec])
        db.flush()
        db.add_all([
            UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
            UserRole(id=2, gym_id=1, branch_id=1, user_id=2, role_id=2),
        ])
        db.commit()


def test_foundation_smoke_auth_rbac_tenant_audit_and_mocks(monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "mock")
    monkeypatch.setenv("PAYMENTS_PROVIDER", "mock")
    monkeypatch.setenv("LLM_ENABLED", "false")
    app, SessionLocal = make_app()
    seed(SessionLocal)
    client = TestClient(app)

    # auth
    login = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and "owner" in me.json()["roles"]

    # rbac
    rec_login = client.post("/auth/login", json={"gym_id": 1, "email": "reception@example.com", "password": "secret123"})
    rec_token = rec_login.json()["access_token"]
    assert client.get("/owner-only", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/owner-only", headers={"Authorization": f"Bearer {rec_token}"}).status_code == 403

    # tenant scoping & audit
    with SessionLocal() as db:
        db.add(Gym(id=2, gym_id=2, branch_id=None, name="Gym B"))
        db.add(Branch(id=2, gym_id=2, branch_id=2, name="B-main"))
        db.add(User(id=10, gym_id=2, branch_id=2, email="other@example.com", full_name="Other", hashed_password="x"))
        db.commit()
        users_g1 = db.scalars(scoped_query(db, User, gym_id=1)).all()
        assert all(u.gym_id == 1 for u in users_g1)
        write_audit_log(db, gym_id=1, branch_id=1, actor_user_id=1, action="smoke", entity_type="system", why="foundation smoke")
        db.commit()

    # provider mocks wired
    msg = get_messaging_provider()
    pay = get_payments_provider()
    llm = get_llm_provider()
    assert isinstance(msg, MockMessagingProvider)
    assert isinstance(pay, MockPaymentsProvider)
    assert isinstance(llm, CannedFallbackLLMProvider)
    msg.send_template(to="+91x", template_name="welcome", who="sys", what="test", why="smoke")
    assert len(msg.sent_messages) == 1
