
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch, Gym, Role, User, UserRole
from app.models.member import Member
from app.models.template import MessageTemplate
from app.providers.messaging import MockMessagingProvider
from app.services.messaging import send_logged_template


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
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999", whatsapp_consent=True),
        Member(id=2, gym_id=1, branch_id=1, full_name="Opted Out", phone="88888", whatsapp_consent=True, whatsapp_opt_out=True),
        MessageTemplate(id=1, gym_id=1, branch_id=1, name="expiry_reminder", body="Hi {name}, expires {date}.", category="reminder", is_active=True),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_send_is_logged_with_who_what_why_and_template():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        provider = MockMessagingProvider()
        log = send_logged_template(
            db,
            member=db.get(Member, 1),
            template=db.get(MessageTemplate, 1),
            params={"name": "Rahul", "date": "2026-02-01"},
            actor_user_id=1,
            why="expiry_7d",
            provider=provider,
        )
        db.commit()
        assert log.status == "sent"
        assert log.template_name == "expiry_reminder"
        assert log.body == "Hi Rahul, expires 2026-02-01."
        assert log.why == "expiry_7d"
        assert log.who == "user:1"
        assert log.provider == "mock"
    app.dependency_overrides.clear()


def test_opt_out_is_logged_blocked_without_send():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        provider = MockMessagingProvider()
        log = send_logged_template(
            db,
            member=db.get(Member, 2),
            template=db.get(MessageTemplate, 1),
            params={"name": "X", "date": "d"},
            provider=provider,
        )
        db.commit()
        assert log.status == "blocked"
        assert "opt" in (log.error or "").lower() or "consent" in (log.error or "").lower()
        assert provider.sent_messages == []
    app.dependency_overrides.clear()


def test_messages_api_lists_and_filters_logs():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        send_logged_template(db, member=db.get(Member, 1), template=db.get(MessageTemplate, 1), params={"name": "Rahul", "date": "d"}, provider=MockMessagingProvider())
        send_logged_template(db, member=db.get(Member, 2), template=db.get(MessageTemplate, 1), params={"name": "X", "date": "d"}, provider=MockMessagingProvider())
        db.commit()
    h = auth(client)
    r = client.get("/messages", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    r = client.get("/messages?status=blocked", headers=h)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["member_id"] == 2

    r = client.get("/messages?member_id=1", headers=h)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["status"] == "sent"
    assert isinstance(r.json()["items"][0]["created_at"], str) and r.json()["items"][0]["created_at"]
    app.dependency_overrides.clear()
