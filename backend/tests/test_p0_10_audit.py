from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.audit import AuditLog
from app.services.audit import write_audit_log


def test_write_audit_log_records_entry():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        write_audit_log(
            db,
            gym_id=1,
            branch_id=1,
            actor_user_id=10,
            action="member.create",
            entity_type="member",
            entity_id="123",
            why="reception registration",
            metadata={"source": "panel"},
        )
        db.commit()
        row = db.query(AuditLog).one()
        assert row.gym_id == 1 and row.branch_id == 1
        assert row.actor_user_id == 10
        assert row.action == "member.create"
        assert row.entity_type == "member"
        assert row.entity_id == "123"
        assert row.why == "reception registration"
        assert row.metadata_json["source"] == "panel"
        assert row.created_at is not None
