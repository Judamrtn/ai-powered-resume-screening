"""
Notifications Router

Read access to the NotificationLog audit trail (spec 7.5), plus a retry
endpoint for failed sends (spec 4.11). Scoped the same way as every
other ownership-aware endpoint in this system: recruiters see only
notifications tied to jobs they own, admins see everything.

A notification can be tied to a candidate, an interview, or neither
(e.g. a future recruiter-alert type with no candidate-facing content).
Scoping is resolved through whichever foreign key is populated, falling
back to "visible to admins only" for the rare case where a log row has
no job/candidate/interview link at all - in practice this should not
happen given how notification_service.py always populates at least
job_id, but the fallback exists so a malformed row fails closed rather
than crashing the endpoint or leaking to the wrong recruiter.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.notification import NotificationLog
from models.jobs import Job
from models.user import User
from security import get_current_user, require_admin
from notification_sender import send_email, EmailSendError, EmailConfigError

router = APIRouter(prefix="/notifications", tags=["Notifications"])

MAX_MANUAL_RETRIES = 5  # hard ceiling independent of the sender's own MAX_RETRIES per attempt


# ── Response schema ───────────────────────────────────────────────────────────

class NotificationLogResponse(BaseModel):
    id:                 UUID
    candidate_id:       Optional[UUID]
    interview_id:       Optional[UUID]
    job_id:             Optional[UUID]
    notification_type:  str
    recipient_email:    str
    subject:            str
    status:             str
    error_message:      Optional[str]
    retry_count:        int
    created_at:         datetime
    sent_at:            Optional[datetime]

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    total:         int
    offset:        int
    limit:         int
    notifications: list[NotificationLogResponse]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_scoped_log_or_404(log_id: UUID, db: Session, current_user: User) -> NotificationLog:
    """
    Fetch a single notification log row, enforcing the same ownership
    scoping as every other resource: admins see anything, recruiters
    only see rows tied (via job_id) to a job they created.
    """
    log = db.get(NotificationLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if current_user.role == "admin":
        return log

    if log.job_id is None:
        raise HTTPException(status_code=404, detail="Notification not found.")

    job = db.get(Job, log.job_id)
    if not job or str(job.created_by) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found.")

    return log


# ── LIST ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=NotificationListResponse)
def list_notifications(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
    job_id:             Optional[UUID] = Query(default=None),
    candidate_id:       Optional[UUID] = Query(default=None),
    notification_type: Optional[str]  = Query(default=None),
    status:             Optional[str]  = Query(default=None, pattern="^(pending|sent|failed)$"),
    limit:  int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    List notification log entries, scoped to jobs you own (or
    everything, if admin). Filter by job, candidate, notification type,
    or delivery status - e.g. status=failed to find everything that
    needs retrying.
    """
    q = db.query(NotificationLog)

    if current_user.role != "admin":
        owned_job_ids = [
            row.id for row in db.query(Job.id).filter(Job.created_by == current_user.id).all()
        ]
        q = q.filter(NotificationLog.job_id.in_(owned_job_ids)) if owned_job_ids else q.filter(False)

    if job_id:
        q = q.filter(NotificationLog.job_id == job_id)
    if candidate_id:
        q = q.filter(NotificationLog.candidate_id == candidate_id)
    if notification_type:
        q = q.filter(NotificationLog.notification_type == notification_type)
    if status:
        q = q.filter(NotificationLog.status == status)

    total = q.count()
    logs  = q.order_by(NotificationLog.created_at.desc()).offset(offset).limit(limit).all()

    return NotificationListResponse(total=total, offset=offset, limit=limit, notifications=logs)


# ── GET ONE ───────────────────────────────────────────────────────────────────

@router.get("/{notification_id}", response_model=NotificationLogResponse)
def get_notification(
    notification_id: UUID,
    db:               Session = Depends(get_db),
    current_user:     User    = Depends(get_current_user),
):
    return get_scoped_log_or_404(notification_id, db, current_user)


# ── RETRY ─────────────────────────────────────────────────────────────────────

@router.post("/{notification_id}/retry", response_model=NotificationLogResponse)
def retry_notification(
    notification_id: UUID,
    db:               Session = Depends(get_db),
    current_user:     User    = Depends(get_current_user),
):
    """
    Manually retry a failed notification. Only valid for notifications
    currently in status='failed' - retrying an already-sent notification
    would re-email the recipient, which is never the intended behavior
    of a "retry failed sends" feature, so that case is rejected rather
    than silently re-sent.
    """
    log = get_scoped_log_or_404(notification_id, db, current_user)

    if log.status != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Only failed notifications can be retried. Current status: '{log.status}'.",
        )

    if log.retry_count >= MAX_MANUAL_RETRIES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This notification has already been retried {log.retry_count} times "
                f"(max {MAX_MANUAL_RETRIES}). Check error_message for the underlying "
                f"cause - repeated identical failures usually indicate a configuration "
                f"problem (e.g. invalid recipient address) rather than a transient one."
            ),
        )

    try:
        send_email(log.recipient_email, log.subject, log.body)
        log.status        = "sent"
        log.sent_at        = datetime.now(log.created_at.tzinfo)
        log.error_message  = None
    except EmailConfigError as e:
        log.error_message = f"Configuration error: {e}"
        log.retry_count    = (log.retry_count or 0) + 1
    except EmailSendError as e:
        log.error_message = str(e)
        log.retry_count    = (log.retry_count or 0) + 1

    db.commit()
    db.refresh(log)
    return log


# ── ADMIN: BULK RETRY ALL FAILED ──────────────────────────────────────────────

@router.post("/retry-all-failed", status_code=200)
def retry_all_failed(
    db: Session = Depends(get_db),
    _:  User    = Depends(require_admin),
):
    """
    Retry every currently-failed notification system-wide that hasn't
    hit MAX_MANUAL_RETRIES yet. Admin only - this is a bulk operation
    that could trigger a burst of outbound emails, so it is deliberately
    not exposed to individual recruiters.
    """
    failed = db.query(NotificationLog).filter(
        NotificationLog.status == "failed",
        NotificationLog.retry_count < MAX_MANUAL_RETRIES,
    ).all()

    results = {"retried": 0, "now_sent": 0, "still_failed": 0}

    for log in failed:
        results["retried"] += 1
        try:
            send_email(log.recipient_email, log.subject, log.body)
            log.status         = "sent"
            log.sent_at         = datetime.now(log.created_at.tzinfo)
            log.error_message   = None
            results["now_sent"] += 1
        except (EmailConfigError, EmailSendError) as e:
            log.error_message = str(e)
            log.retry_count    = (log.retry_count or 0) + 1
            results["still_failed"] += 1

    db.commit()
    return results