"""Database models for PDFChat multi-tenant, multi-session architecture."""

import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, JSON, Index
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    is_guest = Column(Integer, default=0, nullable=False)  # 0 = registered, 1 = guest
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    auth_sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class SessionStatus(str, enum.Enum):

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class Session(Base):

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_status", "user_id", "status"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(
        Enum(SessionStatus),
        default=SessionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata storage for custom session data
    metadata_ = Column(JSON, default=dict, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")
    documents = relationship(
        "Document", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Document(Base):

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_session", "session_id"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Bytes
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc.
    storage_path = Column(String(500), nullable=True)  # Temp storage path
    chunk_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    session = relationship("Session", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, file_name={self.file_name})>"


class AuthSession(Base):

    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user", "user_id"),)

    token = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chat_session_id = Column(String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", back_populates="auth_sessions")
    chat_session = relationship("Session")

    def __repr__(self):
        return f"<AuthSession(token={self.token}, user_id={self.user_id})>"


class VerificationCode(Base):
    """Verification codes for password reset and email verification."""

    __tablename__ = "verification_codes"
    __table_args__ = (Index("ix_verification_codes_user", "user_id"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=False, index=True)
    purpose = Column(String(50), nullable=False)  # 'password_reset', 'email_verify'
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Integer, default=0)  # 0 = not used, 1 = used
    attempts = Column(Integer, default=0)  # Rate limiting
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<VerificationCode(id={self.id}, user_id={self.user_id}, purpose={self.purpose})>"
