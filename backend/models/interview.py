from sqlalchemy import Column, String, Float, DateTime, Text, ARRAY, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import func
import uuid

from database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    job_id       = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    # Interview details
    title            = Column(String(200), nullable=False)
    format           = Column(String(50),  nullable=False)
    # phone_screen | video_call | on_site | technical_assessment | panel
    scheduled_at     = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    location         = Column(String(200), nullable=True)   # room or video link
    meeting_link     = Column(String(500), nullable=True)   # Zoom/Meet/Teams link

    # Interviewers
    interviewers     = Column(ARRAY(String), nullable=False, default=list)
    # list of interviewer emails

    # Round tracking
    round_number     = Column(Integer, nullable=False, default=1)

    # Status
    status = Column(String(30), nullable=False, default="scheduled", index=True)
    # scheduled | confirmed | completed | cancelled | no_show

    # Notifications
    candidate_notified  = Column(Boolean, nullable=False, default=False)
    interviewers_notified = Column(Boolean, nullable=False, default=False)

    # Calendar
    calendar_event_id = Column(String(200), nullable=True)  # Google/Outlook event ID

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    # Relationships
    candidate = relationship("Candidate", backref="interviews")
    job       = relationship("Job",       backref="interviews")
    feedbacks = relationship("InterviewFeedback", back_populates="interview",
                             cascade="all, delete-orphan")


class InterviewFeedback(Base):
    __tablename__ = "interview_feedback"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    # Interviewer info
    interviewer_email = Column(String(255), nullable=False)
    interviewer_name  = Column(String(200), nullable=True)

    # Ratings (1-5)
    technical_score       = Column(Float, nullable=True)
    communication_score   = Column(Float, nullable=True)
    problem_solving_score = Column(Float, nullable=True)
    cultural_fit_score    = Column(Float, nullable=True)
    overall_score         = Column(Float, nullable=True)

    # Outcome
    recommendation = Column(String(50), nullable=True)
    # strong_yes | yes | maybe | no | strong_no

    # Comments
    strengths   = Column(Text, nullable=True)
    weaknesses  = Column(Text, nullable=True)
    comments    = Column(Text, nullable=True)

    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    interview = relationship("Interview", back_populates="feedbacks")