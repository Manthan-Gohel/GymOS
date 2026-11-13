"""add gym webhook_token

Revision ID: f1a2c3d4e5f6
Revises: 141ef34464af
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa

revision = "f1a2c3d4e5f6"
down_revision: str | None = "141ef34464af"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gyms", sa.Column("webhook_token", sa.String(length=64), nullable=True))
    op.create_index("ix_gyms_webhook_token", "gyms", ["webhook_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_gyms_webhook_token", table_name="gyms")
    op.drop_column("gyms", "webhook_token")
