"""
NotificationLog model.

Every notification the system attempts to send gets exactly one row
here, regardless of whether the send actually succeeds. This is the
audit trail the spec calls for in section 7.5 ("A complete audit log of
all automated communications sent to candidates"), and it's also what
retry logic (4.11: "Email delivery tracking and retry logic for failed
sends") depends on - you can't retry a failure you never recorded.

Status lifecycle: pending -> sent | failed -> (failed can become
retrying -> sent | failed again, up to MAX_RETRIES in the sender).
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from database import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # What triggered this notification, and who it's about - both
    # nullable because some notification types (e.g. a recruiter alert
    # about a new high-scoring applicant) aren't tied to a single
    # candidate or interview.
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="SET NULL"),
                          nullable=True, index=True)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="SET NULL"),
                          nullable=True, index=True)
    job_id       = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"),
                          nullable=True, index=True)

    # What kind of notification this is - drives which template was used
    notification_type = Column(String(50), nullable=False, index=True)
    # application_received | status_changed | interview_scheduled |
    # interview_reminder | recruiter_alert

    # Delivery details
    recipient_email = Column(String(255), nullable=False)
    subject          = Column(String(500), nullable=False)
    body              = Column(Text, nullable=False)

    # Delivery tracking
    status        = Column(String(20), nullable=False, default="pending", index=True)
    # pending | sent | failed
    error_message = Column(Text, nullable=True)
    retry_count   = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at    = Column(DateTime(timezone=True), nullable=True)

    candidate = relationship("Candidate", backref="notifications")
    interview = relationship("Interview", backref="notifications")
    job       = relationship("Job",       backref="notifications")