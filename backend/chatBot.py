import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.agents import create_agent
from langchain_core.tools import create_retriever_tool
from langchain_classic import hub 
from vectorDB import initialize_vector_store
from langgraph.checkpoint.sqlite import SqliteSaver

_memory_manager = SqliteSaver.from_conn_string("agent_memory.db")

def initialize_chatbot(userId):
    model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0)
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vectorDatabase = initialize_vector_store(embedding=embeddings, collection_name="vector_DB")
    
    pdf_tool = create_retriever_tool(
        vectorDatabase.as_retriever(), 
        name="pdf_search", 
        description="Searches through the uploaded document for specific facts."
    )    
    checkpointer = _memory_manager.__enter__()
    agent = create_agent(
        model=model, 
        tools=[pdf_tool], 
        checkpointer=checkpointer,
        system_prompt="You are a helpful assistant. Use your tools to answer user queries."
        )
    return agent, userId

def chatBot(agent, sessionId, humanMessage):
    if not humanMessage:
        return "Please enter a message."
    config = {"configurable": {"thread_id": sessionId}}
    inputs = {"messages": [("user", humanMessage)]}
    response = agent.invoke(inputs, config=config)
    messages = response.get('messages', [])
    last_message = messages[-1]

    if isinstance(last_message.content, list):
        ai_text = next((block['text'] for block in last_message.content if block['type'] == 'text'), "")
    else:
        ai_text = last_message.content

    return(ai_text)