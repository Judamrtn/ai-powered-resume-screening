from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Register ──────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email:     EmailStr
    full_name: str  = Field(..., min_length=2, max_length=200)
    password:  str  = Field(..., min_length=8)
    role:      str  = Field(default="recruiter", pattern="^(admin|recruiter)$")


# ── Login ─────────────────────────────────────────────────────────────────────

class UserLogin(BaseModel):
    email:    EmailStr
    password: str


# ── Token responses ───────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── User responses ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:         UUID
    email:      str
    full_name:  str
    role:       str
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    """
    Extended profile shown only on GET /auth/me — includes ownership
    counts so a frontend profile/dashboard widget has real numbers to
    show, rather than just bare identity fields.

    For recruiters: job_count and candidate_count are scoped to jobs
    they personally created.
    For admins: job_count/candidate_count are system-wide totals, and
    managed_recruiters is populated (None for recruiters, since the
    concept doesn't apply to them).
    """
    job_count:          int
    candidate_count:    int
    managed_recruiters: Optional[int] = None


class UserUpdate(BaseModel):
    full_name:  Optional[str] = Field(None, min_length=2, max_length=200)
    is_active:  Optional[bool] = None
    role:       Optional[str] = Field(None, pattern="^(admin|recruiter)$")