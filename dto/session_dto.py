"""Session Data Transfer Objects."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime





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

