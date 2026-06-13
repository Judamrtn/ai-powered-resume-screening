from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Shared base ──────────────────────────────────────────────────────────────

class JobBase(BaseModel):
    title:               str          = Field(..., min_length=2, max_length=200)
    department:          Optional[str] = None
    location:            Optional[str] = None
    employment_type:     Optional[str] = Field(None, pattern="^(Full-time|Part-time|Contract|Internship)$")
    salary_min:          Optional[float] = Field(None, ge=0)
    salary_max:          Optional[float] = Field(None, ge=0)
    description:         str          = Field(..., min_length=10)

    required_skills:     list[str]    = Field(default_factory=list)
    preferred_skills:    list[str]    = Field(default_factory=list)
    min_experience_years: Optional[int] = Field(None, ge=0, le=50)
    education_level:     Optional[str] = None
    certifications:      list[str]    = Field(default_factory=list)
    experience_level:    Optional[str] = Field(None, pattern="^(Junior|Mid-level|Senior|Lead)$")

    deadline: Optional[datetime] = None

    @model_validator(mode="after")
    def salary_range_valid(self) -> JobBase:
        if self.salary_min and self.salary_max:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min must be less than or equal to salary_max")
        return self


# ── Request schemas ───────────────────────────────────────────────────────────

class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    title:               Optional[str]   = Field(None, min_length=2, max_length=200)
    department:          Optional[str]   = None
    location:            Optional[str]   = None
    employment_type:     Optional[str]   = Field(None, pattern="^(Full-time|Part-time|Contract|Internship)$")
    salary_min:          Optional[float] = Field(None, ge=0)
    salary_max:          Optional[float] = Field(None, ge=0)
    description:         Optional[str]   = Field(None, min_length=10)
    required_skills:     Optional[list[str]] = None
    preferred_skills:    Optional[list[str]] = None
    min_experience_years: Optional[int]  = Field(None, ge=0, le=50)
    education_level:     Optional[str]   = None
    certifications:      Optional[list[str]] = None
    experience_level:    Optional[str]   = Field(None, pattern="^(Junior|Mid-level|Senior|Lead)$")
    deadline:            Optional[datetime] = None
    status:              Optional[str]   = Field(None, pattern="^(open|closed|archived)$")


# ── Response schemas ──────────────────────────────────────────────────────────

class JobResponse(JobBase):
    id:              UUID
    status:          str
    created_at:      datetime
    updated_at:      datetime
    duplicated_from: Optional[UUID] = None

    model_config = {"from_attributes": True}


class JobWithStats(JobResponse):
    """Job response enriched with live applicant counts."""
    applicant_count:     int
    shortlisted_count:   int
    avg_match_score:     Optional[float]


class JobListResponse(BaseModel):
    total:  int
    offset: int
    limit:  int
    jobs:   list[JobResponse]