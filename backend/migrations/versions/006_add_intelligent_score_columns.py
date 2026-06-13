"""add intelligent score columns to candidates

Revision ID: 006_intel
Revises: 005_dom
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "006_intel"
down_revision = "005_dom"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Advanced score columns
    op.add_column("candidates", sa.Column("career_progression",  sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("skill_recency",       sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("resume_quality",      sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("job_title_relevance", sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("industry_match",      sa.Float(), nullable=True))
    op.add_column("candidates", sa.Column("education_field",     sa.Float(), nullable=True))

    # Skill detail arrays
    op.add_column("candidates", sa.Column("contextual_skills",
        postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))
    op.add_column("candidates", sa.Column("inferred_skills",
        postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))

    # Red flags
    op.add_column("candidates", sa.Column("red_flags",
        postgresql.ARRAY(sa.String), nullable=True, server_default="{}"))
    op.add_column("candidates", sa.Column("red_flag_penalty", sa.Float(), nullable=True))

    # Recommendation
    op.add_column("candidates", sa.Column("recommendation", sa.String(50), nullable=True))


def downgrade() -> None:
    for col in [
        "career_progression", "skill_recency", "resume_quality",
        "job_title_relevance", "industry_match", "education_field",
        "contextual_skills", "inferred_skills",
        "red_flags", "red_flag_penalty", "recommendation",
    ]:
        op.drop_column("candidates", col)