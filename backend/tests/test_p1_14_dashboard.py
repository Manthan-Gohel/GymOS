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
from app.models.payment import Payment


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
        Payment(id=1, gym_id=1, branch_id=1, member_id=1, amount_paise=500000, method="cash", status="paid", paid_at=date(2026, 1, 5)),
        Payment(id=2, gym_id=1, branch_id=1, member_id=1, amount_paise=100000, method="upi", status="refunded", paid_at=date(2026, 1, 5)),
        Payment(id=3, gym_id=1, branch_id=1, member_id=1, amount_paise=200000, method="cash", status="paid", paid_at=date(2026, 1, 6)),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_expenses_crud_and_daily_dashboard_math():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/expenses", json={
        "category": "rent", "amount_paise": 300000, "spent_on": "2026-01-05", "vendor": "Landlord"
    }, headers=h)
    assert r.status_code == 201, r.text
    r = client.post("/expenses", json={
        "category": "electricity", "amount_paise": 50000, "spent_on": "2026-01-05"
    }, headers=h)
    assert r.status_code == 201

    r = client.get("/expenses?month=2026-01", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    r = client.get("/dashboard/daily?on_date=2026-01-05", headers=h)
    assert r.status_code == 200, r.text
    day = r.json()
    assert day["revenue_paise"] == 500000  # refunded payment excluded
    assert day["expense_paise"] == 350000
    assert day["profit_paise"] == 150000
    assert day["payments_count"] == 1

    r = client.get("/dashboard/summary?from_date=2026-01-01&to_date=2026-01-31", headers=h)
    assert r.status_code == 200
    summary = r.json()
    assert summary["revenue_paise"] == 700000
    assert summary["expense_paise"] == 350000
    assert summary["profit_paise"] == 350000
    app.dependency_overrides.clear()


def test_expense_validation_and_rbac():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/expenses", json={"category": "rent", "amount_paise": -1, "spent_on": "2026-01-05"}, headers=h)
    assert r.status_code == 422
    # VULN-008: clear the auth cookie too — an empty header set alone is no longer "unauthenticated"
    client.cookies.clear()
    r = client.get("/dashboard/daily", headers={})
    assert r.status_code == 401
    app.dependency_overrides.clear()
