"""
Unit tests for auth_service.py
"""
import pytest
from datetime import datetime, timedelta, timezone
from auth_service import AuthService
from models import AuthSession


class TestAuthServicePasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        # bcrypt hashes should start with $2b$
        assert hashed.startswith("$2b$")

    def test_verify_password_success(self, auth_service):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_failure(self, auth_service):
        """Test password verification with wrong password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(wrong_password, hashed) is False


class TestAuthServiceSession:
    """Test session management."""

    def test_create_session(self, auth_service, db_session, test_user):
        """Test creating a new session."""
        token = auth_service.create_session(
            db=db_session,
            user_id=test_user["user"].id,
            chat_session_id=None
        )

        assert isinstance(token, str)
        assert len(token) > 20
        
        # Verify in DB
        session = db_session.query(AuthSession).filter(AuthSession.token == token).first()
        assert session is not None
        assert session.user_id == test_user["user"].id
        assert session.chat_session_id is None
        assert session.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)

    def test_get_session_valid(self, auth_service, db_session, test_user):
        """Test retrieving a valid session."""
        token = auth_service.create_session(db_session, test_user["user"].id)
        
        session = auth_service.get_session(db_session, token)
        assert session is not None
        assert session.token == token
        assert session.user_id == test_user["user"].id

    def test_get_session_invalid_token(self, auth_service, db_session):
        """Test retrieving a session with invalid token."""
        session = auth_service.get_session(db_session, "invalid_token")
        assert session is None

    def test_get_session_expired(self, auth_service, db_session, test_user):
        """Test retrieving an expired session."""
        token = "expired_token"
        expired_session = AuthSession(
            token=token,
            user_id=test_user["user"].id,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(expired_session)
        db_session.commit()

        # Should return None and delete the session
        session = auth_service.get_session(db_session, token)
        assert session is None
        
        # Verify deletion
        db_session_check = db_session.query(AuthSession).filter(AuthSession.token == token).first()
        assert db_session_check is None

    def test_delete_session(self, auth_service, db_session, test_user):
        """Test deleting a session (logout)."""
        token = auth_service.create_session(db_session, test_user["user"].id)
        
        # Verify it exists
        assert auth_service.get_session(db_session, token) is not None
        
        # Delete it
        auth_service.delete_session(db_session, token)
        
        # Verify it's gone
        assert auth_service.get_session(db_session, token) is None

    def test_delete_nonexistent_session(self, auth_service, db_session):
        """Test deleting a session that doesn't exist (should not error)."""
        auth_service.delete_session(db_session, "nonexistent_token")


class TestAuthServiceEdgeCases:
    """Test edge cases."""

    def test_hash_very_long_password(self, auth_service):
        """Test hashing very long password raises error."""
        password = "x" * 1000
        with pytest.raises(ValueError, match="Password is too long"):
            auth_service.hash_password(password)