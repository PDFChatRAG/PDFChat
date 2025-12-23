import os
import logging
from typing import Optional, List, Dict, Any, Set
from langgraph.checkpoint.sqlite import SqliteSaver

logger = logging.getLogger(__name__)

def extract_message_content(msg) -> dict:
    if hasattr(msg, "content"):
        content = msg.content
    else:
        content = str(msg)

    msg_type = msg.__class__.__name__
    role = "assistant"
    if "Human" in msg_type or "User" in msg_type:
        role = "user"
    elif "AI" in msg_type or "Assistant" in msg_type:
        role = "assistant"
    elif "System" in msg_type:
        role = "system"
    elif "Tool" in msg_type:
        role = "tool"

    return {"role": role, "content": content, "type": msg_type}

def get_session_conversation(session_id: str, checkpointer: Any = None, limit: Optional[int] = None) -> dict:
    local_checkpointer = False
    try:
        if not checkpointer:
            # Fallback if checkpointer not provided
            memory_db = os.getenv("AGENT_MEMORY_DB", "agent_memory.db")
            checkpointer = SqliteSaver.from_conn_string(memory_db)
            checkpointer.__enter__()
            local_checkpointer = True

        config = {"configurable": {"thread_id": session_id}}
        all_checkpoints = list(checkpointer.list(config, limit=None))

        if not all_checkpoints:
            return {"session_id": session_id, "messages": [], "checkpoint_count": 0, "message_count": 0}

        all_messages = []
        seen_message_ids = set()

        for checkpoint_tuple in reversed(all_checkpoints):
            checkpoint = checkpoint_tuple[0]
            checkpoint_id = checkpoint_tuple[1]
            state = checkpoint.get("channel_values", {})
            messages = state.get("messages", [])

            for msg_idx, msg in enumerate(messages):
                msg_id = f"{checkpoint_id}_{msg_idx}"
                if msg_id not in seen_message_ids:
                    msg_data = extract_message_content(msg)
                    msg_data["id"] = msg_id
                    msg_data["checkpoint_id"] = checkpoint_id
                    msg_data["timestamp"] = checkpoint.get("ts")
                    all_messages.append(msg_data)
                    seen_message_ids.add(msg_id)

        if limit:
            all_messages = all_messages[-limit:]

        logger.info(f"Retrieved {len(all_messages)} messages from session {session_id}")
        return {"session_id": session_id, "messages": all_messages, "checkpoint_count": len(all_checkpoints), "message_count": len(all_messages)}

    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return {"session_id": session_id, "messages": [], "checkpoint_count": 0, "message_count": 0, "error": str(e)}
    finally:
        if local_checkpointer and checkpointer:
            # We created it, so we should close it.
            # SqliteSaver context manager returns self.
            try:
                checkpointer.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing temporary checkpointer: {e}")
