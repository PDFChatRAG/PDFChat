"""
Unit tests for session_lifecycle.py
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from session_lifecycle import SessionLifecycle, SessionState, ArchivalPolicy
from models import Session as SessionModel
from tests.fixtures.factories import SessionFactory, UserFactory


class TestSessionState:
    """Test SessionState enum."""

    def test_session_state_values(self):
        """Test SessionState enum values."""
        assert SessionState.ACTIVE.value == "ACTIVE"
        assert SessionState.ARCHIVED.value == "ARCHIVED"
        assert SessionState.DELETED.value == "DELETED"


class TestSessionLifecycleStateTransitions:
    """Test SessionLifecycle state transition validation."""

    def test_valid_transition_active_to_archived(self):
        """Test valid transition from ACTIVE to ARCHIVED."""
        assert SessionLifecycle.can_transition(
            SessionState.ACTIVE, SessionState.ARCHIVED
        ) is True

    def test_valid_transition_archived_to_active(self):
        """Test valid transition from ARCHIVED back to ACTIVE."""
        assert SessionLifecycle.can_transition(
            SessionState.ARCHIVED, SessionState.ACTIVE
        ) is True

    def test_valid_transition_active_to_deleted(self):
        """Test valid transition from ACTIVE to DELETED."""
        assert SessionLifecycle.can_transition(
            SessionState.ACTIVE, SessionState.DELETED
        ) is True

    def test_valid_transition_archived_to_deleted(self):
        """Test valid transition from ARCHIVED to DELETED."""
        assert SessionLifecycle.can_transition(
            SessionState.ARCHIVED, SessionState.DELETED
        ) is True

    def test_invalid_transition_deleted_to_active(self):
        """Test invalid transition from DELETED to ACTIVE."""
        assert SessionLifecycle.can_transition(
            SessionState.DELETED, SessionState.ACTIVE
        ) is False

    def test_invalid_transition_deleted_to_archived(self):
        """Test invalid transition from DELETED to ARCHIVED."""
        assert SessionLifecycle.can_transition(
            SessionState.DELETED, SessionState.ARCHIVED
        ) is False

    def test_same_state_transition(self):
        """Test transition to same state."""
        assert SessionLifecycle.can_transition(
            SessionState.ACTIVE, SessionState.ACTIVE
        ) is False


class TestSessionLifecycleSoftDelete:
    """Test SessionLifecycle soft delete (archival)."""

    def test_soft_delete_sets_archived_status(self, db_session):
        """Test soft delete sets ARCHIVED status."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.transition(session, SessionState.ARCHIVED, db_session, None)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"

    def test_soft_delete_sets_archived_at(self, db_session):
        """Test soft delete sets archived_at timestamp."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.transition(session, SessionState.ARCHIVED, db_session, None)
        db_session.refresh(session)

        assert session.archived_at is not None
        assert isinstance(session.archived_at, datetime)

    def test_soft_delete_already_archived(self, db_session):
        """Test soft delete on already archived session."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        
        # Transitioning to same state should raise error (as per validate_transition)
        # But wait, transition method checks can_transition.
        # ARCHIVED -> ARCHIVED is NOT in VALID_TRANSITIONS.
        # So it should raise ValueError
        with pytest.raises(ValueError):
             SessionLifecycle.transition(session, SessionState.ARCHIVED, db_session, None)


class TestSessionLifecycleRestore:
    """Test SessionLifecycle restore from archive."""

    def test_restore_sets_active_status(self, db_session):
        """Test restore sets ACTIVE status."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionLifecycle.transition(session, SessionState.ACTIVE, db_session, None)
        db_session.refresh(session)

        assert session.status == "ACTIVE"

    def test_restore_clears_archived_at(self, db_session):
        """Test restore clears archived_at."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionLifecycle.transition(session, SessionState.ACTIVE, db_session, None)
        db_session.refresh(session)

        assert session.archived_at is None

    def test_restore_active_session(self, db_session):
        """Test restore on already active session."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        # ACTIVE -> ACTIVE is invalid
        with pytest.raises(ValueError):
            SessionLifecycle.transition(session, SessionState.ACTIVE, db_session, None)


class TestSessionLifecyclePermanentDelete:
    """Test SessionLifecycle permanent delete."""

    def test_permanent_delete_sets_deleted_status(self, db_session):
        """Test permanent delete sets DELETED status."""
        session = SessionFactory.create(db_session, status="ACTIVE")
        mock_vectordb = MagicMock()

        SessionLifecycle.transition(session, SessionState.DELETED, db_session, mock_vectordb)
        
        # Session is deleted from DB, so we can't refresh it.
        # We can check if it exists query
        deleted_session = db_session.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert deleted_session is None

    def test_permanent_delete_calls_vector_db_cleanup(self, db_session):
        """Test permanent delete triggers vector DB cleanup."""
        session = SessionFactory.create(db_session)
        mock_vectordb = MagicMock()

        SessionLifecycle.transition(session, SessionState.DELETED, db_session, mock_vectordb)

        # Verify VectorDBService.delete_session_collection was called
        mock_vectordb.delete_session_collection.assert_called_with(session.id, session.user_id)

    def test_permanent_delete_from_active(self, db_session):
        """Test permanent delete from ACTIVE status."""
        session = SessionFactory.create(db_session, status="ACTIVE")
        mock_vectordb = MagicMock()

        SessionLifecycle.transition(session, SessionState.DELETED, db_session, mock_vectordb)
        
        deleted_session = db_session.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert deleted_session is None

    def test_permanent_delete_from_archived(self, db_session):
        """Test permanent delete from ARCHIVED status."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        mock_vectordb = MagicMock()

        SessionLifecycle.transition(session, SessionState.DELETED, db_session, mock_vectordb)
        
        deleted_session = db_session.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert deleted_session is None


class TestSessionLifecycleTransition:
    """Test SessionLifecycle.transition method."""

    def test_transition_to_archived(self, db_session):
        """Test transitioning to ARCHIVED state."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.transition(session, SessionState.ARCHIVED, db_session, None)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"

    def test_transition_to_active(self, db_session):
        """Test transitioning to ACTIVE state."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionLifecycle.transition(session, SessionState.ACTIVE, db_session, None)
        db_session.refresh(session)

        assert session.status == "ACTIVE"

    def test_transition_invalid_raises_error(self, db_session):
        """Test that invalid transition raises an error."""
        session = SessionFactory.create(db_session, status="DELETED")

        with pytest.raises(ValueError):
            SessionLifecycle.transition(session, SessionState.ACTIVE, db_session, None)


class TestArchivalPolicy:
    """Test ArchivalPolicy auto-archival rules."""

    def test_check_inactivity_threshold_not_met(self, db_session):
        """Test inactivity check when threshold not met."""
        session = SessionFactory.create(db_session, status="ACTIVE")
        # Ensure updated_at is recent
        session.updated_at = datetime.now(timezone.utc)
        
        should_archive = ArchivalPolicy.should_auto_archive(session)

        assert should_archive is False

    def test_check_inactivity_threshold_met(self, db_session):
        """Test inactivity check when threshold is met."""
        session = SessionFactory.create(db_session, status="ACTIVE")
        # Manually set updated_at to 31 days ago
        # Note: ArchivalPolicy uses timezone-aware UTC datetime.now()
        session.updated_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.commit()
        db_session.refresh(session)

        should_archive = ArchivalPolicy.should_auto_archive(session)

        assert should_archive is True

    def test_check_retention_threshold_not_met(self, db_session):
        """Test retention check when threshold not met."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        session.archived_at = datetime.now(timezone.utc) - timedelta(days=10)

        should_delete = ArchivalPolicy.should_hard_delete(session)

        assert should_delete is False

    def test_check_retention_threshold_met(self, db_session):
        """Test retention check when threshold is met."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        # Manually set archived_at to 91 days ago
        session.archived_at = datetime.now(timezone.utc) - timedelta(days=91)
        db_session.commit()
        db_session.refresh(session)

        should_delete = ArchivalPolicy.should_hard_delete(session)

        assert should_delete is True

    def test_check_inactivity_archived_session(self, db_session):
        """Test inactivity check ignores archived sessions."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        session.updated_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.commit()
        db_session.refresh(session)

        # Should not archive already archived sessions
        should_archive = ArchivalPolicy.should_auto_archive(session)

        assert should_archive is False


class TestArchivalPolicyAutoCleanup:
    """Test ArchivalPolicy automatic cleanup."""

    def test_cleanup_old_sessions(self, db_session):
        """Test cleanup archiving old inactive sessions."""
        user, _ = UserFactory.create(db_session)
        mock_vectordb = MagicMock()
        
        # Create active session and old inactive session
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        
        old_session = SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        old_session.updated_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.commit()

        ArchivalPolicy.cleanup_job(db_session, mock_vectordb)

        db_session.refresh(old_session)
        assert old_session.status == "ARCHIVED"

    def test_cleanup_respects_retention_policy(self, db_session):
        """Test cleanup respects retention policy (hard deletes old archived sessions)."""
        user, _ = UserFactory.create(db_session)
        mock_vectordb = MagicMock()
        
        session = SessionFactory.create(db_session, user_id=user.id, status="ARCHIVED")
        session.archived_at = datetime.now(timezone.utc) - timedelta(days=91)
        db_session.commit()

        ArchivalPolicy.cleanup_job(db_session, mock_vectordb)

        # Check if session is deleted
        deleted_session = db_session.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert deleted_session is None



