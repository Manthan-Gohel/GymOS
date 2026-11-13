from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit_log(
    db: Session,
    *,
    gym_id: int,
    branch_id: int | None,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    why: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        gym_id=gym_id,
        branch_id=branch_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        why=why,
        metadata_json=metadata,
    )
    db.add(entry)
    return entry
