"""create candidates table

Revision ID: 003
Revises: ccce8b2855bb
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "75d06beaf175"
down_revision = "ccce8b2855bb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id",      postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),

        sa.Column("name",    sa.String(200), nullable=True),
        sa.Column("email",   sa.String(255), nullable=True),
        sa.Column("phone",   sa.String(50),  nullable=True),

        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename",   sa.String(255), nullable=False),
        sa.Column("file_hash",         sa.String(64),  nullable=False),

        sa.Column("skills",   postgresql.ARRAY(sa.String), nullable=False,
                  server_default="{}"),
        sa.Column("raw_text", sa.Text(), nullable=True),

        sa.Column("semantic_score", sa.Float(), nullable=True),
        sa.Column("skills_score",   sa.Float(), nullable=True),
        sa.Column("score",          sa.Float(), nullable=True),

        sa.Column("status", sa.String(30), nullable=False, server_default="applied"),
        sa.Column("notes",  sa.Text(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_index("ix_candidates_job_id", "candidates", ["job_id"])
    op.create_index("ix_candidates_email",  "candidates", ["email"])
    op.create_index("ix_candidates_score",  "candidates", ["score"])
    op.create_index("ix_candidates_status", "candidates", ["status"])


def downgrade() -> None:
    op.drop_table("candidates")