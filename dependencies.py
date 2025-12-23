from typing import Annotated, Tuple, Optional
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLSession
from database import get_db
from auth_service import AuthService
from models import TokenBlacklist

def get_current_user(
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db),
) -> Tuple[str, str]:

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    user_id, session_id, token_type = AuthService.get_token_claims(token)

    if user_id is None or session_id is None or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Check if token is blacklisted
    jti = AuthService.get_jti_from_token(token)
    if jti:
        blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
        if blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    return user_id, session_id
