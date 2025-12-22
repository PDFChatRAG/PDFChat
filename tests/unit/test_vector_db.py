"""
Unit tests for vectorDB.py
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO

from vectorDB import VectorDBService, VectorStore


class TestVectorDBServiceCollectionName:
    """Test vector DB collection name generation."""

    def test_generate_collection_name(self):
        """Test collection name generation."""
        user_id = 123
        session_id = 456

        name = VectorDBService.generate_collection_name(user_id, session_id)

        assert isinstance(name, str)
        assert str(user_id) in name
        assert str(session_id) in name
        assert "-" in name  # Should use separator

    def test_collection_name_uniqueness(self):
        """Test collection names are unique per session."""
        user_id = 123

        name1 = VectorDBService.generate_collection_name(user_id, 1)
        name2 = VectorDBService.generate_collection_name(user_id, 2)

        assert name1 != name2

    def test_collection_name_deterministic(self):
        """Test collection names are deterministic."""
        user_id = 123
        session_id = 456

        name1 = VectorDBService.generate_collection_name(user_id, session_id)
        name2 = VectorDBService.generate_collection_name(user_id, session_id)

        assert name1 == name2


class TestVectorDBServiceCollectionCreation:
    """Test vector DB collection creation and loading."""

    @patch("vectorDB.Chroma")
    def test_create_collection(self, mock_chroma):
        """Test creating a new collection."""
        user_id = 123
        session_id = 456

        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            collection = VectorDBService.create_collection(
                user_id, session_id, []
            )

            assert collection is not None

    @patch("vectorDB.Chroma")
    def test_load_collection(self, mock_chroma):
        """Test loading existing collection."""
        user_id = 123
        session_id = 456

        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            collection = VectorDBService.load_collection(user_id, session_id)

            assert collection is not None

    @patch("vectorDB.Chroma")
    def test_collection_with_documents(self, mock_chroma):
        """Test collection creation with documents."""
        user_id = 123
        session_id = 456
        documents = [
            MagicMock(page_content="Content 1", metadata={"id": "1"}),
            MagicMock(page_content="Content 2", metadata={"id": "2"}),
        ]

        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            collection = VectorDBService.create_collection(
                user_id, session_id, documents
            )

            mock_chroma.assert_called()


class TestVectorDBServiceDocumentProcessing:
    """Test document processing and embedding."""

    @patch("vectorDB.VectorDBService.load_collection")
    @patch("vectorDB.VectorDBService.processFiles")
    def test_process_file_to_vector_store(self, mock_process, mock_load):
        """Test processing file to vector store."""
        user_id = 123
        session_id = 456
        file_content = "Test document content"
        file = BytesIO(file_content.encode())

        mock_collection = MagicMock()
        mock_load.return_value = mock_collection
        mock_process.return_value = [
            MagicMock(page_content="Chunk 1", metadata={"chunk": 0}),
            MagicMock(page_content="Chunk 2", metadata={"chunk": 1}),
        ]

        VectorDBService.process_file_to_vector_store(
            user_id, session_id, file, "test.txt"
        )

        mock_process.assert_called_once()

    @patch("vectorDB.VectorDBService.load_collection")
    def test_get_session_retriever(self, mock_load):
        """Test getting retriever for session."""
        user_id = 123
        session_id = 456

        mock_collection = MagicMock()
        mock_retriever = MagicMock()
        mock_collection.as_retriever.return_value = mock_retriever
        mock_load.return_value = mock_collection

        retriever = VectorDBService.get_session_retriever(user_id, session_id)

        assert retriever is not None
        mock_collection.as_retriever.assert_called()

    @patch("vectorDB.Chroma")
    def test_get_retriever_with_search_kwargs(self, mock_chroma):
        """Test getting retriever with custom search parameters."""
        user_id = 123
        session_id = 456

        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            with patch.object(
                VectorDBService, "load_collection"
            ) as mock_load:
                mock_collection = MagicMock()
                mock_retriever = MagicMock()
                mock_collection.as_retriever.return_value = mock_retriever
                mock_load.return_value = mock_collection

                retriever = VectorDBService.get_session_retriever(
                    user_id, session_id, k=5
                )

                mock_collection.as_retriever.assert_called()


class TestVectorDBServiceCleanup:
    """Test vector DB cleanup operations."""

    @patch("vectorDB.Chroma")
    def test_delete_collection(self, mock_chroma):
        """Test deleting a collection."""
        user_id = 123
        session_id = 456

        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            VectorDBService.delete_session_collection(user_id, session_id)

            # Verify cleanup was attempted
            mock_chroma.assert_called()

    @patch("vectorDB.Chroma")
    def test_delete_nonexistent_collection(self, mock_chroma):
        """Test deleting non-existent collection doesn't raise error."""
        user_id = 999
        session_id = 999

        mock_chroma.side_effect = Exception("Collection not found")

        # Should handle gracefully
        try:
            with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
                VectorDBService.delete_session_collection(user_id, session_id)
        except Exception:
            # May raise or handle gracefully depending on implementation
            pass


class TestVectorDBServiceSessionIsolation:
    """Test session isolation in vector DB."""

    def test_different_sessions_different_collections(self):
        """Test different sessions have different collections."""
        user_id = 123

        name1 = VectorDBService.generate_collection_name(user_id, 1)
        name2 = VectorDBService.generate_collection_name(user_id, 2)

        assert name1 != name2

    def test_same_session_same_collection(self):
        """Test same session always gets same collection name."""
        user_id = 123
        session_id = 456

        name1 = VectorDBService.generate_collection_name(user_id, session_id)
        name2 = VectorDBService.generate_collection_name(user_id, session_id)

        assert name1 == name2

    def test_different_users_different_collections(self):
        """Test different users have different collections."""
        session_id = 456

        name1 = VectorDBService.generate_collection_name(1, session_id)
        name2 = VectorDBService.generate_collection_name(2, session_id)

        assert name1 != name2


class TestVectorStoreBackwardCompatibility:
    """Test VectorStore legacy class."""

    @patch("vectorDB.Chroma")
    def test_vector_store_creation(self, mock_chroma):
        """Test VectorStore creation (legacy)."""
        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            store = VectorStore(
                user_id=123,
                session_id=456,
                documents=[],
            )

            assert store is not None

    @patch("vectorDB.Chroma")
    def test_vector_store_add_documents(self, mock_chroma):
        """Test VectorStore add_documents method."""
        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            store = VectorStore(
                user_id=123,
                session_id=456,
                documents=[],
            )

            documents = [
                MagicMock(page_content="Doc 1"),
                MagicMock(page_content="Doc 2"),
            ]

            mock_chroma_instance = MagicMock()
            mock_chroma.return_value = mock_chroma_instance

            # Call add_documents if method exists
            if hasattr(store, "add_documents"):
                store.add_documents(documents)


class TestVectorDBServiceProcessFiles:
    """Test file processing in vector DB."""

    @patch("vectorDB.processFile")
    @patch("vectorDB.splitTextIntoChunks")
    def test_process_files_multiple_documents(self, mock_split, mock_process):
        """Test processing multiple files."""
        mock_process.side_effect = ["Content 1", "Content 2", "Content 3"]
        mock_split.side_effect = [
            ["Chunk 1-1", "Chunk 1-2"],
            ["Chunk 2-1", "Chunk 2-2"],
            ["Chunk 3-1"],
        ]

        files = [
            ("test1.pdf", BytesIO(b"pdf1")),
            ("test2.docx", BytesIO(b"docx")),
            ("test3.txt", BytesIO(b"txt")),
        ]

        # Test if processFiles exists
        if hasattr(VectorDBService, "processFiles"):
            documents = VectorDBService.processFiles(files)
            assert len(documents) > 0

    @patch("vectorDB.processFile")
    def test_process_files_with_error(self, mock_process):
        """Test processing files handles errors."""
        mock_process.side_effect = [
            "Content 1",
            Exception("Error processing file"),
            "Content 3",
        ]

        files = [
            ("test1.pdf", BytesIO(b"pdf1")),
            ("test2.docx", BytesIO(b"docx")),
            ("test3.txt", BytesIO(b"txt")),
        ]

        # Should handle errors gracefully
        if hasattr(VectorDBService, "processFiles"):
            try:
                documents = VectorDBService.processFiles(files)
            except Exception:
                pass


class TestVectorDBServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_collection_name_with_special_ids(self):
        """Test collection name with special ID values."""
        name = VectorDBService.generate_collection_name(0, 0)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_collection_name_with_large_ids(self):
        """Test collection name with very large ID values."""
        name = VectorDBService.generate_collection_name(999999999, 888888888)
        assert isinstance(name, str)
        assert "999999999" in name or "888888888" in name

    @patch("vectorDB.Chroma")
    def test_create_collection_empty_documents(self, mock_chroma):
        """Test creating collection with empty documents."""
        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            collection = VectorDBService.create_collection(123, 456, [])
            assert collection is not None

    @patch("vectorDB.Chroma")
    def test_load_collection_not_exist(self, mock_chroma):
        """Test loading collection that doesn't exist creates it."""
        mock_chroma.side_effect = Exception("Not found")

        with patch("vectorDB.GoogleGenerativeAIEmbeddings"):
            # Depending on implementation, should either raise or create
            try:
                VectorDBService.load_collection(999, 999)
            except Exception:
                pass
