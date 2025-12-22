"""
Test data factories for creating model instances.
"""
from datetime import datetime, timezone
from faker import Faker
from sqlalchemy.orm import Session

from models import User, Session as SessionModel, Document, TokenBlacklist
from auth_service import AuthService


fake = Faker()
auth_service = AuthService()


class UserFactory:
    """Factory for creating User instances."""

    @staticmethod
    def create(db: Session, email: str = None, password: str = "TestPass123!"):
        """Create a test user."""
        email = email or fake.email()
        hashed_password = auth_service.hash_password(password)

        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, password

    @staticmethod
    def create_batch(db: Session, count: int = 5):
        """Create multiple test users."""
        users = []
        for _ in range(count):
            user, _ = UserFactory.create(db)
            users.append(user)
        return users


class SessionFactory:
    """Factory for creating Session instances."""

    @staticmethod
    def create(
        db: Session,
        user_id: int = None,
        title: str = None,
        status: str = "ACTIVE",
        metadata_: dict = None,
    ):
        """Create a test session."""
        if user_id is None:
            user, _ = UserFactory.create(db)
            user_id = user.id

        session = SessionModel(
            user_id=user_id,
            title=title or f"Test Session {fake.word()}",
            status=status,
            metadata_=metadata_ or {"test": True},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def create_batch(db: Session, user_id: int = None, count: int = 5, status: str = "ACTIVE"):
        """Create multiple test sessions."""
        if user_id is None:
            user, _ = UserFactory.create(db)
            user_id = user.id

        sessions = []
        for _ in range(count):
            session = SessionFactory.create(db, user_id=user_id, status=status)
            sessions.append(session)
        return sessions


class DocumentFactory:
    """Factory for creating Document instances."""

    @staticmethod
    def create(
        db: Session,
        session_id: int = None,
        file_name: str = None,
        file_type: str = "pdf",
        file_size: int = 1024,
        chunk_count: int = 10,
    ):
        """Create a test document."""
        if session_id is None:
            session = SessionFactory.create(db)
            session_id = session.id

        document = Document(
            session_id=session_id,
            file_name=file_name or f"test_document.{file_type}",
            file_type=file_type,
            file_size=file_size,
            storage_path=f"/uploads/{fake.uuid4()}/test_document.{file_type}",
            chunk_count=chunk_count,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def create_batch(db: Session, session_id: int = None, count: int = 3):
        """Create multiple test documents."""
        if session_id is None:
            session = SessionFactory.create(db)
            session_id = session.id

        documents = []
        for i in range(count):
            file_type = ["pdf", "docx", "txt"][i % 3]
            document = DocumentFactory.create(db, session_id=session_id, file_type=file_type)
            documents.append(document)
        return documents


class TokenBlacklistFactory:
    """Factory for creating TokenBlacklist instances."""

    @staticmethod
    def create(db: Session, user_id: int = None, jti: str = None):
        """Create a blacklisted token."""
        if user_id is None:
            user, _ = UserFactory.create(db)
            user_id = user.id

        token = TokenBlacklist(
            jti=jti or fake.uuid4(),
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token
