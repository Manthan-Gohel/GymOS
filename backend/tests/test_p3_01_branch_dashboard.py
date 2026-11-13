from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import Branch
from app.models.expense import Expense
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
        __import__("app.models.core", fromlist=["Gym"]).Gym(id=1, gym_id=1, branch_id=None, name="Gym A"),
        Branch(id=1, gym_id=1, branch_id=1, name="Main"),
        Branch(id=2, gym_id=1, branch_id=2, name="Branch B"),
        __import__("app.models.core", fromlist=["Role"]).Role(id=1, gym_id=1, branch_id=1, name="owner"),
        __import__("app.models.core", fromlist=["User"]).User(id=1, gym_id=1, branch_id=None, email="owner@example.com", full_name="Owner", hashed_password=get_password_hash("secret123"), is_active=True),
        __import__("app.models.core", fromlist=["User"]).User(id=2, gym_id=1, branch_id=2, email="mgr2@example.com", full_name="Mgr B", hashed_password=get_password_hash("secret123"), is_active=True),
        __import__("app.models.core", fromlist=["UserRole"]).UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1),
        __import__("app.models.core", fromlist=["UserRole"]).UserRole(id=2, gym_id=1, branch_id=2, user_id=2, role_id=1),
    ])
    db.flush()
    # Payments: Main branch 1500, Branch B 800
    db.add_all([
        Payment(id=1, gym_id=1, branch_id=1, member_id=1, amount_paise=150000, method="cash", status="paid", paid_at=date(2026, 1, 15), recorded_by=1),
        Payment(id=2, gym_id=1, branch_id=2, member_id=2, amount_paise=80000, method="upi", status="paid", paid_at=date(2026, 1, 15), recorded_by=2),
    ])
    # Expenses: Main branch 500, Branch B 300 (on 2026-01-15 to match dashboard query date)
    db.add_all([
        Expense(id=1, gym_id=1, branch_id=1, category="rent", amount_paise=50000, spent_on=date(2026, 1, 15), recorded_by=1),
        Expense(id=2, gym_id=1, branch_id=2, category="rent", amount_paise=30000, spent_on=date(2026, 1, 15), recorded_by=2),
    ])
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_daily_dashboard_branch_filter():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)

    # No branch filter - all branches
    r = client.get("/dashboard/daily?on_date=2026-01-15", headers=h)
    assert r.status_code == 200
    assert r.json()["revenue_paise"] == 230000
    assert r.json()["expense_paise"] == 80000

    # Filter by Main branch
    r = client.get("/dashboard/daily?on_date=2026-01-15&branch_id=1", headers=h)
    assert r.status_code == 200
    assert r.json()["revenue_paise"] == 150000
    assert r.json()["expense_paise"] == 50000
    assert r.json()["branch_id"] == 1

    # Filter by Branch B
    r = client.get("/dashboard/daily?on_date=2026-01-15&branch_id=2", headers=h)
    assert r.json()["revenue_paise"] == 80000
    assert r.json()["expense_paise"] == 30000
    assert r.json()["branch_id"] == 2


def test_summary_dashboard_branch_filter():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)

    r = client.get("/dashboard/summary?from_date=2026-01-15&to_date=2026-01-15&branch_id=1", headers=h)
    assert r.status_code == 200
    assert r.json()["revenue_paise"] == 150000
    assert r.json()["branch_id"] == 1


def test_branch_comparison():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)

    r = client.get("/dashboard/branch-comparison?from_date=2026-01-15&to_date=2026-01-15", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["branches"]) == 2
    main = next(b for b in data["branches"] if b["branch_id"] == 1)
    assert main["revenue_paise"] == 150000
    assert main["expense_paise"] == 50000
    assert main["profit_paise"] == 100000
    assert data["totals"]["revenue_paise"] == 230000
    assert data["totals"]["profit_paise"] == 150000