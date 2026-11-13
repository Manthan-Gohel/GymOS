from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.lead import Lead
from app.models.member import Member
from app.models.conversation import Conversation
from app.services.chatbot import _detect_intent, _handle_trial_booking, run_chatbot


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


def test_detect_intent_trial():
    intents = _detect_intent("I want to book a trial session")
    assert "trial" in intents

    intents = _detect_intent("Can I try a demo class?")
    assert "trial" in intents

    intents = _detect_intent("Walk in tomorrow for trial")
    assert "trial" in intents


def test_handle_trial_booking_creates_lead():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        knowledge = "Gym: FitZone\nBranch: Andheri\n\nActive Plans:\n  - Monthly: 1,500 INR for 30 days"
        decision = _handle_trial_booking(db, 1, 1, "9999912345", "I want to book a trial", knowledge, "")

    assert decision is not None
    assert decision.handoff is False
    assert "trial" in decision.reply.lower() or "Trial" in decision.reply
    assert decision.meta.get("lead_id") is not None

    with SessionLocal() as db:
        lead = db.query(Lead).filter(Lead.phone == "9999912345").first()
        assert lead is not None
        assert lead.status == "new"
        assert lead.source == "whatsapp"


def test_handle_trial_booking_with_date():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        knowledge = "Gym: FitZone\nBranch: Andheri\n\nActive Plans:\n  - Monthly: 1,500 INR for 30 days"
        decision = _handle_trial_booking(db, 1, 1, "9999912345", "I want a trial tomorrow", knowledge, "")

    assert decision.meta.get("trial_date") is not None


def test_handle_trial_booking_duplicate_lead():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Lead(gym_id=1, branch_id=1, full_name="Test", phone="9999912345", source="whatsapp", status="new"))
        db.commit()
        knowledge = "Gym: FitZone\nBranch: Andheri\n\nActive Plans:\n  - Monthly: 1,500 INR for 30 days"
        decision = _handle_trial_booking(db, 1, 1, "9999912345", "I want a trial", knowledge, "")

    assert decision is not None
    assert "already have a trial request" in decision.reply


def test_handle_trial_booking_existing_member():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Member(gym_id=1, branch_id=1, full_name="Amit", phone="9999912345"))
        db.commit()
        knowledge = "Gym: FitZone\nBranch: Andheri\n\nActive Plans:\n  - Monthly: 1,500 INR for 30 days"
        decision = _handle_trial_booking(db, 1, 1, "9999912345", "I want a trial", knowledge, "")

    assert decision is not None
    assert "already a member" in decision.reply


def test_run_chatbot_trial_booking_integration():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        decision = run_chatbot(db, gym_id=1, branch_id=1, from_phone="9999912345", inbound_text="I want to book a trial session")

    assert decision.handoff is False
    assert "trial" in decision.reply.lower() or "Trial" in decision.reply

    with SessionLocal() as db:
        lead = db.query(Lead).filter(Lead.phone == "9999912345").first()
        assert lead is not None
        assert lead.status == "new"