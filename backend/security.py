from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

# ── Config ────────────────────────────────────────────────────────────────────

SECRET_KEY            = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM             = "HS256"
ACCESS_TOKEN_EXPIRE   = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))    # minutes
REFRESH_TOKEN_EXPIRE  = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",   7))     # days

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = HTTPBearer()


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit for the password string.
    # Trim by bytes (not characters) to avoid ValueError on long inputs.
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    # Mirror the same 72-byte trimming used during hashing.
    plain_bytes = plain.encode("utf-8")
    if len(plain_bytes) > 72:
        plain = plain_bytes[:72].decode("utf-8", errors="ignore")
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        # If hashing backend mismatch causes verify to error, fall back to False.
        return False




# ── Token helpers ─────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE)
    payload["type"] = "access"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE)
    payload["type"] = "refresh"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current user dependency ───────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db:          Session = Depends(get_db),
) -> User:
    token   = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    return user


# ── Role guards ───────────────────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def require_recruiter(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "recruiter"):
        raise HTTPException(status_code=403, detail="Recruiter access required.")
    return current_user