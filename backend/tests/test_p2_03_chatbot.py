from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.core import Branch, Gym, Role, User, UserRole
from app.models.member import Member
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.models.trainer import Trainer, TrainerAvailability
from app.services.chatbot import _canned_reply, _detect_intent, _should_handoff, run_chatbot
from app.services.knowledge import format_knowledge_for_llm, get_gym_knowledge


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
        Gym(id=1, gym_id=1, branch_id=None, name="FitZone"),
        Branch(id=1, gym_id=1, branch_id=1, name="Andheri"),
        Role(id=1, gym_id=1, branch_id=1, name="owner"),
        User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=150000, currency="INR", is_active=True, terms={"auto_renew": True}),
        MembershipPlan(id=2, gym_id=1, branch_id=1, name="Quarterly", duration_days=90, price_paise=400000, currency="INR", is_active=True),
        Trainer(id=1, gym_id=1, branch_id=1, full_name="Coach Rahul", phone="77777", specialty="Strength", bio="5 years exp"),
        Trainer(id=2, gym_id=1, branch_id=1, full_name="Coach Priya", phone="88888", specialty="Yoga"),
        TrainerAvailability(id=1, gym_id=1, branch_id=1, trainer_id=1, weekday=0, start_time=time(6, 0), end_time=time(10, 0)),
        TrainerAvailability(id=2, gym_id=1, branch_id=1, trainer_id=2, weekday=1, start_time=time(7, 0), end_time=time(11, 0)),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def test_should_handoff_detects_medical():
    handoff, reason = _should_handoff("I have a knee injury, can I still workout?")
    assert handoff is True
    assert "injury" in (reason or "")


def test_should_handoff_detects_refund():
    handoff, reason = _should_handoff("I want a refund for my membership")
    assert handoff is True
    assert "refund" in (reason or "")


def test_should_handoff_detects_complaint():
    handoff, reason = _should_handoff("I'm very unhappy with the service")
    assert handoff is True
    assert "unhappy" in (reason or "")


def test_should_handoff_detects_uncertainty():
    handoff, reason = _should_handoff("I'm not sure about this")
    assert handoff is True
    assert "not sure" in (reason or "")


def test_should_handoff_allows_normal_queries():
    handoff, reason = _should_handoff("What are your monthly plan prices?")
    assert handoff is False


def test_detect_intent_plans():
    intents = _detect_intent("How much is the monthly plan?")
    assert "plans" in intents


def test_detect_intent_trainers():
    intents = _detect_intent("Which trainer is available for morning sessions?")
    assert "trainers" in intents


def test_detect_intent_membership():
    intents = _detect_intent("My membership is expiring soon")
    assert "membership" in intents


def test_canned_reply_includes_plan_info():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        knowledge = get_gym_knowledge(db, gym_id=1, branch_id=1)
        text = format_knowledge_for_llm(knowledge)
    reply = _canned_reply(["plans"], text)
    assert "Monthly" in reply
    assert "Quarterly" in reply


def test_canned_reply_includes_trainer_info():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        knowledge = get_gym_knowledge(db, gym_id=1, branch_id=1)
        text = format_knowledge_for_llm(knowledge)
    reply = _canned_reply(["trainers"], text)
    assert "Coach Rahul" in reply or "Coach Priya" in reply


def test_run_chatbot_handoff_on_medical():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        decision = run_chatbot(db, gym_id=1, branch_id=1, from_phone="9999912345", inbound_text="I have chest pain during workout")
    assert decision.handoff is True
    assert "keyword" in (decision.meta or {})


def test_run_chatbot_normal_query_uses_canned():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        decision = run_chatbot(db, gym_id=1, branch_id=1, from_phone="9999912345", inbound_text="What are your plan prices?")
    assert decision.handoff is False
    assert "Monthly" in decision.reply or "Quarterly" in decision.reply


def test_run_chatbot_member_context_included():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Member(id=1, gym_id=1, branch_id=1, full_name="Amit", phone="9999912345", whatsapp_consent=True))
        db.add(Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)))
        db.flush()
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999912345", status="active")
        db.add(conv)
        db.flush()
        decision = run_chatbot(
            db, gym_id=1, branch_id=1, from_phone="9999912345",
            inbound_text="When does my plan expire?",
            conversation_id=conv.id,
        )
    assert "2026-01-31" in decision.reply or "expir" in decision.reply.lower()


def test_run_chatbot_unknown_member_fallback():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        conv = Conversation(gym_id=1, branch_id=1, contact_phone="9999999999", status="active")
        db.add(conv)
        db.flush()
        decision = run_chatbot(
            db, gym_id=1, branch_id=1, from_phone="9999999999",
            inbound_text="What are your plans?",
            conversation_id=conv.id,
        )
    assert "Monthly" in decision.reply or "Quarterly" in decision.reply