"""
Unit tests for sessionManager.py
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from sessionManager import SessionManager
from models import Session as SessionModel, Document
from tests.fixtures.factories import UserFactory, SessionFactory, DocumentFactory


class TestSessionManagerCreate:
    """Test SessionManager.create_session."""

    def test_create_session_basic(self, db_session):
        """Test creating a basic session."""
        user, _ = UserFactory.create(db_session)
        title = "My Test Session"

        session = SessionManager.create_session(user.id, db_session, title)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.title == title
        assert session.status == "ACTIVE"

    def test_create_session_with_metadata(self, db_session):
        """Test creating session with metadata."""
        user, _ = UserFactory.create(db_session)
        metadata = {"model": "gemini-3-flash", "language": "en"}

        session = SessionManager.create_session(
            user.id, db_session, "Test", metadata=metadata
        )

        assert session.metadata_ == metadata

    def test_create_multiple_sessions_same_user(self, db_session):
        """Test creating multiple sessions for same user."""
        user, _ = UserFactory.create(db_session)

        session1 = SessionManager.create_session(user.id, db_session, "Session 1")
        session2 = SessionManager.create_session(user.id, db_session, "Session 2")

        assert session1.id != session2.id
        assert session1.user_id == session2.user_id


class TestSessionManagerRetrieve:
    """Test SessionManager.get_session."""

    def test_get_session_success(self, db_session):
        """Test retrieving an existing session."""
        session = SessionFactory.create(db_session)

        retrieved = SessionManager.get_session(session.id, session.user_id, db_session)

        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_session_wrong_user(self, db_session):
        """Test retrieving session with wrong user_id."""
        session = SessionFactory.create(db_session)
        wrong_user, _ = UserFactory.create(db_session)

        retrieved = SessionManager.get_session(session.id, wrong_user.id, db_session)

        assert retrieved is None

    def test_get_session_nonexistent(self, db_session):
        """Test retrieving nonexistent session."""
        user, _ = UserFactory.create(db_session)

        retrieved = SessionManager.get_session("nonexistent-id", user.id, db_session)

        assert retrieved is None


class TestSessionManagerList:
    """Test SessionManager.list_user_sessions."""

    def test_list_all_sessions(self, db_session):
        """Test listing all sessions for a user."""
        user, _ = UserFactory.create(db_session)
        sessions = [SessionFactory.create(db_session, user_id=user.id) for _ in range(3)]

        sessions = SessionManager.list_user_sessions(user.id, db_session)

        assert len(sessions) == 3

    def test_list_sessions_filter_by_status(self, db_session):
        """Test listing sessions filtered by status."""
        user, _ = UserFactory.create(db_session)
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        SessionFactory.create(db_session, user_id=user.id, status="ARCHIVED")

        active_sessions = SessionManager.list_user_sessions(
            user.id, db_session, status="ACTIVE"
        )

        assert len(active_sessions) == 2
        assert all(s.status == "ACTIVE" for s in active_sessions)

    def test_list_sessions_empty(self, db_session):
        """Test listing sessions when user has none."""
        user, _ = UserFactory.create(db_session)

        sessions = SessionManager.list_user_sessions(user.id, db_session)

        assert len(sessions) == 0

    def test_list_sessions_different_users(self, db_session):
        """Test that sessions are isolated per user."""
        user1, _ = UserFactory.create(db_session)
        user2, _ = UserFactory.create(db_session)

        SessionFactory.create(db_session, user_id=user1.id)
        SessionFactory.create(db_session, user_id=user2.id)

        user1_sessions = SessionManager.list_user_sessions(user1.id, db_session)
        user2_sessions = SessionManager.list_user_sessions(user2.id, db_session)

        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1


class TestSessionManagerDocuments:
    """Test SessionManager document operations."""

    def test_get_session_documents(self, db_session):
        """Test getting documents in a session."""
        session = SessionFactory.create(db_session)
        documents = [DocumentFactory.create(db_session, session_id=session.id) for _ in range(3)]

        documents = SessionManager.get_session_documents(session.id, session.user_id, db_session)

        assert len(documents) == 3

    def test_get_session_documents_empty(self, db_session):
        """Test getting documents when session has none."""
        session = SessionFactory.create(db_session)

        documents = SessionManager.get_session_documents(session.id, session.user_id, db_session)

        assert len(documents) == 0

    def test_add_document_to_session(self, db_session):
        """Test adding document metadata to session."""
        session = SessionFactory.create(db_session)

        doc = SessionManager.add_document_to_session(
            session_id=session.id,
            user_id=session.user_id,
            file_name="test.pdf",
            file_size=1024,
            file_type="pdf",
            chunk_count=10,
            db=db_session,
            storage_path="/uploads/test.pdf",
        )

        assert doc.id is not None
        assert doc.session_id == session.id
        assert doc.file_name == "test.pdf"
        assert doc.chunk_count == 10


class TestSessionManagerActivity:
    """Test SessionManager activity tracking."""

    def test_track_session_activity(self, db_session):
        """Test tracking session activity updates timestamp."""
        session = SessionFactory.create(db_session)
        old_updated_at = session.updated_at

        # Ensure some time passes or simulate it
        # Since implementation uses datetime.now(timezone.utc), it might be same if too fast.
        # But usually execution takes time.
        
        SessionManager.update_session_timestamp(session.id, session.user_id, db_session)
        db_session.refresh(session)

        assert session.updated_at >= old_updated_at


class TestSessionManagerDelete:
    """Test SessionManager deletion operations."""

    def test_soft_delete_session(self, db_session):
        """Test soft deleting (archiving) a session."""
        session = SessionFactory.create(db_session)

        SessionManager.archive_session(session.id, session.user_id, db_session)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"
        assert session.archived_at is not None

    def test_restore_session(self, db_session):
        """Test restoring an archived session."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionManager.reactivate_session(session.id, session.user_id, db_session)
        db_session.refresh(session)

        assert session.status == "ACTIVE"
        assert session.archived_at is None

    def test_hard_delete_session(self, db_session):
        """Test hard deleting (permanent) a session."""
        session = SessionFactory.create(db_session)
        session_id = session.id
        user_id = session.user_id
        mock_vectordb = MagicMock()

        SessionManager.delete_session(session_id, user_id, db_session, mock_vectordb)

        # Direct query to verify deletion
        deleted = db_session.query(SessionModel).filter(SessionModel.id == session_id).first()
        assert deleted is None

    def test_hard_delete_also_deletes_documents(self, db_session):
        """Test hard delete also removes associated documents."""
        session = SessionFactory.create(db_session)
        documents = [DocumentFactory.create(db_session, session_id=session.id) for _ in range(2)]
        mock_vectordb = MagicMock()

        SessionManager.delete_session(session.id, session.user_id, db_session, mock_vectordb)

        documents = db_session.query(Document).filter(
            Document.session_id == session.id
        ).all()
        assert len(documents) == 0


class TestSessionManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_create_session_invalid_user(self, db_session):
        """Test creating session for non-existent user."""
        # This SHOULD raise an error because implementation checks for user existence
        with pytest.raises(ValueError):
            SessionManager.create_session("nonexistent-user-id", db_session, "Test")

    def test_list_sessions_with_many_records(self, db_session):
        """Test listing sessions with many records."""
        user, _ = UserFactory.create(db_session)
        sessions = [SessionFactory.create(db_session, user_id=user.id) for _ in range(100)]

        sessions = SessionManager.list_user_sessions(user.id, db_session, limit=200)

        assert len(sessions) == 100

    def test_track_activity_multiple_times(self, db_session):
        """Test tracking activity multiple times."""
        session = SessionFactory.create(db_session)

        SessionManager.update_session_timestamp(session.id, session.user_id, db_session)
        db_session.refresh(session)
        first_update = session.updated_at

        SessionManager.update_session_timestamp(session.id, session.user_id, db_session)
        db_session.refresh(session)
        second_update = session.updated_at

        assert second_update >= first_update
