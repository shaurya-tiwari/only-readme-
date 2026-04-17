from typing import Any, Dict, Optional

def get_message_text(message: Dict[str, Any]) -> str:
    """Extract text from an incoming WhatsApp message."""
    msg_type = message.get("type")
    if msg_type == "text":
        return message.get("text", {}).get("body", "").strip()
    elif msg_type == "interactive":
        # Check if it's a button reply
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("title", "").strip()
    return ""

def get_button_reply_id(message: Dict[str, Any]) -> Optional[str]:
    """Extract the button ID from an interactive button reply."""
    msg_type = message.get("type")
    if msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("id")
    return None

def is_greeting(text: str) -> bool:
    """Check if the normalized text is a greeting."""
    if not text:
        return False
    
    # Common greetings and their variations
    greetings = {"hi", "hii", "hiii", "hello", "hey", "heey", "heeyy", "heyo", "hola", "namaste", "morning", "evening"}
    
    normalized = text.lower().strip().rstrip("!?. ")
    return normalized in greetings or normalized.startswith(("hi ", "hey ", "hello "))

def normalize_phone(phone: str) -> str:
    """
    Ensure phone number is in digits-only format without leading '+'.
    Example: '+91 98765-43210' -> '919876543210'
    """
    return "".join(filter(str.isdigit, phone))
