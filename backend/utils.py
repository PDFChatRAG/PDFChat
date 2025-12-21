import json
import os
from langchain_core.messages import messages_from_dict, messages_to_dict
from langchain_community.chat_message_histories import ChatMessageHistory

def getJsonSessionHistory(session_id: str):
    os.makedirs("history", exist_ok=True)

    file_path = f"history/history_{session_id}.json"
    history = ChatMessageHistory()
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                content = json.load(f)
                history.add_messages(messages_from_dict(content))
            except json.JSONDecodeError:
                pass # File is empty or corrupt
                
    return history

def saveHistoryToJson(session_id: str, history: ChatMessageHistory):
    os.makedirs("history", exist_ok=True)
    file_path = f"history/history_{session_id}.json"
    messages_dict = messages_to_dict(history.messages)
    with open(file_path, "w") as f:
        json.dump(messages_dict, f, indent=4)