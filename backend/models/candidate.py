from sqlalchemy import Column, String, Float, DateTime, Text, ARRAY, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import func
import uuid

from database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id   = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    # Personal info
    name     = Column(String(200), nullable=True)
    email    = Column(String(255), nullable=True, index=True)
    phone    = Column(String(50),  nullable=True)

    # Resume file
    original_filename = Column(String(255), nullable=False)
    stored_filename   = Column(String(255), nullable=False)
    file_hash         = Column(String(64),  nullable=False)

    # Extracted data
    skills   = Column(ARRAY(String), nullable=False, default=list)
    raw_text = Column(Text, nullable=True)

    # ── Core scores (0-100) ────────────────────────────────────────────────
    semantic_score      = Column(Float, nullable=True)
    skills_score        = Column(Float, nullable=True)
    experience_score    = Column(Float, nullable=True)
    education_score     = Column(Float, nullable=True)
    certification_score = Column(Float, nullable=True)
    score               = Column(Float, nullable=True, index=True)

    # ── Advanced scores (0-100) ────────────────────────────────────────────
    career_progression  = Column(Float, nullable=True)
    skill_recency       = Column(Float, nullable=True)
    resume_quality      = Column(Float, nullable=True)
    job_title_relevance = Column(Float, nullable=True)
    industry_match      = Column(Float, nullable=True)
    education_field     = Column(Float, nullable=True)

    # ── Skill gap details ──────────────────────────────────────────────────
    matched_skills   = Column(ARRAY(String), nullable=False, default=list)
    missing_skills   = Column(ARRAY(String), nullable=False, default=list)
    matched_certs    = Column(ARRAY(String), nullable=False, default=list)
    missing_certs    = Column(ARRAY(String), nullable=False, default=list)
    contextual_skills = Column(ARRAY(String), nullable=False, default=list)
    inferred_skills  = Column(ARRAY(String), nullable=False, default=list)

    # ── Detected info ──────────────────────────────────────────────────────
    experience_years_found = Column(Float,       nullable=True)
    education_level_found  = Column(String(100), nullable=True)
    resume_domain          = Column(String(50),  nullable=True)
    job_domain             = Column(String(50),  nullable=True)

    # ── Red flags ──────────────────────────────────────────────────────────
    red_flags         = Column(ARRAY(String), nullable=False, default=list)
    red_flag_penalty  = Column(Float, nullable=True)

    # ── Recommendation ─────────────────────────────────────────────────────
    recommendation = Column(String(50), nullable=True)

    # Pipeline
    status = Column(String(30), nullable=False, default="applied", index=True)
    notes  = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    job = relationship("Job", backref="candidates")