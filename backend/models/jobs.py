from sqlalchemy import (
    Column, String, Text, Integer, Float,
    DateTime, Boolean, ARRAY, func
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core fields
    title       = Column(String(200), nullable=False)
    department  = Column(String(100), nullable=True)
    location    = Column(String(100), nullable=True)
    employment_type = Column(String(50), nullable=True)   # Full-time, Part-time, Contract
    salary_min  = Column(Float, nullable=True)
    salary_max  = Column(Float, nullable=True)
    description = Column(Text, nullable=False)

    # Requirements
    required_skills   = Column(ARRAY(String), nullable=False, default=list)
    preferred_skills  = Column(ARRAY(String), nullable=False, default=list)
    min_experience_years = Column(Integer, nullable=True)
    education_level   = Column(String(100), nullable=True)  # Bachelor's, Master's, PhD
    certifications    = Column(ARRAY(String), nullable=False, default=list)
    experience_level  = Column(String(50), nullable=True)   # Junior, Mid, Senior, Lead

    # Lifecycle
    status      = Column(String(20), nullable=False, default="open")   # open | closed | archived
    deadline    = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    # Source tracking (for duplicated postings)
    duplicated_from = Column(UUID(as_uuid=True), nullable=True)