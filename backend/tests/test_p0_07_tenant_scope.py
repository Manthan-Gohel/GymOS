import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.tenant import TenantScopeError, scoped_query, tenant_add
from app.models.core import Branch, Gym, User


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def seed(db: Session):
    g1 = Gym(id=1, gym_id=1, branch_id=None, name="Gym A")
    g2 = Gym(id=2, gym_id=2, branch_id=None, name="Gym B")
    b1 = Branch(id=10, gym_id=1, branch_id=10, name="A-main")
    b2 = Branch(id=20, gym_id=2, branch_id=20, name="B-main")
    db.add_all([g1, g2, b1, b2])
    db.commit()
    return g1, g2, b1, b2


def test_scoped_query_filters_by_tenant(db: Session):
    seed(db)
    db.add_all(
        [
            User(id=100, gym_id=1, branch_id=10, email="a@example.com", full_name="A"),
            User(id=200, gym_id=2, branch_id=20, email="b@example.com", full_name="B"),
        ]
    )
    db.commit()

    users_g1 = db.scalars(scoped_query(db, User, gym_id=1, branch_id=10)).all()
    assert [u.id for u in users_g1] == [100]
    users_g2 = db.scalars(scoped_query(db, User, gym_id=2, branch_id=20)).all()
    assert [u.id for u in users_g2] == [200]


def test_scoped_query_prevents_cross_tenant_read(db: Session):
    seed(db)
    db.add(User(id=100, gym_id=1, branch_id=10, email="a@example.com", full_name="A"))
    db.commit()
    stmt = scoped_query(db, User, gym_id=2, branch_id=20).where(User.id == 100)
    leaked = db.scalars(stmt).all()
    assert leaked == []


def test_tenant_add_rejects_wrong_tenant_object(db: Session):
    seed(db)
    wrong = User(id=300, gym_id=2, branch_id=20, email="x@example.com", full_name="X")
    with pytest.raises(TenantScopeError):
        tenant_add(db, wrong, gym_id=1, branch_id=10)
