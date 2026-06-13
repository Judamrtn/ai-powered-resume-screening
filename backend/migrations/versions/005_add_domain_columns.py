"""add domain columns to candidates

Revision ID: 005_dom
Revises: 8d98ffdf38fb
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision      = "005_dom"
down_revision = "8d98ffdf38fb"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("candidates", sa.Column("resume_domain", sa.String(50), nullable=True))
    op.add_column("candidates", sa.Column("job_domain",    sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("candidates", "resume_domain")
    op.drop_column("candidates", "job_domain")