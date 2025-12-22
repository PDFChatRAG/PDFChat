"""
FastAPI application with multi-user, multi-session support and JWT authentication.

Features:
- User registration and login with JWT tokens
- Multi-session management per user
- Session-isolated chat and document uploads
- Auto-archival of inactive sessions
- Token revocation on logout
"""

import os
import tempfile
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as SQLSession
from pydantic import BaseModel, EmailStr
from typing import Annotated
import passlib.exc

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver

from database import init_db, get_db, engine
from models import Base, User, TokenBlacklist, SessionStatus
from auth_service import AuthService
from chatBot import create_session_chatbot
from sessionManager import SessionManager
from session_lifecycle import SessionLifecycle, SessionState, ArchivalPolicy
from vectorDB import VectorDBService
from dto.session_dto import SessionRequestDTO, SessionResponseDTO
from dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from dto.conversation_dto import MessageDTO, ConversationHistoryDTO, PaginatedConversationDTO

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_FILE_TYPES = {".pdf", ".docx", ".txt"}
CLEANUP_JOB_INTERVAL_HOURS = 24  # Run cleanup daily

# Global instances
checkpointer = None


# DTOs for authentication
class UserRegisterDTO(BaseModel):
    email: EmailStr
    password: str


class UserLoginDTO(BaseModel):
    email: EmailStr
    password: str


class TokenResponseDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponseDTO(BaseModel):
    id: str
    email: str
    created_at: datetime


# ============================================================================
# HELPER FUNCTIONS: Conversation History
# ============================================================================


def extract_message_content(msg) -> dict:
    """Extract content from a LangChain message object."""
    if hasattr(msg, "content"):
        content = msg.content
    else:
        content = str(msg)

    msg_type = msg.__class__.__name__
    role = "assistant"
    if "Human" in msg_type or "User" in msg_type:
        role = "user"
    elif "AI" in msg_type or "Assistant" in msg_type:
        role = "assistant"
    elif "System" in msg_type:
        role = "system"
    elif "Tool" in msg_type:
        role = "tool"

    return {"role": role, "content": content, "type": msg_type}


def get_session_conversation(session_id: str, limit: Optional[int] = None) -> dict:
    """Retrieve all messages in a session's conversation from LangGraph checkpoints."""
    try:
        global checkpointer
        if not checkpointer:
            # Fallback if checkpointer not initialized (e.g. tests without lifespan)
            memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
            checkpointer = SqliteSaver.from_conn_string(memory_db)
            checkpointer.__enter__()

        config = {"configurable": {"thread_id": session_id}}
        all_checkpoints = list(checkpointer.list(config, limit=None))

        if not all_checkpoints:
            return {"session_id": session_id, "messages": [], "checkpoint_count": 0, "message_count": 0}

        all_messages = []
        seen_message_ids = set()

        for checkpoint_tuple in reversed(all_checkpoints):
            checkpoint = checkpoint_tuple[0]
            checkpoint_id = checkpoint_tuple[1]
            state = checkpoint.get("channel_values", {})
            messages = state.get("messages", [])

            for msg_idx, msg in enumerate(messages):
                msg_id = f"{checkpoint_id}_{msg_idx}"
                if msg_id not in seen_message_ids:
                    msg_data = extract_message_content(msg)
                    msg_data["id"] = msg_id
                    msg_data["checkpoint_id"] = checkpoint_id
                    msg_data["timestamp"] = checkpoint.get("ts")
                    all_messages.append(msg_data)
                    seen_message_ids.add(msg_id)

        if limit:
            all_messages = all_messages[-limit:]

        logger.info(f"Retrieved {len(all_messages)} messages from session {session_id}")
        return {"session_id": session_id, "messages": all_messages, "checkpoint_count": len(all_checkpoints), "message_count": len(all_messages)}

    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return {"session_id": session_id, "messages": [], "checkpoint_count": 0, "message_count": 0, "error": str(e)}


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
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

    # TODO: Initialize APScheduler for cleanup job
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(
    #     ArchivalPolicy.cleanup_job,
    #     "interval",
    #     hours=CLEANUP_JOB_INTERVAL_HOURS,
    #     args=[db, VectorDBService]
    # )
    # scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down PDFChat application...")
    if checkpointer:
        try:
            # We need the manager to exit, but we only have the entered object.
            # SqliteSaver context manager returns self.
            # So checkpointer is the manager instance.
            checkpointer.__exit__(None, None, None)
            logger.info("Memory checkpointer closed")
        except Exception as e:
            logger.warning(f"Error closing checkpointer: {e}")
    # TODO: scheduler.shutdown()


# FastAPI App
app = FastAPI(
    title="PDFChat",
    description="Multi-user, multi-session PDF chat application",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# FastAPI App
app = FastAPI(
    title="PDFChat",
    description="Multi-user, multi-session PDF chat application",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware
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
    """Register a new user."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    try:
        hashed_pw = AuthService.hash_password(req.password)
    except passlib.exc.PasswordSizeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long",
        )

    # Create user
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
    """Login user and get JWT tokens."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not AuthService.verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create tokens
    # First, create a default session or use existing active session
    sessions = SessionManager.list_user_sessions(user.id, db, SessionState.ACTIVE, limit=1)
    session_id = sessions[0].id if sessions else SessionManager.create_session(user.id, db).id

    access_token = AuthService.create_access_token(user.id, session_id)
    refresh_token = AuthService.create_refresh_token(user.id)

    logger.info(f"User logged in: {user.email}")

    return TokenResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@app.post("/auth/refresh", response_model=TokenResponseDTO)
def refresh_token(
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    payload = AuthService.decode_token(token)

    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    # Get user's active session
    sessions = SessionManager.list_user_sessions(user_id, db, SessionState.ACTIVE, limit=1)
    session_id = sessions[0].id if sessions else SessionManager.create_session(user_id, db).id

    new_access_token = AuthService.create_access_token(user_id, session_id)

    return TokenResponseDTO(
        access_token=new_access_token,
        refresh_token=token,  # Return same refresh token
    )


@app.post("/auth/logout")
def logout(
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db)
):
    """Logout user by blacklisting token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    jti = AuthService.get_jti_from_token(token)
    payload = AuthService.decode_token(token)

    if not jti or not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("user_id")
    expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)

    # Add to blacklist
    blacklist_entry = TokenBlacklist(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(blacklist_entry)
    db.commit()

    logger.info(f"User {user_id} logged out")

    return {"status": "logged out"}


# ============================================================================
# DEPENDENCY: Get current user from JWT token
# ============================================================================


def get_current_user(
    authorization: Annotated[str, Header()] = None,
    db: SQLSession = Depends(get_db),
) -> tuple:
    """Extract and validate user from JWT token."""
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


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================


@app.post("/sessions", response_model=SessionResponseDTO)
def create_session(
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Create a new session for the current user."""
    user_id, _ = current_user

    session = SessionManager.create_session(user_id, db)

    return SessionResponseDTO(session_id=session.id)


@app.get("/sessions")
def list_sessions(
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
    status_filter: Optional[str] = None,
):
    """List all sessions for current user."""
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
    """Archive a session."""
    user_id, _ = current_user

    session = SessionManager.archive_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "archived", "session_id": session_id}


@app.post("/sessions/{session_id}/reactivate")
def reactivate_session(
    session_id: str,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Reactivate an archived session."""
    user_id, _ = current_user

    session = SessionManager.reactivate_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "active", "session_id": session_id}


@app.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Hard delete a session (permanent)."""
    user_id, _ = current_user

    success = SessionManager.delete_session(
        session_id, user_id, db, VectorDBService
    )
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "session_id": session_id}


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================


@app.post("/chat", response_model=ChatResponseDTO)
def chat(
    req: ChatRequestDTO,
    current_user: tuple = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """Send message to chatbot in a session."""
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

    # Update session activity timestamp
    SessionManager.update_session_timestamp(session_id, user_id, db)

    # Create session-specific chatbot
    try:
        global checkpointer
        if not checkpointer:
             # Just in case lifespan didn't run (e.g. tests)
             memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
             checkpointer = SqliteSaver.from_conn_string(memory_db).__enter__()

        chatbot = create_session_chatbot(user_id, session_id, checkpointer)
        response = chatbot.chat(req.message)
        chatbot.cleanup()
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
    """Retrieve full conversation history for a session."""
    user_id, _ = current_user

    # Verify session ownership
    session = SessionManager.get_session(session_id, user_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get conversation from checkpoints
    conv_data = get_session_conversation(session_id)
    
    return ConversationHistoryDTO(
        session_id=session_id,
        messages=conv_data.get("messages", []),
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
    conv_data = get_session_conversation(session_id)
    all_messages = conv_data.get("messages", [])
    total_count = len(all_messages)

    # Paginate results
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_messages = all_messages[start_idx:end_idx]

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
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Max size is 100MB.",
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
