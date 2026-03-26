"""Pydantic schemas for public auth endpoints."""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    invite_code: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str

    class Config:
        from_attributes = True


class ApiKeyRequest(BaseModel):
    email: EmailStr
    username: str


class ApiKeyResponse(BaseModel):
    api_key: str
