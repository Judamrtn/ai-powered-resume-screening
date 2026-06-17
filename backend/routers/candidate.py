from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import hashlib, uuid, os

from database import get_db
from models.candidate import Candidate
from models.jobs import Job
from schemas.candidate import (
    CandidateResponse, CandidateStatusUpdate,
    CandidateNotesUpdate, CandidateListResponse,
)
from security import require_recruiter
from models.user import User
from resume_parser import parse_resume
from extractor import extract_email, extract_phone, extract_name
from services.skills import extract_skills
from services.embedding import get_embedding
from services.ranking import cosine_similarity
from taxonomy import normalize_skills
from intelligent_scorer import compute_intelligent_score
from document_classifier import validate_resume

router = APIRouter(prefix="/jobs/{job_id}/candidates", tags=["Candidate Management"])

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
MAX_FILE_SIZE = 5 * 1024 * 1024

VALID_STATUSES = {
    "applied", "screening", "shortlisted",
    "interview", "offer", "hired", "rejected"
}


def normalize_cosine(score: float) -> float:
    return (score + 1) / 2


def get_job_or_404(job_id: UUID, db: Session) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "open":
        raise HTTPException(status_code=409, detail="Job is not open for applications.")
    return job


def get_candidate_or_404(candidate_id: UUID, job_id: UUID, db: Session) -> Candidate:
    c = db.get(Candidate, candidate_id)
    if not c or str(c.job_id) != str(job_id):
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return c


@router.post("/upload", response_model=CandidateResponse, status_code=201)
async def upload_resume(
    job_id: UUID,
    file:   UploadFile = File(...),
    db:     Session    = Depends(get_db),
):
    """Upload resume and score using intelligent 10-signal scoring engine."""
    job = get_job_or_404(job_id, db)

    allowed_extensions = (".pdf", ".docx")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=422,
            detail="Only PDF and DOCX files are accepted.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File exceeds 5 MB size limit.")

    file_hash = hashlib.md5(content).hexdigest()
    if db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.file_hash == file_hash,
    ).first():
        raise HTTPException(status_code=409, detail="Duplicate resume for this job.")

    file_ext    = ".docx" if file.filename.lower().endswith(".docx") else ".pdf"
    unique_name = f"{uuid.uuid4()}{file_ext}"
    file_path   = os.path.join(UPLOAD_FOLDER, unique_name)

    try:
        with open(file_path, "wb") as f:
            f.write(content)

        try:
            extracted_text = parse_resume(file_path, file.filename)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        if not extracted_text or not extracted_text.strip():
            raise HTTPException(status_code=422,
                detail="Could not extract text — file may be scanned, image-only, or corrupted.")

        # Validate document is actually a resume
        is_valid, error_msg = validate_resume(extracted_text)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error_msg)

        email  = extract_email(extracted_text)
        phone  = extract_phone(extracted_text)
        name   = extract_name(extracted_text)
        skills = extract_skills(extracted_text)
        raw_skills        = skills.get("technical_skills", []) + skills.get("soft_skills", [])
        normalized_skills = normalize_skills(raw_skills)

        # Semantic score
        job_text      = " ".join(job.required_skills or []) + " " + (job.description or "")
        job_vector    = get_embedding(job_text.strip())
        skills_text   = " ".join(normalized_skills) if normalized_skills else extracted_text[:500]
        resume_vector = get_embedding(skills_text)
        semantic_raw  = normalize_cosine(cosine_similarity(resume_vector, job_vector)) * 100

        # Intelligent composite score
        result = compute_intelligent_score(
            resume_text          = extracted_text,
            resume_skills        = normalized_skills,
            semantic_score       = semantic_raw,
            job_required_skills  = job.required_skills or [],
            job_required_certs   = job.certifications  or [],
            job_min_experience   = job.min_experience_years,
            job_education_level  = job.education_level,
            job_title            = job.title or "",
            job_text             = job_text.strip(),
        )

        candidate = Candidate(
            job_id                 = job_id,
            name                   = name,
            email                  = email,
            phone                  = phone,
            original_filename      = file.filename,
            stored_filename        = unique_name,
            file_hash              = file_hash,
            skills                 = normalized_skills,
            raw_text               = extracted_text[:5000],
            semantic_score         = result.semantic_score,
            skills_score           = result.skills_score,
            experience_score       = result.experience_score,
            education_score        = result.education_score,
            certification_score    = result.certification_score,
            score                  = result.final_score,
            career_progression     = result.career_progression,
            skill_recency          = result.skill_recency,
            resume_quality         = result.resume_quality,
            job_title_relevance    = result.job_title_relevance,
            industry_match         = result.industry_match,
            education_field        = result.education_field,
            matched_skills         = result.matched_skills,
            missing_skills         = result.missing_skills,
            matched_certs          = result.matched_certs,
            missing_certs          = result.missing_certs,
            contextual_skills      = result.contextual_skills,
            inferred_skills        = result.inferred_skills,
            experience_years_found = result.experience_years_found,
            education_level_found  = result.education_level_found,
            resume_domain          = result.resume_domain,
            job_domain             = result.job_domain,
            red_flags              = result.red_flags,
            red_flag_penalty       = result.red_flag_penalty,
            recommendation         = result.recommendation,
            status                 = "applied",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/", response_model=CandidateListResponse)
def list_candidates(
    job_id:    UUID,
    db:        Session = Depends(get_db),
    _:         User    = Depends(require_recruiter),
    status:    str     = Query(default=None),
    min_score: float   = Query(default=0.0, ge=0, le=100),
    limit:     int     = Query(default=50, ge=1, le=200),
    offset:    int     = Query(default=0, ge=0),
):
    if not db.get(Job, job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    q = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.score  >= min_score,
    )
    if status:
        q = q.filter(Candidate.status == status)
    total      = q.count()
    candidates = q.order_by(Candidate.score.desc()).offset(offset).limit(limit).all()
    return CandidateListResponse(
        total=total, offset=offset, limit=limit, candidates=candidates
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    job_id: UUID, candidate_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(require_recruiter),
):
    return get_candidate_or_404(candidate_id, job_id, db)


@router.patch("/{candidate_id}/status", response_model=CandidateResponse)
def update_status(
    job_id: UUID, candidate_id: UUID,
    payload: CandidateStatusUpdate,
    db: Session = Depends(get_db),
    _:  User    = Depends(require_recruiter),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    c = get_candidate_or_404(candidate_id, job_id, db)
    c.status = payload.status
    db.commit()
    db.refresh(c)
    return c


@router.patch("/{candidate_id}/notes", response_model=CandidateResponse)
def update_notes(
    job_id: UUID, candidate_id: UUID,
    payload: CandidateNotesUpdate,
    db: Session = Depends(get_db),
    _:  User    = Depends(require_recruiter),
):
    c = get_candidate_or_404(candidate_id, job_id, db)
    c.notes = payload.notes
    db.commit()
    db.refresh(c)
    return c


@router.patch("/bulk/status", status_code=200)
def bulk_status_update(
    job_id: UUID, candidate_ids: list[UUID], status: str,
    db: Session = Depends(get_db),
    _:  User    = Depends(require_recruiter),
):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status.")
    updated = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.id.in_(candidate_ids),
    ).all()
    for c in updated:
        c.status = status
    db.commit()
    return {"updated": len(updated), "status": status}