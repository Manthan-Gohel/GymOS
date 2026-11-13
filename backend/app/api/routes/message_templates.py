from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.template import MessageTemplate

router = APIRouter(prefix="/message-templates", tags=["message-templates"])

OwnerAdmin = Annotated[User, Depends(require_roles(["owner", "admin"]))]
StaffRead = Annotated[User, Depends(require_roles(["owner", "admin", "reception", "trainer"]))]


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1)
    category: str = "reminder"
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: str | None = None
    body: str | None = None
    category: str | None = None
    is_active: bool | None = None


def _to_dict(t: MessageTemplate) -> dict:
    return {
        "id": t.id,
        "gym_id": t.gym_id,
        "branch_id": t.branch_id,
        "name": t.name,
        "body": t.body,
        "category": t.category,
        "is_active": t.is_active,
    }


def _get_template(db: Session, gym_id: int, template_id: int) -> MessageTemplate:
    t = db.query(MessageTemplate).filter(MessageTemplate.id == template_id, MessageTemplate.gym_id == gym_id).first()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return t


@router.post("", status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    if db.query(MessageTemplate).filter(
        MessageTemplate.gym_id == current_user.gym_id, MessageTemplate.name == payload.name
    ).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template name already exists")
    t = MessageTemplate(
        gym_id=current_user.gym_id,
        branch_id=current_user.branch_id or 0,
        **payload.model_dump(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_dict(t)


@router.get("")
def list_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    _role: StaffRead,
    db: Annotated[Session, Depends(get_db)],
):
    items = (
        db.query(MessageTemplate)
        .filter(MessageTemplate.gym_id == current_user.gym_id)
        .order_by(MessageTemplate.name)
        .all()
    )
    return {"items": [_to_dict(t) for t in items], "total": len(items)}


@router.patch("/{template_id}")
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _role: OwnerAdmin,
    db: Annotated[Session, Depends(get_db)],
):
    t = _get_template(db, current_user.gym_id, template_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != t.name:
        if db.query(MessageTemplate).filter(
            MessageTemplate.gym_id == current_user.gym_id, MessageTemplate.name == data["name"]
        ).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template name already exists")
    for key, value in data.items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return _to_dict(t)
