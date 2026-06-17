"""create interviews and feedback tables

Revision ID: 007_interviews
Revises: 006_intel
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "007_interviews"
down_revision = "006_intel"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Interviews table
    op.create_table(
        "interviews",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",            sa.String(200), nullable=False),
        sa.Column("format",           sa.String(50),  nullable=False),
        sa.Column("scheduled_at",     sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(),   nullable=False, server_default="60"),
        sa.Column("location",         sa.String(200), nullable=True),
        sa.Column("meeting_link",     sa.String(500), nullable=True),
        sa.Column("interviewers",     postgresql.ARRAY(sa.String), nullable=False,
                  server_default="{}"),
        sa.Column("round_number",     sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status",           sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("candidate_notified",   sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("interviewers_notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("calendar_event_id", sa.String(200), nullable=True),
        sa.Column("notes",      sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"])
    op.create_index("ix_interviews_job_id",       "interviews", ["job_id"])
    op.create_index("ix_interviews_status",        "interviews", ["status"])
    op.create_index("ix_interviews_scheduled_at",  "interviews", ["scheduled_at"])

    # Interview feedback table
    op.create_table(
        "interview_feedback",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interviewer_email", sa.String(255), nullable=False),
        sa.Column("interviewer_name",  sa.String(200), nullable=True),
        sa.Column("technical_score",       sa.Float(), nullable=True),
        sa.Column("communication_score",   sa.Float(), nullable=True),
        sa.Column("problem_solving_score", sa.Float(), nullable=True),
        sa.Column("cultural_fit_score",    sa.Float(), nullable=True),
        sa.Column("overall_score",         sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(50), nullable=True),
        sa.Column("strengths",  sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("comments",   sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_feedback_interview_id", "interview_feedback", ["interview_id"])


def downgrade() -> None:
    op.drop_table("interview_feedback")
    op.drop_table("interviews")