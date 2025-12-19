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
        ("system", "You have access to a tool that retrieves context from a document. Use the tool to help answer user queries."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    vector_store = create_vector_store(GoogleGenerativeAIEmbeddings(model="models/text-embedding-004"), "documents_collection")
    text = processFile("../resources/bill.pdf")
    chunks = splitTextIntoChunks(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    ids = [f"chunk-{i}" for i in range(len(docs))]
    add_documents_to_vector_store(vector_store, docs, ids)
    pdf_tool = create_retriever_tool(vector_store)
    tools = [pdf_tool]
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
        tools=tools,
        inputMessagesKey="input",
        historyMessagesKey="chat_history"
    )
    return chainWithHistory, sessionId

def chatBot(chainWithHistory, sessionId, humanMessage):
    if not humanMessage:
        return "Please enter a message."
    
    response = chainWithHistory.invoke(
        {"input": humanMessage}, 
        config={"configurable": {"session_id": sessionId}}
    )
    current_history = utils.getJsonSessionHistory(sessionId)
    utils.saveHistoryToJson(sessionId, current_history)
    return response.text
