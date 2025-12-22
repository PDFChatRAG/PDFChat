"""
Mock implementations for external dependencies.
"""
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime


class MockLLM(MagicMock):
    """Mock Google Generative AI LLM."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoke = MagicMock(return_value="This is a mocked AI response.")
        self.stream = AsyncMock(return_value=AsyncMock())


class MockEmbeddings(MagicMock):
    """Mock Google Generative AI Embeddings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embed_documents = MagicMock(
            return_value=[[0.1, 0.2, 0.3] * 384 for _ in range(5)]
        )
        self.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3] * 384)


class MockChromaVector(MagicMock):
    """Mock Chroma vector store."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.similarity_search = MagicMock(
            return_value=[
                MagicMock(page_content="Mock document content 1", metadata={"id": "1"}),
                MagicMock(page_content="Mock document content 2", metadata={"id": "2"}),
            ]
        )
        self.add_documents = MagicMock(return_value=["doc1", "doc2"])
        self.delete = MagicMock(return_value=None)
        self.as_retriever = MagicMock(
            return_value=MagicMock(
                invoke=MagicMock(
                    return_value=[
                        MagicMock(page_content="Retrieved document", metadata={"id": "1"})
                    ]
                )
            )
        )


class MockCheckpointer(MagicMock):
    """Mock LangGraph SqliteSaver."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_checkpoint = AsyncMock(return_value=None)
        self.put_checkpoint = AsyncMock(return_value=None)
        self.list_checkpoints = AsyncMock(return_value=[])


class MockMessage(MagicMock):
    """Mock LangChain Message object."""

    def __init__(self, content: str, message_type: str = "human"):
        super().__init__()
        self.content = content
        self.type = message_type

    def __str__(self):
        return self.content


class MockAIMessage(MockMessage):
    """Mock LangChain AIMessage."""

    def __init__(self, content: str):
        super().__init__(content, message_type="ai")


class MockHumanMessage(MockMessage):
    """Mock LangChain HumanMessage."""

    def __init__(self, content: str):
        super().__init__(content, message_type="human")


class MockRetriever(MagicMock):
    """Mock document retriever."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoke = MagicMock(
            return_value=[
                MagicMock(page_content="Mock retrieved content 1"),
                MagicMock(page_content="Mock retrieved content 2"),
            ]
        )
        self.get_relevant_documents = MagicMock(
            return_value=[
                MagicMock(page_content="Mock relevant content"),
            ]
        )
