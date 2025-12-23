"""Session lifecycle management with state transitions and auto-archival."""

from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session as SQLSession
import logging
from models import Session

logger = logging.getLogger(__name__)


class SessionState(str, Enum):

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class SessionLifecycle:

    # Define valid state transitions
    VALID_TRANSITIONS = {
        SessionState.ACTIVE: [SessionState.ARCHIVED, SessionState.DELETED],
        SessionState.ARCHIVED: [SessionState.ACTIVE, SessionState.DELETED],
        SessionState.DELETED: [],  # Terminal state
    }

    @staticmethod
    def can_transition(
        current_state: SessionState, target_state: SessionState
    ) -> bool:
        """Check if transition is allowed."""
        return target_state in SessionLifecycle.VALID_TRANSITIONS.get(
            current_state, []
        )

    @staticmethod
    def transition(
        session,
        target_state: SessionState,
        db: SQLSession,
        vectordb_service,
    ) -> bool:

        if not SessionLifecycle.can_transition(session.status, target_state):
            raise ValueError(
                f"Cannot transition from {session.status} to {target_state}"
            )

        if target_state == SessionState.ARCHIVED:
            return SessionLifecycle._archive(session, db)

        elif target_state == SessionState.ACTIVE:
            return SessionLifecycle._reactivate(session, db)

        elif target_state == SessionState.DELETED:
            return SessionLifecycle._hard_delete(session, db, vectordb_service)

        return False

    @staticmethod
    def _archive(session, db: SQLSession) -> bool:
        session.status = SessionState.ARCHIVED
        session.archived_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Session {session.id} archived")
        return True

    @staticmethod
    def _reactivate(session, db: SQLSession) -> bool:
        session.status = SessionState.ACTIVE
        session.archived_at = None
        db.commit()
        logger.info(f"Session {session.id} reactivated")
        return True

    @staticmethod
    def _hard_delete(session, db: SQLSession, vectordb_service) -> bool:
        # Delete Chroma collection
        try:
            vectordb_service.delete_session_collection(session.id, session.user_id)
        except Exception as e:
            logger.warning(f"Could not delete Chroma collection: {e}")

        # Delete documents (cascades via SQLAlchemy)
        session.status = SessionState.DELETED
        db.delete(session)
        db.commit()
        logger.info(f"Session {session.id} permanently deleted")
        return True


class ArchivalPolicy:

    # Configuration (can be overridden via environment variables)
    INACTIVITY_DAYS = int(__import__("os").getenv("SESSION_INACTIVITY_DAYS", 30))
    RETENTION_DAYS = int(__import__("os").getenv("SESSION_RETENTION_DAYS", 90))

    @staticmethod
    def should_auto_archive(session) -> bool:
        if session.status != SessionState.ACTIVE:
            return False

        updated_at = session.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        days_since_update = (
            datetime.now(timezone.utc) - updated_at
        ).days

        return days_since_update >= ArchivalPolicy.INACTIVITY_DAYS

    @staticmethod
    def should_hard_delete(session) -> bool:
        if session.status != SessionState.ARCHIVED or not session.archived_at:
            return False

        archived_at = session.archived_at
        if archived_at.tzinfo is None:
            archived_at = archived_at.replace(tzinfo=timezone.utc)

        days_since_archival = (
            datetime.now(timezone.utc) - archived_at
        ).days

        return days_since_archival >= ArchivalPolicy.RETENTION_DAYS

    @staticmethod
    def cleanup_job(db: SQLSession, vectordb_service):


        logger.info("Running session archival cleanup job")

        # Auto-archive inactive active sessions
        inactive_sessions = (
            db.query(Session)
            .filter(Session.status == SessionState.ACTIVE)
            .all()
        )

        archived_count = 0
        for session in inactive_sessions:
            if ArchivalPolicy.should_auto_archive(session):
                try:
                    SessionLifecycle.transition(
                        session, SessionState.ARCHIVED, db, vectordb_service
                    )
                    archived_count += 1
                except Exception as e:
                    logger.error(f"Error archiving session {session.id}: {e}")

        # Hard delete old archived sessions
        archived_sessions = (
            db.query(Session)
            .filter(Session.status == SessionState.ARCHIVED)
            .all()
        )

        deleted_count = 0
        for session in archived_sessions:
            if ArchivalPolicy.should_hard_delete(session):
                try:
                    SessionLifecycle.transition(
                        session, SessionState.DELETED, db, vectordb_service
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error hard-deleting session {session.id}: {e}")

        logger.info(
            f"Cleanup job completed: {archived_count} archived, {deleted_count} deleted"
        )
