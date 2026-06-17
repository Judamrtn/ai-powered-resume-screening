from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


# ── Interview schemas ─────────────────────────────────────────────────────────

class InterviewCreate(BaseModel):
    candidate_id:     UUID
    title:            str   = Field(..., min_length=2, max_length=200)
    format:           str   = Field(..., pattern="^(phone_screen|video_call|on_site|technical_assessment|panel)$")
    scheduled_at:     datetime
    duration_minutes: int   = Field(default=60, ge=15, le=480)
    location:         Optional[str] = None
    meeting_link:     Optional[str] = None
    interviewers:     list[str]     = Field(default_factory=list)
    round_number:     int   = Field(default=1, ge=1)
    notes:            Optional[str] = None


class InterviewUpdate(BaseModel):
    title:            Optional[str]      = None
    format:           Optional[str]      = Field(None, pattern="^(phone_screen|video_call|on_site|technical_assessment|panel)$")
    scheduled_at:     Optional[datetime] = None
    duration_minutes: Optional[int]      = Field(None, ge=15, le=480)
    location:         Optional[str]      = None
    meeting_link:     Optional[str]      = None
    interviewers:     Optional[list[str]] = None
    round_number:     Optional[int]      = Field(None, ge=1)
    notes:            Optional[str]      = None
    status:           Optional[str]      = Field(None, pattern="^(scheduled|confirmed|completed|cancelled|no_show)$")


class InterviewResponse(BaseModel):
    id:                    UUID
    candidate_id:          UUID
    job_id:                UUID
    title:                 str
    format:                str
    scheduled_at:          datetime
    duration_minutes:      int
    location:              Optional[str]
    meeting_link:          Optional[str]
    interviewers:          list[str]
    round_number:          int
    status:                str
    candidate_notified:    bool
    interviewers_notified: bool
    calendar_event_id:     Optional[str]
    notes:                 Optional[str]
    created_at:            datetime
    feedbacks:             list[FeedbackResponse] = []

    model_config = {"from_attributes": True}


# ── Feedback schemas ──────────────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    interviewer_email:    str
    interviewer_name:     Optional[str] = None
    technical_score:      Optional[float] = Field(None, ge=1, le=5)
    communication_score:  Optional[float] = Field(None, ge=1, le=5)
    problem_solving_score: Optional[float] = Field(None, ge=1, le=5)
    cultural_fit_score:   Optional[float] = Field(None, ge=1, le=5)
    overall_score:        Optional[float] = Field(None, ge=1, le=5)
    recommendation:       Optional[str]   = Field(None, pattern="^(strong_yes|yes|maybe|no|strong_no)$")
    strengths:            Optional[str]   = None
    weaknesses:           Optional[str]   = None
    comments:             Optional[str]   = None


class FeedbackResponse(BaseModel):
    id:                    UUID
    interview_id:          UUID
    interviewer_email:     str
    interviewer_name:      Optional[str]
    technical_score:       Optional[float]
    communication_score:   Optional[float]
    problem_solving_score: Optional[float]
    cultural_fit_score:    Optional[float]
    overall_score:         Optional[float]
    recommendation:        Optional[str]
    strengths:             Optional[str]
    weaknesses:            Optional[str]
    comments:              Optional[str]
    submitted_at:          datetime

    model_config = {"from_attributes": True}


# ── Calendar schemas ──────────────────────────────────────────────────────────

class CalendarEvent(BaseModel):
    title:       str
    description: str
    start:       datetime
    end:         datetime
    attendees:   list[str]
    location:    Optional[str] = None
    meeting_link: Optional[str] = None


class InterviewSummary(BaseModel):
    """Aggregated interview summary for a candidate."""
    candidate_id:     UUID
    total_interviews: int
    completed:        int
    pending:          int
    avg_overall_score: Optional[float]
    final_recommendation: Optional[str]
    interviews:       list[InterviewResponse]

# Fix forward reference
InterviewResponse.model_rebuild()