"""
Unit tests for models.py and database interactions.
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from models import User, Session as SessionModel, Document, TokenBlacklist, SessionStatus
from tests.fixtures.factories import UserFactory, SessionFactory, DocumentFactory, TokenBlacklistFactory


class TestUserModel:
    """Test User model."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        user = User(email="test@example.com", hashed_password="hashed_pass")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_pass"
        assert user.created_at is not None

    def test_user_email_unique(self, db_session):
        """Test that email must be unique."""
        email = "unique@example.com"
        user1 = User(email=email, hashed_password="pass1")
        user2 = User(email=email, hashed_password="pass2")

        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_user_relationships(self, db_session):
        """Test User relationships."""
        user, _ = UserFactory.create(db_session)
        session = SessionFactory.create(db_session, user_id=user.id)

        db_session.refresh(user)
        assert len(user.sessions) == 1
        assert user.sessions[0].id == session.id

    def test_user_cascade_delete(self, db_session):
        """Test cascade delete when user is deleted."""
        user, _ = UserFactory.create(db_session)
        session = SessionFactory.create(db_session, user_id=user.id)
        session_id = session.id

        db_session.delete(user)
        db_session.commit()

        deleted_session = db_session.query(SessionModel).filter(SessionModel.id == session_id).first()
        assert deleted_session is None


class TestSessionModel:
    """Test Session model."""

    def test_create_session(self, db_session, test_user):
        """Test creating a session."""
        session = SessionModel(
            user_id=test_user["user"].id,
            title="Test Session",
            status="ACTIVE",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == test_user["user"].id
        assert session.title == "Test Session"
        assert session.status == "ACTIVE"

    def test_session_default_status(self, db_session, test_user):
        """Test session default status is ACTIVE."""
        session = SessionModel(
            user_id=test_user["user"].id,
            title="Test Session",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.status == "ACTIVE"

    def test_session_metadata(self, db_session, test_user):
        """Test session metadata storage."""
        metadata = {"key1": "value1", "key2": 123}
        session = SessionModel(
            user_id=test_user["user"].id,
            title="Test Session",
            metadata_=metadata,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.metadata_ == metadata

    def test_session_timestamps(self, db_session, test_user):
        """Test session timestamps."""
        session = SessionModel(
            user_id=test_user["user"].id,
            title="Test Session",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.created_at is not None
        assert session.updated_at is not None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_session_archived_at_null_by_default(self, db_session, test_user):
        """Test archived_at is null by default."""
        session = SessionModel(
            user_id=test_user["user"].id,
            title="Test Session",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.archived_at is None

    def test_session_status_enum(self, db_session, test_user):
        """Test session status enum values."""
        session_active = SessionModel(
            user_id=test_user["user"].id,
            title="Active",
            status="ACTIVE",
        )
        session_archived = SessionModel(
            user_id=test_user["user"].id,
            title="Archived",
            status="ARCHIVED",
        )
        session_deleted = SessionModel(
            user_id=test_user["user"].id,
            title="Deleted",
            status="DELETED",
        )

        db_session.add_all([session_active, session_archived, session_deleted])
        db_session.commit()

        assert session_active.status == "ACTIVE"
        assert session_archived.status == "ARCHIVED"
        assert session_deleted.status == "DELETED"


class TestDocumentModel:
    """Test Document model."""

    def test_create_document(self, db_session):
        """Test creating a document."""
        session = SessionFactory.create(db_session)
        document = Document(
            session_id=session.id,
            file_name="test.pdf",
            file_type="pdf",
            file_size=1024,
            storage_path="/uploads/test.pdf",
            chunk_count=5,
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)

        assert document.id is not None
        assert document.session_id == session.id
        assert document.file_name == "test.pdf"
        assert document.file_type == "pdf"
        assert document.chunk_count == 5

    def test_document_timestamps(self, db_session):
        """Test document timestamps."""
        document = DocumentFactory.create(db_session)
        db_session.refresh(document)

        assert document.created_at is not None
        assert isinstance(document.created_at, datetime)

    def test_document_foreign_key(self, db_session):
        """Test document foreign key to session."""
        session = SessionFactory.create(db_session)
        document = DocumentFactory.create(db_session, session_id=session.id)

        retrieved_doc = db_session.query(Document).filter(Document.id == document.id).first()
        assert retrieved_doc.session_id == session.id

    def test_document_cascade_delete(self, db_session):
        """Test cascade delete when session is deleted."""
        session = SessionFactory.create(db_session)
        document = DocumentFactory.create(db_session, session_id=session.id)
        document_id = document.id

        db_session.delete(session)
        db_session.commit()

        deleted_doc = db_session.query(Document).filter(Document.id == document_id).first()
        assert deleted_doc is None

    def test_document_multiple_file_types(self, db_session):
        """Test documents with different file types."""
        session = SessionFactory.create(db_session)
        pdf_doc = DocumentFactory.create(db_session, session_id=session.id, file_type="pdf")
        docx_doc = DocumentFactory.create(db_session, session_id=session.id, file_type="docx")
        txt_doc = DocumentFactory.create(db_session, session_id=session.id, file_type="txt")

        db_session.refresh(session)
        assert len(session.documents) == 3
        assert any(d.file_type == "pdf" for d in session.documents)
        assert any(d.file_type == "docx" for d in session.documents)
        assert any(d.file_type == "txt" for d in session.documents)


class TestTokenBlacklistModel:
    """Test TokenBlacklist model."""

    def test_create_token_blacklist(self, db_session):
        """Test creating a token blacklist entry."""
        user, _ = UserFactory.create(db_session)
        token = TokenBlacklist(
            jti="jti-123",
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)

        assert token.id is not None
        assert token.jti == "jti-123"
        assert token.user_id == user.id

    def test_token_blacklist_foreign_key(self, db_session):
        """Test token blacklist foreign key to user."""
        user, _ = UserFactory.create(db_session)
        token = TokenBlacklistFactory.create(db_session, user_id=user.id)

        retrieved_token = db_session.query(TokenBlacklist).filter(TokenBlacklist.id == token.id).first()
        assert retrieved_token.user_id == user.id

    def test_token_blacklist_cascade_delete(self, db_session):
        """Test cascade delete when user is deleted."""
        user, _ = UserFactory.create(db_session)
        token = TokenBlacklistFactory.create(db_session, user_id=user.id)
        token_id = token.id

        db_session.delete(user)
        db_session.commit()

        deleted_token = db_session.query(TokenBlacklist).filter(TokenBlacklist.id == token_id).first()
        assert deleted_token is None

    def test_token_blacklist_jti_unique(self, db_session):
        """Test that JTI should be unique."""
        user, _ = UserFactory.create(db_session)
        jti = "unique-jti-456"
        token1 = TokenBlacklist(
            jti=jti,
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
        )
        token2 = TokenBlacklist(
            jti=jti,
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
        )

        db_session.add(token1)
        db_session.commit()

        db_session.add(token2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestDatabaseRelationships:
    """Test complex database relationships."""

    def test_user_has_multiple_sessions(self, db_session):
        """Test user can have multiple sessions."""
        user, _ = UserFactory.create(db_session)
        sessions = SessionFactory.create_batch(db_session, user_id=user.id, count=5)

        db_session.refresh(user)
        assert len(user.sessions) == 5

    def test_session_has_multiple_documents(self, db_session):
        """Test session can have multiple documents."""
        session = SessionFactory.create(db_session)
        documents = DocumentFactory.create_batch(db_session, session_id=session.id, count=3)

        db_session.refresh(session)
        assert len(session.documents) == 3

    def test_query_sessions_by_status(self, db_session):
        """Test querying sessions by status."""
        user, _ = UserFactory.create(db_session)
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        SessionFactory.create(db_session, user_id=user.id, status="ACTIVE")
        SessionFactory.create(db_session, user_id=user.id, status="ARCHIVED")

        active_sessions = db_session.query(SessionModel).filter(
            SessionModel.user_id == user.id,
            SessionModel.status == "ACTIVE"
        ).all()

        assert len(active_sessions) == 2

    def test_query_documents_by_session(self, db_session):
        """Test querying documents by session."""
        session = SessionFactory.create(db_session)
        documents = DocumentFactory.create_batch(db_session, session_id=session.id, count=2)

        queried_docs = db_session.query(Document).filter(Document.session_id == session.id).all()
        assert len(queried_docs) == 2
