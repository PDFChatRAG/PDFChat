"""
Coverage tests for SessionManager to hit missing lines.
"""
import pytest
from unittest.mock import MagicMock, patch
from sessionManager import SessionManager
from models import Session, User
from session_lifecycle import SessionState

class TestSessionManagerCoverage:
    
    def test_create_session_user_not_found(self):
        """Test creating session for non-existent user raises ValueError."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="User non_existent not found"):
            SessionManager.create_session("non_existent", mock_db)

    def test_get_session_documents_no_session(self):
        """Test getting documents returns empty list if session not found."""
        mock_db = MagicMock()
        # Mock get_session returning None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        docs = SessionManager.get_session_documents("sess1", "user1", mock_db)
        assert docs == []

    def test_add_document_to_session_not_found(self):
        """Test adding document to non-existent session raises ValueError."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            SessionManager.add_document_to_session("sess1", "user1", "file.pdf", 100, "pdf", 1, mock_db)

    def test_archive_session_lifecycle_error(self):
        """Test error logging when archive transition fails."""
        mock_db = MagicMock()
        mock_session = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        
        with patch("sessionManager.SessionLifecycle.transition", side_effect=ValueError("Invalid state")):
             with pytest.raises(ValueError, match="Invalid state"):
                 SessionManager.archive_session("sess1", "user1", mock_db)

    def test_reactivate_session_lifecycle_error(self):
        """Test error logging when reactivate transition fails."""
        mock_db = MagicMock()
        mock_session = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        
        with patch("sessionManager.SessionLifecycle.transition", side_effect=ValueError("Invalid state")):
             with pytest.raises(ValueError, match="Invalid state"):
                 SessionManager.reactivate_session("sess1", "user1", mock_db)

    def test_delete_session_lifecycle_error(self):
        """Test error logging when delete transition fails."""
        mock_db = MagicMock()
        mock_session = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_vector_service = MagicMock()
        
        with patch("sessionManager.SessionLifecycle.transition", side_effect=ValueError("Invalid state")):
             with pytest.raises(ValueError, match="Invalid state"):
                 SessionManager.delete_session("sess1", "user1", mock_db, mock_vector_service)
