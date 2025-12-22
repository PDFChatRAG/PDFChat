"""
Additional unit tests for session_lifecycle.py exception handling.
"""
import pytest
from unittest.mock import MagicMock
from session_lifecycle import SessionLifecycle, SessionState
from tests.fixtures.factories import SessionFactory

def test_hard_delete_exception_handling(db_session):
    """Test _hard_delete handles vector DB errors gracefully."""
    session = SessionFactory.create(db_session, status="DELETED")
    mock_vector_db = MagicMock()
    mock_vector_db.delete_session_collection.side_effect = Exception("Chroma Error")
    
    # calling transition to DELETED triggers _hard_delete
    # But session is already DELETED? validate_transition checks logic.
    # We need to transition FROM something else.
    session.status = "ARCHIVED"
    
    # Should not raise exception
    SessionLifecycle.transition(session, SessionState.DELETED, db_session, mock_vector_db)
    
    # Session is deleted from DB, cannot refresh.
    # Check in-memory status
    assert session.status == "DELETED"
    
    # Verify it is deleted from DB
    from models import Session as SessionModel
    deleted = db_session.query(SessionModel).filter_by(id=session.id).first()
    assert deleted is None
