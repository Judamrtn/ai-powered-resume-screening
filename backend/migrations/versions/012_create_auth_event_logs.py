"""create auth_event_logs table

Revision ID: 012_auth_events
Revises: 011_lockout
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "012_auth_events"
down_revision = "011_lockout"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "auth_event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("email",      sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(50),  nullable=False),
        sa.Column("ip_address", sa.String(64),  nullable=True),
        sa.Column("detail",     sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_auth_event_logs_user_id",    "auth_event_logs", ["user_id"])
    op.create_index("ix_auth_event_logs_email",      "auth_event_logs", ["email"])
    op.create_index("ix_auth_event_logs_event_type", "auth_event_logs", ["event_type"])


def downgrade() -> None:
    op.drop_table("auth_event_logs")
