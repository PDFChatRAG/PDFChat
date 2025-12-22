"""
Session management with SQLAlchemy backend.

Handles creation, retrieval, and management of user sessions with proper
ownership verification and lifecycle tracking.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SQLSession
from models import Session, User, Document
from session_lifecycle import SessionLifecycle, SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    """Manager for session CRUD operations and ownership verification."""

    @staticmethod
    def create_session(
        user_id: str,
        db: SQLSession,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Session:
        """
        Create new session for user.

        Args:
            user_id: User identifier
            db: SQLAlchemy database session
            title: Optional session title
            metadata: Optional custom metadata dict

        Returns:
            Created Session model instance
        """
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        session = Session(
            user_id=user_id,
            title=title or f"Session {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            status=SessionState.ACTIVE,
            metadata_=metadata or {},
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    @staticmethod
    def get_session(session_id: str, user_id: str, db: SQLSession) -> Optional[Session]:
        """
        Retrieve session with ownership verification.

        Args:
            session_id: Session identifier
            user_id: User identifier (for ownership check)
            db: SQLAlchemy database session

        Returns:
            Session model instance if found and owned by user, None otherwise
        """
        session = (
            db.query(Session)
            .filter(Session.id == session_id, Session.user_id == user_id)
            .first()
        )
        return session

    @staticmethod
    def list_user_sessions(
        user_id: str,
        db: SQLSession,
        status: Optional[SessionState] = None,
        limit: int = 100,
    ) -> List[Session]:
        """
        List all sessions for user.

        Args:
            user_id: User identifier
            db: SQLAlchemy database session
            status: Optional filter by session status
            limit: Maximum number of sessions to return

        Returns:
            List of Session model instances
        """
        query = db.query(Session).filter(Session.user_id == user_id)

        if status:
            query = query.filter(Session.status == status)

        # Order by most recently updated
        sessions = query.order_by(Session.updated_at.desc()).limit(limit).all()

        return sessions

    @staticmethod
    def get_session_documents(
        session_id: str, user_id: str, db: SQLSession
    ) -> List[Document]:
        """
        Get all documents in a session.

        Args:
            session_id: Session identifier
            user_id: User identifier (for ownership check)
            db: SQLAlchemy database session

        Returns:
            List of Document model instances
        """
        session = SessionManager.get_session(session_id, user_id, db)
        if not session:
            return []

        documents = db.query(Document).filter(Document.session_id == session_id).all()
        return documents

    @staticmethod
    def add_document_to_session(
        session_id: str,
        user_id: str,
        file_name: str,
        file_size: int,
        file_type: str,
        chunk_count: int,
        db: SQLSession,
        storage_path: Optional[str] = None,
    ) -> Document:
        """
        Add document metadata to session.

        Args:
            session_id: Session identifier
            user_id: User identifier (for ownership check)
            file_name: Original file name
            file_size: File size in bytes
            file_type: File type (pdf, docx, txt, etc.)
            chunk_count: Number of chunks created from document
            db: SQLAlchemy database session
            storage_path: Optional path to temporary storage

        Returns:
            Created Document model instance

        Raises:
            ValueError: If session not found or not owned by user
        """
        session = SessionManager.get_session(session_id, user_id, db)
        if not session:
            raise ValueError(f"Session {session_id} not found or not owned by user")

        document = Document(
            session_id=session_id,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            chunk_count=chunk_count,
            storage_path=storage_path,
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(f"Added document {file_name} to session {session_id}")
        return document

    @staticmethod
    def update_session_timestamp(session_id: str, user_id: str, db: SQLSession):
        """
        Update session's updated_at timestamp (for activity tracking).

        Args:
            session_id: Session identifier
            user_id: User identifier
            db: SQLAlchemy database session
        """
        session = SessionManager.get_session(session_id, user_id, db)
        if session:
            session.updated_at = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def archive_session(
        session_id: str, user_id: str, db: SQLSession
    ) -> Optional[Session]:
        """
        Archive session (soft delete).

        Args:
            session_id: Session identifier
            user_id: User identifier
            db: SQLAlchemy database session

        Returns:
            Updated Session model instance or None if not found

        Raises:
            ValueError: If transition is invalid
        """
        session = SessionManager.get_session(session_id, user_id, db)
        if not session:
            return None

        try:
            SessionLifecycle.transition(session, SessionState.ARCHIVED, db, None)
            return session
        except ValueError as e:
            logger.error(f"Error archiving session {session_id}: {e}")
            raise

    @staticmethod
    def reactivate_session(
        session_id: str, user_id: str, db: SQLSession
    ) -> Optional[Session]:
        """
        Reactivate archived session.

        Args:
            session_id: Session identifier
            user_id: User identifier
            db: SQLAlchemy database session

        Returns:
            Updated Session model instance or None if not found

        Raises:
            ValueError: If transition is invalid
        """
        session = SessionManager.get_session(session_id, user_id, db)
        if not session:
            return None

        try:
            SessionLifecycle.transition(session, SessionState.ACTIVE, db, None)
            return session
        except ValueError as e:
            logger.error(f"Error reactivating session {session_id}: {e}")
            raise

    @staticmethod
    def delete_session(
        session_id: str,
        user_id: str,
        db: SQLSession,
        vectordb_service,
    ) -> bool:
        """
        Hard delete session (permanent deletion).

        Args:
            session_id: Session identifier
            user_id: User identifier
            db: SQLAlchemy database session
            vectordb_service: VectorDB service for collection cleanup

        Returns:
            True if deletion successful, False if session not found

        Raises:
            ValueError: If transition is invalid
        """
        session = SessionManager.get_session(session_id, user_id, db)
        if not session:
            return False

        try:
            SessionLifecycle.transition(
                session, SessionState.DELETED, db, vectordb_service
            )
            return True
        except ValueError as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            raise
