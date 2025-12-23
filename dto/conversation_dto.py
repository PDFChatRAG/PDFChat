"""Conversation History Data Transfer Objects."""

from pydantic import BaseModel
from typing import Optional, List


class MessageDTO(BaseModel):
    """Single message in conversation."""

    id: str
    role: str  # "user", "assistant", "system", or "tool"
    content: str
    type: str  # LangChain message class name
    timestamp: Optional[str] = None
    checkpoint_id: Optional[str] = None


class ConversationHistoryDTO(BaseModel):
    """Full conversation history for a session."""

    session_id: str
    messages: List[MessageDTO]
    message_count: int
    checkpoint_count: int


class PaginatedConversationDTO(BaseModel):
    """Paginated conversation history."""

    session_id: str
    page: int
    page_size: int
    messages: List[MessageDTO]
    total_messages: int
    total_pages: int
    has_more: bool
    message_count: int = 0
    checkpoint_count: int = 0
