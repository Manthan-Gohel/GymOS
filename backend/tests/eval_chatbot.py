#!/usr/bin/env python
"""Chatbot evaluation harness - runs as pytest-compatible test module."""

from __future__ import annotations

import os
from datetime import date

# Ensure LLM is disabled for deterministic canned replies
os.environ["LLM_ENABLED"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.member import Member
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.models.trainer import Trainer, TrainerAvailability
from app.services.chatbot import _detect_intent, run_chatbot


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
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

    db = TestingSessionLocal()
    try:
        seed_gym(db)
        yield db
    finally:
        db.close()
        app.dependency_overrides.clear()


def seed_gym(db):
    db.add_all([
        __import__("app.models.core", fromlist=["Gym", "Branch", "Role", "User", "UserRole"]).Gym(id=1, gym_id=1, branch_id=None, name="FitZone"),
        __import__("app.models.core", fromlist=["Branch"]).Branch(id=1, gym_id=1, branch_id=1, name="Andheri"),
        __import__("app.models.core", fromlist=["Role"]).Role(id=1, gym_id=1, branch_id=1, name="owner"),
        __import__("app.models.core", fromlist=["User"]).User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=150000, currency="INR", is_active=True, terms={"auto_renew": True}),
        MembershipPlan(id=2, gym_id=1, branch_id=1, name="Quarterly", duration_days=90, price_paise=400000, currency="INR", is_active=True),
        Trainer(id=1, gym_id=1, branch_id=1, full_name="Coach Rahul", phone="77777", specialty="Strength", bio="5 years exp"),
        Trainer(id=2, gym_id=1, branch_id=1, full_name="Coach Priya", phone="88888", specialty="Yoga"),
        TrainerAvailability(id=1, gym_id=1, branch_id=1, trainer_id=1, weekday=0, start_time=__import__("datetime").time(6, 0), end_time=__import__("datetime").time(10, 0)),
        TrainerAvailability(id=2, gym_id=1, branch_id=1, trainer_id=2, weekday=1, start_time=__import__("datetime").time(7, 0), end_time=__import__("datetime").time(11, 0)),
    ])
    db.flush()
    db.add(__import__("app.models.core", fromlist=["UserRole"]).UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def add_member(db, phone: str, name: str, with_membership: bool = False):
    db.add(Member(gym_id=1, branch_id=1, full_name=name, phone=phone, whatsapp_consent=True))
    if with_membership:
        db.add(Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)))
    db.commit()


def add_conversation(db, phone: str) -> int:
    conv = Conversation(gym_id=1, branch_id=1, contact_phone=phone, status="active")
    db.add(conv)
    db.flush()
    db.commit()
    return conv.id


class EvalCase:
    def __init__(
        self,
        name: str,
        inbound_text: str,
        expected_handoff: bool,
        expected_handoff_reason_contains: str | None = None,
        expected_intents: list[str] | None = None,
        expected_reply_contains: list[str] | None = None,
        expected_reply_not_contains: list[str] | None = None,
        setup_member: bool = False,
        member_phone: str = "9999912345",
        member_name: str = "Amit",
        conversation_id: int | None = None,
    ):
        self.name = name
        self.inbound_text = inbound_text
        self.expected_handoff = expected_handoff
        self.expected_handoff_reason_contains = expected_handoff_reason_contains
        self.expected_intents = expected_intents or []
        self.expected_reply_contains = expected_reply_contains or []
        self.expected_reply_not_contains = expected_reply_not_contains or []
        self.setup_member = setup_member
        self.member_phone = member_phone
        self.member_name = member_name
        self.conversation_id = conversation_id


def run_eval(db, case: EvalCase):
    """Run a single eval case against the chatbot."""
    conv_id = case.conversation_id
    if case.setup_member:
        add_member(db, case.member_phone, case.member_name, with_membership=True)
        if conv_id is None:
            conv_id = add_conversation(db, case.member_phone)

    decision = run_chatbot(
        db,
        gym_id=1,
        branch_id=1,
        from_phone=case.member_phone,
        inbound_text=case.inbound_text,
        conversation_id=conv_id,
    )

    errors = []
    if decision.handoff != case.expected_handoff:
        errors.append(f"handoff: expected {case.expected_handoff}, got {decision.handoff}")

    if case.expected_handoff_reason_contains and case.expected_handoff:
        reason = decision.meta.get("keyword", "") if decision.meta else ""
        if case.expected_handoff_reason_contains not in reason:
            errors.append(f"handoff reason: expected to contain '{case.expected_handoff_reason_contains}', got '{reason}'")

    for intent in case.expected_intents:
        intents = _detect_intent(case.inbound_text)
        if intent not in intents:
            errors.append(f"intent: expected '{intent}' in {intents}")

    for substr in case.expected_reply_contains:
        if substr not in decision.reply:
            errors.append(f"reply: expected to contain '{substr}', got '{decision.reply[:200]}'")

    for substr in case.expected_reply_not_contains:
        if substr in decision.reply:
            errors.append(f"reply: expected NOT to contain '{substr}', got '{decision.reply[:200]}'")

    if errors:
        pytest.fail(f"{case.name}: {', '.join(errors)}")


# ============================================================
# Guardrail handoffs
# ============================================================

def test_guardrail_medical(db_session):
    case = EvalCase("guardrail_medical", "I have chest pain during workout", True, "pain")
    run_eval(db_session, case)


def test_guardrail_injury(db_session):
    case = EvalCase("guardrail_injury", "I injured my knee doing squats", True, "injured")
    run_eval(db_session, case)


def test_guardrail_refund(db_session):
    case = EvalCase("guardrail_refund", "I want a full refund for my membership", True, "refund")
    run_eval(db_session, case)


def test_guardrail_complaint(db_session):
    case = EvalCase("guardrail_complaint", "I'm very unhappy with the service here", True, "unhappy")
    run_eval(db_session, case)


def test_guardrail_uncertainty(db_session):
    case = EvalCase("guardrail_uncertainty", "I'm not sure if I should continue", True, "not sure")
    run_eval(db_session, case)


def test_guardrail_legal(db_session):
    case = EvalCase("guardrail_legal", "I'm going to take legal action against you", True, "legal")
    run_eval(db_session, case)


# ============================================================
# Plan queries
# ============================================================

def test_plan_price_query(db_session):
    case = EvalCase(
        "plan_price_query",
        "What is the price of the monthly plan?",
        False,
        expected_intents=["plans"],
        expected_reply_contains=["Monthly", "1,500"],
    )
    run_eval(db_session, case)


def test_plan_all_query(db_session):
    case = EvalCase(
        "plan_all_query",
        "What plans do you offer?",
        False,
        expected_intents=["plans"],
        expected_reply_contains=["Monthly", "Quarterly"],
    )
    run_eval(db_session, case)


# ============================================================
# Trainer queries
# ============================================================

def test_trainer_availability(db_session):
    case = EvalCase(
        "trainer_availability",
        "Which trainers are available in the morning?",
        False,
        expected_intents=["trainers"],
        expected_reply_contains=["Coach Rahul", "Coach Priya"],
    )
    run_eval(db_session, case)


def test_trainer_specialty(db_session):
    case = EvalCase(
        "trainer_specialty",
        "Who teaches yoga?",
        False,
        expected_intents=["trainers"],
        expected_reply_contains=["Priya", "Yoga"],
    )
    run_eval(db_session, case)


# ============================================================
# Location/timing
# ============================================================

def test_location_query(db_session):
    case = EvalCase(
        "location_query",
        "Where is your gym located?",
        False,
        expected_intents=["location"],
        expected_reply_contains=["Andheri"],
    )
    run_eval(db_session, case)


def test_timing_query(db_session):
    case = EvalCase(
        "timing_query",
        "What are your opening hours?",
        False,
        expected_intents=["timings"],
        expected_reply_contains=["6 AM", "10 PM"],
    )
    run_eval(db_session, case)


# ============================================================
# Membership queries
# ============================================================

def test_membership_expiry(db_session):
    case = EvalCase(
        "membership_expiry",
        "When does my membership expire?",
        False,
        expected_intents=["membership"],
        expected_reply_contains=["contact reception"],
        setup_member=True,
    )
    run_eval(db_session, case)


def test_membership_freeze(db_session):
    case = EvalCase(
        "membership_freeze",
        "Can I freeze my membership?",
        False,
        expected_intents=["membership"],
        expected_reply_contains=["freeze", "reception"],
    )
    run_eval(db_session, case)


# ============================================================
# Trial booking
# ============================================================

def test_trial_booking_new(db_session):
    case = EvalCase(
        "trial_booking_new",
        "I want to book a trial session tomorrow",
        False,
        expected_intents=["trial"],
        expected_reply_contains=["trial", "team will"],
    )
    run_eval(db_session, case)


# ============================================================
# Member context
# ============================================================

def test_member_context_included(db_session):
    case = EvalCase(
        "member_context_included",
        "When does my plan end?",
        False,
        expected_intents=["membership"],
        expected_reply_contains=["2026-01-31"],
        setup_member=True,
    )
    run_eval(db_session, case)


# ============================================================
# Non-member fallback
# ============================================================

def test_non_member_plan_query(db_session):
    case = EvalCase(
        "non_member_plan_query",
        "How much is the quarterly plan?",
        False,
        expected_intents=["plans"],
        expected_reply_contains=["Quarterly", "4,000"],
        member_phone="9999999999",
    )
    run_eval(db_session, case)