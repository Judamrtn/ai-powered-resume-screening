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


class UserUpdate(BaseModel):
    full_name:  Optional[str] = Field(None, min_length=2, max_length=200)
    is_active:  Optional[bool] = None
    role:       Optional[str] = Field(None, pattern="^(admin|recruiter)$")