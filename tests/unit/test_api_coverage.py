"""
Coverage tests for API endpoints to hit missing lines.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from api import app, get_db
from dependencies import get_current_user
from session_lifecycle import SessionState

client = TestClient(app)

class TestAPICoverage:

    def setup_method(self):
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        # Default user override
        app.dependency_overrides[get_current_user] = lambda: ("user1", "sess1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_register_password_too_long(self):
        """Test registration with password that triggers ValueError in hashing."""
        # Ensure user does not exist
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Remove get_current_user override for public endpoint
        del app.dependency_overrides[get_current_user]

        with patch("api.AuthService.hash_password", side_effect=ValueError("Too long")):
            response = client.post("/auth/register", json={"email": "test@example.com", "password": "long"})
            assert response.status_code == 400
            assert "Password is too long" in response.json()["detail"]

    def test_list_sessions_invalid_status(self):
        """Test listing sessions with invalid status enum."""
        response = client.get("/sessions?status_filter=INVALID")
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_chat_session_not_active(self):
        """Test chat in non-active session."""
        mock_session = MagicMock()
        mock_session.status = SessionState.ARCHIVED
        
        with patch("api.SessionManager.get_session", return_value=mock_session):
            response = client.post("/chat", json={"message": "hi"})
            assert response.status_code == 400
            assert "not active" in response.json()["detail"]

    def test_chat_internal_error(self):
        """Test chat endpoint handles internal errors."""
        mock_session = MagicMock()
        mock_session.status = SessionState.ACTIVE
        
        with patch("api.SessionManager.get_session", return_value=mock_session):
            with patch("api.create_session_chatbot", side_effect=Exception("Boom")):
                 response = client.post("/chat", json={"message": "hi"})
                 assert response.status_code == 500

    def test_upload_file_too_large(self):
        """Test uploading file larger than max size."""
        with patch("api.MAX_FILE_SIZE", 10): # 10 bytes
             with patch("api.SessionManager.get_session", return_value=MagicMock(status=SessionState.ACTIVE)):
                 files = {'file': ('test.txt', b'This is longer than 10 bytes', 'text/plain')}
                 response = client.post("/sessions/sess1/upload", files=files)
                 assert response.status_code == 413

    def test_upload_file_invalid_type(self):
        """Test uploading invalid file type."""
        with patch("api.SessionManager.get_session", return_value=MagicMock(status=SessionState.ACTIVE)):
             files = {'file': ('test.exe', b'content', 'application/x-msdownload')}
             response = client.post("/sessions/sess1/upload", files=files)
             assert response.status_code == 400
             assert "File type not allowed" in response.json()["detail"]

    def test_upload_processing_error(self):
        """Test upload endpoint handles processing errors."""
        with patch("api.SessionManager.get_session", return_value=MagicMock(status=SessionState.ACTIVE)):
             with patch("api.VectorDBService.add_documents_to_session", side_effect=Exception("Processing failed")):
                 files = {'file': ('test.txt', b'content', 'text/plain')}
                 response = client.post("/sessions/sess1/upload", files=files)
                 assert response.status_code == 500