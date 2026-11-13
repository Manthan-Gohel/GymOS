
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
        Invoice(id=1, gym_id=1, branch_id=1, member_id=1, invoice_number="INV-1-000001", status="issued", taxable_value_paise=100000, gst_rate=0.0, cgst_paise=0, sgst_paise=0, igst_paise=0, total_paise=100000, currency="INR"),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_receipt_lookup_and_list():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/payments", json={"member_id": 1, "invoice_id": 1, "amount_paise": 40000, "method": "cash"}, headers=h)
    assert r.status_code == 201
    pid = r.json()["payment"]["id"]

    r = client.get(f"/payments/{pid}/receipt", headers=h)
    assert r.status_code == 200, r.text
    receipt = r.json()
    assert receipt["receipt_number"] == f"RCPT-1-{pid:06d}"
    assert receipt["payment"]["amount_paise"] == 40000
    assert receipt["invoice"]["invoice_number"] == "INV-1-000001"
    assert receipt["member"]["full_name"] == "Rahul"

    r = client.get("/payments?member_id=1", headers=h)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    app.dependency_overrides.clear()


def test_refunded_status_reopens_invoice_dues():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/payments", json={"member_id": 1, "invoice_id": 1, "amount_paise": 100000, "method": "upi"}, headers=h)
    pid = r.json()["payment"]["id"]
    assert r.json()["invoice"]["status"] == "paid"

    r = client.post(f"/payments/{pid}/status", json={"status": "refunded"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["payment"]["status"] == "refunded"
    assert r.json()["invoice"]["status"] == "issued"
    assert r.json()["dues"]["total_due_paise"] == 100000

    r = client.post(f"/payments/{pid}/status", json={"status": "nonsense"}, headers=h)
    assert r.status_code == 422
    app.dependency_overrides.clear()


def test_receipt_cross_tenant_not_visible():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        db.add_all([
            Gym(id=2, gym_id=2, branch_id=None, name="Gym B"),
            Member(id=2, gym_id=2, branch_id=9, full_name="Other", phone="111"),
        ])
        db.commit()
    h = auth(client)
    r = client.post("/payments", json={"member_id": 2, "amount_paise": 1000, "method": "cash"}, headers=h)
    assert r.status_code == 404
    r = client.get("/payments/999/receipt", headers=h)
    assert r.status_code == 404
    app.dependency_overrides.clear()
