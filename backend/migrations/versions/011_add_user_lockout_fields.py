"""add brute-force login protection fields to users

Revision ID: 011_lockout
Revises: 010_notifications
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision      = "011_lockout"
down_revision = "010_notifications"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
