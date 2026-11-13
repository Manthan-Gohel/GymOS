from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.conversation import Conversation, InboundMessage
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
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        User(id=2, gym_id=1, branch_id=1, email="front@example.com", full_name="Front", hashed_password=get_password_hash("secret123"), is_active=True),
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


def test_webhook_creates_conversation_and_message():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    r = client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "Hi, what are your timings?"})
    assert r.status_code == 202, r.text
    data = r.json()
    assert data["status"] == "accepted"
    assert data["conversation_id"] == 1

    with SessionLocal() as db:
        conv = db.query(Conversation).filter(Conversation.gym_id == 1, Conversation.contact_phone == "9999912345").first()
        assert conv is not None
        assert conv.status == "active"
        assert conv.bot_paused is False
        msg = db.query(InboundMessage).filter(InboundMessage.conversation_id == conv.id).first()
        assert msg is not None
        assert msg.body == "Hi, what are your timings?"


def test_webhook_idempotent_on_same_contact():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "First"})
    r = client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "Second"})
    assert r.status_code == 202
    assert r.json()["conversation_id"] == 1

    with SessionLocal() as db:
        msgs = db.query(InboundMessage).filter(InboundMessage.from_phone == "9999912345").all()
        assert len(msgs) == 2


def test_list_conversations_and_messages():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "Hello"})
    client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "How much is monthly?"})

    h = auth(client)
    r = client.get("/whatsapp/conversations", headers=h)
    assert r.status_code == 200
    convs = r.json()["items"]
    assert len(convs) == 1
    assert convs[0]["contact_phone"] == "9999912345"

    conv_id = convs[0]["id"]
    r = client.get(f"/whatsapp/conversations/{conv_id}/messages", headers=h)
    assert r.status_code == 200
    msgs = r.json()["items"]
    assert len(msgs) == 2
    assert msgs[0]["body"] == "Hello"
    assert msgs[1]["body"] == "How much is monthly?"


def test_pause_resume_bot():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "Hello"})

    h = auth(client)
    r = client.get("/whatsapp/conversations", headers=h)
    conv_id = r.json()["items"][0]["id"]

    r = client.post(f"/whatsapp/conversations/{conv_id}/pause", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "paused"

    r = client.get("/whatsapp/conversations", headers=h)
    assert r.json()["items"][0]["bot_paused"] is True

    r = client.post(f"/whatsapp/conversations/{conv_id}/resume", headers=h)
    assert r.json()["status"] == "active"

    r = client.get("/whatsapp/conversations", headers=h)
    assert r.json()["items"][0]["bot_paused"] is False


def test_reception_can_manage_conversations():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    client.post("/whatsapp/webhook", json={"from": "9999912345", "body": "Hello"})

    h = auth(client, "front@example.com")
    r = client.get("/whatsapp/conversations", headers=h)
    assert r.status_code == 200
    conv_id = r.json()["items"][0]["id"]

    r = client.post(f"/whatsapp/conversations/{conv_id}/pause", headers=h)
    assert r.status_code == 200
    app.dependency_overrides.clear()


def test_trainer_cannot_access_whatsapp():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        db.add_all([
            Gym(id=1, gym_id=1, branch_id=None, name="Gym A"),
            Branch(id=1, gym_id=1, branch_id=1, name="Main"),
            Role(id=1, gym_id=1, branch_id=1, name="owner"),
            Role(id=3, gym_id=1, branch_id=1, name="trainer"),
            User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
            User(id=3, gym_id=1, branch_id=1, email="coach@example.com", full_name="Coach", hashed_password=get_password_hash("secret123"), is_active=True),
        ])
        db.flush()
        db.add_all([
            UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
            UserRole(id=3, gym_id=1, branch_id=1, user_id=3, role_id=3),
        ])
        db.commit()
    h = auth(client, "coach@example.com")
    r = client.get("/whatsapp/conversations", headers=h)
    assert r.status_code == 403
    app.dependency_overrides.clear()