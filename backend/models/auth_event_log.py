"""
AuthEventLog model.

Records every authentication event - successful logins, failed login
attempts, account lockouts, and lockout-triggered rejections - as its
own immutable row, for compliance audit purposes (spec 4.1).

Deliberately NOT cascade-deleted with the user - if an account is ever
deleted, the audit trail of what it did should survive. user_id is
nullable (ON DELETE SET NULL), with email captured as plain text so the
row stays meaningful even after user_id becomes null.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database import Base


class AuthEventLog(Base):
    __tablename__ = "auth_event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
                     nullable=True, index=True)
    email   = Column(String(255), nullable=False, index=True)

    event_type = Column(String(50), nullable=False, index=True)

    ip_address = Column(String(64), nullable=True)

    detail = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
