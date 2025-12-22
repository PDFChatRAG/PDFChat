"""
Unit tests for sessionManager.py
"""
import pytest
from sqlalchemy.orm import Session as DBSession

from sessionManager import SessionManager
from models import Session as SessionModel, Document
from tests.fixtures.factories import UserFactory, SessionFactory, DocumentFactory


class TestSessionManagerCreate:
    """Test SessionManager.create_session."""

    def test_create_session_basic(self, db_session):
        """Test creating a basic session."""
        user, _ = UserFactory.create(db_session)
        title = "My Test Session"

        session = SessionManager.create_session(db_session, user.id, title)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.title == title
        assert session.status == "ACTIVE"

    def test_create_session_with_metadata(self, db_session):
        """Test creating session with metadata."""
        user, _ = UserFactory.create(db_session)
        metadata = {"model": "gemini-3-flash", "language": "en"}

        session = SessionManager.create_session(
            db_session, user.id, "Test", metadata=metadata
        )

        assert session.metadata_ == metadata

    def test_create_multiple_sessions_same_user(self, db_session):
        """Test creating multiple sessions for same user."""
        user, _ = UserFactory.create(db_session)

        session1 = SessionManager.create_session(db_session, user.id, "Session 1")
        session2 = SessionManager.create_session(db_session, user.id, "Session 2")

        assert session1.id != session2.id
        assert session1.user_id == session2.user_id


class TestSessionManagerRetrieve:
    """Test SessionManager.get_session."""

    def test_get_session_success(self, db_session):
        """Test retrieving an existing session."""
        session = SessionFactory.create(db_session)

        retrieved = SessionManager.get_session(db_session, session.id, session.user_id)

        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_session_wrong_user(self, db_session):
        """Test retrieving session with wrong user_id."""
        session = SessionFactory.create(db_session)
        wrong_user, _ = UserFactory.create(db_session)

        retrieved = SessionManager.get_session(db_session, session.id, wrong_user.id)

        assert retrieved is None

    def test_get_session_nonexistent(self, db_session):
        """Test retrieving nonexistent session."""
        user, _ = UserFactory.create(db_session)

        retrieved = SessionManager.get_session(db_session, 99999, user.id)

        assert retrieved is None


class TestSessionManagerList:
    """Test SessionManager.list_sessions."""

    def test_list_all_sessions(self, db_session):
        """Test listing all sessions for a user."""
        user, _ = UserFactory.create(db_session)
        SessionFactory.create_batch(db_session, user_id=user.id, count=3)

        sessions = SessionManager.list_sessions(db_session, user.id)

        assert len(sessions) == 3

    def test_list_sessions_filter_by_status(self, db_session):
        """Test listing sessions filtered by status."""
        user, _ = UserFactory.create(db_session)
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        SessionFactory.create(db_session, user_id=user.id, status="ARCHIVED")

        active_sessions = SessionManager.list_sessions(
            db_session, user.id, status="ACTIVE"
        )

        assert len(active_sessions) == 2
        assert all(s.status == "ACTIVE" for s in active_sessions)

    def test_list_sessions_empty(self, db_session):
        """Test listing sessions when user has none."""
        user, _ = UserFactory.create(db_session)

        sessions = SessionManager.list_sessions(db_session, user.id)

        assert len(sessions) == 0

    def test_list_sessions_different_users(self, db_session):
        """Test that sessions are isolated per user."""
        user1, _ = UserFactory.create(db_session)
        user2, _ = UserFactory.create(db_session)

        SessionFactory.create(db_session, user_id=user1.id)
        SessionFactory.create(db_session, user_id=user2.id)

        user1_sessions = SessionManager.list_sessions(db_session, user1.id)
        user2_sessions = SessionManager.list_sessions(db_session, user2.id)

        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1


class TestSessionManagerDocuments:
    """Test SessionManager document operations."""

    def test_get_session_documents(self, db_session):
        """Test getting documents in a session."""
        session = SessionFactory.create(db_session)
        DocumentFactory.create_batch(db_session, session_id=session.id, count=3)

        documents = SessionManager.get_session_documents(db_session, session.id)

        assert len(documents) == 3

    def test_get_session_documents_empty(self, db_session):
        """Test getting documents when session has none."""
        session = SessionFactory.create(db_session)

        documents = SessionManager.get_session_documents(db_session, session.id)

        assert len(documents) == 0

    def test_add_document_to_session(self, db_session):
        """Test adding document metadata to session."""
        session = SessionFactory.create(db_session)

        doc = SessionManager.add_document_to_session(
            db_session,
            session.id,
            "test.pdf",
            "pdf",
            1024,
            "/uploads/test.pdf",
            10,
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

        SessionManager.track_session_activity(db_session, session.id)
        db_session.refresh(session)

        assert session.updated_at > old_updated_at


class TestSessionManagerDelete:
    """Test SessionManager deletion operations."""

    def test_soft_delete_session(self, db_session):
        """Test soft deleting (archiving) a session."""
        session = SessionFactory.create(db_session)

        SessionManager.soft_delete_session(db_session, session.id)
        db_session.refresh(session)

        assert session.status == "ARCHIVED"
        assert session.archived_at is not None

    def test_restore_session(self, db_session):
        """Test restoring an archived session."""
        session = SessionFactory.create(db_session, status="ARCHIVED")

        SessionManager.restore_session(db_session, session.id)
        db_session.refresh(session)

        assert session.status == "ACTIVE"
        assert session.archived_at is None

    def test_hard_delete_session(self, db_session):
        """Test hard deleting (permanent) a session."""
        session = SessionFactory.create(db_session)
        session_id = session.id
        user_id = session.user_id

        SessionManager.hard_delete_session(db_session, session_id, user_id)

        deleted = SessionManager.get_session(db_session, session_id, user_id)
        assert deleted is None

    def test_hard_delete_also_deletes_documents(self, db_session):
        """Test hard delete also removes associated documents."""
        session = SessionFactory.create(db_session)
        DocumentFactory.create_batch(db_session, session_id=session.id, count=2)

        SessionManager.hard_delete_session(db_session, session.id, session.user_id)

        documents = db_session.query(Document).filter(
            Document.session_id == session.id
        ).all()
        assert len(documents) == 0


class TestSessionManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_create_session_invalid_user(self, db_session):
        """Test creating session for non-existent user."""
        # This should not raise an error, just creates the record
        session = SessionManager.create_session(db_session, 99999, "Test")
        assert session.user_id == 99999

    def test_list_sessions_with_many_records(self, db_session):
        """Test listing sessions with many records."""
        user, _ = UserFactory.create(db_session)
        SessionFactory.create_batch(db_session, user_id=user.id, count=100)

        sessions = SessionManager.list_sessions(db_session, user.id)

        assert len(sessions) == 100

    def test_track_activity_multiple_times(self, db_session):
        """Test tracking activity multiple times."""
        session = SessionFactory.create(db_session)

        SessionManager.track_session_activity(db_session, session.id)
        db_session.refresh(session)
        first_update = session.updated_at

        SessionManager.track_session_activity(db_session, session.id)
        db_session.refresh(session)
        second_update = session.updated_at

        assert second_update >= first_update
