from models import User, Session as SessionModel, Document, AuthSession
from datetime import datetime, timedelta, timezone
import uuid

class UserFactory:
    """Factory for creating User instances."""
    
    @staticmethod
    def create(session, email=None, password="password123"):
        if not email:
            email = f"test_{uuid.uuid4()}@example.com"
            
        user = User(
            email=email,
            hashed_password="hashed_password_placeholder" 
        )
        session.add(user)
        session.commit()
        # Return tuple to match legacy test expectations (user, password)
        return user, password

class SessionFactory:
    """Factory for creating Session instances."""
    
    @staticmethod
    def create(session, user_id=None, title="Test Session", status="ACTIVE"):
        if user_id is None:
            user, _ = UserFactory.create(session)
            user_id = user.id

        chat_session = SessionModel(
            user_id=user_id,
            title=title,
            status=status
        )
        session.add(chat_session)
        session.commit()
        return chat_session

class DocumentFactory:
    """Factory for creating Document instances."""
    
    @staticmethod
    def create(session, session_id=None, file_name="test.pdf", file_type="pdf"):
        if session_id is None:
            chat_session = SessionFactory.create(session)
            session_id = chat_session.id
            
        doc = Document(
            session_id=session_id,
            file_name=file_name,
            file_size=1024,
            file_type=file_type
        )
        session.add(doc)
        session.commit()
        return doc

class AuthSessionFactory:
    """Factory for creating AuthSession instances."""
    
    @staticmethod
    def create(session, user_id, chat_session_id=None):
        """Create an active auth session."""
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        auth_session = AuthSession(
            token=f"test_token_{uuid.uuid4()}",
            user_id=user_id,
            chat_session_id=chat_session_id,
            expires_at=expires
        )
        session.add(auth_session)
        session.commit()
        return auth_session