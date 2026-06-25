"""
Interview Management Router
Endpoints for scheduling, managing, and tracking interviews.
Includes calendar event generation and feedback collection.

IMPORTANT: Route ordering matters in FastAPI â€” more specific paths
like /candidates/{candidate_id}/summary must be declared BEFORE
generic /{interview_id} routes, otherwise FastAPI will try to match
"candidates" as an interview_id value.
"""
from uuid import UUID
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.interview import Interview, InterviewFeedback
from models.candidate import Candidate
from models.jobs import Job
from schemas.interview import (
    InterviewCreate, InterviewUpdate, InterviewResponse,
    FeedbackCreate, FeedbackResponse,
    CalendarEvent, InterviewSummary,
)
from security import require_recruiter
from models.user import User

router = APIRouter(prefix="/jobs/{job_id}/interviews", tags=["Interview Management"])

VALID_STATUSES = {"scheduled", "confirmed", "completed", "cancelled", "no_show"}


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_interview_or_404(interview_id: UUID, job_id: UUID, db: Session) -> Interview:
    interview = db.get(Interview, interview_id)
    if not interview or str(interview.job_id) != str(job_id):
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview


def generate_calendar_event(interview: Interview, candidate: Candidate, job: Job) -> CalendarEvent:
    """Generate a calendar event dict for the interview."""
    format_labels = {
        "phone_screen":        "Phone Screen",
        "video_call":          "Video Call",
        "on_site":             "On-Site Interview",
        "technical_assessment": "Technical Assessment",
        "panel":               "Panel Interview",
    }
    format_label = format_labels.get(interview.format, "Interview")
    title        = f"{format_label} â€” {candidate.name} for {job.title}"
    description  = (
        f"Interview with {candidate.name} ({candidate.email})\n"
        f"Position: {job.title} â€” {job.department or ''}\n"
        f"Format: {format_label}\n"
        f"Round: {interview.round_number}\n"
        f"Duration: {interview.duration_minutes} minutes\n"
    )
    if interview.meeting_link:
        description += f"Meeting Link: {interview.meeting_link}\n"
    if interview.notes:
        description += f"\nNotes: {interview.notes}"

    end_time  = interview.scheduled_at + timedelta(minutes=interview.duration_minutes)
    attendees = list(interview.interviewers or [])
    if candidate.email:
        attendees.append(candidate.email)

    return CalendarEvent(
        title        = title,
        description  = description,
        start        = interview.scheduled_at,
        end          = end_time,
        attendees    = attendees,
        location     = interview.location,
        meeting_link = interview.meeting_link,
    )


def generate_ical(event: CalendarEvent) -> str:
    """Generate iCal format string for calendar integration."""
    from datetime import timezone, datetime as dt
    import uuid as uuid_mod

    def fmt_dt(d):
        if d.tzinfo:
            return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return d.strftime("%Y%m%dT%H%M%SZ")

    attendees_str = "\n".join(
        f"ATTENDEE;CN={email}:mailto:{email}"
        for email in event.attendees
    )
    location_str = f"LOCATION:{event.location}" if event.location else ""
    url_str      = f"URL:{event.meeting_link}" if event.meeting_link else ""
    description_escaped = event.description.replace("\n", "\\n")

    ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Resume Screening//Interview//EN
BEGIN:VEVENT
UID:{uuid_mod.uuid4()}@ai-resume-screening
DTSTAMP:{fmt_dt(dt.now())}
DTSTART:{fmt_dt(event.start)}
DTEND:{fmt_dt(event.end)}
SUMMARY:{event.title}
DESCRIPTION:{description_escaped}
{attendees_str}
{location_str}
{url_str}
END:VEVENT
END:VCALENDAR""".strip()

    return ical


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SCHEDULE INTERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.post("/", response_model=InterviewResponse, status_code=201)
def schedule_interview(
    job_id:           UUID,
    payload:          InterviewCreate,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
    _:                User    = Depends(require_recruiter),
):
    """Schedule a new interview for a candidate."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate or str(candidate.job_id) != str(job_id):
        raise HTTPException(status_code=404, detail="Candidate not found for this job.")

    conflict = db.query(Interview).filter(
        Interview.candidate_id == payload.candidate_id,
        Interview.scheduled_at == payload.scheduled_at,
        Interview.status.in_(["scheduled", "confirmed"]),
    ).first()
    if conflict:
        raise HTTPException(status_code=409,
            detail="Candidate already has an interview scheduled at this time.")

    interview = Interview(
        candidate_id     = payload.candidate_id,
        job_id           = job_id,
        title            = payload.title,
        format           = payload.format,
        scheduled_at     = payload.scheduled_at,
        duration_minutes = payload.duration_minutes,
        location         = payload.location,
        meeting_link     = payload.meeting_link,
        interviewers     = payload.interviewers or [],
        round_number     = payload.round_number,
        notes            = payload.notes,
        status           = "scheduled",
    )
    db.add(interview)
    candidate.status = "interview"
    db.commit()
    db.refresh(interview)
    from notification_service import notify_interview_scheduled
    notify_interview_scheduled(db, interview, candidate)
    return interview


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIST INTERVIEWS FOR JOB
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.get("/", response_model=list[InterviewResponse])
def list_interviews(
    job_id: UUID,
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_recruiter),
    status: str     = Query(default=None),
    format: str     = Query(default=None),
):
    """List all interviews for a job."""
    if not db.get(Job, job_id):
        raise HTTPException(status_code=404, detail="Job not found.")

    q = db.query(Interview).filter(Interview.job_id == job_id)
    if status:
        q = q.filter(Interview.status == status)
    if format:
        q = q.filter(Interview.format == format)

    return q.order_by(Interview.scheduled_at).all()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CANDIDATE INTERVIEW SUMMARY
# (must be declared BEFORE /{interview_id} routes â€” more specific path first)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.get("/candidates/{candidate_id}/summary", response_model=InterviewSummary)
def candidate_interview_summary(
    job_id:       UUID,
    candidate_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Get full interview summary for a candidate including all rounds and feedback."""
    interviews = db.query(Interview).filter(
        Interview.job_id       == job_id,
        Interview.candidate_id == candidate_id,
    ).order_by(Interview.round_number, Interview.scheduled_at).all()

    if not interviews:
        raise HTTPException(status_code=404, detail="No interviews found for this candidate.")

    completed = [i for i in interviews if i.status == "completed"]
    pending   = [i for i in interviews if i.status in ("scheduled", "confirmed")]

    all_scores = []
    all_recs   = []
    for interview in completed:
        for fb in interview.feedbacks:
            if fb.overall_score:
                all_scores.append(fb.overall_score)
            if fb.recommendation:
                all_recs.append(fb.recommendation)

    avg_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

    rec_weights = {
        "strong_yes": 2, "yes": 1, "maybe": 0, "no": -1, "strong_no": -2
    }
    if all_recs:
        total_weight = sum(rec_weights.get(r, 0) for r in all_recs)
        avg_weight   = total_weight / len(all_recs)
        if avg_weight >= 1.5:    final_rec = "strong_yes"
        elif avg_weight >= 0.5:  final_rec = "yes"
        elif avg_weight >= -0.5: final_rec = "maybe"
        elif avg_weight >= -1.5: final_rec = "no"
        else:                    final_rec = "strong_no"
    else:
        final_rec = None

    return InterviewSummary(
        candidate_id          = candidate_id,
        total_interviews      = len(interviews),
        completed             = len(completed),
        pending                = len(pending),
        avg_overall_score      = avg_score,
        final_recommendation   = final_rec,
        interviews              = interviews,
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GET ONE INTERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    return get_interview_or_404(interview_id, job_id, db)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# UPDATE INTERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.patch("/{interview_id}", response_model=InterviewResponse)
def update_interview(
    job_id:       UUID,
    interview_id: UUID,
    payload:      InterviewUpdate,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Update interview details."""
    interview = get_interview_or_404(interview_id, job_id, db)
    changes   = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No fields provided.")

    for field, value in changes.items():
        setattr(interview, field, value)

    db.commit()
    db.refresh(interview)
    return interview


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CANCEL INTERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.patch("/{interview_id}/cancel", response_model=InterviewResponse)
def cancel_interview(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Cancel a scheduled interview."""
    interview = get_interview_or_404(interview_id, job_id, db)
    if interview.status == "completed":
        raise HTTPException(status_code=409, detail="Cannot cancel a completed interview.")
    interview.status = "cancelled"
    db.commit()
    db.refresh(interview)
    return interview


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CONFIRM INTERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.patch("/{interview_id}/confirm", response_model=InterviewResponse)
def confirm_interview(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Mark interview as confirmed by candidate."""
    interview = get_interview_or_404(interview_id, job_id, db)
    if interview.status != "scheduled":
        raise HTTPException(status_code=409,
            detail=f"Interview is already '{interview.status}'.")
    interview.status             = "confirmed"
    interview.candidate_notified = True
    db.commit()
    db.refresh(interview)
    return interview


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COMPLETE INTERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.patch("/{interview_id}/complete", response_model=InterviewResponse)
def complete_interview(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Mark interview as completed."""
    interview = get_interview_or_404(interview_id, job_id, db)
    if interview.status not in ("scheduled", "confirmed"):
        raise HTTPException(status_code=409,
            detail=f"Cannot complete interview with status '{interview.status}'.")
    interview.status = "completed"
    db.commit()
    db.refresh(interview)
    return interview


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CALENDAR EVENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.get("/{interview_id}/calendar", response_model=CalendarEvent)
def get_calendar_event(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Get calendar event details for an interview."""
    interview = get_interview_or_404(interview_id, job_id, db)
    candidate = db.get(Candidate, interview.candidate_id)
    job       = db.get(Job, job_id)
    return generate_calendar_event(interview, candidate, job)


@router.get("/{interview_id}/calendar.ics")
def download_ical(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
):
    """Download iCal file for the interview â€” can be imported into any calendar app."""
    from fastapi.responses import Response
    interview = get_interview_or_404(interview_id, job_id, db)
    candidate = db.get(Candidate, interview.candidate_id)
    job       = db.get(Job, job_id)
    event     = generate_calendar_event(interview, candidate, job)
    ical_str  = generate_ical(event)
    return Response(
        content    = ical_str,
        media_type = "text/calendar",
        headers    = {"Content-Disposition": f"attachment; filename=interview_{interview_id}.ics"},
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FEEDBACK
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.post("/{interview_id}/feedback", response_model=FeedbackResponse, status_code=201)
def submit_feedback(
    job_id:       UUID,
    interview_id: UUID,
    payload:      FeedbackCreate,
    db:           Session = Depends(get_db),
):
    """Submit post-interview feedback. No auth required â€” interviewers submit directly."""
    interview = get_interview_or_404(interview_id, job_id, db)

    if interview.status != "completed":
        raise HTTPException(status_code=409,
            detail="Feedback can only be submitted for completed interviews.")

    existing = db.query(InterviewFeedback).filter(
        InterviewFeedback.interview_id      == interview_id,
        InterviewFeedback.interviewer_email == payload.interviewer_email,
    ).first()
    if existing:
        raise HTTPException(status_code=409,
            detail="Feedback already submitted by this interviewer.")

    feedback = InterviewFeedback(
        interview_id          = interview_id,
        interviewer_email     = payload.interviewer_email,
        interviewer_name      = payload.interviewer_name,
        technical_score       = payload.technical_score,
        communication_score   = payload.communication_score,
        problem_solving_score = payload.problem_solving_score,
        cultural_fit_score    = payload.cultural_fit_score,
        overall_score         = payload.overall_score,
        recommendation        = payload.recommendation,
        strengths              = payload.strengths,
        weaknesses              = payload.weaknesses,
        comments                = payload.comments,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/{interview_id}/feedback", response_model=list[FeedbackResponse])
def get_feedback(
    job_id:       UUID,
    interview_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(require_recruiter),
):
    """Get all feedback for an interview."""
    get_interview_or_404(interview_id, job_id, db)
    return db.query(InterviewFeedback).filter(
        InterviewFeedback.interview_id == interview_id
    ).all()
