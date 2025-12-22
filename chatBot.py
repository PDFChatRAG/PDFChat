"""
ChatBot factory for creating session-specific chat instances.

Each session gets its own isolated ChatBot instance with:
- Session-specific vector database collection
- Independent chat memory (thread ID)
- Isolated conversation context
"""

import os
import logging
from typing import Tuple
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.agents import create_agent
from langchain_core.tools import create_retriever_tool
from vectorDB import VectorDBService
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables once
load_dotenv()

# Global memory manager (shared across all sessions)
_MEMORY_MANAGER = None


def get_memory_manager():
    """Get or initialize the global memory manager."""
    global _MEMORY_MANAGER
    if _MEMORY_MANAGER is None:
        memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
        _MEMORY_MANAGER = SqliteSaver.from_conn_string(memory_db)
    return _MEMORY_MANAGER


class ChatBot:
    """Session-specific ChatBot instance with isolated memory and vector store."""

    def __init__(self, user_id: str, session_id: str):
        """
        Initialize session-specific ChatBot.

        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        self.user_id = user_id
        self.session_id = session_id
        self.model = None
        self.embeddings = None
        self.vector_store = None
        self.agent = None
        self.checkpointer = None
        logger.info(f"Initialized ChatBot for user {user_id}, session {session_id}")

    def initialize(self) -> "ChatBot":
        """
        Initialize the agent with session-specific settings.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If GOOGLE_API_KEY is not set
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Please set it in your .env file or system environment."
            )

        # Initialize model and embeddings
        self.model = ChatGoogleGenerativeAI(
            model="gemini-3-pro-preview", temperature=0
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004"
        )

        # Create session-specific vector retriever
        retriever = VectorDBService.get_session_retriever(
            self.session_id, self.user_id, self.embeddings
        )

        pdf_tool = create_retriever_tool(
            retriever,
            name="pdf_search",
            description="Searches through the uploaded documents for specific facts.",
        )

        # Get memory manager and create checkpointer with session-specific thread
        memory_manager = get_memory_manager()
        self.checkpointer = memory_manager.__enter__()

        # Create agent with session-isolated thread ID
        self.agent = create_agent(
            model=self.model,
            tools=[pdf_tool],
            checkpointer=self.checkpointer,
            system_prompt=(
                "You are a helpful assistant. Use your tools to answer user queries. "
                "Provide accurate, concise, and helpful responses based on the documents available."
            ),
        )

        logger.info(f"Agent initialized for session {self.session_id}")
        return self

    def chat(self, human_message: str) -> str:
        """
        Process user message and return AI response.

        Args:
            human_message: User's message

        Returns:
            AI response text

        Raises:
            RuntimeError: If agent not initialized
        """
        if not self.agent:
            raise RuntimeError("ChatBot not initialized. Call initialize() first.")

        if not human_message or not human_message.strip():
            return "Please enter a message."

        # Use session_id as thread_id for isolated conversation memory
        config = {"configurable": {"thread_id": self.session_id}}
        inputs = {"messages": [("user", human_message)]}

        try:
            response = self.agent.invoke(inputs, config=config)
            messages = response.get("messages", [])

            if not messages:
                return "No response generated."

            last_message = messages[-1]

            # Extract text content (handles both string and list content)
            if isinstance(last_message.content, list):
                ai_text = next(
                    (block["text"] for block in last_message.content
                     if block.get("type") == "text"),
                    "No text response generated.",
                )
            else:
                ai_text = last_message.content

            return ai_text

        except Exception as e:
            logger.error(f"Error in chat for session {self.session_id}: {e}")
            raise

    def cleanup(self):
        """Clean up resources."""
        if self.checkpointer:
            try:
                get_memory_manager().__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


def create_session_chatbot(user_id: str, session_id: str) -> ChatBot:
    """
    Factory function to create a session-specific ChatBot instance.

    Args:
        user_id: User identifier
        session_id: Session identifier

    Returns:
        Initialized ChatBot instance

    Raises:
        ValueError: If GOOGLE_API_KEY is not set
    """
    chatbot = ChatBot(user_id, session_id)
    chatbot.initialize()
    return chatbot


# Legacy global instance for backward compatibility
_LEGACY_CHATBOT = None


def get_legacy_chatbot() -> ChatBot:
    """
    Get or create legacy global ChatBot instance.

    DEPRECATED: Use create_session_chatbot() for new code.
    This is provided only for backward compatibility.
    """
    global _LEGACY_CHATBOT
    if _LEGACY_CHATBOT is None:
        _LEGACY_CHATBOT = ChatBot(user_id="legacy", session_id="legacy")
        _LEGACY_CHATBOT.initialize()
    return _LEGACY_CHATBOT