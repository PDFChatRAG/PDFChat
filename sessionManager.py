import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SQLSession
from models import Session, User, Document
from session_lifecycle import SessionLifecycle, SessionState

logger = logging.getLogger(__name__)


class SessionManager:

    @staticmethod
    def _archive_other_active_sessions(user_id: str, db: SQLSession, except_session_id: Optional[str] = None):
        query = db.query(Session).filter(
            Session.user_id == user_id, 
            Session.status == SessionState.ACTIVE
        )
        if except_session_id:
            query = query.filter(Session.id != except_session_id)
            
        active_sessions = query.all()
        for session in active_sessions:
            logger.info(f"Auto-archiving session {session.id} because a new session became active.")
            SessionLifecycle.transition(session, SessionState.ARCHIVED, db, None)

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

        # Archive other active sessions
        SessionManager._archive_other_active_sessions(user_id, db)

        session = Session(
            user_id=user_id,
            title=title or "New Conversation",
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
    def get_or_create_empty_session(
        user_id: str,
        db: SQLSession,
        checkpointer,
        vectordb_service
    ) -> Session:

        # Find all active sessions
        active_sessions = SessionManager.list_user_sessions(user_id, db, SessionState.ACTIVE)
        
        empty_sessions = []
        non_empty_sessions = []
        
        # Identify empty sessions
        from utils.conversation_helper import get_session_conversation
        
        for session in active_sessions:
            # Check for documents
            has_docs = db.query(Document).filter(Document.session_id == session.id).count() > 0
            if has_docs:
                non_empty_sessions.append(session)
                continue
                
            # Check for chat history
            history = get_session_conversation(session.id, checkpointer, limit=1)
            if history.get("message_count", 0) > 0:
                non_empty_sessions.append(session)
                continue
                
            empty_sessions.append(session)
            
        if not empty_sessions:
            # create_session will handle archiving others automatically
            return SessionManager.create_session(user_id, db)
            
        # Sort by updated_at descending (newest first)
        empty_sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        # Keep the first one (newest)
        session_to_keep = empty_sessions[0]
        
        # Delete the rest of the empty sessions
        for session_to_delete in empty_sessions[1:]:
            logger.info(f"Cleaning up redundant empty session {session_to_delete.id}")
            SessionManager.delete_session(session_to_delete.id, user_id, db, vectordb_service)

        # Archive non-empty active sessions
        for session_to_archive in non_empty_sessions:
            logger.info(f"Auto-archiving active session {session_to_archive.id} to focus on reused empty session.")
            SessionLifecycle.transition(session_to_archive, SessionState.ARCHIVED, db, None)
            
        # Update timestamp of the kept session
        session_to_keep.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return session_to_keep

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
            # Archive others first
            SessionManager._archive_other_active_sessions(user_id, db, except_session_id=session_id)
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
