"""
Public Router

Unauthenticated endpoints for the candidate-facing side of the system
(Model C hybrid approach). No auth token required for any of these.

Endpoints:
  GET  /public/jobs                        - list open jobs (paginated)
  GET  /public/jobs/{job_id}               - single job detail
  GET  /public/applications/{candidate_id} - candidate checks their own status
"""
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.jobs import Job
from models.candidate import Candidate

router = APIRouter(prefix="/public", tags=["Public - Candidate Portal"])


class PublicJobSummary(BaseModel):
    id:              UUID
    title:           str
    department:      Optional[str]
    location:        Optional[str]
    employment_type: Optional[str]
    salary_min:      Optional[float]
    salary_max:      Optional[float]
    experience_level: Optional[str]
    deadline:        Optional[datetime]
    created_at:      datetime

    model_config = {"from_attributes": True}


class PublicJobDetail(BaseModel):
    id:                  UUID
    title:               str
    department:          Optional[str]
    location:            Optional[str]
    employment_type:     Optional[str]
    salary_min:          Optional[float]
    salary_max:          Optional[float]
    description:         str
    required_skills:     list[str]
    preferred_skills:    list[str]
    min_experience_years: Optional[int]
    education_level:     Optional[str]
    certifications:      list[str]
    experience_level:    Optional[str]
    deadline:            Optional[datetime]
    created_at:          datetime

    model_config = {"from_attributes": True}


class PublicJobListResponse(BaseModel):
    total:  int
    offset: int
    limit:  int
    jobs:   list[PublicJobSummary]


class ApplicationStatusResponse(BaseModel):
    candidate_id:      UUID
    job_title:         str
    candidate_name:    Optional[str]
    status:            str
    applied_at:        datetime
    last_updated:      datetime
    status_message:    str

    model_config = {"from_attributes": True}


PORTAL_STATUS_MESSAGES = {
    "applied":     "Your application has been received and is awaiting review.",
    "screening":   "Your application is currently under review by our recruitment team.",
    "shortlisted": "Congratulations - you have been shortlisted for this role.",
    "interview":   "You have been invited to interview. Please check your email for details.",
    "offer":       "We are pleased to inform you that you are being considered for an offer.",
    "hired":       "Congratulations! You have been selected for this role.",
    "rejected":    "After careful consideration, we have decided not to move forward with your application at this time.",
}


@router.get("/jobs", response_model=PublicJobListResponse)
def list_public_jobs(
    db:         Session = Depends(get_db),
    department: Optional[str] = Query(default=None),
    location:   Optional[str] = Query(default=None),
    search:     Optional[str] = Query(default=None),
    limit:      int = Query(default=20, ge=1, le=100),
    offset:     int = Query(default=0, ge=0),
):
    q   = db.query(Job).filter(Job.status == "open")
    now = datetime.now(timezone.utc)
    q   = q.filter((Job.deadline == None) | (Job.deadline > now))

    if department:
        q = q.filter(Job.department.ilike(f"%{department}%"))
    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))
    if search:
        q = q.filter(
            Job.title.ilike(f"%{search}%") | Job.description.ilike(f"%{search}%")
        )

    total = q.count()
    jobs  = q.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    return PublicJobListResponse(total=total, offset=offset, limit=limit, jobs=jobs)


@router.get("/jobs/{job_id}", response_model=PublicJobDetail)
def get_public_job(
    job_id: UUID,
    db:     Session = Depends(get_db),
):
    job = db.get(Job, job_id)
    if not job or job.status != "open":
        raise HTTPException(status_code=404, detail="Job not found or no longer accepting applications.")
    now = datetime.now(timezone.utc)
    if job.deadline and job.deadline.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=404, detail="This job posting has closed.")
    return job


@router.get("/applications/{candidate_id}", response_model=ApplicationStatusResponse)
def check_application_status(
    candidate_id: UUID,
    db:           Session = Depends(get_db),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Application not found.")

    job = db.get(Job, candidate.job_id)

    return ApplicationStatusResponse(
        candidate_id   = candidate.id,
        job_title      = job.title if job else "Unknown Position",
        candidate_name = candidate.name,
        status         = candidate.status,
        applied_at     = candidate.created_at,
        last_updated   = candidate.updated_at,
        status_message = PORTAL_STATUS_MESSAGES.get(
            candidate.status,
            "Please contact our recruitment team for an update on your application."
        ),
    )
