"""Authentication dependency for public API endpoints."""
from datetime import datetime
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.auth.user import User
from app.models.auth.public_api_key import PublicApiKey
from app.core.security import hash_api_key


def verify_api_key(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """Verify API key from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    raw_key = authorization[7:]
    key_hash = hash_api_key(raw_key)

    api_key = db.query(PublicApiKey).filter(
        PublicApiKey.key_hash == key_hash,
        PublicApiKey.is_active == True
    ).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    api_key.last_used_at = datetime.utcnow()
    db.commit()

    return api_key.user
