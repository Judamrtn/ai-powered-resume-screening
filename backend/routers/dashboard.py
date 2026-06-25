"""
Dashboard Router
Provides a single aggregated endpoint that returns everything a recruiter
or admin needs on their homepage - in one API call, not six.

Recruiter view:  scoped to their own jobs and candidates only
Admin view:      system-wide aggregates across all recruiters
"""
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.jobs import Job
from models.candidate import Candidate
from models.interview import Interview
from models.user import User
from security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class PipelineBreakdown(BaseModel):
    applied:     int = 0
    screening:   int = 0
    shortlisted: int = 0
    interview:   int = 0
    offer:       int = 0
    hired:       int = 0
    rejected:    int = 0


class JobSummary(BaseModel):
    id:              UUID
    title:           str
    department:      Optional[str]
    status:          str
    applicant_count: int
    avg_score:       Optional[float]
    created_at:      datetime

    model_config = {"from_attributes": True}


class UpcomingInterview(BaseModel):
    id:            UUID
    candidate_name: Optional[str]
    job_title:     str
    format:        str
    scheduled_at:  datetime
    round_number:  int

    model_config = {"from_attributes": True}


class RecruiterDashboard(BaseModel):
    recruiter_id:        UUID
    recruiter_name:      str
    recruiter_email:     str
    total_jobs:          int
    open_jobs:           int
    closed_jobs:         int
    archived_jobs:       int
    total_candidates:    int
    pipeline:            PipelineBreakdown
    avg_match_score:     Optional[float]
    pending_review_count: int
    interviews_this_week: int
    upcoming_interviews:  list[UpcomingInterview]
    jobs:                list[JobSummary]


class AdminDashboard(BaseModel):
    total_recruiters:    int
    active_recruiters:   int
    total_jobs:          int
    open_jobs:           int
    total_candidates:    int
    pipeline:            PipelineBreakdown
    avg_match_score:     Optional[float]
    interviews_this_week: int
    recruiter_stats:     list[dict]


@router.get("/", response_model=RecruiterDashboard | AdminDashboard)
def get_dashboard(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    if current_user.role == "admin":
        return _build_admin_dashboard(db)
    return _build_recruiter_dashboard(db, current_user)


def _build_recruiter_dashboard(db: Session, user: User) -> RecruiterDashboard:
    now           = datetime.now(timezone.utc)
    week_from_now = now + timedelta(days=7)

    all_jobs = db.query(Job).filter(Job.created_by == user.id).all()

    open_jobs     = [j for j in all_jobs if j.status == "open"]
    closed_jobs   = [j for j in all_jobs if j.status == "closed"]
    archived_jobs = [j for j in all_jobs if j.status == "archived"]
    job_ids       = [j.id for j in all_jobs]

    candidates = (
        db.query(Candidate)
        .filter(Candidate.job_id.in_(job_ids))
        .all()
    ) if job_ids else []

    pipeline = PipelineBreakdown(
        applied     = sum(1 for c in candidates if c.status == "applied"),
        screening   = sum(1 for c in candidates if c.status == "screening"),
        shortlisted = sum(1 for c in candidates if c.status == "shortlisted"),
        interview   = sum(1 for c in candidates if c.status == "interview"),
        offer       = sum(1 for c in candidates if c.status == "offer"),
        hired       = sum(1 for c in candidates if c.status == "hired"),
        rejected    = sum(1 for c in candidates if c.status == "rejected"),
    )

    scores = [c.score for c in candidates if c.score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else None

    pending_review = sum(1 for c in candidates if c.status == "applied")

    upcoming = (
        db.query(Interview)
        .filter(
            Interview.job_id.in_(job_ids),
            Interview.status.in_(["scheduled", "confirmed"]),
            Interview.scheduled_at >= now,
            Interview.scheduled_at <= week_from_now,
        )
        .order_by(Interview.scheduled_at)
        .all()
    ) if job_ids else []

    upcoming_interviews = [
        UpcomingInterview(
            id             = i.id,
            candidate_name = i.candidate.name if i.candidate else None,
            job_title      = i.job.title if i.job else "",
            format         = i.format,
            scheduled_at   = i.scheduled_at,
            round_number   = i.round_number,
        )
        for i in upcoming
    ]

    job_summaries = []
    for job in sorted(all_jobs, key=lambda j: j.created_at, reverse=True):
        job_candidates = [c for c in candidates if c.job_id == job.id]
        job_scores     = [c.score for c in job_candidates if c.score is not None]
        job_summaries.append(JobSummary(
            id              = job.id,
            title           = job.title,
            department      = job.department,
            status          = job.status,
            applicant_count = len(job_candidates),
            avg_score       = round(sum(job_scores) / len(job_scores), 2) if job_scores else None,
            created_at      = job.created_at,
        ))

    return RecruiterDashboard(
        recruiter_id         = user.id,
        recruiter_name       = user.full_name,
        recruiter_email      = user.email,
        total_jobs           = len(all_jobs),
        open_jobs            = len(open_jobs),
        closed_jobs          = len(closed_jobs),
        archived_jobs        = len(archived_jobs),
        total_candidates     = len(candidates),
        pipeline             = pipeline,
        avg_match_score      = avg_score,
        pending_review_count = pending_review,
        interviews_this_week = len(upcoming),
        upcoming_interviews  = upcoming_interviews,
        jobs                 = job_summaries,
    )


def _build_admin_dashboard(db: Session) -> AdminDashboard:
    now           = datetime.now(timezone.utc)
    week_from_now = now + timedelta(days=7)

    total_recruiters  = db.query(User).filter(User.role == "recruiter").count()
    active_recruiters = db.query(User).filter(
        User.role == "recruiter", User.is_active == True
    ).count()

    total_jobs = db.query(Job).count()
    open_jobs  = db.query(Job).filter(Job.status == "open").count()

    total_candidates = db.query(Candidate).count()

    pipeline_raw = db.query(
        Candidate.status,
        func.count(Candidate.id).label("count")
    ).group_by(Candidate.status).all()
    pipeline_map = {row.status: row.count for row in pipeline_raw}

    pipeline = PipelineBreakdown(
        applied     = pipeline_map.get("applied",     0),
        screening   = pipeline_map.get("screening",   0),
        shortlisted = pipeline_map.get("shortlisted", 0),
        interview   = pipeline_map.get("interview",   0),
        offer       = pipeline_map.get("offer",       0),
        hired       = pipeline_map.get("hired",       0),
        rejected    = pipeline_map.get("rejected",    0),
    )

    avg_row = db.query(func.avg(Candidate.score)).scalar()
    avg_score = round(float(avg_row), 2) if avg_row else None

    interviews_this_week = db.query(Interview).filter(
        Interview.status.in_(["scheduled", "confirmed"]),
        Interview.scheduled_at >= now,
        Interview.scheduled_at <= week_from_now,
    ).count()

    recruiters = db.query(User).filter(
        User.role == "recruiter", User.is_active == True
    ).all()

    recruiter_stats = []
    for recruiter in recruiters:
        recruiter_jobs = db.query(Job).filter(Job.created_by == recruiter.id).all()
        job_ids        = [j.id for j in recruiter_jobs]
        recruiter_candidates = db.query(Candidate).filter(
            Candidate.job_id.in_(job_ids)
        ).count() if job_ids else 0

        recruiter_stats.append({
            "recruiter_id":    str(recruiter.id),
            "recruiter_name":  recruiter.full_name,
            "recruiter_email": recruiter.email,
            "total_jobs":      len(recruiter_jobs),
            "open_jobs":       sum(1 for j in recruiter_jobs if j.status == "open"),
            "total_candidates": recruiter_candidates,
        })

    return AdminDashboard(
        total_recruiters     = total_recruiters,
        active_recruiters    = active_recruiters,
        total_jobs           = total_jobs,
        open_jobs            = open_jobs,
        total_candidates     = total_candidates,
        pipeline             = pipeline,
        avg_match_score      = avg_score,
        interviews_this_week = interviews_this_week,
        recruiter_stats      = recruiter_stats,
    )
