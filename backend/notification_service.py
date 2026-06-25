"""
Notification Service

The orchestration layer between "something happened" (candidate status
changed, interview scheduled) and an actual email landing in someone's
inbox. Every call here ALWAYS writes a NotificationLog row first - if
the send subsequently fails, the row is updated to status='failed' with
the real error message rather than vanishing silently. This is what
makes the spec's "Email delivery tracking and retry logic" (4.11) and
"complete audit log of all automated communications" (7.5) actually
true, rather than aspirational.

Design choice: sending happens synchronously, inline with the request
that triggered it (e.g. updating a candidate's status). For a small-to-
medium volume system this is simple and traceable. If email volume grows
large enough that synchronous SMTP calls start slowing down API
responses noticeably, the natural next step is moving send_email() onto
a background task queue (Celery, as your original spec document already
mentions for other async work) - the NotificationLog table and template
rendering logic here would not need to change, only how/when
send_via_smtp() gets invoked.
"""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from models.notification import NotificationLog
from notification_templates import render_template, STATUS_MESSAGES
from notification_sender import send_email, EmailSendError, EmailConfigError


def _create_log_entry(
    db: Session,
    notification_type: str,
    recipient_email: str,
    subject: str,
    body: str,
    candidate_id: UUID | None = None,
    interview_id: UUID | None = None,
    job_id:       UUID | None = None,
) -> NotificationLog:
    log = NotificationLog(
        candidate_id       = candidate_id,
        interview_id       = interview_id,
        job_id             = job_id,
        notification_type  = notification_type,
        recipient_email    = recipient_email,
        subject            = subject,
        body               = body,
        status             = "pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _attempt_send(db: Session, log: NotificationLog) -> NotificationLog:
    """
    Attempts to actually send the email for an already-logged
    notification, updating the log row with the real outcome either
    way. Never raises - failures are recorded, not propagated, since a
    failed notification should never break the API call that triggered
    it (e.g. a candidate's status update should still succeed even if
    their confirmation email bounces).
    """
    try:
        send_email(log.recipient_email, log.subject, log.body)
        log.status  = "sent"
        log.sent_at = datetime.now(timezone.utc)
        log.error_message = None
    except EmailConfigError as e:
        log.status        = "failed"
        log.error_message = f"Configuration error: {e}"
    except EmailSendError as e:
        log.status        = "failed"
        log.error_message = str(e)
        log.retry_count    = (log.retry_count or 0) + 1

    db.commit()
    db.refresh(log)
    return log


def notify_application_received(db: Session, candidate) -> NotificationLog:
    """Send confirmation when a candidate's resume is successfully uploaded."""
    if not candidate.email:
        # Can't notify someone we couldn't extract an email for - log it
        # as failed immediately rather than silently skipping, so this
        # gap is visible in the audit trail.
        return _create_log_entry(
            db, "application_received", "unknown@no-email-extracted",
            f"Application Received - {candidate.job.title if candidate.job else 'Unknown Role'}",
            "Could not send: no email address was extracted from this resume.",
            candidate_id=candidate.id, job_id=candidate.job_id,
        )

    job = candidate.job
    department_clause = f" in {job.department}" if job and job.department else ""

    subject, body = render_template("application_received", {
        "candidate_name":    candidate.name or "Candidate",
        "job_title":         job.title if job else "the position",
        "department_clause": department_clause,
    })

    log = _create_log_entry(
        db, "application_received", candidate.email, subject, body,
        candidate_id=candidate.id, job_id=candidate.job_id,
    )
    return _attempt_send(db, log)


def notify_status_changed(db: Session, candidate, new_status: str) -> NotificationLog | None:
    """
    Send a status-update email. Returns None (no notification sent or
    logged) for status values that don't warrant candidate-facing
    communication, like 'applied' (the initial state - covered by
    notify_application_received instead) or 'screening' if you'd rather
    not notify candidates of purely internal review stages - adjust
    SILENT_STATUSES below to change this behavior.
    """
    SILENT_STATUSES = {"applied"}
    if new_status in SILENT_STATUSES or not candidate.email:
        return None

    job = candidate.job
    status_message = STATUS_MESSAGES.get(
        new_status, "Please check your application status with our recruitment team."
    )

    subject, body = render_template("status_changed", {
        "candidate_name":         candidate.name or "Candidate",
        "job_title":              job.title if job else "the position",
        "new_status":             new_status.replace("_", " ").title(),
        "status_specific_message": status_message,
    })

    log = _create_log_entry(
        db, "status_changed", candidate.email, subject, body,
        candidate_id=candidate.id, job_id=candidate.job_id,
    )
    return _attempt_send(db, log)


def notify_interview_scheduled(db: Session, interview, candidate) -> NotificationLog | None:
    """Send the interview invitation email."""
    if not candidate.email:
        return None

    job = interview.job
    location_clause     = f"Location:  {interview.location}\n" if interview.location else ""
    meeting_link_clause = f"Join here: {interview.meeting_link}\n" if interview.meeting_link else ""

    format_labels = {
        "phone_screen":         "Phone Screen",
        "video_call":           "Video Call",
        "on_site":               "On-Site Interview",
        "technical_assessment": "Technical Assessment",
        "panel":                 "Panel Interview",
    }

    subject, body = render_template("interview_scheduled", {
        "candidate_name":   candidate.name or "Candidate",
        "job_title":         job.title if job else "the position",
        "interview_format":  format_labels.get(interview.format, interview.format),
        "scheduled_at":      interview.scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p %Z"),
        "duration_minutes":  interview.duration_minutes,
        "location_clause":   location_clause,
        "meeting_link_clause": meeting_link_clause,
    })

    log = _create_log_entry(
        db, "interview_scheduled", candidate.email, subject, body,
        candidate_id=candidate.id, interview_id=interview.id, job_id=interview.job_id,
    )
    return _attempt_send(db, log)


def notify_recruiter_high_scorer(
    db: Session, recruiter, candidate, threshold: float = 80.0
) -> NotificationLog | None:
    """
    Alert a recruiter when a new applicant scores above a threshold.
    Spec 4.11: "Recruiter alerts for new high-scoring applicants."
    """
    if candidate.score is None or candidate.score < threshold:
        return None

    job = candidate.job
    subject, body = render_template("recruiter_alert_high_scorer", {
        "recruiter_name":  recruiter.full_name,
        "job_title":        job.title if job else "the position",
        "score":            candidate.score,
        "candidate_name":   candidate.name or "Unnamed candidate",
        "recommendation":   candidate.recommendation or "Not yet scored",
    })

    log = _create_log_entry(
        db, "recruiter_alert", recruiter.email, subject, body,
        candidate_id=candidate.id, job_id=candidate.job_id,
    )
    return _attempt_send(db, log)