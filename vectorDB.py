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

    @staticmethod
    def get_collection_name(session_id: str, user_id: str) -> str:

        sanitized_user = user_id.lower().replace("-", "_")
        sanitized_session = session_id.lower().replace("-", "_")
        return f"user_{sanitized_user}_session_{sanitized_session}"

    @staticmethod
    def create_session_collection(
        user_id: str, session_id: str, embedding_function
    ) -> Chroma:

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
        vectordb = VectorDBService.create_session_collection(
            user_id, session_id, embedding_function
        )
        return vectordb.as_retriever()






