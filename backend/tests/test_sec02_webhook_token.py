"""VULN-002: webhook authentication + tenant isolation via per-gym URL token."""
import hashlib
import hmac

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.core import Branch, Gym


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


def seed_two_gyms(db):
    """Gym 1 (id=1) with a webhook token, and Gym 2 (id=2) with another."""
    db.add_all([
        Gym(id=1, gym_id=1, branch_id=None, name="Gym A", webhook_token="tok-gym1"),
        Branch(id=1, gym_id=1, branch_id=1, name="Main"),
        Gym(id=2, gym_id=2, branch_id=None, name="Gym B", webhook_token="tok-gym2"),
        Branch(id=11, gym_id=2, branch_id=1, name="B-Main"),
    ])
    db.commit()


def test_tokened_webhook_resolves_tenant_from_token():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed_two_gyms(db)

    r = client.post("/whatsapp/webhook/tok-gym1", json={"from": "9111111111", "body": "Hi"})
    assert r.status_code == 202, r.text

    with SessionLocal() as db:
        conv = db.query(Conversation).first()
        assert conv.gym_id == 1
    app.dependency_overrides.clear()


def test_tokened_webhook_ignores_payload_gym_id():
    """Spoof attempt: payload claims gym_id=2 but token belongs to gym 1."""
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed_two_gyms(db)

    r = client.post(
        "/whatsapp/webhook/tok-gym1",
        json={"from": "9222222222", "body": "Hi", "gym_id": 2},
    )
    assert r.status_code == 202, r.text

    with SessionLocal() as db:
        conv = db.query(Conversation).first()
        assert conv.gym_id == 1, "payload gym_id must never override the URL token"
    app.dependency_overrides.clear()


def test_unknown_token_404():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed_two_gyms(db)

    r = client.post("/whatsapp/webhook/nope", json={"from": "9333333333", "body": "Hi"})
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_legacy_webhook_blocked_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed_two_gyms(db)

    r = client.post("/whatsapp/webhook", json={"from": "9444444444", "body": "Hi"})
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_signature_enforced_when_secret_set(monkeypatch):
    secret = "test-webhook-secret-0123456789abcdef"
    monkeypatch.setattr(settings, "openwa_webhook_secret", secret)
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed_two_gyms(db)

    raw = b'{"from": "9555555555", "body": "Hi"}'
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()

    # valid signature
    r = client.post(
        "/whatsapp/webhook/tok-gym1",
        content=raw,
        headers={"Content-Type": "application/json", "X-GymOS-Signature": sig},
    )
    assert r.status_code == 202, r.text

    # missing signature
    r = client.post(
        "/whatsapp/webhook/tok-gym1",
        content=b'{"from": "9555555556", "body": "Hi"}',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 401

    # tampered body
    r = client.post(
        "/whatsapp/webhook/tok-gym1",
        content=b'{"from": "9555555557", "body": "hacked"}',
        headers={"Content-Type": "application/json", "X-GymOS-Signature": sig},
    )
    assert r.status_code == 401
    app.dependency_overrides.clear()
