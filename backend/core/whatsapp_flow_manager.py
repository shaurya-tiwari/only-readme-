from enum import Enum
from typing import Dict, Any, Optional

class FlowState(Enum):
    START = "start"
    LANG_SELECTION = "lang_selection"
    MAIN_MENU = "main_menu"
    ONBOARD_ROLE_SELECTION = "onboard_role_selection"
    ONBOARD_NAME = "onboard_name"
    ONBOARD_CITY = "onboard_city"
    ONBOARD_PLATFORM = "onboard_platform"
    ONBOARD_PLAN = "onboard_plan"
    ONBOARD_PAYMENT = "onboard_payment"
    COMPLETED = "completed"

class WhatsAppFlowManager:
    """In-memory session manager for WhatsApp conversation state."""
    
    def __init__(self):
        # session store: phone -> {state: FlowState, data: dict}
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, phone: str) -> Dict[str, Any]:
        """Get or initialize a session for a phone number."""
        if phone not in self._sessions:
            self._sessions[phone] = {
                "state": FlowState.START,
                "data": {}
            }
        return self._sessions[phone]

    def set_state(self, phone: str, state: FlowState):
        """Update the state for a phone number."""
        session = self.get_session(phone)
        session["state"] = state

    def update_data(self, phone: str, key: str, value: Any):
        """Store transient data for a phone number."""
        session = self.get_session(phone)
        session["data"][key] = value

    def clear_session(self, phone: str):
        """Reset the flow."""
        if phone in self._sessions:
            del self._sessions[phone]

whatsapp_flow = WhatsAppFlowManager()
