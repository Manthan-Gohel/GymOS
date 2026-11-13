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
from app.services.payments import member_dues, record_payment


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
        Invoice(id=1, gym_id=1, branch_id=1, member_id=1, invoice_number="INV-1-000001", status="issued", taxable_value_paise=100000, gst_rate=18.0, cgst_paise=9000, sgst_paise=9000, igst_paise=0, total_paise=118000, currency="INR"),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.add(Membership(id=1, gym_id=1, branch_id=1, member_id=1, plan_id=1, status="active", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_partial_then_full_payment_updates_invoice_and_dues():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        p1 = record_payment(
            db, gym_id=1, branch_id=1, member_id=1, invoice_id=1, amount_paise=50000, method="cash"
        )
        db.commit()
        assert p1.status == "paid"
        assert db.get(Invoice, 1).status == "partial"
        assert member_dues(db, gym_id=1, member_id=1)["total_due_paise"] == 68000

        record_payment(
            db, gym_id=1, branch_id=1, member_id=1, invoice_id=1, amount_paise=68000, method="upi", reference="UPI-123"
        )
        db.commit()
        assert db.get(Invoice, 1).status == "paid"
        assert member_dues(db, gym_id=1, member_id=1)["total_due_paise"] == 0
    app.dependency_overrides.clear()


def test_overpayment_clamps_dues_to_zero():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        record_payment(db, gym_id=1, branch_id=1, member_id=1, invoice_id=1, amount_paise=120000, method="card")
        db.commit()
        assert db.get(Invoice, 1).status == "paid"
        assert member_dues(db, gym_id=1, member_id=1)["total_due_paise"] == 0
    app.dependency_overrides.clear()


def test_api_record_payment_and_dues_endpoint():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/payments", json={
        "member_id": 1,
        "invoice_id": 1,
        "membership_id": 1,
        "amount_paise": 118000,
        "method": "upi",
        "reference": "UPI-999",
        "paid_at": "2026-01-05",
    }, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["payment"]["amount_paise"] == 118000
    assert body["invoice"]["status"] == "paid"
    assert body["dues"]["total_due_paise"] == 0

    r = client.get("/payments/dues?member_id=1", headers=h)
    assert r.status_code == 200
    assert r.json()["total_due_paise"] == 0
    app.dependency_overrides.clear()


def test_invalid_method_and_negative_amount_rejected():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/payments", json={"member_id": 1, "amount_paise": 1000, "method": "bitcoin"}, headers=h)
    assert r.status_code == 422
    r = client.post("/payments", json={"member_id": 1, "amount_paise": -5, "method": "cash"}, headers=h)
    assert r.status_code == 422
    app.dependency_overrides.clear()


def test_late_fee_increases_dues_and_cross_tenant_invoice_blocked():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add(Invoice(id=2, gym_id=2, branch_id=9, member_id=99, invoice_number="INV-2-000001", status="issued", taxable_value_paise=5000, gst_rate=0.0, cgst_paise=0, sgst_paise=0, igst_paise=0, total_paise=5000, currency="INR"))
        db.commit()
    h = auth(client)
    r = client.post("/invoices/1/late-fee", json={"late_fee_paise": 5000}, headers=h)
    assert r.status_code == 200
    assert r.json()["total_due_paise"] == 123000

    r = client.post("/payments", json={"member_id": 1, "invoice_id": 2, "amount_paise": 1000, "method": "cash"}, headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()
