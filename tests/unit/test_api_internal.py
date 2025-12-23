"""
Additional unit tests for api.py internals and startup/shutdown.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager
from api import lifespan, app
from utils.conversation_helper import get_session_conversation

@pytest.mark.anyio
async def test_lifespan():
    """Test application lifespan (startup and shutdown)."""
    # Mock init_db and SqliteSaver
    with patch("api.init_db") as mock_init_db, \
         patch("api.SqliteSaver") as mock_saver, \
         patch("api.os.getenv") as mock_getenv:
        
        # Setup mocks
        mock_manager = MagicMock()
        mock_saver.from_conn_string.return_value = mock_manager
        
        mock_checkpointer = MagicMock()
        mock_manager.__enter__.return_value = mock_checkpointer
        
        # Test startup
        async with lifespan(app):
            mock_init_db.assert_called_once()
            mock_saver.from_conn_string.assert_called()
            mock_manager.__enter__.assert_called()
            
        # Test shutdown (context exit)
        # In api.py: checkpointer.__exit__(None, None, None) is called
        # checkpointer is the result of __enter__, which is mock_checkpointer
        mock_checkpointer.__exit__.assert_called()

def test_get_session_conversation_fallback():
    """Test get_session_conversation fallback when checkpointer arg is None."""
    # Patch SqliteSaver in the utils module where it is used
    with patch("utils.conversation_helper.SqliteSaver") as mock_saver:
        mock_instance = MagicMock()
        mock_saver.from_conn_string.return_value = mock_instance
        mock_instance.__enter__.return_value = MagicMock() # The entered object
        
        # Mock the list method on the ENTERED object? 
        mock_instance.__enter__.return_value.list.return_value = []
        
        # Call without checkpointer arg to trigger fallback
        get_session_conversation("session1", checkpointer=None)
        
        mock_saver.from_conn_string.assert_called()

def test_get_session_conversation_exception():
    """Test exception handling in get_session_conversation."""
    mock_cp = MagicMock()
    mock_cp.list.side_effect = Exception("DB Error")
    
    result = get_session_conversation("session1", checkpointer=mock_cp)
    assert "error" in result
    assert result["messages"] == []