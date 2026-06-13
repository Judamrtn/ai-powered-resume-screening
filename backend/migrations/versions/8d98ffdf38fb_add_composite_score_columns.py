"""add composite score columns to candidates

Revision ID: 004
Revises: 003
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "8d98ffdf38fb"
down_revision = "75d06beaf175"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new score columns
    op.add_column("candidates", sa.Column("experience_score",    sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("education_score",     sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("certification_score", sa.Float(), nullable=True))

    # Skill gap arrays
    op.add_column("candidates", sa.Column("matched_skills",
        sa.dialects.postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))
    op.add_column("candidates", sa.Column("missing_skills",
        sa.dialects.postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))
    op.add_column("candidates", sa.Column("matched_certs",
        sa.dialects.postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))
    op.add_column("candidates", sa.Column("missing_certs",
        sa.dialects.postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))

    # Detected experience / education
    op.add_column("candidates", sa.Column("experience_years_found", sa.Float(),       nullable=True))
    op.add_column("candidates", sa.Column("education_level_found",  sa.String(100),   nullable=True))


def downgrade() -> None:
    op.drop_column("candidates", "experience_score")
    op.drop_column("candidates", "education_score")
    op.drop_column("candidates", "certification_score")
    op.drop_column("candidates", "matched_skills")
    op.drop_column("candidates", "missing_skills")
    op.drop_column("candidates", "matched_certs")
    op.drop_column("candidates", "missing_certs")
    op.drop_column("candidates", "experience_years_found")
    op.drop_column("candidates", "education_level_found")