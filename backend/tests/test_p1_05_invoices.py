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
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.services.invoices import generate_invoice


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
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999"),
        MembershipPlan(id=1, gym_id=1, branch_id=1, name="Monthly", duration_days=30, price_paise=100000, currency="INR", is_active=True),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.add(Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_generate_invoice_gst_totals_via_service():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        inv = generate_invoice(
            db,
            gym_id=1,
            branch_id=1,
            member_id=1,
            membership_id=1,
            taxable_value_paise=100000,
            gst_rate=18.0,
            gst_mode="intra",  # CGST+SGST
        )
        db.commit()
        assert inv.taxable_value_paise == 100000
        assert inv.cgst_paise == 9000
        assert inv.sgst_paise == 9000
        assert inv.igst_paise == 0
        assert inv.total_paise == 118000
        assert inv.invoice_number
    app.dependency_overrides.clear()


def test_create_and_get_invoice_api():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/invoices", json={
        "member_id": 1,
        "membership_id": 1,
        "taxable_value_paise": 100000,
        "gst_rate": 18.0,
        "gst_mode": "intra",
        "seller_gstin": "27ABCDE1234F1Z5",
        "buyer_name": "Rahul",
    }, headers=h)
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["total_paise"] == 118000
    assert inv["seller_gstin"] == "27ABCDE1234F1Z5"
    rid = inv["id"]
    r = client.get(f"/invoices/{rid}", headers=h)
    assert r.status_code == 200
    assert r.json()["invoice_number"] == inv["invoice_number"]
    app.dependency_overrides.clear()
