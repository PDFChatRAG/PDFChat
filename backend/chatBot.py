from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import utils

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