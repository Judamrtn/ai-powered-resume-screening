"""
Reporting & Analytics Router

Covers two of the three metrics from spec section 4.12 that have real,
trustworthy data behind them right now:

  - Recruitment funnel metrics (applied -> screened -> shortlisted ->
    interviewed -> hired/rejected), optionally broken down by source
  - AI model performance metrics: score distribution across candidates,
    so recruiters/admins can sanity-check whether the scoring engine is
    producing a sensible spread rather than clustering everyone at one
    extreme.

Deliberately NOT included yet:
  - Time-to-fill: no exact data source exists (Candidate has no status-
    change history, only created_at/updated_at on the row as a whole).
    Building this properly requires a status_history table first, so it
    is left out rather than shipped as a silently approximate number.
  - Source effectiveness "which source yields the most HIRES": the
    `source` field on Candidate was only just added and has no real
    historical data yet. The funnel-by-source breakdown below is the
    honest first step toward this, but drawing conclusions from it
    today would be drawing conclusions from near-empty data.
  - Diversity metrics: no demographic data is collected anywhere in the
    system. Not stubbed out here deliberately - this needs an explicit
    decision about what (if anything) to collect, not a silent default.
  - PDF/Excel export: separate piece of work, follows once these JSON
    endpoints are confirmed to return correct numbers.

Scoping: identical ownership rules as everywhere else in the system -
recruiters see only their own jobs' data, admins see everything.
"""
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from database import get_db
from models.jobs import Job
from models.candidate import Candidate
from models.user import User
from security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reporting & Analytics"])


# ── Response schemas ──────────────────────────────────────────────────────────

class FunnelStage(BaseModel):
    status: str
    count:  int


class SourceBreakdown(BaseModel):
    source: str
    count:  int


class FunnelReport(BaseModel):
    job_id:          Optional[UUID]   # None when this is an aggregate across multiple jobs
    job_title:       Optional[str]
    total_applicants: int
    funnel:          list[FunnelStage]
    by_source:       list[SourceBreakdown]
    date_from:       Optional[datetime]
    date_to:         Optional[datetime]


class ScoreBucket(BaseModel):
    range_label: str   # e.g. "0-20", "20-40"
    count:       int


class ScoreDistributionReport(BaseModel):
    job_id:           Optional[UUID]
    job_title:        Optional[str]
    total_scored:     int
    avg_score:        Optional[float]
    median_score:     Optional[float]
    min_score:        Optional[float]
    max_score:        Optional[float]
    distribution:     list[ScoreBucket]
    # Average of each individual sub-signal, so you can see e.g. whether
    # semantic_score is systematically pulling scores up/down relative
    # to skills_score across the whole candidate pool for this job.
    avg_semantic_score:      Optional[float]
    avg_skills_score:        Optional[float]
    avg_experience_score:    Optional[float]
    avg_education_score:     Optional[float]
    avg_certification_score: Optional[float]
    recommendation_counts:   dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_scoped_job_ids(db: Session, current_user: User, job_id: Optional[UUID]) -> list[UUID]:
    """
    Returns the list of job IDs this report should cover, respecting
    ownership scoping. If job_id is given, validates the caller actually
    owns it (or is admin) and returns just that one. Otherwise returns
    every job the caller is allowed to see.
    """
    if job_id:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if current_user.role != "admin" and str(job.created_by) != str(current_user.id):
            raise HTTPException(status_code=404, detail="Job not found.")
        return [job_id]

    q = db.query(Job.id)
    if current_user.role != "admin":
        q = q.filter(Job.created_by == current_user.id)
    return [row.id for row in q.all()]


def get_job_title(db: Session, job_id: Optional[UUID]) -> Optional[str]:
    if not job_id:
        return None
    job = db.get(Job, job_id)
    return job.title if job else None


# ── Funnel report ─────────────────────────────────────────────────────────────

ALL_STATUSES = ["applied", "screening", "shortlisted", "interview", "offer", "hired", "rejected"]


@router.get("/funnel", response_model=FunnelReport)
def get_funnel_report(
    db:           Session  = Depends(get_db),
    current_user: User     = Depends(get_current_user),
    job_id:       Optional[UUID] = Query(default=None, description="Scope to a single job; omit for an aggregate across all your jobs"),
    date_from:    Optional[datetime] = Query(default=None, description="Only count candidates who applied on/after this date"),
    date_to:      Optional[datetime] = Query(default=None, description="Only count candidates who applied on/before this date"),
):
    """
    Recruitment funnel: how many candidates are at each pipeline stage,
    plus a breakdown by application source. Scoped to jobs you own
    (or all jobs, if admin and job_id is omitted).
    """
    job_ids = get_scoped_job_ids(db, current_user, job_id)
    if not job_ids:
        return FunnelReport(
            job_id=job_id, job_title=get_job_title(db, job_id),
            total_applicants=0, funnel=[], by_source=[],
            date_from=date_from, date_to=date_to,
        )

    q = db.query(Candidate).filter(Candidate.job_id.in_(job_ids))
    if date_from:
        q = q.filter(Candidate.created_at >= date_from)
    if date_to:
        q = q.filter(Candidate.created_at <= date_to)

    candidates = q.all()
    total = len(candidates)

    status_counts = {s: 0 for s in ALL_STATUSES}
    for c in candidates:
        if c.status in status_counts:
            status_counts[c.status] += 1

    funnel = [FunnelStage(status=s, count=status_counts[s]) for s in ALL_STATUSES]

    source_counts: dict[str, int] = {}
    for c in candidates:
        src = c.source or "direct"
        source_counts[src] = source_counts.get(src, 0) + 1
    by_source = [
        SourceBreakdown(source=src, count=cnt)
        for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1])
    ]

    return FunnelReport(
        job_id           = job_id,
        job_title        = get_job_title(db, job_id),
        total_applicants = total,
        funnel           = funnel,
        by_source        = by_source,
        date_from        = date_from,
        date_to          = date_to,
    )


# ── Score distribution report ─────────────────────────────────────────────────

def bucket_label(score: float) -> str:
    if score < 20:  return "0-20"
    if score < 40:  return "20-40"
    if score < 60:  return "40-60"
    if score < 80:  return "60-80"
    return "80-100"


@router.get("/score-distribution", response_model=ScoreDistributionReport)
def get_score_distribution(
    db:           Session  = Depends(get_db),
    current_user: User     = Depends(get_current_user),
    job_id:       Optional[UUID] = Query(default=None, description="Scope to a single job; omit for an aggregate across all your jobs"),
    date_from:    Optional[datetime] = Query(default=None),
    date_to:      Optional[datetime] = Query(default=None),
):
    """
    Distribution of final composite scores across candidates, plus the
    average of each individual scoring sub-signal. Useful for sanity-
    checking the AI engine: if every candidate clusters at one extreme,
    or one sub-signal is dominating, that's visible here.
    """
    job_ids = get_scoped_job_ids(db, current_user, job_id)
    if not job_ids:
        return ScoreDistributionReport(
            job_id=job_id, job_title=get_job_title(db, job_id),
            total_scored=0, avg_score=None, median_score=None,
            min_score=None, max_score=None, distribution=[],
            avg_semantic_score=None, avg_skills_score=None,
            avg_experience_score=None, avg_education_score=None,
            avg_certification_score=None, recommendation_counts={},
        )

    q = db.query(Candidate).filter(
        Candidate.job_id.in_(job_ids),
        Candidate.score.isnot(None),
    )
    if date_from:
        q = q.filter(Candidate.created_at >= date_from)
    if date_to:
        q = q.filter(Candidate.created_at <= date_to)

    candidates = q.all()
    scores = sorted(c.score for c in candidates)
    total  = len(scores)

    if total == 0:
        return ScoreDistributionReport(
            job_id=job_id, job_title=get_job_title(db, job_id),
            total_scored=0, avg_score=None, median_score=None,
            min_score=None, max_score=None, distribution=[],
            avg_semantic_score=None, avg_skills_score=None,
            avg_experience_score=None, avg_education_score=None,
            avg_certification_score=None, recommendation_counts={},
        )

    avg_score = round(sum(scores) / total, 2)
    mid = total // 2
    median_score = round(scores[mid] if total % 2 == 1 else (scores[mid - 1] + scores[mid]) / 2, 2)

    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for s in scores:
        buckets[bucket_label(s)] += 1
    distribution = [ScoreBucket(range_label=k, count=v) for k, v in buckets.items()]

    def avg_of(field: str) -> Optional[float]:
        vals = [getattr(c, field) for c in candidates if getattr(c, field) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    recommendation_counts: dict[str, int] = {}
    for c in candidates:
        rec = c.recommendation or "Unscored"
        recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

    return ScoreDistributionReport(
        job_id                   = job_id,
        job_title                = get_job_title(db, job_id),
        total_scored             = total,
        avg_score                = avg_score,
        median_score             = median_score,
        min_score                = round(scores[0], 2),
        max_score                = round(scores[-1], 2),
        distribution             = distribution,
        avg_semantic_score       = avg_of("semantic_score"),
        avg_skills_score         = avg_of("skills_score"),
        avg_experience_score     = avg_of("experience_score"),
        avg_education_score      = avg_of("education_score"),
        avg_certification_score  = avg_of("certification_score"),
        recommendation_counts    = recommendation_counts,
    )