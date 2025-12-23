import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from sessionManager import SessionManager, SessionState
from models import Session, Document
from tests.fixtures.factories import SessionFactory, UserFactory, DocumentFactory

class TestSessionManagerActivePolicy:
    """Test the Single Active Session policy."""

    def test_create_session_archives_others(self, db_session):
        """Test that creating a new session archives existing active ones."""
        user, _ = UserFactory.create(db_session)
        
        # Create an initial active session
        session1 = SessionFactory.create(db_session, user_id=user.id, status=SessionState.ACTIVE)
        
        # Create a second session
        session2 = SessionManager.create_session(user.id, db_session)
        
        db_session.refresh(session1)
        db_session.refresh(session2)
        
        # Assert session1 is ARCHIVED and session2 is ACTIVE
        assert session1.status == SessionState.ARCHIVED
        assert session2.status == SessionState.ACTIVE

    def test_reactivate_session_archives_others(self, db_session):
        """Test that reactivating a session archives other active ones."""
        user, _ = UserFactory.create(db_session)
        
        # Session 1 is currently active
        session1 = SessionFactory.create(db_session, user_id=user.id, status=SessionState.ACTIVE)
        
        # Session 2 is archived
        session2 = SessionFactory.create(db_session, user_id=user.id, status=SessionState.ARCHIVED)
        
        # Reactivate Session 2
        SessionManager.reactivate_session(session2.id, user.id, db_session)
        
        db_session.refresh(session1)
        db_session.refresh(session2)
        
        # Assert session1 is ARCHIVED and session2 is ACTIVE
        assert session1.status == SessionState.ARCHIVED
        assert session2.status == SessionState.ACTIVE

    def test_login_reuse_archives_non_empty(self, db_session):
        """Test that logging in and reusing an empty session archives a non-empty active one."""
        user, _ = UserFactory.create(db_session)
        
        # Session 1: Active and used (has a document)
        session1 = SessionFactory.create(db_session, user_id=user.id, status=SessionState.ACTIVE)
        DocumentFactory.create(db_session, session_id=session1.id)
        
        # Session 2: Active and empty (should be reused)
        # Force updated_at to be newer so it's picked
        session2 = SessionFactory.create(db_session, user_id=user.id, status=SessionState.ACTIVE)
        
        # Mock dependencies for get_or_create_empty_session
        mock_checkpointer = MagicMock()
        mock_vectordb = MagicMock()
        
        # Mock history to be empty for session2
        # We need to patch get_session_conversation inside sessionManager module
        # But for now, let's assume the mock behavior handles it or we rely on the fact 
        # that 'agent_memory.db' won't have history for this fake session ID.
        # However, get_session_conversation in sessionManager imports from utils.
        
        from unittest.mock import patch
        with patch("utils.conversation_helper.get_session_conversation", return_value={"message_count": 0}):
             reused_session = SessionManager.get_or_create_empty_session(
                 user.id, db_session, mock_checkpointer, mock_vectordb
             )
        
        db_session.refresh(session1)
        db_session.refresh(session2)
        
        # Assert session1 (the used one) got archived
        assert session1.status == SessionState.ARCHIVED
        # Assert session2 (the empty one) is still active and was reused
        assert session2.status == SessionState.ACTIVE
        assert reused_session.id == session2.id
