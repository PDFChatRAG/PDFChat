"""
Unit tests for ChatBot class in chatBot.py
"""
import pytest
from unittest.mock import MagicMock, patch, ANY
import os
from chatBot import ChatBot, create_session_chatbot

# Dummy classes to mock dependencies
class DummyCheckpointer:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-api-key"}):
        yield

@pytest.fixture
def mock_dependencies():
    with patch("chatBot.ChatGoogleGenerativeAI") as mock_llm, \
         patch("chatBot.GoogleGenerativeAIEmbeddings") as mock_embeddings, \
         patch("chatBot.VectorDBService.get_session_retriever") as mock_retriever, \
         patch("chatBot.create_retriever_tool") as mock_tool, \
         patch("chatBot.create_agent") as mock_agent:
        
        mock_retriever.return_value = MagicMock()
        mock_tool.return_value = MagicMock()
        mock_agent.return_value = MagicMock()
        
        yield {
            "llm": mock_llm,
            "embeddings": mock_embeddings,
            "retriever": mock_retriever,
            "tool": mock_tool,
            "agent": mock_agent
        }

class TestChatBot:
    """Test ChatBot class functionality."""

    def test_init(self):
        """Test initialization of ChatBot instance."""
        bot = ChatBot("user1", "session1")
        assert bot.user_id == "user1"
        assert bot.session_id == "session1"
        assert bot.model is None
        assert bot.agent is None

    def test_initialize_success(self, mock_env, mock_dependencies):
        """Test successful initialization with dependencies."""
        bot = ChatBot("user1", "session1")
        checkpointer = DummyCheckpointer()
        
        initialized_bot = bot.initialize(checkpointer)
        
        assert initialized_bot is bot
        assert bot.checkpointer is checkpointer
        assert bot.agent is not None
        
        mock_dependencies["llm"].assert_called_with(
            model="gemini-3-flash-preview", temperature=0
        )
        mock_dependencies["retriever"].assert_called()
        mock_dependencies["agent"].assert_called()

    def test_initialize_missing_api_key(self):
        """Test initialization raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            bot = ChatBot("user1", "session1")
            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                bot.initialize(DummyCheckpointer())

    def test_chat_success(self, mock_env, mock_dependencies):
        """Test successful chat interaction."""
        bot = ChatBot("user1", "session1")
        bot.initialize(DummyCheckpointer())
        
        # Mock agent response
        mock_response = {"messages": [MagicMock(content="Hello user")]}
        bot.agent.invoke.return_value = mock_response
        
        response = bot.chat("Hi")
        assert response == "Hello user"
        
        bot.agent.invoke.assert_called_with(
            {"messages": [("user", "Hi")]},
            config={"configurable": {"thread_id": "session1"}}
        )

    def test_chat_not_initialized(self):
        """Test chat raises error if not initialized."""
        bot = ChatBot("user1", "session1")
        with pytest.raises(RuntimeError, match="not initialized"):
            bot.chat("Hi")

    def test_chat_empty_message(self, mock_env, mock_dependencies):
        """Test chat returns prompt for empty message."""
        bot = ChatBot("user1", "session1")
        bot.initialize(DummyCheckpointer())
        
        response = bot.chat("")
        assert response == "Please enter a message."
        
        response = bot.chat("   ")
        assert response == "Please enter a message."

    def test_chat_no_response(self, mock_env, mock_dependencies):
        """Test chat handles empty response from agent."""
        bot = ChatBot("user1", "session1")
        bot.initialize(DummyCheckpointer())
        
        bot.agent.invoke.return_value = {"messages": []}
        
        response = bot.chat("Hi")
        assert response == "No response generated."

    def test_chat_complex_content(self, mock_env, mock_dependencies):
        """Test chat handles complex content format (list of blocks)."""
        bot = ChatBot("user1", "session1")
        bot.initialize(DummyCheckpointer())
        
        content_blocks = [
            {"type": "text", "text": "This is text response."}, 
            {"type": "image", "image_url": "..."}
        ]
        mock_response = {"messages": [MagicMock(content=content_blocks)]}
        bot.agent.invoke.return_value = mock_response
        
        response = bot.chat("Show me")
        assert response == "This is text response."

    def test_chat_error_handling(self, mock_env, mock_dependencies):
        """Test chat raises exception on agent error."""
        bot = ChatBot("user1", "session1")
        bot.initialize(DummyCheckpointer())
        
        bot.agent.invoke.side_effect = Exception("Agent failed")
        
        with pytest.raises(Exception, match="Agent failed"):
            bot.chat("Hi")

    def test_create_session_chatbot_factory(self, mock_env, mock_dependencies):
        """Test factory function."""
        checkpointer = DummyCheckpointer()
        bot = create_session_chatbot("user1", "session1", checkpointer)
        
        assert isinstance(bot, ChatBot)
        assert bot.checkpointer is checkpointer
        assert bot.agent is not None
