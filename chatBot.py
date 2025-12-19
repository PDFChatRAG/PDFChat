from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import utils
from vectorDB import create_vector_store, add_documents_to_vector_store, create_retriever_tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from DataSource import processFile, splitTextIntoChunks
from langchain_core.documents import Document 
from langchain.agents import create_agent



def initialize_chatbot(userId):
    sessionId = userId
    model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that helps a new developer learn to use the Google Generative AI API to create a RAG chatbot."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    def get_history(session_id):
        return utils.getJsonSessionHistory(session_id)
    
    def format_input(x):
        if isinstance(x, dict):
            return x
        return {"input": x}
    
    chain = (
        RunnableLambda(format_input)
        | RunnablePassthrough.assign(chat_history=lambda _: [])
        | prompt
        | model
    )

    chainWithHistory = RunnableWithMessageHistory(
        chain,
        get_history,
        inputMessagesKey="input",
        historyMessagesKey="chat_history"
    )
    return chainWithHistory, sessionId

def chatBot(chainWithHistory, sessionId, user_input):

    vector_store = create_vector_store(GoogleGenerativeAIEmbeddings(model="models/text-embedding-004"), "documents_collection")
    text = processFile("bill.pdf")

    
    chunks = splitTextIntoChunks(text)
    docs = [Document(page_content=chunk) for chunk in chunks]

    ids = [f"chunk-{i}" for i in range(len(docs))]
    add_documents_to_vector_store(vector_store, docs, ids)

    model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
    system_msg = (
    "You have access to a tool that retrieves context from a document. "
    "Use the tool to help answer user queries."
    )
    pdf_tool = create_retriever_tool(vector_store)
    tools = [pdf_tool]

    agent = create_agent(model, tools, system_prompt=system_msg)
    print("\n--- PDF Chat Agent Active ---")
    print("Type 'exit' or 'quit' to stop.")

    # Run the agent
    response = agent.invoke({"messages": [("human", user_input)]})
    
    # The agent returns a list of messages; the last one is the AI response
    ai_message = response["messages"][-1].content
    print(f"\nAgent: {ai_message}")
    current_history = utils.getJsonSessionHistory(sessionId)
    utils.saveHistoryToJson(sessionId, current_history)
    return ai_message
