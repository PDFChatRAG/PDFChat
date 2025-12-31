import os
import logging
from typing import Tuple, Any
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.agents import create_agent
from langchain_core.tools import create_retriever_tool
from vectorDB import VectorDBService
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables once
load_dotenv()


class ChatBot:

    def __init__(self, user_id: str, session_id: str):

        self.user_id = user_id
        self.session_id = session_id
        self.model = None
        self.embeddings = None
        self.vector_store = None
        self.agent = None
        self.checkpointer = None
        logger.info(f"Initialized ChatBot for user {user_id}, session {session_id}")

    def initialize(self, checkpointer: Any) -> "ChatBot":
  
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

        self.checkpointer = checkpointer

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


def generate_session_title(first_message: str) -> str:
    """Generate a concise title from the first user message.
    
    Args:
        first_message: The first message from the user
        
    Returns:
        A short descriptive title
    """
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "New Conversation"
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", 
            temperature=0
        )
        
        prompt = f"""Generate a short, descriptive title for a conversation that starts with:
"{first_message}"

Return only the title, nothing else. Do not use quotes."""
        
        response = llm.invoke(prompt)
        title = response.content.strip()
        
        # Remove quotes if present
        title = title.strip('"\"').strip("'")
        
        # Limit to 60 characters
        if len(title) > 60:
            title = title[:57] + "..."
            
        return title if title else "New Conversation"
        
    except Exception as e:
        logger.warning(f"Failed to generate session title: {e}")
        return "New Conversation"


def create_session_chatbot(user_id: str, session_id: str, checkpointer: Any) -> ChatBot:

    chatbot = ChatBot(user_id, session_id)
    chatbot.initialize(checkpointer)
    return chatbot
