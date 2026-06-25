from sqlalchemy import (
    Column, String, Text, Integer, Float,
    DateTime, Boolean, ARRAY, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Ownership: the recruiter who created this job posting. Required
    # for access scoping - a recruiter should only see/manage jobs they
    # own, while an admin sees everything regardless of this field.
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True, index=True)

    # Core fields
    title       = Column(String(200), nullable=False)
    department  = Column(String(100), nullable=True)
    location    = Column(String(100), nullable=True)
    employment_type = Column(String(50), nullable=True)
    salary_min  = Column(Float, nullable=True)
    salary_max  = Column(Float, nullable=True)
    description = Column(Text, nullable=False)

    # Requirements
    required_skills   = Column(ARRAY(String), nullable=False, default=list)
    preferred_skills  = Column(ARRAY(String), nullable=False, default=list)
    min_experience_years = Column(Integer, nullable=True)
    education_level   = Column(String(100), nullable=True)
    certifications    = Column(ARRAY(String), nullable=False, default=list)
    experience_level  = Column(String(50), nullable=True)

    # Lifecycle
    status      = Column(String(20), nullable=False, default="open")
    deadline    = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    duplicated_from = Column(UUID(as_uuid=True), nullable=True)

    # Relationship back to the owning recruiter
    owner = relationship("User", backref="jobs", foreign_keys=[created_by])
