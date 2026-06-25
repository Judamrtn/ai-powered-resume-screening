"""
Job Management Router â€” now with ownership-based access scoping.

Access rules:
- admin:     sees and manages ALL jobs across every recruiter
- recruiter: sees and manages ONLY jobs they personally created

Note: the original version of this router had no authentication at all
on any endpoint. That has been fixed here as a prerequisite to ownership
scoping â€” you cannot meaningfully scope "my jobs" without first requiring
the caller to be an authenticated, known user.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.jobs import Job
from models.user import User
from schemas.jobs import JobCreate, JobUpdate, JobResponse, JobWithStats, JobListResponse
from security import get_current_user, require_admin

router = APIRouter(prefix="/jobs", tags=["Job Management"])


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_job_or_404(job_id: UUID, db: Session) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def get_owned_job_or_404(job_id: UUID, db: Session, current_user: User) -> Job:
    """
    Fetch a job, enforcing ownership scoping:
    - admin can access any job
    - recruiter can only access jobs they created
    """
    job = get_job_or_404(job_id, db)
    if current_user.role != "admin" and str(job.created_by) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def close_expired_jobs(db: Session) -> int:
    """Set status='closed' for all open jobs whose deadline has passed."""
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Job)
        .filter(Job.status == "open", Job.deadline < now)
        .all()
    )
    for job in updated:
        job.status = "closed"
    db.commit()
    return len(updated)


def get_applicant_stats(job_id: UUID, db: Session) -> dict:
    """Returns applicant counts and average score for a job."""
    from sqlalchemy import text
    try:
        result = db.execute(
            text("""
                SELECT
                    COUNT(*)                                          AS applicant_count,
                    COUNT(*) FILTER (WHERE status = 'shortlisted')   AS shortlisted_count,
                    ROUND(AVG(score)::numeric, 2)                    AS avg_match_score
                FROM candidates
                WHERE job_id = :job_id
            """),
            {"job_id": str(job_id)},
        ).fetchone()
        return {
            "applicant_count":   result.applicant_count or 0,
            "shortlisted_count": result.shortlisted_count or 0,
            "avg_match_score":   float(result.avg_match_score) if result.avg_match_score else None,
        }
    except Exception:
        return {"applicant_count": 0, "shortlisted_count": 0, "avg_match_score": None}


# â”€â”€ CREATE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/", response_model=JobResponse, status_code=201)
def create_job(
    payload:      JobCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Create a new job posting, owned by the authenticated recruiter."""
    job = Job(**payload.model_dump(), created_by=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# â”€â”€ LIST â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/", response_model=JobListResponse)
def list_jobs(
    background_tasks: BackgroundTasks,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
    status:       str     = Query(default="open", pattern="^(open|closed|archived|all)$"),
    department:   str     = Query(default=None),
    location:     str     = Query(default=None),
    experience_level: str = Query(default=None),
    search:       str     = Query(default=None, description="Full-text search on title and description"),
    mine_only:    bool    = Query(default=False, description="Admins only: if true, filter down to just the jobs this admin personally created. Has no effect for recruiters, who are always scoped to their own jobs regardless of this flag."),
    limit:        int     = Query(default=20, ge=1, le=100),
    offset:       int     = Query(default=0, ge=0),
):
    """
    List job postings with filtering and pagination. Auto-closes expired jobs.

    Scoping: a recruiter ALWAYS sees only jobs they created, regardless of
    mine_only (that flag only has an effect for admins, letting them
    optionally filter down to their own jobs too).
    """
    background_tasks.add_task(close_expired_jobs, db)

    q = db.query(Job)

    if current_user.role != "admin":
        q = q.filter(Job.created_by == current_user.id)
    elif current_user.role == "admin" and mine_only:
        q = q.filter(Job.created_by == current_user.id)

    if status != "all":
        q = q.filter(Job.status == status)
    if department:
        q = q.filter(Job.department.ilike(f"%{department}%"))
    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))
    if experience_level:
        q = q.filter(Job.experience_level == experience_level)
    if search:
        q = q.filter(
            Job.title.ilike(f"%{search}%") | Job.description.ilike(f"%{search}%")
        )

    total = q.count()
    jobs  = q.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    return JobListResponse(total=total, offset=offset, limit=limit, jobs=jobs)


# â”€â”€ GET ONE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{job_id}", response_model=JobWithStats)
def get_job(
    job_id:       UUID,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Fetch a single job with live applicant stats. Scoped to owner unless admin."""
    job   = get_owned_job_or_404(job_id, db, current_user)
    stats = get_applicant_stats(job_id, db)
    return JobWithStats(**JobResponse.model_validate(job).model_dump(), **stats)


# â”€â”€ UPDATE (PATCH) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id:       UUID,
    payload:      JobUpdate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Partially update a job posting. Scoped to owner unless admin."""
    job     = get_owned_job_or_404(job_id, db, current_user)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    for field, value in changes.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


# â”€â”€ ARCHIVE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{job_id}/archive", response_model=JobResponse)
def archive_job(
    job_id:       UUID,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Archive a job posting (soft delete â€” preserves applicant history)."""
    job = get_owned_job_or_404(job_id, db, current_user)
    if job.status == "archived":
        raise HTTPException(status_code=409, detail="Job is already archived.")
    job.status = "archived"
    db.commit()
    db.refresh(job)
    return job


# â”€â”€ CLOSE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{job_id}/close", response_model=JobResponse)
def close_job(
    job_id:       UUID,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Manually close a job posting."""
    job = get_owned_job_or_404(job_id, db, current_user)
    if job.status != "open":
        raise HTTPException(status_code=409, detail=f"Job is already '{job.status}'.")
    job.status = "closed"
    db.commit()
    db.refresh(job)
    return job


# â”€â”€ DUPLICATE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{job_id}/duplicate", response_model=JobResponse, status_code=201)
def duplicate_job(
    job_id:       UUID,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Clone an existing job posting as a new open draft, owned by the
    duplicating recruiter (not necessarily the original owner â€” e.g. an
    admin duplicating someone else's template becomes the new owner).
    """
    source = get_owned_job_or_404(job_id, db, current_user)

    clone = Job(
        title               = f"{source.title} (copy)",
        department          = source.department,
        location            = source.location,
        employment_type     = source.employment_type,
        salary_min          = source.salary_min,
        salary_max          = source.salary_max,
        description         = source.description,
        required_skills     = list(source.required_skills or []),
        preferred_skills    = list(source.preferred_skills or []),
        min_experience_years= source.min_experience_years,
        education_level     = source.education_level,
        certifications      = list(source.certifications or []),
        experience_level    = source.experience_level,
        status              = "open",
        deadline            = None,
        duplicated_from     = source.id,
        created_by          = current_user.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


# â”€â”€ BULK DEADLINE CHECK (admin only) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/admin/expire", status_code=200)
def trigger_expire(
    db: Session = Depends(get_db),
    _:  User    = Depends(require_admin),
):
    """Manually trigger deadline expiry check across ALL jobs. Admin only."""
    closed = close_expired_jobs(db)
    return {"message": f"{closed} job(s) closed due to expired deadline."}


