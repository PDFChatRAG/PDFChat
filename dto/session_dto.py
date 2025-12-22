"""Session Data Transfer Objects."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SessionRequestDTO(BaseModel):
    """Request body for creating a session (legacy, not used in new auth)."""

    user_id: str


class SessionResponseDTO(BaseModel):
    """Response with session ID."""

    session_id: str


class SessionDetailDTO(BaseModel):
    """Detailed session information."""

    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

