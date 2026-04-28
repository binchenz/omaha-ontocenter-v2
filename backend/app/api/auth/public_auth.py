"""Public authentication endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import secrets

from app.database import get_db
from app.models import User, InviteCode, PublicApiKey
from app.schemas.auth.public_auth import (
    RegisterRequest,
    UserResponse,
    ApiKeyRequest,
    ApiKeyResponse
)
from app.core.security import hash_api_key

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with an invite code."""
    invite = db.query(InviteCode).filter_by(code=request.invite_code).first()

    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite code")

    if invite.is_used:
        raise HTTPException(status_code=400, detail="Invite code already used")

    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite code expired")

    user = User(
        email=request.email,
        username=request.username,
        hashed_password=""
    )
    db.add(user)
    db.flush()

    invite.is_used = True
    invite.used_by = user.id
    invite.used_at = datetime.utcnow()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register user")
    db.refresh(user)

    return user


@router.post("/api-key", response_model=ApiKeyResponse)
def generate_api_key(request: ApiKeyRequest, db: Session = Depends(get_db)):
    """Generate API key for registered user."""
    user = db.query(User).filter_by(
        email=request.email,
        username=request.username
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    raw_key = f"omaha_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)

    api_key = PublicApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=raw_key[:16]
    )
    db.add(api_key)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to generate API key")

    return ApiKeyResponse(api_key=raw_key)
