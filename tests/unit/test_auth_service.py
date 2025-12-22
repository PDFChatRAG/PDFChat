"""
Unit tests for auth_service.py
"""
import pytest
from datetime import datetime, timedelta, timezone
import jwt
from auth_service import AuthService, SECRET_KEY, ALGORITHM


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

    def test_hash_consistency(self, auth_service):
        """Test that same password produces different hashes."""
        password = "TestPassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # bcrypt hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify
        assert auth_service.verify_password(password, hash1) is True
        assert auth_service.verify_password(password, hash2) is True


class TestAuthServiceJWT:
    """Test JWT token creation and validation."""

    def test_create_access_token(self, auth_service):
        """Test creating an access token."""
        user_id = 123
        session_id = "session-123"

        token = auth_service.create_access_token(user_id, session_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify token content
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["user_id"] == user_id
        assert decoded["session_id"] == session_id
        assert decoded["token_type"] == "access"

    def test_create_refresh_token(self, auth_service):
        """Test creating a refresh token."""
        user_id = 456
        session_id = "session-456"

        token = auth_service.create_refresh_token(user_id, session_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify token content
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["user_id"] == user_id
        assert decoded["session_id"] == session_id
        assert decoded["token_type"] == "refresh"

    def test_access_token_expiration(self, auth_service):
        """Test that access token includes expiration."""
        user_id = 789
        session_id = "session-789"

        token = auth_service.create_access_token(user_id, session_id)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in decoded
        # Verify token expires in approximately 60 minutes
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert 50 < (exp_time - now).total_seconds() < 70 * 60

    def test_refresh_token_expiration(self, auth_service):
        """Test that refresh token expires in 7 days."""
        user_id = 999
        session_id = "session-999"

        token = auth_service.create_refresh_token(user_id, session_id)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in decoded
        # Verify token expires in approximately 7 days
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert 6.9 * 24 * 3600 < (exp_time - now).total_seconds() < 7.1 * 24 * 3600


class TestAuthServiceTokenValidation:
    """Test JWT token validation and decoding."""

    def test_verify_token_valid(self, auth_service, valid_jwt_token):
        """Test verifying a valid token."""
        result = auth_service.decode_token(valid_jwt_token)
        assert result is not None
        assert isinstance(result, dict)
        assert "user_id" in result

    def test_verify_token_invalid_signature(self, auth_service):
        """Test verifying token with invalid signature."""
        payload = {
            "user_id": 123,
            "session_id": "session-123",
            "token_type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # Encode with wrong key
        wrong_token = jwt.encode(payload, "wrong-secret-key", algorithm=ALGORITHM)

        result = auth_service.decode_token(wrong_token)
        assert result is None

    def test_verify_token_expired(self, auth_service, expired_jwt_token):
        """Test verifying an expired token."""
        result = auth_service.decode_token(expired_jwt_token)
        # expired token decoding fails in decode_token which returns None on JWTError
        # (assuming jose.jwt raises ExpiredSignatureError which inherits from JWTError)
        assert result is None

    def test_get_user_id_from_token(self, auth_service, valid_jwt_token):
        """Test extracting user_id from token."""
        user_id, _, _ = auth_service.get_token_claims(valid_jwt_token)
        assert user_id is not None

    def test_get_session_id_from_token(self, auth_service, valid_jwt_token):
        """Test extracting session_id from token."""
        _, session_id, _ = auth_service.get_token_claims(valid_jwt_token)
        assert session_id is not None

    def test_get_token_type_from_token(self, auth_service):
        """Test extracting token_type from token."""
        user_id = 111
        session_id = "session-111"
        access_token = auth_service.create_access_token(user_id, session_id)

        _, _, token_type = auth_service.get_token_claims(access_token)
        assert token_type == "access"

    def test_get_jti_from_token(self, auth_service):
        """Test extracting JTI from token."""
        user_id = 222
        session_id = "session-222"
        token = auth_service.create_access_token(user_id, session_id)

        jti = auth_service.get_jti_from_token(token)
        assert jti is not None
        assert isinstance(jti, str)

    def test_get_user_id_from_invalid_token(self, auth_service):
        """Test extracting user_id from invalid token."""
        user_id, _, _ = auth_service.get_token_claims("invalid.token.here")
        assert user_id is None

    def test_get_session_id_from_invalid_token(self, auth_service):
        """Test extracting session_id from invalid token."""
        _, session_id, _ = auth_service.get_token_claims("invalid.token.here")
        assert session_id is None


class TestAuthServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_hash_empty_password(self, auth_service):
        """Test hashing empty password."""
        password = ""
        hashed = auth_service.hash_password(password)
        assert len(hashed) > 0
        assert auth_service.verify_password(password, hashed) is True

    def test_hash_very_long_password(self, auth_service):
        """Test hashing very long password raises error."""
        password = "x" * 1000
        with pytest.raises(ValueError, match="Password is too long"):
            auth_service.hash_password(password)

    def test_create_token_with_negative_user_id(self, auth_service):
        """Test creating token with negative user_id."""
        user_id = -1
        session_id = "session-neg"

        token = auth_service.create_access_token(user_id, session_id)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["user_id"] == user_id

    def test_create_token_with_special_session_id(self, auth_service):
        """Test creating token with special characters in session_id."""
        user_id = 333
        session_id = "session-!@#$%^&*()"

        token = auth_service.create_access_token(user_id, session_id)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["session_id"] == session_id
