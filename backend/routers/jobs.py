from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from database import get_db
from models.jobs import Job
from schemas.jobs import JobCreate, JobUpdate, JobResponse, JobWithStats, JobListResponse
router = APIRouter(prefix="/jobs", tags=["Job Management"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_job_or_404(job_id: UUID, db: Session) -> Job:
    job = db.get(Job, job_id)
    if not job:
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
    """
    Returns applicant counts and average score for a job.
    Reads from the candidates table — adjust column names to match
    your actual Candidate model once you migrate to PostgreSQL.
    """
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
        # Candidates table not yet migrated — return zeroed stats
        return {"applicant_count": 0, "shortlisted_count": 0, "avg_match_score": None}


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=JobResponse, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting."""
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ── LIST ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=JobListResponse)
def list_jobs(
    background_tasks: BackgroundTasks,
    db:         Session = Depends(get_db),
    status:     str     = Query(default="open", pattern="^(open|closed|archived|all)$"),
    department: str     = Query(default=None),
    location:   str     = Query(default=None),
    experience_level: str = Query(default=None),
    search:     str     = Query(default=None, description="Full-text search on title and description"),
    limit:      int     = Query(default=20, ge=1, le=100),
    offset:     int     = Query(default=0, ge=0),
):
    """List job postings with filtering and pagination. Auto-closes expired jobs."""
    # Expire stale jobs in the background — don't block the response
    background_tasks.add_task(close_expired_jobs, db)

    q = db.query(Job)

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


# ── GET ONE ───────────────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobWithStats)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single job with live applicant stats."""
    job   = get_job_or_404(job_id, db)
    stats = get_applicant_stats(job_id, db)
    return JobWithStats(**JobResponse.model_validate(job).model_dump(), **stats)


# ── UPDATE (PATCH) ────────────────────────────────────────────────────────────

@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: UUID, payload: JobUpdate, db: Session = Depends(get_db)):
    """Partially update a job posting."""
    job     = get_job_or_404(job_id, db)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    for field, value in changes.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


# ── ARCHIVE ───────────────────────────────────────────────────────────────────

@router.patch("/{job_id}/archive", response_model=JobResponse)
def archive_job(job_id: UUID, db: Session = Depends(get_db)):
    """Archive a job posting (soft delete — preserves applicant history)."""
    job = get_job_or_404(job_id, db)
    if job.status == "archived":
        raise HTTPException(status_code=409, detail="Job is already archived.")
    job.status = "archived"
    db.commit()
    db.refresh(job)
    return job


# ── CLOSE ─────────────────────────────────────────────────────────────────────

@router.patch("/{job_id}/close", response_model=JobResponse)
def close_job(job_id: UUID, db: Session = Depends(get_db)):
    """Manually close a job posting."""
    job = get_job_or_404(job_id, db)
    if job.status != "open":
        raise HTTPException(status_code=409, detail=f"Job is already '{job.status}'.")
    job.status = "closed"
    db.commit()
    db.refresh(job)
    return job


# ── DUPLICATE ─────────────────────────────────────────────────────────────────

@router.post("/{job_id}/duplicate", response_model=JobResponse, status_code=201)
def duplicate_job(job_id: UUID, db: Session = Depends(get_db)):
    """
    Clone an existing job posting as a new open draft.
    Deadline is cleared so the recruiter sets a new one.
    """
    source = get_job_or_404(job_id, db)

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
        deadline            = None,          # recruiter must set a new deadline
        duplicated_from     = source.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


# ── BULK DEADLINE CHECK (admin endpoint) ─────────────────────────────────────

@router.post("/admin/expire", status_code=200)
def trigger_expire(db: Session = Depends(get_db)):
    """Manually trigger deadline expiry check. Useful for cron/scheduler calls."""
    closed = close_expired_jobs(db)
    return {"message": f"{closed} job(s) closed due to expired deadline."}