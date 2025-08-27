# utils/config.py
import os

def get_bot_settings():
    return {
        "agent_url": os.getenv("AGENT_URL", "http://10.250.37.64:8000/api/chat/v1/test"),
        "agent_timeout": float(os.getenv("AGENT_TIMEOUT", "30")),
    }