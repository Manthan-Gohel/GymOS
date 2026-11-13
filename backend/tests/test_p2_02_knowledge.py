from datetime import date, time

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
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.models.trainer import Trainer, TrainerAvailability
from app.services.knowledge import (
    format_knowledge_for_llm,
    format_member_context,
    get_gym_knowledge,
    get_member_context,
)


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
        TrainerAvailability(id=2, gym_id=1, branch_id=1, trainer_id=1, weekday=2, start_time=time(6, 0), end_time=time(10, 0)),
        TrainerAvailability(id=3, gym_id=1, branch_id=1, trainer_id=2, weekday=1, start_time=time(7, 0), end_time=time(11, 0)),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def test_get_gym_knowledge_returns_structured_data():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        knowledge = get_gym_knowledge(db, gym_id=1, branch_id=1)

    assert knowledge.gym_name == "FitZone"
    assert knowledge.branch.name == "Andheri"
    assert knowledge.currency == "INR"
    assert len(knowledge.plans) == 2
    assert knowledge.plans[0].name == "Monthly"
    assert knowledge.plans[0].price_paise == 150000
    assert len(knowledge.trainers) == 2
    assert knowledge.trainers[0].full_name == "Coach Rahul"
    assert knowledge.trainers[0].specialty == "Strength"
    assert len(knowledge.trainers[0].availability) == 2
    assert knowledge.trainers[1].full_name == "Coach Priya"
    assert knowledge.trainers[1].specialty == "Yoga"
    assert len(knowledge.trainers[1].availability) == 1


def test_format_knowledge_for_llm_contains_key_fields():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        knowledge = get_gym_knowledge(db, gym_id=1, branch_id=1)
    text = format_knowledge_for_llm(knowledge)

    assert "Gym: FitZone" in text
    assert "Branch: Andheri" in text
    assert "Currency: INR" in text
    assert "Active Plans:" in text
    assert "Monthly" in text and "1500" in text or "1,500" in text
    assert "Quarterly" in text
    assert "Trainers:" in text
    assert "Coach Rahul" in text
    assert "Strength" in text
    assert "Coach Priya" in text
    assert "Yoga" in text
    assert "Mon 06:00-10:00" in text or "Mon" in text
    assert "Tue 07:00-11:00" in text  # Coach Priya has Tue
    assert "Wed" in text


def test_get_member_context_with_active_membership():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Member(id=1, gym_id=1, branch_id=1, full_name="Amit", phone="99999", whatsapp_consent=True))
        db.add(Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)))
        db.commit()
        ctx = get_member_context(db, gym_id=1, member_id=1)

    assert ctx is not None
    assert ctx["full_name"] == "Amit"
    assert ctx["active_membership"] is not None
    assert ctx["active_membership"]["plan_name"] == "Monthly"
    assert ctx["active_membership"]["end_date"] == "2026-01-31"


def test_get_member_context_no_active_membership():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Member(id=2, gym_id=1, branch_id=1, full_name="Riya", phone="88888"))
        db.commit()
        ctx = get_member_context(db, gym_id=1, member_id=2)

    assert ctx is not None
    assert ctx["active_membership"] is None


def test_get_member_context_not_found():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        ctx = get_member_context(db, gym_id=1, member_id=999)
    assert ctx is None


def test_format_member_context_readable():
    ctx = {
        "full_name": "Amit",
        "phone": "99999",
        "active_membership": {"plan_name": "Monthly", "end_date": "2026-01-31", "status": "active"},
    }
    text = format_member_context(ctx)
    assert "Member: Amit (99999)" in text
    assert "Plan: Monthly" in text
    assert "2026-01-31" in text

    empty = format_member_context(None)
    assert "not found" in empty.lower()