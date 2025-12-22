"""Authentication service with JWT token generation, validation, and password hashing."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for user registration, login, token management."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        user_id: str, session_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User identifier
            session_id: Session identifier
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = {
            "user_id": user_id,
            "session_id": session_id,
            "token_type": "access",
            "jti": str(uuid.uuid4()),  # JWT ID for revocation tracking
        }

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: str, session_id: str = None) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User identifier
            session_id: Optional session identifier

        Returns:
            Encoded JWT refresh token string
        """
        to_encode = {
            "user_id": user_id,
            "token_type": "refresh",
            "jti": str(uuid.uuid4()),
        }
        if session_id:
            to_encode["session_id"] = session_id
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def get_token_claims(token: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract user_id, session_id, and token type from token.

        Args:
            token: JWT token string

        Returns:
            Tuple of (user_id, session_id, token_type) or (None, None, None) if invalid
        """
        payload = AuthService.decode_token(token)
        if payload is None:
            return None, None, None

        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        token_type = payload.get("token_type")

        return user_id, session_id, token_type

    @staticmethod
    def get_jti_from_token(token: str) -> Optional[str]:
        """Extract JWT ID (jti) from token for revocation tracking."""
        payload = AuthService.decode_token(token)
        if payload:
            return payload.get("jti")
        return None
