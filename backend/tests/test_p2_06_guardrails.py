
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.conversation import Conversation, InboundMessage
from app.models.message import OutboundMessage


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
        __import__("app.models.core", fromlist=["Gym", "Branch", "Role", "User", "UserRole"]).Gym(id=1, gym_id=1, branch_id=None, name="FitZone"),
        __import__("app.models.core", fromlist=["Branch"]).Branch(id=1, gym_id=1, branch_id=1, name="Andheri"),
        __import__("app.models.core", fromlist=["Role"]).Role(id=1, gym_id=1, branch_id=1, name="owner"),
        __import__("app.models.core", fromlist=["User"]).User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
    ])
    db.flush()
    db.add(__import__("app.models.core", fromlist=["UserRole"]).UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_audit_trail_includes_inbound_and_outbound():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="active")
        db.add(conv)
        db.flush()
        db.add(InboundMessage(gym_id=1, branch_id=1, conversation_id=conv.id, from_phone="9999912345", body="Hello"))
        db.add(OutboundMessage(
            gym_id=1, branch_id=1, member_id=None, phone="9999912345",
            template_name="welcome", body="Welcome!", kind="template_message", status="sent",
            provider="mock", who="system", why=f"conversation:{conv.id}"
        ))
        db.commit()
        conv_id = conv.id

    h = auth(client)
    r = client.get(f"/whatsapp/conversations/{conv_id}/audit", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["conversation_id"] == conv_id
    assert len(data["events"]) == 2
    assert data["events"][0]["type"] == "inbound"
    assert data["events"][1]["type"] == "outbound"


def test_guardrails_test_endpoint():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)

    h = auth(client)
    r = client.get("/whatsapp/guardrails/test?text=I want a refund", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["handoff_triggered"] is True
    assert "refund" in data["reason"]

    r = client.get("/whatsapp/guardrails/test?text=What are your prices?", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["handoff_triggered"] is False


def test_rate_limit_check_and_reset():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)

    h = auth(client)

    # First few requests allowed
    for _ in range(5):
        r = client.get("/whatsapp/rate-limits/9999912345", headers=h)
        assert r.json()["allowed"] is True

    # Exhaust limit
    config = {"window_seconds": 60, "max_messages": 5}
    for _ in range(5):
        from app.api.routes.whatsapp_guardrails import RateLimitConfig, check_rate_limit
        allowed, _ = check_rate_limit("9999912345", RateLimitConfig(**config))
    # Next should be denied
    allowed, remaining = check_rate_limit("9999912345", RateLimitConfig(**config))
    assert allowed is False
    assert remaining == 0

    # Reset
    from app.api.routes.whatsapp_guardrails import clear_rate_limit
    clear_rate_limit("9999912345")
    allowed, remaining = check_rate_limit("9999912345", RateLimitConfig(**config))
    assert allowed is True


def test_conversation_audit_requires_auth():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="active")
        db.add(conv)
        db.commit()
        conv_id = conv.id

    r = client.get(f"/whatsapp/conversations/{conv_id}/audit")
    assert r.status_code in (401, 403)

    h = auth(client)
    r = client.get(f"/whatsapp/conversations/{conv_id}/audit", headers=h)
    assert r.status_code == 200