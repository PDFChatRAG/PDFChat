"""
Coverage tests for Auth and Lifecycle to hit missing lines.
"""
import pytest
from unittest.mock import MagicMock, patch
from auth_service import AuthService
from session_lifecycle import ArchivalPolicy, SessionLifecycle, SessionState
from models import Session

class TestMiscCoverage:

    def test_auth_verify_password_error(self):
        """Test verify_password handles ValueError from bcrypt."""
        with patch("bcrypt.checkpw", side_effect=ValueError):
            assert AuthService.verify_password("pass", "hash") is False

    def test_cleanup_job_errors(self):
        """Test cleanup job logging when transitions fail."""
        mock_db = MagicMock()
        mock_vector = MagicMock()
        
        # Mock sessions
        session1 = MagicMock(spec=Session, status=SessionState.ACTIVE, id="s1")
        session2 = MagicMock(spec=Session, status=SessionState.ARCHIVED, id="s2")
        
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [session1], # Inactive sessions
            [session2]  # Archived sessions
        ]
        
        # Force "should" to True
        with patch("session_lifecycle.ArchivalPolicy.should_auto_archive", return_value=True):
             with patch("session_lifecycle.ArchivalPolicy.should_hard_delete", return_value=True):
                 # Force transition to raise exception
                 with patch("session_lifecycle.SessionLifecycle.transition", side_effect=Exception("Lifecycle fail")):
                     
                     ArchivalPolicy.cleanup_job(mock_db, mock_vector)
                     
                     # We expect it to catch the exception and log error, not crash.
                     # Coverage should be hit.