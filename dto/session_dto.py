"""Session Data Transfer Objects."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UpdateSessionTitleDTO(BaseModel):
    """Request to update session title."""
    
    title: str = Field(..., min_length=1, max_length=50, description="New session title")


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

