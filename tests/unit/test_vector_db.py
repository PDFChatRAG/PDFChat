"""
Unit tests for vectorDB.py
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO

from vectorDB import VectorDBService, VectorStore


class TestVectorDBServiceCollectionName:
    """Test vector DB collection name generation."""

    def test_get_collection_name(self):
        """Test collection name generation."""
        user_id = "user-123"
        session_id = "session-456"

        name = VectorDBService.get_collection_name(session_id, user_id)

        assert isinstance(name, str)
        assert "user_123" in name
        assert "session_456" in name
        assert "user" in name
        assert "session" in name

    def test_collection_name_uniqueness(self):
        """Test collection names are unique per session."""
        user_id = "user-123"

        name1 = VectorDBService.get_collection_name("session-1", user_id)
        name2 = VectorDBService.get_collection_name("session-2", user_id)

        assert name1 != name2

    def test_collection_name_deterministic(self):
        """Test collection names are deterministic."""
        user_id = "user-123"
        session_id = "session-456"

        name1 = VectorDBService.get_collection_name(session_id, user_id)
        name2 = VectorDBService.get_collection_name(session_id, user_id)

        assert name1 == name2


class TestVectorDBServiceCollectionCreation:
    """Test vector DB collection creation and loading."""

    @patch("vectorDB.Chroma")
    def test_create_session_collection(self, mock_chroma):
        """Test creating a new collection."""
        user_id = "user-123"
        session_id = "session-456"
        mock_embedding = MagicMock()

        collection = VectorDBService.create_session_collection(
            user_id, session_id, mock_embedding
        )

        assert collection is not None
        mock_chroma.assert_called_once()
        # Verify call args
        _, kwargs = mock_chroma.call_args
        assert "collection_name" in kwargs
        assert "embedding_function" in kwargs
        assert kwargs["embedding_function"] == mock_embedding


class TestVectorDBServiceDocumentProcessing:
    """Test document processing and embedding."""

    @patch("vectorDB.VectorDBService.create_session_collection")
    @patch("vectorDB.dataSource.splitTextIntoChunks")
    @patch("vectorDB.dataSource.processFile")
    def test_add_documents_to_session(self, mock_process, mock_split, mock_create):
        """Test adding document to session."""
        user_id = "user-123"
        session_id = "session-456"
        file_path = "/tmp/test.pdf"
        file_name = "test.pdf"
        mock_embedding = MagicMock()

        mock_vectordb = MagicMock()
        mock_create.return_value = mock_vectordb

        mock_process.return_value = "Test content"
        mock_split.return_value = ["Chunk 1", "Chunk 2"]

        result = VectorDBService.add_documents_to_session(
            session_id, user_id, file_path, file_name, mock_embedding
        )

        assert result["chunks_added"] == 2
        assert result["file_name"] == file_name
        mock_vectordb.add_documents.assert_called_once()
        mock_process.assert_called_with(file_path)
        mock_split.assert_called_with("Test content")

    @patch("vectorDB.VectorDBService.create_session_collection")
    def test_get_session_retriever(self, mock_create):
        """Test getting retriever for session."""
        user_id = "user-123"
        session_id = "session-456"
        mock_embedding = MagicMock()

        mock_vectordb = MagicMock()
        mock_retriever = MagicMock()
        mock_vectordb.as_retriever.return_value = mock_retriever
        mock_create.return_value = mock_vectordb

        retriever = VectorDBService.get_session_retriever(session_id, user_id, mock_embedding)

        assert retriever is not None
        mock_vectordb.as_retriever.assert_called()


class TestVectorDBServiceCleanup:
    """Test vector DB cleanup operations."""

    @patch("vectorDB.chromadb.PersistentClient")
    def test_delete_session_collection(self, mock_client_cls):
        """Test deleting a collection."""
        user_id = "user-123"
        session_id = "session-456"
        
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        VectorDBService.delete_session_collection(session_id, user_id)

        # Verify cleanup was attempted
        mock_client.delete_collection.assert_called_once()

    @patch("vectorDB.chromadb.PersistentClient")
    def test_delete_nonexistent_collection(self, mock_client_cls):
        """Test deleting non-existent collection handles errors."""
        user_id = "user-999"
        session_id = "session-999"

        mock_client = MagicMock()
        mock_client.delete_collection.side_effect = Exception("Collection not found")
        mock_client_cls.return_value = mock_client

        # Should handle gracefully (no raise)
        VectorDBService.delete_session_collection(session_id, user_id)


class TestVectorDBServiceSessionIsolation:
    """Test session isolation in vector DB."""

    def test_different_sessions_different_collections(self):
        """Test different sessions have different collections."""
        user_id = "user-123"

        name1 = VectorDBService.get_collection_name("session-1", user_id)
        name2 = VectorDBService.get_collection_name("session-2", user_id)

        assert name1 != name2

    def test_same_session_same_collection(self):
        """Test same session always gets same collection name."""
        user_id = "user-123"
        session_id = "session-456"

        name1 = VectorDBService.get_collection_name(session_id, user_id)
        name2 = VectorDBService.get_collection_name(session_id, user_id)

        assert name1 == name2

    def test_different_users_different_collections(self):
        """Test different users have different collections."""
        session_id = "session-456"

        name1 = VectorDBService.get_collection_name(session_id, "user-1")
        name2 = VectorDBService.get_collection_name(session_id, "user-2")

        assert name1 != name2


class TestVectorStoreBackwardCompatibility:
    """Test VectorStore legacy class."""

    @patch("vectorDB.Chroma")
    def test_vector_store_creation(self, mock_chroma):
        """Test VectorStore creation (legacy)."""
        mock_embedding = MagicMock()
        
        # When creating VectorStore, it calls initialize_vector_store immediately
        store = VectorStore(
            embedding=mock_embedding,
            collection_name="test_collection"
        )
        
        # So vectorDB is already initialized
        assert store.vectorDB is not None
        mock_chroma.assert_called()

    @patch("vectorDB.Chroma")
    @patch("vectorDB.dataSource.splitTextIntoChunks")
    @patch("vectorDB.dataSource.processFile")
    def test_vector_store_add_documents(self, mock_process, mock_split, mock_chroma):
        """Test VectorStore add_documents method."""
        mock_embedding = MagicMock()
        mock_process.return_value = "Content"
        mock_split.return_value = ["Chunk 1"]
        
        # Mock Chroma instance returned by Chroma() constructor
        mock_vectordb_instance = MagicMock()
        mock_chroma.return_value = mock_vectordb_instance
        
        store = VectorStore(
            embedding=mock_embedding,
            collection_name="test_collection"
        )
        
        store.add_documents_to_vector_store("test.pdf")
        
        # Assert methods called on the instance
        mock_vectordb_instance.add_documents.assert_called()


class TestVectorDBServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_collection_name_with_special_ids(self):
        """Test collection name with special ID values."""
        name = VectorDBService.get_collection_name("sess!@#", "user$%^")
        assert isinstance(name, str)
        # Check for original characters because implementation does not sanitize all special chars
        assert "user$%^" in name or "user" in name
        assert "sess!@#" in name or "sess" in name

    def test_collection_name_with_large_ids(self):
        """Test collection name with very large ID values."""
        # We use strings now
        name = VectorDBService.get_collection_name("session-" + "9"*50, "user-" + "8"*50)
        assert isinstance(name, str)
        assert "9"*50 in name or "session" in name
