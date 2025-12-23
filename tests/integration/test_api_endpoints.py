"""
Integration tests for FastAPI endpoints in api.py
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import json


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201 or response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["email"] == "newuser@example.com"

    def test_register_user_duplicate_email(self, client, test_user):
        """Test registering with duplicate email."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user["email"],
                "password": "AnotherPass123!",
            },
        )

        assert response.status_code == 400 or response.status_code == 409

    def test_register_user_invalid_email(self, client):
        """Test registering with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422 or response.status_code == 400

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )

        assert response.status_code == 401



    def test_logout_success(self, client, test_user, valid_auth_token):
        """Test logout with token revocation."""
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200

    def test_logout_without_token(self, client):
        """Test logout without token."""
        response = client.post("/auth/logout")

        assert response.status_code == 401


class TestSessionManagementEndpoints:
    """Test session management endpoints."""

    def test_create_session_success(self, client, test_user, valid_auth_token):
        """Test creating a session."""
        response = client.post(
            "/sessions",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
            json={
                "title": "My New Session",
                "metadata": {"model": "gemini"},
            },
        )

        assert response.status_code == 201 or response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_create_session_unauthorized(self, client):
        """Test creating session without authorization."""
        response = client.post(
            "/sessions",
            json={"title": "My New Session"},
        )

        assert response.status_code == 401

    def test_create_session_invalid_token(self, client):
        """Test creating session with invalid token."""
        response = client.post(
            "/sessions",
            headers={"Authorization": "Bearer invalid.token.here"},
            json={"title": "My New Session"},
        )

        assert response.status_code == 401

    def test_get_sessions_list(self, client, test_user, valid_auth_token, test_session_data):
        """Test getting sessions list."""
        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_sessions_filter_by_status(self, client, test_user, valid_auth_token):
        """Test filtering sessions by status."""
        response = client.get(
            "/sessions?status_filter=ACTIVE",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "ACTIVE" for s in data)

    def test_archive_session(self, client, test_user, valid_auth_token, test_session_data):
        """Test archiving a session."""
        response = client.post(
            f"/sessions/{test_session_data.id}/archive",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    def test_restore_session(self, client, test_user, valid_auth_token, test_session_data, db_session):
        """Test restoring archived session."""
        # First archive it
        test_session_data.status = "ARCHIVED"
        test_session_data.archived_at = datetime.now(timezone.utc)
        db_session.commit()

        response = client.post(
            f"/sessions/{test_session_data.id}/reactivate",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_delete_session(self, client, test_user, valid_auth_token, test_session_data):
        """Test deleting a session."""
        # Mock VectorDBService inside delete logic if needed, but api.py passes class
        # We need to mock delete_session_collection on VectorDBService
        with patch("api.VectorDBService.delete_session_collection"):
            response = client.delete(
                f"/sessions/{test_session_data.id}",
                headers={"Authorization": f"Bearer {valid_auth_token}"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "deleted"


class TestChatEndpoints:
    """Test chat endpoints."""

    @patch("api.create_session_chatbot")
    def test_send_message_success(
        self, mock_chatbot, client, test_user, auth_service, test_session_data, db_session
    ):
        """Test sending a message to chatbot."""
        mock_instance = MagicMock()
        mock_instance.chat = MagicMock(return_value="Mocked AI response")
        mock_chatbot.return_value = mock_instance

        # Create token specifically for this session
        token = auth_service.create_session(db_session, test_user["user"].id, test_session_data.id)

        response = client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "What is this document about?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_send_message_unauthorized(self, client):
        """Test sending message without authorization."""
        response = client.post(
            "/chat",
            json={"message": "What is this document about?"},
        )

        assert response.status_code == 401

    def test_send_message_empty(self, client, test_user, auth_service, test_session_data, db_session):
        """Test sending empty message."""
        # Create token for valid session
        token = auth_service.create_session(db_session, test_user["user"].id, test_session_data.id)
        
        response = client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": ""},
        )

        assert response.status_code == 400 or response.status_code == 422


class TestConversationHistoryEndpoints:
    """Test conversation history endpoints."""

    @patch("api.get_session_conversation")
    def test_get_conversation_history(self, mock_get_hist, client, test_user, valid_auth_token, test_session_data):
        """Test retrieving conversation history."""
        mock_get_hist.return_value = {"messages": [], "checkpoint_count": 0, "message_count": 0}
        
        response = client.get(
            f"/sessions/{test_session_data.id}/chat-history",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data

    @patch("api.get_session_conversation")
    def test_get_conversation_history_paginated(
        self, mock_get_hist, client, test_user, valid_auth_token, test_session_data
    ):
        """Test retrieving paginated conversation history."""
        mock_get_hist.return_value = {"messages": [], "checkpoint_count": 0, "message_count": 0}

        response = client.get(
            f"/sessions/{test_session_data.id}/chat-history/paginated?page=0&page_size=10",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "page" in data

    def test_get_conversation_history_unauthorized(self, client, test_session_data):
        """Test getting history without authorization."""
        response = client.get(
            f"/sessions/{test_session_data.id}/chat-history",
        )

        assert response.status_code == 401

    def test_get_conversation_history_nonexistent_session(
        self, client, test_user, auth_service, db_session
    ):
        """Test getting history for nonexistent session."""
        token = auth_service.create_session(db_session, test_user["user"].id, None)
        
        response = client.get(
            "/sessions/99999/chat-history",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestFileUploadEndpoints:
    """Test file upload endpoints."""

    def test_upload_pdf_file(self, client, test_user, valid_auth_token, test_session_data):
        """Test uploading a PDF file."""
        # Mock VectorDBService.add_documents_to_session to return a dict
        with patch("api.VectorDBService.add_documents_to_session") as mock_add:
            mock_add.return_value = {"chunks_added": 5, "file_name": "test.pdf", "collection": "col"}
            
            response = client.post(
                f"/sessions/{test_session_data.id}/upload",
                headers={"Authorization": f"Bearer {valid_auth_token}"},
                files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
            )

            assert response.status_code == 200 or response.status_code == 201
            assert response.json()["chunks"] == 5

    def test_upload_docx_file(self, client, test_user, valid_auth_token, test_session_data):
        """Test uploading a DOCX file."""
        with patch("api.VectorDBService.add_documents_to_session") as mock_add:
            mock_add.return_value = {"chunks_added": 5}
            
            response = client.post(
                f"/sessions/{test_session_data.id}/upload",
                headers={"Authorization": f"Bearer {valid_auth_token}"},
                files={"file": ("test.docx", b"PK\x03\x04...", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )

            assert response.status_code == 200 or response.status_code == 201

    def test_upload_txt_file(self, client, test_user, valid_auth_token, test_session_data):
        """Test uploading a TXT file."""
        with patch("api.VectorDBService.add_documents_to_session") as mock_add:
            mock_add.return_value = {"chunks_added": 5}
            
            response = client.post(
                f"/sessions/{test_session_data.id}/upload",
                headers={"Authorization": f"Bearer {valid_auth_token}"},
                files={"file": ("test.txt", b"This is test content", "text/plain")},
            )

            assert response.status_code == 200 or response.status_code == 201

    def test_upload_unsupported_file(self, client, test_user, valid_auth_token, test_session_data):
        """Test uploading unsupported file type."""
        response = client.post(
            f"/sessions/{test_session_data.id}/upload",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
            files={"file": ("test.exe", b"fake executable", "application/x-msdownload")},
        )

        assert response.status_code == 400 or response.status_code == 415

    def test_upload_without_authorization(self, client, test_session_data):
        """Test uploading without authorization."""
        response = client.post(
            f"/sessions/{test_session_data.id}/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 401

    def test_upload_to_nonexistent_session(self, client, test_user, valid_auth_token):
        """Test uploading to nonexistent session."""
        response = client.post(
            "/sessions/99999/upload",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_missing_required_fields(self, client):
        """Test missing required fields in request."""
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com"},  # Missing password
        )

        assert response.status_code == 422 or response.status_code == 400

    def test_invalid_json_body(self, client):
        """Test invalid JSON in request body."""
        response = client.post(
            "/auth/register",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422 or response.status_code == 400

    def test_very_long_password(self, client):
        """Test very long password in registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "x" * 10000,
            },
        )

        # Should either accept or reject appropriately
        assert response.status_code in [201, 200, 400, 422]

    def test_sql_injection_attempt(self, client):
        """Test SQL injection protection."""
        response = client.post(
            "/auth/register",
            json={
                "email": "' OR '1'='1",
                "password": "password' --",
            },
        )

        # Should not cause SQL injection
        assert response.status_code in [400, 422]


class TestEndpointSecurity:
    """Test security aspects of endpoints."""

    def test_expired_token(self, client, expired_auth_token):
        """Test using expired token."""
        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {expired_auth_token}"},
        )

        assert response.status_code == 401

    def test_token_from_different_user(self, client, test_user, valid_auth_token, db_session):
        """Test using token from different user."""
        from tests.fixtures.factories import SessionFactory, UserFactory

        another_user, _ = UserFactory.create(db_session)
        another_session = SessionFactory.create(db_session, user_id=another_user.id)

        # We try to access another session with current user's token
        # This route /sessions/{id} does not exist, so let's try upload or archive which checks ownership
        response = client.post(
            f"/sessions/{another_session.id}/archive",
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

        assert response.status_code == 403 or response.status_code == 404

    def test_missing_authorization_header(self, client):
        """Test request without authorization header."""
        response = client.get("/sessions")

        assert response.status_code == 401

    def test_malformed_authorization_header(self, client):
        """Test malformed authorization header."""
        response = client.get(
            "/sessions",
            headers={"Authorization": "InvalidToken"},
        )

        assert response.status_code == 401


# Helper import for tests
from tests.fixtures.factories import UserFactory
