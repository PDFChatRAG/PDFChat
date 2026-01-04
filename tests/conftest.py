"""
Shared pytest fixtures and configuration for PDFChat tests.
"""
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from models import Base, User, Session as SessionModel, AuthSession
from auth_service import AuthService
from database import get_db


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Set dummy environment variables for testing."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy_key_for_testing"}):
        yield


@pytest.fixture(scope="session")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys for SQLite
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_db):
    """Create a new database session for each test."""
    SessionLocal = sessionmaker(bind=test_db)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def app_with_db(db_session):
    """Provide FastAPI app with test database."""
    from api import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_db):
    """Create a TestClient for FastAPI app."""
    from fastapi.testclient import TestClient

    return TestClient(app_with_db)


@pytest.fixture
def auth_service():
    """Provide AuthService instance."""
    return AuthService()


@pytest.fixture
def test_user(db_session, auth_service):
    """Create a test user in the database."""
    email = "testuser@example.com"
    password = "TestPassword123!"
    hashed_password = auth_service.hash_password(password)

    user = User(email=email, hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {"user": user, "password": password, "email": email}


@pytest.fixture
def test_session_data(db_session, test_user):
    """Create a test session in the database."""
    session = SessionModel(
        user_id=test_user["user"].id,
        title="Test Session",
        status="ACTIVE",
        metadata_={"test": True},
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def valid_auth_token(test_user, auth_service, db_session):
    """Create a valid session token for testing."""
    return auth_service.create_session(
        db=db_session,
        user_id=test_user["user"].id,
        chat_session_id=None,
    )


@pytest.fixture
def expired_auth_token(db_session, test_user):
    """Create an expired session token for testing."""
    from models import AuthSession
    from datetime import datetime, timedelta, timezone
    import uuid
    
    token = f"expired_token_{uuid.uuid4()}"
    auth_session = AuthSession(
        token=token,
        user_id=test_user["user"].id,
        chat_session_id=None,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db_session.add(auth_session)
    db_session.commit()
    return token


@pytest.fixture
def mock_google_genai():
    """Mock Google Generative AI API."""
    with patch("chatBot.ChatGoogleGenerativeAI") as mock_llm:
        mock_instance = MagicMock()
        mock_instance.invoke = MagicMock(return_value="Mocked AI response")
        mock_llm.return_value = mock_instance
        yield mock_llm


@pytest.fixture
def mock_embeddings():
    """Mock Google Embeddings."""
    with patch("chatBot.GoogleGenerativeAIEmbeddings") as mock_emb:
        mock_instance = MagicMock()
        mock_emb.return_value = mock_instance
        yield mock_emb


@pytest.fixture
def mock_chroma():
    """Mock Chroma vector store."""
    with patch("vectorDB.Chroma") as mock_chroma_store:
        mock_instance = MagicMock()
        mock_instance.as_retriever = MagicMock()
        mock_chroma_store.return_value = mock_instance
        yield mock_chroma_store


@pytest.fixture
def mock_checkpointer():
    """Mock LangGraph SqliteSaver checkpointer."""
    with patch("chatBot.SqliteSaver") as mock_saver:
        mock_instance = MagicMock()
        mock_saver.return_value = mock_instance
        yield mock_saver


@pytest.fixture
def temp_upload_dir():
    """Create a temporary directory for file uploads."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_file_system(temp_upload_dir):
    """Mock file system operations."""
    with patch("vectorDB.os.path.exists") as mock_exists:
        mock_exists.return_value = True
        yield temp_upload_dir


@pytest.fixture
def test_pdf_content():
    """Provide sample PDF content as text."""
    return """
    This is a test PDF document.
    It contains multiple paragraphs.
    Each paragraph has some test content.
    This is useful for testing text extraction.
    """


@pytest.fixture
def test_docx_content():
    """Provide sample DOCX content."""
    return """
    This is a test DOCX document.
    It contains multiple paragraphs.
    Each paragraph has some test content.
    This is useful for testing document processing.
    """


@pytest.fixture
def test_txt_content():
    """Provide sample TXT content."""
    return "This is a simple text file content for testing."


@pytest.fixture
def mock_pdf_loader(test_pdf_content):
    """Mock PyPDF2 PDF loader."""
    with patch("dataSource.PdfReader") as mock_pdf:
        mock_instance = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = test_pdf_content
        mock_instance.pages = [mock_page, mock_page]
        mock_pdf.return_value = mock_instance
        yield mock_pdf


@pytest.fixture
def mock_docx_loader(test_docx_content):
    """Mock python-docx loader."""
    with patch("dataSource.Document") as mock_docx:
        mock_instance = MagicMock()
        mock_para = MagicMock()
        mock_para.text = test_docx_content
        mock_instance.paragraphs = [mock_para, mock_para]
        mock_docx.return_value = mock_instance
        yield mock_docx


@pytest.fixture(autouse=True)
def reset_database(db_session):
    """Reset database between tests."""
    yield
    try:
        db_session.rollback()
    except Exception:
        pass
    for table in reversed(Base.metadata.sorted_tables):
        try:
            db_session.execute(table.delete())
        except Exception:
            pass
    db_session.commit()

# Pytest configuration

