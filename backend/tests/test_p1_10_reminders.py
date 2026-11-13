from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch, Gym, Role, User, UserRole
from app.models.invoice import Invoice
from app.models.member import Member
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.models.template import MessageTemplate
from app.providers.messaging import MockMessagingProvider
from app.services.reminders import run_reminders


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
        Member(id=2, gym_id=1, branch_id=1, full_name="Opted", phone="88888", whatsapp_consent=True, whatsapp_opt_out=True),
        MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=100000, currency="INR", is_active=True),
        MessageTemplate(id=1, gym_id=1, branch_id=1, name="welcome", body="Welcome {name}!", category="welcome", is_active=True),
        MessageTemplate(id=2, gym_id=1, branch_id=1, name="expiry_reminder", body="Hi {name}, plan expires in {days} days on {date}.", category="reminder", is_active=True),
        MessageTemplate(id=3, gym_id=1, branch_id=1, name="payment_due", body="Hi {name}, {amount} INR is due.", category="payment", is_active=True),
        Invoice(id=1, gym_id=1, branch_id=1, member_id=2, invoice_number="INV-1-000001", status="issued", taxable_value_paise=100000, gst_rate=0.0, cgst_paise=0, sgst_paise=0, igst_paise=0, total_paise=100000, currency="INR"),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    # starts today -> welcome + expires in 7 days
    db.add(Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 8)))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_reminders_send_once_and_respect_opt_out():
    client, SessionLocal = setup_client()
    today = date(2026, 1, 1)
    with SessionLocal() as db:
        seed(db)
        provider = MockMessagingProvider()
        logs = run_reminders(db, gym_id=1, today=today, provider=provider)
        db.commit()
        sent = [log for log in logs if log.status == "sent"]
        blocked = [log for log in logs if log.status == "blocked"]
        assert {log.template_name for log in sent} == {"welcome", "expiry_reminder"}
        assert any(log.body == "Welcome Rahul!" for log in sent)
        assert any("7 days on 2026-01-08" in log.body for log in sent)
        # member 2 opted out: payment due still attempted and blocked, not sent
        assert any(log.member_id == 2 and log.status == "blocked" for log in blocked)
        assert all(log.member_id != 2 for log in sent)

        # idempotent same day: nothing new sent
        before = len(provider.sent_messages)
        logs2 = run_reminders(db, gym_id=1, today=today, provider=provider)
        db.commit()
        assert [log for log in logs2 if log.status == "sent"] == []
        assert len(provider.sent_messages) == before
    app.dependency_overrides.clear()


def test_reminders_api_requires_auth_and_runs():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/reminders/run", json={"today": "2026-01-01"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["sent"] >= 2
    assert r.json()["blocked"] >= 1
    # default provider is mock; second run same day is idempotent
    r = client.post("/reminders/run", json={"today": "2026-01-01"}, headers=h)
    assert r.json()["sent"] == 0
    app.dependency_overrides.clear()
