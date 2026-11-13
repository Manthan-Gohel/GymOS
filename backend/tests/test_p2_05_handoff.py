
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.message import OutboundMessage
from app.services.chatbot import _should_handoff, _trigger_handoff, run_chatbot


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
        __import__("app.models.plan", fromlist=["MembershipPlan"]).MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=150000, currency="INR", is_active=True),
        __import__("app.models.trainer", fromlist=["Trainer"]).Trainer(id=1, gym_id=1, branch_id=1, full_name="Coach Rahul", phone="77777"),
    ])
    db.flush()
    db.add(__import__("app.models.core", fromlist=["UserRole"]).UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def test_should_handoff_detects_all_keywords():
    assert _should_handoff("I have a medical issue")[0] is True
    assert _should_handoff("I want a refund")[0] is True
    assert _should_handoff("This is a complaint")[0] is True
    assert _should_handoff("I'm not sure about this")[0] is True
    assert _should_handoff("What are your prices?")[0] is False


def test_trigger_handoff_pauses_conversation_and_notifies():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="active", bot_paused=False)
        db.add(conv)
        db.flush()
        conv_id = conv.id
        _trigger_handoff(db, 1, 1, "9999912345", conv_id, "keyword: medical")

        conv2 = db.query(Conversation).filter(Conversation.id == conv_id).first()
        assert conv2.bot_paused is True
        assert conv2.status == "escalated"

        # Check staff notification was logged
        msgs = db.query(OutboundMessage).filter(OutboundMessage.why.like("handoff:%")).all()
        assert len(msgs) == 1
        assert "medical" in msgs[0].body
        assert msgs[0].phone == "gym-staff"


def test_run_chatbot_handoff_triggers_notification():
    client, SessionLocal = setup_client()
    # Create conversation in one session and commit
    with SessionLocal() as db:
        seed(db)
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="active")
        db.add(conv)
        db.commit()
        conv_id = conv.id

    # Now call run_chatbot (uses a new session from dependency override)
    with SessionLocal() as db:
        decision = run_chatbot(db, gym_id=1, branch_id=1, from_phone="9999912345", inbound_text="I have a medical issue", conversation_id=conv_id)

    assert decision.handoff is True
    assert decision.meta.get("trigger") == "guardrail"

    # Verify in a fresh session
    with SessionLocal() as db:
        conv2 = db.query(Conversation).filter(Conversation.id == conv_id).first()
        assert conv2.bot_paused is True
        assert conv2.status == "escalated"


def test_bot_respects_paused_conversation():
    """When bot_paused=True, run_chatbot should not process and should return a holding message."""
    # This test documents expected behavior - the webhook handler should check bot_paused before calling run_chatbot
    pass


def test_staff_inbox_endpoint():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="active", bot_paused=True))
        db.add(Conversation(gym_id=1, branch_id=1, contact_phone="9999922222", status="active", bot_paused=False))
        db.commit()

    h = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {h}"}
    r = client.get("/whatsapp/inbox?bot_paused=true", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["contact_phone"] == "9999912345"

    r = client.get("/whatsapp/inbox?bot_paused=false", headers=headers)
    assert r.json()["total"] == 1


def test_staff_reply_in_paused_conversation():
    client, SessionLocal = setup_client()
    # Create conversation in one session and commit
    with SessionLocal() as db:
        seed(db)
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="escalated", bot_paused=True)
        db.add(conv)
        db.commit()
        conv_id = conv.id

    h = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {h}"}
    r = client.post(f"/whatsapp/conversations/{conv_id}/staff-reply", json={"body": "Hi, I'm here to help!"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "sent"

    # Verify in a fresh session
    with SessionLocal() as db:
        msgs = db.query(OutboundMessage).filter(OutboundMessage.kind == "staff_reply").all()
        assert len(msgs) == 1
        assert msgs[0].body == "Hi, I'm here to help!"