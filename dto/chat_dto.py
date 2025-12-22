"""Chat Data Transfer Objects."""

from pydantic import BaseModel
from typing import Optional


class ChatRequestDTO(BaseModel):
    """Request body for chat endpoint."""

    message: str
    # session_id is now extracted from JWT token, not in request body


class ChatResponseDTO(BaseModel):
    """Response from chat endpoint."""

    response: str

