"""Vector database service with session isolation for multi-tenant, multi-session architecture."""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from datetime import datetime
import dataSource
import chromadb
import logging
import os

logger = logging.getLogger(__name__)

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")


class VectorDBService:
    """Service for managing isolated vector stores per session."""

    @staticmethod
    def get_collection_name(session_id: str, user_id: str) -> str:
        """
        Generate collection name for user session.

        Naming convention: user_<user_id>_session_<session_id>
        Enables rapid isolation and multi-tenancy
        """
        sanitized_user = user_id.lower().replace("-", "_")
        sanitized_session = session_id.lower().replace("-", "_")
        return f"user_{sanitized_user}_session_{sanitized_session}"

    @staticmethod
    def create_session_collection(
        user_id: str, session_id: str, embedding_function
    ) -> Chroma:
        """
        Create isolated collection for user session.

        Args:
            user_id: User identifier
            session_id: Session identifier
            embedding_function: LangChain embedding function

        Returns:
            Chroma vector store instance
        """
        collection_name = VectorDBService.get_collection_name(session_id, user_id)

        vectordb = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_function,
            persist_directory=CHROMA_PATH,
        )
        logger.info(f"Created/loaded collection: {collection_name}")
        return vectordb

    @staticmethod
    def delete_session_collection(session_id: str, user_id: str):
        """
        Delete collection when session is archived/deleted.

        Args:
            session_id: Session identifier
            user_id: User identifier
        """
        collection_name = VectorDBService.get_collection_name(session_id, user_id)

        try:
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Error deleting collection {collection_name}: {e}")
            # Non-fatal error - collection might not exist

    @staticmethod
    def add_documents_to_session(
        session_id: str,
        user_id: str,
        file_path: str,
        file_name: str,
        embedding_function,
    ) -> dict:
        """
        Add document to session-specific collection.

        Args:
            session_id: Session identifier
            user_id: User identifier
            file_path: Path to file to process
            file_name: Original file name
            embedding_function: LangChain embedding function

        Returns:
            Dict with document metadata (chunks added, document id)
        """
        vectordb = VectorDBService.create_session_collection(
            user_id, session_id, embedding_function
        )

        # Process file into chunks
        text = dataSource.processFile(file_path)
        chunks = dataSource.splitTextIntoChunks(text)

        # Include metadata for tracking
        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "source_file": file_name,
                    "chunk_index": i,
                    "uploaded_at": datetime.now().isoformat(),
                },
            )
            for i, chunk in enumerate(chunks)
        ]

        # Generate unique document IDs with file context
        doc_ids = [f"{file_name}_chunk_{i}" for i in range(len(docs))]
        
        vectordb.add_documents(documents=docs, ids=doc_ids)
        logger.info(
            f"Added {len(docs)} chunks from {file_name} to session {session_id}"
        )

        return {
            "file_name": file_name,
            "chunks_added": len(docs),
            "collection": VectorDBService.get_collection_name(session_id, user_id),
        }

    @staticmethod
    def get_session_retriever(
        session_id: str, user_id: str, embedding_function
    ):
        """
        Get retriever for session-specific vector store.

        Args:
            session_id: Session identifier
            user_id: User identifier
            embedding_function: LangChain embedding function

        Returns:
            LangChain retriever for the session's collection
        """
        vectordb = VectorDBService.create_session_collection(
            user_id, session_id, embedding_function
        )
        return vectordb.as_retriever()


# Legacy class for backward compatibility during migration
class VectorStore:
    """Legacy vector store class - use VectorDBService for new code."""

    def __init__(self, embedding, collection_name):
        self.embedding = embedding
        self.collection_name = collection_name
        self.vectorDB = None
        self.initialize_vector_store()

    def create_vector_store(self):
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding,
            persist_directory=CHROMA_PATH,
        )

    def initialize_vector_store(self):
        if self.vectorDB is None:
            self.vectorDB = self.create_vector_store()
        return self.vectorDB

    def add_documents_to_vector_store(self, file_path):
        if self.vectorDB is None:
            self.initialize_vector_store()

        text = dataSource.processFile(file_path)
        chunks = dataSource.splitTextIntoChunks(text)
        docs = [Document(page_content=chunk) for chunk in chunks]
        ids = [f"chunk-{i}" for i in range(len(docs))]
        self.vectorDB.add_documents(documents=docs, ids=ids)
        return self.vectorDB

    def get_vector_store(self):
        if self.vectorDB is None:
            self.initialize_vector_store()
        return self.vectorDB

    def as_retriever(self):
        if self.vectorDB is None:
            self.initialize_vector_store()
        return self.vectorDB.as_retriever()



