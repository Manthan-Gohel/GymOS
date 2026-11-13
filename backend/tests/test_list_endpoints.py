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
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul Sharma", phone="99999"),
        Member(id=2, gym_id=1, branch_id=1, full_name="Anita", phone="88888", is_active=False),
        Member(id=3, gym_id=2, branch_id=9, full_name="Other", phone="111"),
        MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=100000, currency="INR", is_active=True),
        Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)),
        Invoice(id=1, gym_id=1, branch_id=1, member_id=1, invoice_number="INV-1-000001", status="issued", taxable_value_paise=100000, gst_rate=0.0, cgst_paise=0, sgst_paise=0, igst_paise=0, total_paise=100000, currency="INR"),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_member_list_search_filter_and_tenant_scope():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.get("/members", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    r = client.get("/members?q=rahul", headers=h)
    assert [m["id"] for m in r.json()["items"]] == [1]

    r = client.get("/members?is_active=false", headers=h)
    assert [m["id"] for m in r.json()["items"]] == [2]
    app.dependency_overrides.clear()


def test_membership_and_invoice_lists_with_filters():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.get("/memberships?member_id=1", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["status"] == "active"

    r = client.get("/memberships?status=expired", headers=h)
    assert r.json()["total"] == 0

    r = client.get("/invoices?member_id=1", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["invoice_number"] == "INV-1-000001"

    r = client.get("/invoices?status=paid", headers=h)
    assert r.json()["total"] == 0
    app.dependency_overrides.clear()
