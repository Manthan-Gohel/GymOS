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
from app.models.member import Member
from app.models.plan import MembershipPlan
from app.services.memberships import expire_due_memberships


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
    gym = Gym(id=1, gym_id=1, branch_id=None, name="Gym A")
    branch = Branch(id=1, gym_id=1, branch_id=1, name="Main")
    role = Role(id=1, gym_id=1, branch_id=1, name="owner")
    user = User(id=1, gym_id=1, branch_id=1, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True)
    member = Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999")
    plan30 = MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=100000, currency="INR", is_active=True)
    plan90 = MembershipPlan(id=2, gym_id=1, branch_id=1, name="Quarterly", duration_days=90, price_paise=250000, currency="INR", is_active=True)
    db.add_all([gym, branch, role, user, member, plan30, plan90])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_purchase_freeze_unfreeze_and_expiry():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)

    # purchase
    r = client.post("/memberships/purchase", json={"member_id": 1, "plan_id": 1, "start_date": "2026-01-01"}, headers=h)
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["status"] == "active"
    assert m["end_date"] == "2026-01-31"
    mid = m["id"]

    # freeze
    r = client.post(f"/memberships/{mid}/freeze", json={"frozen_on": "2026-01-10"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "frozen"

    # unfreeze after 5 days -> end_date extends by 5
    r = client.post(f"/memberships/{mid}/unfreeze", json={"unfrozen_on": "2026-01-15"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert r.json()["end_date"] == "2026-02-05"

    # expiry engine
    with SessionLocal() as db:
        count = expire_due_memberships(db, gym_id=1, today=date(2026, 2, 6))
        db.commit()
        assert count >= 1
    r = client.get(f"/memberships/{mid}", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "expired"

    app.dependency_overrides.clear()


def test_upgrade_creates_new_membership_and_marks_old_upgraded():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/memberships/purchase", json={"member_id": 1, "plan_id": 1, "start_date": "2026-01-01"}, headers=h)
    old_id = r.json()["id"]

    r = client.post(f"/memberships/{old_id}/upgrade", json={"new_plan_id": 2, "start_date": "2026-01-10"}, headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["old_membership"]["status"] == "upgraded"
    assert data["new_membership"]["status"] == "active"
    assert data["new_membership"]["plan_id"] == 2
    assert data["new_membership"]["end_date"] == "2026-04-10"  # 90 days from 2026-01-10 inclusive? 10+89
    app.dependency_overrides.clear()
