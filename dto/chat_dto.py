"""Chat Data Transfer Objects."""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequestDTO(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., min_length=1)
    # session_id is now extracted from JWT token, not in request body


class ChatResponseDTO(BaseModel):
    """Response from chat endpoint."""

    response: str

