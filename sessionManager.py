import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SQLSession
from models import Session, User, Document
from session_lifecycle import SessionLifecycle, SessionState

logger = logging.getLogger(__name__)


class SessionManager:

    @staticmethod
    def create_session(
        user_id: str,
        db: SQLSession,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Session:

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
 
        session = SessionManager.get_session(session_id, user_id, db)
        if session:
            session.updated_at = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def archive_session(
        session_id: str, user_id: str, db: SQLSession
    ) -> Optional[Session]:

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
