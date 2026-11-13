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
from app.models.template import MessageTemplate
from app.providers.messaging import MockMessagingProvider
from app.services.messaging import OptOutError, render_template, send_template_to_member


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
        Member(id=1, gym_id=1, branch_id=1, full_name="Rahul", phone="99999", whatsapp_consent=True),
        Member(id=2, gym_id=1, branch_id=1, full_name="Opted Out", phone="88888", whatsapp_consent=True, whatsapp_opt_out=True),
        Member(id=3, gym_id=1, branch_id=1, full_name="No Consent", phone="77777", whatsapp_consent=False),
        MessageTemplate(id=1, gym_id=1, branch_id=1, name="expiry_reminder", body="Hi {name}, your membership expires on {date}.", category="reminder", is_active=True),
    ])
    db.flush()
    db.add(UserRole(id=1, gym_id=1, branch_id=1, user_id=1, role_id=1))
    db.commit()


def auth(client):
    r = client.post("/auth/login", json={"gym_id": 1, "email": "owner@example.com", "password": "secret123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_template_crud_api():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
    h = auth(client)
    r = client.post("/message-templates", json={
        "name": "welcome",
        "body": "Welcome {name} to {gym}!",
        "category": "welcome",
    }, headers=h)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert r.json()["is_active"] is True

    r = client.get("/message-templates", headers=h)
    assert r.status_code == 200
    assert {t["name"] for t in r.json()["items"]} == {"expiry_reminder", "welcome"}

    r = client.patch(f"/message-templates/{tid}", json={"is_active": False}, headers=h)
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    app.dependency_overrides.clear()


def test_send_respects_opt_out_and_consent():
    client, SessionLocal = setup_client()
    with SessionLocal() as db:
        seed(db)
        tmpl = db.get(MessageTemplate, 1)
        provider = MockMessagingProvider()

        m1 = db.get(Member, 1)
        sent = send_template_to_member(db, member=m1, template=tmpl, params={"name": "Rahul", "date": "2026-02-01"}, provider=provider, why="expiry_reminder")
        assert sent["status"] == "sent"
        assert provider.sent_messages[0]["body"] == "Hi Rahul, your membership expires on 2026-02-01."
        assert provider.sent_messages[0]["template_name"] == "expiry_reminder"

        for mid in (2, 3):
            member = db.get(Member, mid)
            try:
                send_template_to_member(db, member=member, template=tmpl, params={"name": "X", "date": "d"}, provider=provider)
            except OptOutError as exc:
                assert "opt" in str(exc).lower() or "consent" in str(exc).lower()
            else:
                raise AssertionError("send should be blocked")
        assert len(provider.sent_messages) == 1

        try:
            render_template("Hi {missing}", {})
        except ValueError:
            pass
        else:
            raise AssertionError("missing params should raise ValueError")
    app.dependency_overrides.clear()
