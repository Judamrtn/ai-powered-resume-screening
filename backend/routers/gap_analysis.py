"""
Skills Gap Analysis Router
Provides endpoints for analyzing skill gaps between candidates and job requirements.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.candidate import Candidate
from models.jobs import Job
from security import require_recruiter
from models.user import User
from taxonomy import normalize_skill, skills_match_with_synonyms

router = APIRouter(prefix="/jobs/{job_id}/gap-analysis", tags=["Skills Gap Analysis"])


# ── Response schemas ──────────────────────────────────────────────────────────

class CandidateGapSummary(BaseModel):
    candidate_id:    UUID
    name:            Optional[str]
    email:           Optional[str]
    score:           Optional[float]
    status:          str
    matched_skills:  list[str]
    missing_skills:  list[str]
    matched_certs:   list[str]
    missing_certs:   list[str]
    skills_match_pct: float
    experience_years_found: Optional[float]
    education_level_found:  Optional[str]


class JobGapAnalysis(BaseModel):
    job_id:          UUID
    job_title:       str
    required_skills: list[str]
    total_candidates: int

    # Skill coverage across all candidates
    skill_coverage: list[dict]   # [{skill, candidates_with_skill, coverage_pct}]

    # Most common missing skills
    top_missing_skills: list[dict]  # [{skill, missing_count, missing_pct}]

    # Candidate summaries
    candidates: list[CandidateGapSummary]


class SingleCandidateGap(BaseModel):
    candidate_id:    UUID
    name:            Optional[str]
    job_title:       str
    required_skills: list[str]
    matched_skills:  list[str]
    missing_skills:  list[str]
    required_certs:  list[str]
    matched_certs:   list[str]
    missing_certs:   list[str]
    skills_match_pct:  float
    overall_score:     Optional[float]
    experience_years_found: Optional[float]
    education_level_found:  Optional[str]
    recommendation:  str   # "Strong Match" | "Good Match" | "Partial Match" | "Weak Match"


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_recommendation(score: float) -> str:
    if score >= 80:
        return "Strong Match"
    elif score >= 60:
        return "Good Match"
    elif score >= 40:
        return "Partial Match"
    else:
        return "Weak Match"


# ── SINGLE CANDIDATE GAP ──────────────────────────────────────────────────────

@router.get("/candidates/{candidate_id}", response_model=SingleCandidateGap)
def candidate_gap_analysis(
    job_id:       UUID,
    candidate_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Detailed skill gap analysis for a single candidate against a job."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidate = db.get(Candidate, candidate_id)
    if not candidate or str(candidate.job_id) != str(job_id):
        raise HTTPException(status_code=404, detail="Candidate not found.")

    # Re-compute gap with synonym normalization
    gap = skills_match_with_synonyms(
        candidate.skills or [],
        job.required_skills or [],
    )

    return SingleCandidateGap(
        candidate_id           = candidate.id,
        name                   = candidate.name,
        job_title              = job.title,
        required_skills        = job.required_skills or [],
        matched_skills         = gap["matched"],
        missing_skills         = gap["missing"],
        required_certs         = job.certifications or [],
        matched_certs          = candidate.matched_certs or [],
        missing_certs          = candidate.missing_certs or [],
        skills_match_pct       = round(gap["match_ratio"] * 100, 2),
        overall_score          = candidate.score,
        experience_years_found = candidate.experience_years_found,
        education_level_found  = candidate.education_level_found,
        recommendation         = get_recommendation(candidate.score or 0),
    )


# ── JOB-WIDE GAP ANALYSIS ─────────────────────────────────────────────────────

@router.get("/", response_model=JobGapAnalysis)
def job_gap_analysis(
    job_id: UUID,
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_recruiter),
):
    """
    Aggregate skill gap analysis across all candidates for a job.
    Shows which required skills are most commonly missing.
    """
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidates = db.query(Candidate).filter(Candidate.job_id == job_id).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found for this job.")

    required_skills = job.required_skills or []
    total           = len(candidates)

    # Count how many candidates have each required skill
    skill_counts = {skill: 0 for skill in required_skills}
    missing_counts = {skill: 0 for skill in required_skills}

    candidate_summaries = []

    for c in candidates:
        gap = skills_match_with_synonyms(c.skills or [], required_skills)

        for skill in gap["matched"]:
            if skill in skill_counts:
                skill_counts[skill] += 1

        for skill in gap["missing"]:
            if skill in missing_counts:
                missing_counts[skill] += 1

        candidate_summaries.append(CandidateGapSummary(
            candidate_id      = c.id,
            name              = c.name,
            email             = c.email,
            score             = c.score,
            status            = c.status,
            matched_skills    = gap["matched"],
            missing_skills    = gap["missing"],
            matched_certs     = c.matched_certs or [],
            missing_certs     = c.missing_certs or [],
            skills_match_pct  = round(gap["match_ratio"] * 100, 2),
            experience_years_found = c.experience_years_found,
            education_level_found  = c.education_level_found,
        ))

    # Build skill coverage stats
    skill_coverage = [
        {
            "skill":                  skill,
            "candidates_with_skill":  count,
            "coverage_pct":           round((count / total) * 100, 1),
        }
        for skill, count in sorted(skill_counts.items(), key=lambda x: -x[1])
    ]

    # Top missing skills
    top_missing = [
        {
            "skill":         skill,
            "missing_count": count,
            "missing_pct":   round((count / total) * 100, 1),
        }
        for skill, count in sorted(missing_counts.items(), key=lambda x: -x[1])
        if count > 0
    ]

    # Sort candidates by score descending
    candidate_summaries.sort(key=lambda x: x.score or 0, reverse=True)

    return JobGapAnalysis(
        job_id             = job.id,
        job_title          = job.title,
        required_skills    = required_skills,
        total_candidates   = total,
        skill_coverage     = skill_coverage,
        top_missing_skills = top_missing,
        candidates         = candidate_summaries,
    )