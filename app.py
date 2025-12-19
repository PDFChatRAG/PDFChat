import os
import dotenv
import getpass
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document 
from langchain_chroma import Chroma
from langchain.agents import create_agent

from vectorDB import create_vector_store, add_documents_to_vector_store, create_retriever_tool
from DataSource import processFile, splitTextIntoChunks

import chatBot

dotenv.load_dotenv()
def main():
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google API key: ")

    print("Please Enter User ID: ")
    userId = input().strip()
    chatWithMemory, sessionId = chatBot.initialize_chatbot(userId)

    while True:
        user_input = input("\nInput a question: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if not user_input.strip():
            continue
        print(chatBot.chatBot(chatWithMemory, sessionId, user_input))
    


if __name__ == "__main__":
    main()