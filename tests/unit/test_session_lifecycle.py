"""
Unit tests for session_lifecycle.py
"""
import pytest
from datetime import datetime, timedelta
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
        assert SessionLifecycle.validate_transition(
            SessionState.ACTIVE, SessionState.ARCHIVED
        ) is True

    def test_valid_transition_archived_to_active(self):
        """Test valid transition from ARCHIVED back to ACTIVE."""
        assert SessionLifecycle.validate_transition(
            SessionState.ARCHIVED, SessionState.ACTIVE
        ) is True

    def test_valid_transition_active_to_deleted(self):
        """Test valid transition from ACTIVE to DELETED."""
        assert SessionLifecycle.validate_transition(
            SessionState.ACTIVE, SessionState.DELETED
        ) is True

    def test_valid_transition_archived_to_deleted(self):
        """Test valid transition from ARCHIVED to DELETED."""
        assert SessionLifecycle.validate_transition(
            SessionState.ARCHIVED, SessionState.DELETED
        ) is True

    def test_invalid_transition_deleted_to_active(self):
        """Test invalid transition from DELETED to ACTIVE."""
        assert SessionLifecycle.validate_transition(
            SessionState.DELETED, SessionState.ACTIVE
        ) is False

    def test_invalid_transition_deleted_to_archived(self):
        """Test invalid transition from DELETED to ARCHIVED."""
        assert SessionLifecycle.validate_transition(
            SessionState.DELETED, SessionState.ARCHIVED
        ) is False

    def test_same_state_transition(self):
        """Test transition to same state."""
        assert SessionLifecycle.validate_transition(
            SessionState.ACTIVE, SessionState.ACTIVE
        ) is False


class TestSessionLifecycleSoftDelete:
    """Test SessionLifecycle soft delete (archival)."""

    def test_soft_delete_sets_archived_status(self, db_session):
        """Test soft delete sets ARCHIVED status."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.soft_delete(db_session, session.id)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"

    def test_soft_delete_sets_archived_at(self, db_session):
        """Test soft delete sets archived_at timestamp."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.soft_delete(db_session, session.id)
        db_session.refresh(session)

        assert session.archived_at is not None
        assert isinstance(session.archived_at, datetime)

    def test_soft_delete_already_archived(self, db_session):
        """Test soft delete on already archived session."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        archived_at = session.archived_at

        SessionLifecycle.soft_delete(db_session, session.id)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"
        # archived_at should remain the same (or be updated, depending on implementation)
        assert session.archived_at is not None


class TestSessionLifecycleRestore:
    """Test SessionLifecycle restore from archive."""

    def test_restore_sets_active_status(self, db_session):
        """Test restore sets ACTIVE status."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionLifecycle.restore(db_session, session.id)
        db_session.refresh(session)

        assert session.status == "ACTIVE"

    def test_restore_clears_archived_at(self, db_session):
        """Test restore clears archived_at."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionLifecycle.restore(db_session, session.id)
        db_session.refresh(session)

        assert session.archived_at is None

    def test_restore_active_session(self, db_session):
        """Test restore on already active session."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.restore(db_session, session.id)
        db_session.refresh(session)

        assert session.status == "ACTIVE"


class TestSessionLifecyclePermanentDelete:
    """Test SessionLifecycle permanent delete."""

    def test_permanent_delete_sets_deleted_status(self, db_session):
        """Test permanent delete sets DELETED status."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        with patch("session_lifecycle.VectorDBService") as mock_vector_db:
            SessionLifecycle.permanent_delete(db_session, session.id)
            db_session.refresh(session)

            assert session.status == "DELETED"

    def test_permanent_delete_calls_vector_db_cleanup(self, db_session):
        """Test permanent delete triggers vector DB cleanup."""
        session = SessionFactory.create(db_session)

        with patch("session_lifecycle.VectorDBService") as mock_vector_db:
            SessionLifecycle.permanent_delete(db_session, session.id)

            # Verify VectorDBService.delete_session_collection was called
            mock_vector_db.delete_session_collection.assert_called()

    def test_permanent_delete_from_active(self, db_session):
        """Test permanent delete from ACTIVE status."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        with patch("session_lifecycle.VectorDBService"):
            SessionLifecycle.permanent_delete(db_session, session.id)
            db_session.refresh(session)

            assert session.status == "DELETED"

    def test_permanent_delete_from_archived(self, db_session):
        """Test permanent delete from ARCHIVED status."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        with patch("session_lifecycle.VectorDBService"):
            SessionLifecycle.permanent_delete(db_session, session.id)
            db_session.refresh(session)

            assert session.status == "DELETED"


class TestSessionLifecycleTransition:
    """Test SessionLifecycle.transition method."""

    def test_transition_to_archived(self, db_session):
        """Test transitioning to ARCHIVED state."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        SessionLifecycle.transition(db_session, session.id, SessionState.ARCHIVED)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"

    def test_transition_to_active(self, db_session):
        """Test transitioning to ACTIVE state."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionLifecycle.transition(db_session, session.id, SessionState.ACTIVE)
        db_session.refresh(session)

        assert session.status == "ACTIVE"

    def test_transition_invalid_raises_error(self, db_session):
        """Test that invalid transition raises an error."""
        session = SessionFactory.create(db_session, status="DELETED")

        with pytest.raises(ValueError):
            SessionLifecycle.transition(db_session, session.id, SessionState.ACTIVE)


class TestArchivalPolicy:
    """Test ArchivalPolicy auto-archival rules."""

    def test_check_inactivity_threshold_not_met(self, db_session):
        """Test inactivity check when threshold not met."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        should_archive = ArchivalPolicy.check_inactivity(
            session, inactivity_days=30
        )

        assert should_archive is False

    def test_check_inactivity_threshold_met(self, db_session):
        """Test inactivity check when threshold is met."""
        session = SessionFactory.create(db_session, status="ACTIVE")
        # Manually set updated_at to 31 days ago
        session.updated_at = datetime.utcnow() - timedelta(days=31)
        db_session.commit()
        db_session.refresh(session)

        should_archive = ArchivalPolicy.check_inactivity(
            session, inactivity_days=30
        )

        assert should_archive is True

    def test_check_retention_threshold_not_met(self, db_session):
        """Test retention check when threshold not met."""
        session = SessionFactory.create(db_session, status="ACTIVE")

        should_archive = ArchivalPolicy.check_retention(
            session, retention_days=90
        )

        assert should_archive is False

    def test_check_retention_threshold_met(self, db_session):
        """Test retention check when threshold is met."""
        session = SessionFactory.create(db_session, status="ACTIVE")
        # Manually set created_at to 91 days ago
        session.created_at = datetime.utcnow() - timedelta(days=91)
        db_session.commit()
        db_session.refresh(session)

        should_archive = ArchivalPolicy.check_retention(
            session, retention_days=90
        )

        assert should_archive is True

    def test_check_inactivity_archived_session(self, db_session):
        """Test inactivity check ignores archived sessions."""
        session = SessionFactory.create(db_session, status="ARCHIVED")
        session.updated_at = datetime.utcnow() - timedelta(days=31)
        db_session.commit()
        db_session.refresh(session)

        # Should not archive already archived sessions
        should_archive = ArchivalPolicy.check_inactivity(
            session, inactivity_days=30
        )

        assert should_archive is False


class TestArchivalPolicyAutoCleanup:
    """Test ArchivalPolicy automatic cleanup."""

    def test_cleanup_old_sessions(self, db_session):
        """Test cleanup archiving old inactive sessions."""
        user, _ = UserFactory.create(db_session)
        
        # Create active session and old inactive session
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        
        old_session = SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        old_session.updated_at = datetime.utcnow() - timedelta(days=31)
        db_session.commit()

        ArchivalPolicy.cleanup_old_sessions(
            db_session, inactivity_days=30
        )

        db_session.refresh(old_session)
        assert old_session.status == "ARCHIVED"

    def test_cleanup_respects_retention_policy(self, db_session):
        """Test cleanup respects retention policy."""
        user, _ = UserFactory.create(db_session)
        
        session = SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        session.created_at = datetime.utcnow() - timedelta(days=91)
        db_session.commit()

        ArchivalPolicy.cleanup_old_sessions(
            db_session, retention_days=90
        )

        db_session.refresh(session)
        assert session.status == "ARCHIVED"


class TestSessionLifecycleEdgeCases:
    """Test edge cases and error handling."""

    def test_transition_nonexistent_session(self, db_session):
        """Test transitioning nonexistent session."""
        # Should not raise error, just no-op
        SessionLifecycle.transition(db_session, 99999, SessionState.ARCHIVED)

    def test_soft_delete_nonexistent_session(self, db_session):
        """Test soft delete of nonexistent session."""
        # Should not raise error, just no-op
        SessionLifecycle.soft_delete(db_session, 99999)

    def test_restore_nonexistent_session(self, db_session):
        """Test restore of nonexistent session."""
        # Should not raise error, just no-op
        SessionLifecycle.restore(db_session, 99999)

    def test_permanent_delete_nonexistent_session(self, db_session):
        """Test permanent delete of nonexistent session."""
        with patch("session_lifecycle.VectorDBService"):
            # Should not raise error, just no-op
            SessionLifecycle.permanent_delete(db_session, 99999)
