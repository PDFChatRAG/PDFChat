import os
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session as SQLSession
from models import AuthSession

# Configuration
SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", 60 * 24))  # 24 hours default
MAX_PASSWORD_LENGTH = 72


class AuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        if len(password.encode('utf-8')) > MAX_PASSWORD_LENGTH:
            raise ValueError("Password is too long")
        
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except ValueError:
            return False

    @staticmethod
    def create_session(
        db: SQLSession, user_id: str, chat_session_id: Optional[str] = None
    ) -> str:
        """Creates a new session token and stores it in the database.
        Also cleans up any expired sessions for this user.
        """
        # Cleanup expired sessions for this user
        db.query(AuthSession).filter(
            AuthSession.user_id == user_id,
            AuthSession.expires_at < datetime.now(timezone.utc)
        ).delete()

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=SESSION_EXPIRE_MINUTES)
        
        auth_session = AuthSession(
            token=token,
            user_id=user_id,
            chat_session_id=chat_session_id,
            expires_at=expires_at
        )
        db.add(auth_session)
        db.commit()
        return token

    @staticmethod
    def get_session(db: SQLSession, token: str) -> Optional[AuthSession]:
        """Retrieves a valid session from the database."""
        session = db.query(AuthSession).filter(AuthSession.token == token).first()
        
        if not session:
            return None
            
        if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            # Clean up expired session
            db.delete(session)
            db.commit()
            return None
            
        return session

    @staticmethod
    def delete_session(db: SQLSession, token: str) -> None:
        """Deletes a session from the database (logout)."""
        session = db.query(AuthSession).filter(AuthSession.token == token).first()
        if session:
            db.delete(session)
            db.commit()

    @staticmethod
    def update_session_ref(db: SQLSession, token: str, new_chat_session_id: str) -> None:
        """Updates the chat session ID associated with an auth token."""
        session = db.query(AuthSession).filter(AuthSession.token == token).first()
        if session:
            session.chat_session_id = new_chat_session_id
            db.commit()