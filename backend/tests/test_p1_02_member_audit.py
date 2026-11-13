from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.core import Branch, Gym, Role, User, UserRole


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
        Role(id=1, gym_id=1, branch_id=1, name="reception"),
        User(id=1, gym_id=1, branch_id=1, email="reception@example.com", full_name="Reception", hashed_password=get_password_hash("secret123"), is_active=True),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def token(client):
    resp = client.post("/auth/login", json={"gym_id": 1, "email": "reception@example.com", "password": "secret123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_member_create_and_update_write_audit_logs():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    t = token(client)
    h = {"Authorization": f"Bearer {t}"}

    r = client.post("/members", json={"full_name": "Test User", "phone": "99999", "kyc_id_number": "SECRET-KYC"}, headers=h)
    assert r.status_code == 201
    member_id = r.json()["id"]

    r = client.patch(f"/members/{member_id}", json={"health_notes": "sensitive"}, headers=h)
    assert r.status_code == 200

    with SessionLocal() as db:
        logs = db.query(AuditLog).filter(AuditLog.entity_type == "member").order_by(AuditLog.id).all()
        assert len(logs) >= 2
        actions = [log.action for log in logs]
        assert "member.create" in actions
        assert "member.update" in actions
        # sensitive field values should not be stored in audit metadata
        for log in logs:
            meta_str = str(log.metadata_json or {})
            assert "SECRET-KYC" not in meta_str
            assert "sensitive" not in meta_str  # updated health note value
            assert "1234-5678-9012" not in meta_str

    app.dependency_overrides.clear()
