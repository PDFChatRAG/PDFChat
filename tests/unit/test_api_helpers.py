"""
Unit tests for helper functions in utils/conversation_helper.py
"""
import pytest
from unittest.mock import MagicMock, patch, ANY
from utils.conversation_helper import extract_message_content, get_session_conversation

class TestApiHelpers:
    """Test helper functions in utils/conversation_helper.py."""

    def test_extract_message_content_string(self):
        """Test extracting content from string message."""
        msg = "Simple string message"
        result = extract_message_content(msg)
        assert result["content"] == "Simple string message"
        # Type might vary based on how it's passed, str object has no __class__.__name__ like that?
        # Actually str(msg) is used if no content attr.
        # But msg.__class__.__name__ would be 'str'.
        assert result["role"] == "assistant" # Default fallback

    def test_extract_message_content_human(self):
        """Test extracting from HumanMessage."""
        msg = MagicMock()
        msg.content = "User input"
        msg.__class__.__name__ = "HumanMessage"
        
        result = extract_message_content(msg)
        assert result["role"] == "user"
        assert result["content"] == "User input"
        assert result["type"] == "HumanMessage"

    def test_extract_message_content_ai(self):
        """Test extracting from AIMessage."""
        msg = MagicMock()
        msg.content = "AI output"
        msg.__class__.__name__ = "AIMessage"
        
        result = extract_message_content(msg)
        assert result["role"] == "assistant"
        assert result["content"] == "AI output"

    def test_extract_message_content_system(self):
        """Test extracting from SystemMessage."""
        msg = MagicMock()
        msg.content = "System prompt"
        msg.__class__.__name__ = "SystemMessage"
        
        result = extract_message_content(msg)
        assert result["role"] == "system"

    def test_extract_message_content_tool(self):
        """Test extracting from ToolMessage."""
        msg = MagicMock()
        msg.content = "Tool output"
        msg.__class__.__name__ = "ToolMessage"
        
        result = extract_message_content(msg)
        assert result["role"] == "tool"

    def test_get_session_conversation_empty(self):
        """Test retrieving history when empty."""
        mock_cp = MagicMock()
        mock_cp.list.return_value = []
        
        result = get_session_conversation("session1", checkpointer=mock_cp)
        assert result["messages"] == []
        assert result["checkpoint_count"] == 0

    def test_get_session_conversation_checkpoints(self):
        """Test retrieving history from checkpoints."""
        # Mock checkpoints: list of tuples (checkpoint, checkpoint_id)
        # Checkpoint structure: {'channel_values': {'messages': [...]}, 'ts': timestamp}
        
        msg1 = MagicMock(content="Hello")
        msg1.__class__.__name__ = "HumanMessage"
        
        msg2 = MagicMock(content="Hi there")
        msg2.__class__.__name__ = "AIMessage"
        
        cp1 = (
            {"channel_values": {"messages": [msg1]}, "ts": "2023-01-01T10:00:00"},
            "cp_id_1"
        )
        cp2 = (
            {"channel_values": {"messages": [msg1, msg2]}, "ts": "2023-01-01T10:01:00"},
            "cp_id_2"
        )
        
        # API iterates reversed(list(checkpointer.list(...)))
        mock_cp = MagicMock()
        mock_cp.list.return_value = [cp2, cp1]
        
        result = get_session_conversation("session1", checkpointer=mock_cp)
        
        messages = result["messages"]
        # Note: Keeps the original logic (duplication behavior) to ensure refactoring doesn't change logic.
        assert len(messages) == 3 
        assert messages[0]["content"] == "Hello"
        assert messages[2]["content"] == "Hi there"

    def test_get_session_conversation_error(self):
        """Test error handling in history retrieval."""
        mock_cp = MagicMock()
        mock_cp.list.side_effect = Exception("DB Error")
        
        result = get_session_conversation("session1", checkpointer=mock_cp)
        assert "error" in result
        assert result["messages"] == []