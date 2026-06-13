from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import (
    UserRegister, UserLogin, UserUpdate,
    Token, AccessToken, UserResponse,
)
from security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user, require_admin,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── REGISTER ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. First registered user is automatically admin."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")

    # First user ever becomes admin automatically
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


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password. Returns access + refresh tokens."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    token_data = {"sub": str(user.id), "role": user.role}
    return Token(
        access_token  = create_access_token(token_data),
        refresh_token = create_refresh_token(token_data),
    )


# ── REFRESH ───────────────────────────────────────────────────────────────────

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


# ── CURRENT USER ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


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


# ── ADMIN: USER MANAGEMENT ────────────────────────────────────────────────────

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