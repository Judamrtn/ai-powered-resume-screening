from sqlalchemy import Column, String, Boolean, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    full_name  = Column(String(200), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role       = Column(String(20), nullable=False, default="recruiter")  # admin | recruiter
    is_active  = Column(Boolean, nullable=False, default=True)

    # Brute-force login protection (spec 4.1).
    # failed_login_attempts resets to 0 on any successful login.
    # locked_until is null when the account is not locked; once set,
    # login attempts are rejected until that timestamp passes, even
    # if the correct password is supplied.
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until          = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)
