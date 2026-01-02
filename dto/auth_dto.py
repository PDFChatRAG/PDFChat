"""Authentication Data Transfer Objects."""

from typing import Optional
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


class RequestResetCodeDTO(BaseModel):
    """Request body for requesting password reset code."""
    email: EmailStr


class VerifyResetCodeDTO(BaseModel):
    """Request body for verifying reset code."""
    email: EmailStr
    code: str


class ResetPasswordDTO(BaseModel):
    """Request body for resetting password."""
    reset_token: str
    new_password: str
