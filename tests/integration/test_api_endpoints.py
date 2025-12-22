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
            "/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201 or response.status_code == 200
        data = response.json()
        assert "user_id" in data or "id" in data

    def test_register_user_duplicate_email(self, client, test_user):
        """Test registering with duplicate email."""
        response = client.post(
            "/register",
            json={
                "email": test_user["email"],
                "password": "AnotherPass123!",
            },
        )

        assert response.status_code == 400 or response.status_code == 409

    def test_register_user_invalid_email(self, client):
        """Test registering with invalid email."""
        response = client.post(
            "/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422 or response.status_code == 400

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/login",
            json={
                "email": test_user["email"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post(
            "/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )

        assert response.status_code == 401

    def test_refresh_token_success(self, client, test_user, auth_service):
        """Test refreshing access token."""
        # First login
        login_response = client.post(
            "/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        refresh_response = client.post(
            "/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data

    def test_refresh_token_invalid(self, client):
        """Test refreshing with invalid token."""
        response = client.post(
            "/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    def test_logout_success(self, client, test_user, valid_jwt_token):
        """Test logout with token revocation."""
        response = client.post(
            "/logout",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200

    def test_logout_without_token(self, client):
        """Test logout without token."""
        response = client.post("/logout")

        assert response.status_code == 401


class TestSessionManagementEndpoints:
    """Test session management endpoints."""

    def test_create_session_success(self, client, test_user, valid_jwt_token):
        """Test creating a session."""
        response = client.post(
            "/sessions",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={
                "title": "My New Session",
                "metadata": {"model": "gemini"},
            },
        )

        assert response.status_code == 201 or response.status_code == 200
        data = response.json()
        assert "id" in data or "session_id" in data
        assert data["status"] == "ACTIVE"

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

    def test_get_sessions_list(self, client, test_user, valid_jwt_token, test_session_data):
        """Test getting sessions list."""
        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_sessions_filter_by_status(self, client, test_user, valid_jwt_token):
        """Test filtering sessions by status."""
        response = client.get(
            "/sessions?status=ACTIVE",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "ACTIVE" for s in data)

    def test_get_session_details(self, client, test_user, valid_jwt_token, test_session_data):
        """Test getting session details."""
        response = client.get(
            f"/sessions/{test_session_data.id}",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session_data.id
        assert data["user_id"] == test_user["user"].id

    def test_get_session_wrong_user(self, client, test_session_data):
        """Test getting session with wrong user."""
        from tests.fixtures.factories import UserFactory
        from fastapi.testclient import TestClient
        from auth_service import AuthService

        auth = AuthService()
        # Create another user
        another_user = MagicMock()
        another_user.id = 999

        token = auth.create_access_token(999, "session-999")

        response = client.get(
            f"/sessions/{test_session_data.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403 or response.status_code == 404

    def test_archive_session(self, client, test_user, valid_jwt_token, test_session_data):
        """Test archiving a session."""
        response = client.post(
            f"/sessions/{test_session_data.id}/archive",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ARCHIVED"

    def test_restore_session(self, client, test_user, valid_jwt_token, test_session_data, db_session):
        """Test restoring archived session."""
        # First archive it
        test_session_data.status = "ARCHIVED"
        test_session_data.archived_at = datetime.utcnow()
        db_session.commit()

        response = client.post(
            f"/sessions/{test_session_data.id}/restore",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"

    def test_delete_session(self, client, test_user, valid_jwt_token, test_session_data):
        """Test deleting a session."""
        response = client.delete(
            f"/sessions/{test_session_data.id}",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200 or response.status_code == 204


class TestChatEndpoints:
    """Test chat endpoints."""

    @patch("api.create_session_chatbot")
    def test_send_message_success(
        self, mock_chatbot, client, test_user, valid_jwt_token, test_session_data
    ):
        """Test sending a message to chatbot."""
        mock_instance = MagicMock()
        mock_instance.chat = MagicMock(return_value="Mocked AI response")
        mock_chatbot.return_value = mock_instance

        response = client.post(
            f"/sessions/{test_session_data.id}/chat",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"message": "What is this document about?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "message" in data

    def test_send_message_unauthorized(self, client, test_session_data):
        """Test sending message without authorization."""
        response = client.post(
            f"/sessions/{test_session_data.id}/chat",
            json={"message": "What is this document about?"},
        )

        assert response.status_code == 401

    def test_send_message_empty(self, client, test_user, valid_jwt_token, test_session_data):
        """Test sending empty message."""
        response = client.post(
            f"/sessions/{test_session_data.id}/chat",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"message": ""},
        )

        assert response.status_code == 400 or response.status_code == 422

    def test_send_message_nonexistent_session(self, client, test_user, valid_jwt_token):
        """Test sending message to nonexistent session."""
        response = client.post(
            "/sessions/99999/chat",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"message": "Hello"},
        )

        assert response.status_code == 404


class TestConversationHistoryEndpoints:
    """Test conversation history endpoints."""

    def test_get_conversation_history(self, client, test_user, valid_jwt_token, test_session_data):
        """Test retrieving conversation history."""
        response = client.get(
            f"/sessions/{test_session_data.id}/history",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data or isinstance(data, list)

    def test_get_conversation_history_paginated(
        self, client, test_user, valid_jwt_token, test_session_data
    ):
        """Test retrieving paginated conversation history."""
        response = client.get(
            f"/sessions/{test_session_data.id}/history?skip=0&limit=10",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should have pagination metadata
        assert "messages" in data or "items" in data or isinstance(data, dict)

    def test_get_conversation_history_unauthorized(self, client, test_session_data):
        """Test getting history without authorization."""
        response = client.get(
            f"/sessions/{test_session_data.id}/history",
        )

        assert response.status_code == 401

    def test_get_conversation_history_nonexistent_session(
        self, client, test_user, valid_jwt_token
    ):
        """Test getting history for nonexistent session."""
        response = client.get(
            "/sessions/99999/history",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
        )

        assert response.status_code == 404


class TestFileUploadEndpoints:
    """Test file upload endpoints."""

    def test_upload_pdf_file(self, client, test_user, valid_jwt_token, test_session_data):
        """Test uploading a PDF file."""
        with patch("api.VectorDBService") as mock_vector_db:
            response = client.post(
                f"/sessions/{test_session_data.id}/upload",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
                files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
            )

            assert response.status_code == 200 or response.status_code == 201

    def test_upload_docx_file(self, client, test_user, valid_jwt_token, test_session_data):
        """Test uploading a DOCX file."""
        with patch("api.VectorDBService"):
            response = client.post(
                f"/sessions/{test_session_data.id}/upload",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
                files={"file": ("test.docx", b"PK\x03\x04...", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )

            assert response.status_code == 200 or response.status_code == 201

    def test_upload_txt_file(self, client, test_user, valid_jwt_token, test_session_data):
        """Test uploading a TXT file."""
        with patch("api.VectorDBService"):
            response = client.post(
                f"/sessions/{test_session_data.id}/upload",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
                files={"file": ("test.txt", b"This is test content", "text/plain")},
            )

            assert response.status_code == 200 or response.status_code == 201

    def test_upload_unsupported_file(self, client, test_user, valid_jwt_token, test_session_data):
        """Test uploading unsupported file type."""
        response = client.post(
            f"/sessions/{test_session_data.id}/upload",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
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

    def test_upload_to_nonexistent_session(self, client, test_user, valid_jwt_token):
        """Test uploading to nonexistent session."""
        response = client.post(
            "/sessions/99999/upload",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_missing_required_fields(self, client):
        """Test missing required fields in request."""
        response = client.post(
            "/register",
            json={"email": "test@example.com"},  # Missing password
        )

        assert response.status_code == 422 or response.status_code == 400

    def test_invalid_json_body(self, client):
        """Test invalid JSON in request body."""
        response = client.post(
            "/register",
            data="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422 or response.status_code == 400

    def test_very_long_password(self, client):
        """Test very long password in registration."""
        response = client.post(
            "/register",
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
            "/register",
            json={
                "email": "' OR '1'='1",
                "password": "password' --",
            },
        )

        # Should not cause SQL injection
        assert response.status_code in [400, 422]


class TestEndpointSecurity:
    """Test security aspects of endpoints."""

    def test_expired_token(self, client, expired_jwt_token):
        """Test using expired token."""
        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {expired_jwt_token}"},
        )

        assert response.status_code == 401

    def test_token_from_different_user(self, client, test_user, valid_jwt_token, db_session):
        """Test using token from different user."""
        from tests.fixtures.factories import SessionFactory

        another_user, _ = UserFactory.create(db_session)
        another_session = SessionFactory.create(db_session, user_id=another_user.id)

        response = client.get(
            f"/sessions/{another_session.id}",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
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
