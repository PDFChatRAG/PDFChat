import os
import tempfile
import logging
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as SQLSession

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver

from database import init_db, get_db
from models import User, SessionStatus, VerificationCode, AuthSession
from auth_service import AuthService
from chatBot import create_session_chatbot
from sessionManager import SessionManager
from session_lifecycle import SessionState
from vectorDB import VectorDBService
from email_service import EmailService
from dto.session_dto import SessionResponseDTO, UpdateSessionTitleDTO
from dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from dto.conversation_dto import ConversationHistoryDTO, PaginatedConversationDTO
from dto.auth_dto import (
    UserRegisterDTO,
    UserLoginDTO,
    TokenResponseDTO,
    UserResponseDTO,
    RequestResetCodeDTO,
    VerifyResetCodeDTO,
    ResetPasswordDTO,
)
from dependencies import get_current_user
from utils.conversation_helper import get_session_conversation

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_FILE_TYPES = {".pdf", ".docx", ".txt"}
CLEANUP_JOB_INTERVAL_HOURS = 24  # Run cleanup daily

# Global instances
checkpointer = None


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing PDFChat application...")
    init_db()
    logger.info("Database initialized")

    # Initialize global checkpointer
    global checkpointer
    memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
    checkpointer_manager = SqliteSaver.from_conn_string(memory_db)
    checkpointer = checkpointer_manager.__enter__()
    logger.info("Memory checkpointer initialized")

    yield

    # Shutdown
    logger.info("Shutting down PDFChat application...")
    if checkpointer:
        try:
            checkpointer.__exit__(None, None, None)
            logger.info("Memory checkpointer closed")
        except Exception as e:
            logger.warning(f"Error closing checkpointer: {e}")


app = FastAPI(
    title="PDFChat",
    description="Multi-user, multi-session PDF chat application",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@app.post("/auth/register", response_model=UserResponseDTO)
def register(req: UserRegisterDTO, db: SQLSession = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    try:
        hashed_pw = AuthService.hash_password(req.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long",
        )

    user = User(
        email=req.email,
        hashed_password=hashed_pw,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"User registered: {user.email}")

    return UserResponseDTO(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )


@app.post("/auth/login", response_model=TokenResponseDTO)
def login(req: UserLoginDTO, db: SQLSession = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not AuthService.verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    global checkpointer
    if not checkpointer:
         memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
         checkpointer = SqliteSaver.from_conn_string(memory_db).__enter__()

    session = SessionManager.get_or_create_empty_session(
        user.id, db, checkpointer, VectorDBService
    )
    session_id = session.id

    access_token = AuthService.create_session(db, user.id, session_id)

    logger.info(f"User logged in: {user.email}")

    return TokenResponseDTO(
        access_token=access_token,
        session_id=session_id
    )




@app.post("/auth/logout")
def logout(
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    
    token = authorization
    AuthService.delete_session(db, token)

    return {"status": "You have successfully logged out"}


@app.post("/auth/request-reset-code")
def request_reset_code(
    req: RequestResetCodeDTO,
    db: SQLSession = Depends(get_db)
):
    """Request a password reset verification code.
    
    Sends a 6-digit code to the user's email if the account exists.
    For security, always returns success even if email doesn't exist.
    """
    # Find user
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        # Don't reveal if email exists (security best practice)
        logger.info(f"Password reset requested for non-existent email: {req.email}")
        return {"status": "If the email exists, a verification code has been sent"}
    
    # Delete any existing unused codes for this user
    db.query(VerificationCode).filter(
        VerificationCode.user_id == user.id,
        VerificationCode.purpose == "password_reset",
        VerificationCode.used == 0
    ).delete()
    db.commit()
    
    # Generate 6-digit code
    code = ''.join(secrets.choice(string.digits) for _ in range(6))
    
    # Create expiration time (10 minutes from now)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Store verification code
    verification = VerificationCode(
        user_id=user.id,
        code=code,
        purpose="password_reset",
        expires_at=expires_at,
        used=0,
        attempts=0
    )
    db.add(verification)
    db.commit()
    
    # Send email
    email_service = EmailService()
    email_sent = email_service.send_verification_code(user.email, code, "password reset")
    
    if email_sent:
        logger.info(f"Password reset code sent to {user.email}")
    else:
        logger.error(f"Failed to send password reset code to {user.email}")
    
    return {"status": "If the email exists, a verification code has been sent"}


@app.post("/auth/verify-reset-code")
def verify_reset_code(
    req: VerifyResetCodeDTO,
    db: SQLSession = Depends(get_db)
):
    """Verify the reset code and return a temporary reset token.
    
    The reset token is valid for 15 minutes and can be used once to reset the password.
    """
    # Find user
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Find valid verification code
    verification = db.query(VerificationCode).filter(
        VerificationCode.user_id == user.id,
        VerificationCode.code == req.code,
        VerificationCode.purpose == "password_reset",
        VerificationCode.used == 0,
        VerificationCode.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not verification:
        # Increment attempts if code exists but is wrong
        existing_code = db.query(VerificationCode).filter(
            VerificationCode.user_id == user.id,
            VerificationCode.purpose == "password_reset",
            VerificationCode.used == 0,
            VerificationCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if existing_code:
            existing_code.attempts += 1
            
            # Delete code after too many attempts
            if existing_code.attempts >= 5:
                db.delete(existing_code)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many incorrect attempts. Please request a new code."
                )
            
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Mark code as used
    verification.used = 1
    db.commit()
    
    # Generate temporary reset token (valid for 15 minutes)
    reset_token = secrets.token_urlsafe(32)
    
    # Store reset token as a new verification entry
    reset_token_entry = VerificationCode(
        user_id=user.id,
        code=reset_token,
        purpose="reset_token",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        used=0,
        attempts=0
    )
    db.add(reset_token_entry)
    db.commit()
    
    logger.info(f"Verification code validated for user {user.email}")
    
    return {
        "status": "verified",
        "reset_token": reset_token,
        "expires_in": 900  # 15 minutes in seconds
    }


@app.post("/auth/reset-password")
def reset_password(
    req: ResetPasswordDTO,
    db: SQLSession = Depends(get_db)
):
    """Reset password using the temporary reset token.
    
    The reset token is obtained from verify-reset-code endpoint.
    """
    # Validate password strength
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Find valid reset token
    reset_token_entry = db.query(VerificationCode).filter(
        VerificationCode.code == req.reset_token,
        VerificationCode.purpose == "reset_token",
        VerificationCode.used == 0,
        VerificationCode.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not reset_token_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == reset_token_entry.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    try:
        user.hashed_password = AuthService.hash_password(req.new_password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long"
        )
    
    # Mark reset token as used
    reset_token_entry.used = 1
    
    # Delete all auth sessions (force re-login)
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id
    ).delete()
    
    db.commit()
    
    # Send confirmation email
    email_service = EmailService()
    email_sent = email_service.send_password_reset_confirmation(user.email)
    
    if email_sent:
        logger.info(f"Password reset confirmation email sent successfully to {user.email}")
    else:
        logger.error(f"Failed to send password reset confirmation email to {user.email}")
    
    logger.info(f"Password reset successful for user {user.email}")
    
    return {"status": "Password reset successful"}


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================


@app.post("/sessions", response_model=SessionResponseDTO)
def create_session(
    current_user: tuple = Depends(get_current_user),
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db),
):
    user_id, _ = current_user

    session = SessionManager.create_session(user_id, db)

    # Update current auth token to point to this new session
    # Update current auth token to point to this new session
    if authorization:
        token = authorization
        if token.startswith("Bearer "):
            token = token[7:]
        AuthService.update_session_ref(db, token, session.id)

    return SessionResponseDTO(session_id=session.id)


@app.get("/sessions")
def list_sessions(
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
    status_filter: Optional[str] = None,
):
    user_id, _ = current_user

    status_enum = None
    if status_filter:
        try:
            status_enum = SessionState[status_filter.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    sessions = SessionManager.list_user_sessions(user_id, db, status_enum)

    return [
        {
            "id": s.id,
            "title": s.title,
            "status": s.status.value,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "archived_at": s.archived_at,
        }
        for s in sessions
    ]


@app.post("/sessions/{session_id}/archive")
def archive_session(
    session_id: str,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    user_id, _ = current_user

    session = SessionManager.archive_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "archived", "session_id": session_id}


@app.post("/sessions/{session_id}/reactivate")
def reactivate_session(
    session_id: str,
    current_user: tuple = Depends(get_current_user),
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db),
):
    user_id, _ = current_user

    session = SessionManager.reactivate_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update current auth token to point to this reactivated session
    # Update current auth token to point to this new session
    if authorization:
        token = authorization
        if token.startswith("Bearer "):
            token = token[7:]
        AuthService.update_session_ref(db, token, session.id)

    return {"status": "active", "session_id": session_id}


@app.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    user_id, _ = current_user

    success = SessionManager.delete_session(
        session_id, user_id, db, VectorDBService
    )
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "session_id": session_id}


@app.patch("/sessions/{session_id}/title")
def update_session_title(
    session_id: str,
    req: UpdateSessionTitleDTO,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Update the title of a session.
    
    Args:
        session_id: The session ID
        req: Request body with new title (1-50 characters)
        
    Returns:
        Updated session title
    """
    user_id, _ = current_user
    
    session = SessionManager.get_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate and sanitize title
    stripped_title = req.title.strip()
    if len(stripped_title) < 1 or len(stripped_title) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title must be between 1 and 50 characters after removing whitespace"
        )
    
    session.title = stripped_title
    db.commit()
    
    logger.info(f"Updated title for session {session_id}: {session.title}")
    return {"status": "updated", "session_id": session_id, "title": session.title}


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================


@app.post("/chat", response_model=ChatResponseDTO)
def chat(
    req: ChatRequestDTO,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    global checkpointer
    
    user_id, session_id = current_user
    # Verify session ownership
    session = SessionManager.get_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionState.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is {session.status}, not active",
        )

    SessionManager.update_session_timestamp(session_id, user_id, db)

    # Ensure checkpointer is initialized
    if not checkpointer:
         memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
         checkpointer = SqliteSaver.from_conn_string(memory_db).__enter__()

    print("session title:", session.title)
    # Check if this is the first message and generate title
    conv_data = get_session_conversation(session_id, checkpointer)
    message_count = conv_data.get("message_count", 0)
    
    if message_count == 0 and session.title == "New Conversation":
        from chatBot import generate_session_title
        new_title = generate_session_title(req.message)
        session.title = new_title
        db.commit()
        logger.info(f"Generated title for session {session_id}: {new_title}")

    try:

        chatbot = create_session_chatbot(user_id, session_id, checkpointer)
        response = chatbot.chat(req.message)
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing message",
        )

    return ChatResponseDTO(response=response)


# ============================================================================
# CONVERSATION HISTORY ENDPOINTS
# ============================================================================


@app.get("/sessions/{session_id}/chat-history", response_model=ConversationHistoryDTO)
def get_chat_history(
    session_id: str,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    user_id, _ = current_user

    # Verify session ownership
    session = SessionManager.get_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get conversation from checkpoints
    conv_data = get_session_conversation(session_id, checkpointer)
    messages = conv_data.get("messages", [])

    # Filter to only include user and assistant messages with non-empty content
    filtered_messages = [msg for msg in messages if msg.get("role") in ("user", "assistant") and msg.get("content")]
    
    normalized_messages = []
    for msg in filtered_messages:
        normalized_msg = msg.copy()
        if isinstance(msg.get("content"), list):
            # Join all text blocks
            content_list = msg.get("content", [])
            normalized_msg["content"] = " ".join([
                block.get("text", "") for block in content_list if isinstance(block, dict)
            ])
        normalized_messages.append(normalized_msg)
    
    return ConversationHistoryDTO(
        session_id=session_id,
        messages=normalized_messages,
        checkpoint_count=conv_data.get("checkpoint_count", 0),
        message_count=conv_data.get("message_count", 0),
    )


@app.get("/sessions/{session_id}/chat-history/paginated", response_model=PaginatedConversationDTO)
def get_chat_history_paginated(
    session_id: str,
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Retrieve paginated conversation history for a session."""
    user_id, _ = current_user

    # Verify session ownership
    session = SessionManager.get_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get conversation from checkpoints
    conv_data = get_session_conversation(session_id, checkpointer)
    all_messages = conv_data.get("messages", [])
    
    # Filter to only include user and assistant messages with non-empty content
    filtered_messages = [msg for msg in all_messages if msg.get("role") in ("user", "assistant") and msg.get("content")]
    total_count = len(filtered_messages)

    # Paginate results
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_messages = filtered_messages[start_idx:end_idx]

    total_pages = (total_count + page_size - 1) // page_size
    has_more = page < total_pages - 1

    return PaginatedConversationDTO(
        session_id=session_id,
        messages=paginated_messages,
        page=page,
        page_size=page_size,
        total_messages=total_count,
        total_pages=total_pages,
        has_more=has_more,
        checkpoint_count=conv_data.get("checkpoint_count", 0),
        message_count=conv_data.get("message_count", 0),
    )


# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================


@app.post("/sessions/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Upload a document to a session."""
    user_id, _ = current_user

    # Verify session ownership
    session = SessionManager.get_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionState.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is {session.status}, not active",
        )

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no name",
        )

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_FILE_TYPES)}",
        )

    # Read file
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large. Max size is 20MB.",
        )

    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        # Process file and add to vector store
        result = VectorDBService.add_documents_to_session(
            session_id,
            user_id,
            tmp_path,
            file.filename,
            GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004"
            ),
        )

        # Record document metadata in database
        document = SessionManager.add_document_to_session(
            session_id,
            user_id,
            file.filename,
            len(file_content),
            file_ext[1:],  # Remove the dot
            result.get("chunks_added", 0),
            db,
            tmp_path,
        )

        logger.info(f"File {file.filename} uploaded to session {session_id}")

        return {
            "filename": file.filename,
            "status": "processed",
            "chunks": result.get("chunks_added"),
        }

    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing file",
        )

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)