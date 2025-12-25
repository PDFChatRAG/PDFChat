from typing import Annotated, Tuple
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLSession
from database import get_db
from auth_service import AuthService

def get_current_user(
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db),
) -> Tuple[str, str]:

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    token = authorization
    
    session = AuthService.get_session(db, token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Return user_id and chat_session_id (if set)
    # If chat_session_id is None, endpoints requiring it should handle that check
    return session.user_id, session.chat_session_id