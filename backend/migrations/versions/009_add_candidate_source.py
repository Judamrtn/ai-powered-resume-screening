"""add source tracking column to candidates

Revision ID: 009_source
Revises: 008_ownership
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision      = "009_source"
down_revision = "008_ownership"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("source", sa.String(50), nullable=False, server_default="direct"),
    )


def downgrade() -> None:
    op.drop_column("candidates", "source")
