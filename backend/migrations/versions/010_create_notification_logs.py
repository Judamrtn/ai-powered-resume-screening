"""create notification_logs table

Revision ID: 010_notifications
Revises: 009_source
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "010_notifications"
down_revision = "009_source"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notification_type", sa.String(50),  nullable=False),
        sa.Column("recipient_email",   sa.String(255), nullable=False),
        sa.Column("subject",           sa.String(500), nullable=False),
        sa.Column("body",              sa.Text(),      nullable=False),
        sa.Column("status",        sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(),     nullable=True),
        sa.Column("retry_count",   sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_logs_candidate_id", "notification_logs", ["candidate_id"])
    op.create_index("ix_notification_logs_interview_id", "notification_logs", ["interview_id"])
    op.create_index("ix_notification_logs_job_id",       "notification_logs", ["job_id"])
    op.create_index("ix_notification_logs_type",         "notification_logs", ["notification_type"])
    op.create_index("ix_notification_logs_status",       "notification_logs", ["status"])


def downgrade() -> None:
    op.drop_table("notification_logs")
