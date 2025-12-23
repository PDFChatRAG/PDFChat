"""Authentication Data Transfer Objects."""

from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserRegisterDTO(BaseModel):
    """Request body for user registration."""
    email: EmailStr
    password: str


class UserLoginDTO(BaseModel):
    """Request body for user login."""
    email: EmailStr
    password: str


class TokenResponseDTO(BaseModel):
    """Response containing session token."""
    access_token: str
    token_type: str = "bearer"
    session_id: str


class UserResponseDTO(BaseModel):
    """Response with user details."""
    id: str
    email: str
    created_at: datetime
