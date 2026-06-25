"""
Auth Router v2 â€” adds profile completeness to /auth/me.

Change from v1: GET /auth/me now returns job_count and candidate_count
(for recruiters) so a profile page has something real to display beyond
bare identity fields. Admins get a slightly different summary (total
recruiters they manage, system-wide job count) since "their own jobs"
isn't a meaningful concept for an admin.

Everything else (register, login, refresh, user management) is
unchanged from the original auth router.
"""
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.jobs import Job
from models.candidate import Candidate
from schemas.auth import (
    UserRegister, UserLogin, UserUpdate,
    Token, AccessToken, UserResponse, UserProfileResponse,
)
from security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user, require_admin,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# â”€â”€ REGISTER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. First registered user is automatically admin."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")

    role = "admin" if db.query(User).count() == 0 else payload.role

    user = User(
        email           = payload.email,
        full_name       = payload.full_name,
        hashed_password = hash_password(payload.password),
        role            = role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# â”€â”€ LOGIN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/login", response_model=Token)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    from models.auth_event_log import AuthEventLog
    from datetime import timezone, timedelta
    ip_address = request.client.host if request.client else None
    now        = datetime.now(timezone.utc)
    def log_event(event_type: str, user_id=None, detail: str = None):
        entry = AuthEventLog(
            user_id    = user_id,
            email      = payload.email,
            event_type = event_type,
            ip_address = ip_address,
            detail     = detail,
        )
        db.add(entry)
        db.commit()
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        log_event('login_failed_no_account')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password.')
    if user.locked_until and user.locked_until > now:
        remaining = int((user.locked_until - now).total_seconds() / 60) + 1
        log_event('login_blocked_locked_out', user_id=user.id,
            detail=f'Account locked. {remaining} minute(s) remaining.')
        raise HTTPException(status_code=429,
            detail=f'Account temporarily locked. Try again in {remaining} minute(s).')
    if not user.is_active:
        log_event('login_blocked_inactive', user_id=user.id)
        raise HTTPException(status_code=403, detail='Account is deactivated.')
    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        detail = f'Failed attempt {user.failed_login_attempts} of 5'
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            user.failed_login_attempts = 0
            detail = 'Account locked for 15 minutes after 5 consecutive failures'
            log_event('account_locked', user_id=user.id, detail=detail)
        else:
            log_event('login_failed_wrong_password', user_id=user.id, detail=detail)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password.')
    user.failed_login_attempts = 0
    user.locked_until          = None
    db.commit()
    log_event('login_success', user_id=user.id)
    token_data = {'sub': str(user.id), 'role': user.role}
    return Token(
        access_token  = create_access_token(token_data),
        refresh_token = create_refresh_token(token_data),
    )


# â”€â”€ REFRESH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/refresh", response_model=AccessToken)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")

    return AccessToken(
        access_token=create_access_token({"sub": str(user.id), "role": user.role})
    )


# â”€â”€ CURRENT USER (now with profile stats) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/me", response_model=UserProfileResponse)
def get_me(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Return the currently authenticated user's profile, including
    job/candidate counts scoped to their own ownership (or system-wide
    counts for admins).
    """
    base = UserResponse.model_validate(current_user).model_dump()

    if current_user.role == "admin":
        job_count       = db.query(Job).count()
        candidate_count = db.query(Candidate).count()
        managed_recruiters = db.query(User).filter(User.role == "recruiter").count()
    else:
        owned_job_ids = [
            j.id for j in db.query(Job.id).filter(Job.created_by == current_user.id).all()
        ]
        job_count       = len(owned_job_ids)
        candidate_count = (
            db.query(Candidate).filter(Candidate.job_id.in_(owned_job_ids)).count()
            if owned_job_ids else 0
        )
        managed_recruiters = None

    return UserProfileResponse(
        **base,
        job_count          = job_count,
        candidate_count    = candidate_count,
        managed_recruiters = managed_recruiters,
    )


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update own profile. Role change requires admin."""
    changes = payload.model_dump(exclude_unset=True)

    if "role" in changes and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change roles.")

    for field, value in changes.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


# â”€â”€ ADMIN: USER MANAGEMENT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all users. Admin only."""
    return db.query(User).order_by(User.created_at).all()


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Update any user's profile, role, or active status. Admin only."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=200)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deactivate a user account (soft delete). Admin only."""
    if str(user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    db.commit()
    return {"message": f"User {user.email} has been deactivated."}
