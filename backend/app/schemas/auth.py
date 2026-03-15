"""
Authentication Pydantic schemas.
"""
from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""

    user_id: int
    username: str


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str
