from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class CandidateResponse(BaseModel):
    id:     UUID
    job_id: UUID
    name:   Optional[str]
    email:  Optional[str]
    phone:  Optional[str]
    skills: list[str]

    # Core scores
    semantic_score:      Optional[float]
    skills_score:        Optional[float]
    experience_score:    Optional[float]
    education_score:     Optional[float]
    certification_score: Optional[float]
    score:               Optional[float]

    # Advanced scores
    career_progression:  Optional[float]
    skill_recency:       Optional[float]
    resume_quality:      Optional[float]
    job_title_relevance: Optional[float]
    industry_match:      Optional[float]
    education_field:     Optional[float]

    # Skill gap
    matched_skills:    list[str]
    missing_skills:    list[str]
    matched_certs:     list[str]
    missing_certs:     list[str]
    contextual_skills: list[str]
    inferred_skills:   list[str]

    # Detected info
    experience_years_found: Optional[float]
    education_level_found:  Optional[str]
    resume_domain:          Optional[str]
    job_domain:             Optional[str]

    # Red flags
    red_flags:        list[str]
    red_flag_penalty: Optional[float]
    recommendation:   Optional[str]

    status: str
    notes:  Optional[str]
    original_filename: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateStatusUpdate(BaseModel):
    status: str


class CandidateNotesUpdate(BaseModel):
    notes: str


class CandidateListResponse(BaseModel):
    total:      int
    offset:     int
    limit:      int
    candidates: list[CandidateResponse]