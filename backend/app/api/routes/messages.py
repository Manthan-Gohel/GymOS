from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.message import OutboundMessage

router = APIRouter(prefix="/messages", tags=["messages"])

StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


def _to_dict(m: OutboundMessage) -> dict:
    return {
        "id": m.id,
        "gym_id": m.gym_id,
        "branch_id": m.branch_id,
        "member_id": m.member_id,
        "phone": m.phone,
        "template_name": m.template_name,
        "body": m.body,
        "kind": m.kind,
        "status": m.status,
        "provider": m.provider,
        "who": m.who,
        "why": m.why,
        "error": m.error,
        "created_at": m.created_at.isoformat(),
    }


@router.get("")
def list_messages(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
    member_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
):
    query = db.query(OutboundMessage).filter(OutboundMessage.gym_id == current_user.gym_id)
    if member_id is not None:
        query = query.filter(OutboundMessage.member_id == member_id)
    if status is not None:
        query = query.filter(OutboundMessage.status == status)
    items = query.order_by(OutboundMessage.id.desc()).limit(min(max(limit, 1), 200)).all()
    return {"items": [_to_dict(m) for m in items], "total": len(items)}
