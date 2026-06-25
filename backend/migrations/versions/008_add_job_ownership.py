"""add created_by ownership column to jobs

Revision ID: 008_ownership
Revises: 007_interviews
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "008_ownership"
down_revision = "007_interviews"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_jobs_created_by", "jobs", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_jobs_created_by", table_name="jobs")
    op.drop_column("jobs", "created_by")
