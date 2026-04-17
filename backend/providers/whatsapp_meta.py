import logging
from typing import Any, Dict, List, Optional
import httpx
from backend.config import settings
from backend.utils.whatsapp_localization import get_string

logger = logging.getLogger("rideshield.whatsapp")

class WhatsAppMetaProvider:
    """
    Provider for interacting with the Meta WhatsApp Cloud API with multi-language support.
    """
    
    API_VERSION = "v19.0"
    
    def __init__(self):
        self.access_token = settings.META_ACCESS_TOKEN
        self.phone_number_id = settings.PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/{self.API_VERSION}/{self.phone_number_id}/messages"
        
    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Base method to send requests to Meta API."""
        if not self.access_token or not self.phone_number_id:
            logger.error("WhatsApp credentials missing: META_ACCESS_TOKEN or PHONE_NUMBER_ID")
            return {"error": "Credentials missing", "status": "failed"}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response_data = response.json()
                
                if response.status_code != 200:
                    logger.error(f"WhatsApp API error: {response.status_code} - {response_data}")
                    return {"error": response_data, "status": "failed"}
                
                return response_data
        except Exception as e:
            logger.exception("Failed to send WhatsApp message")
            return {"error": str(e), "status": "failed"}

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a simple text message."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        return await self._send_request(payload)

    async def send_interactive_buttons(self, to: str, body_text: str, buttons: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send an interactive message with buttons (max 3)."""
        formatted_buttons = []
        for btn in buttons[:3]:
            # Meta limit: Button title 20 chars
            title = btn["title"]
            if len(title) > 20:
                title = title[:17] + "..."
                
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": title
                }
            })
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": formatted_buttons}
            }
        }
        return await self._send_request(payload)

    # --- Localized Flow Methods ---

    async def send_lang_selection(self, to: str) -> Dict[str, Any]:
        """Initial step: Select language."""
        body = get_string("lang_select", lang="en")  # Always ask in English first (or bilingual body)
        body = "Please select your language / अपनी भाषा चुनें:"
        buttons = [
            {"id": "lang_en", "title": "English"},
            {"id": "lang_hi", "title": "Hindi (हिंदी)"}
        ]
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_welcome_message(self, to: str, lang: str = "en") -> Dict[str, Any]:
        """Send welcome message in user's language."""
        body = get_string("welcome", lang=lang)
        buttons = [
            {"id": "start", "title": get_string("start_protection", lang=lang)},
            {"id": "status", "title": get_string("check_status", lang=lang)}
        ]
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_role_selection(self, to: str, lang: str = "en") -> Dict[str, Any]:
        """Step 1 of Onboarding: Role."""
        body = get_string("select_role", lang=lang)
        buttons = [
            {"id": "role_rider", "title": get_string("role_rider", lang=lang)},
            {"id": "role_driver", "title": get_string("role_driver", lang=lang)},
            {"id": "role_delivery", "title": get_string("role_delivery", lang=lang)}
        ]
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_hours_selection(self, to: str, lang: str = "en") -> Dict[str, Any]:
        """Step 2 of Onboarding: Hours."""
        body = get_string("select_hours", lang=lang)
        buttons = [
            {"id": "hours_4", "title": get_string("hours_low", lang=lang)},
            {"id": "hours_8", "title": get_string("hours_mid", lang=lang)},
            {"id": "hours_plus", "title": get_string("hours_high", lang=lang)}
        ]
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_onboarding_link(self, to: str, lang: str = "en") -> Dict[str, Any]:
        """Step 3: Deep Link."""
        body = get_string("onboarding_complete", lang=lang)
        # Deep link (using localhost for dev, but would be production URL)
        # Meta doesn't support 'URL' buttons in standard 'interactive button' type,
        # it needs a CTA button template. For now, we'll send it as text or just a button that says 'Open App'
        # followed by a text msg with the link.
        
        await self.send_interactive_buttons(to, body, [{"id": "open_app", "title": get_string("open_app", lang=lang)}])
        
        frontend_url = "http://localhost:3000/onboarding" # In prod, this comes from config
        return await self.send_text_message(to, f"👉 {frontend_url}")

    async def send_proactive_coverage_alert(self, to: str, trigger_type: str, lang: str = "en") -> Dict[str, Any]:
        """Proactive alert when a risk is detected for a covered worker."""
        body = get_string("proactive_covered", lang=lang, trigger=trigger_type.replace("_", " "))
        return await self.send_text_message(to, body)

    # --- Onboarding Methods ---

    async def ask_onboard_name(self, to: str, lang: str = "en") -> Dict[str, Any]:
        """Ask the user for their name."""
        return await self.send_text_message(to, get_string("onboard_name", lang=lang))

    async def send_city_selection(self, to: str, name: str, lang: str = "en") -> Dict[str, Any]:
        """Show city selection buttons."""
        body = get_string("onboard_city", lang=lang, name=name)
        buttons = [
            {"id": "city_delhi", "title": "Delhi"},
            {"id": "city_mumbai", "title": "Mumbai"},
            {"id": "city_bangalore", "title": "Bangalore"}
        ]
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_platform_selection(self, to: str, lang: str = "en") -> Dict[str, Any]:
        """Show platform selection buttons."""
        body = get_string("onboard_platform", lang=lang)
        buttons = [
            {"id": "plat_uber", "title": "Uber"},
            {"id": "plat_zomato", "title": "Zomato"},
            {"id": "plat_swiggy", "title": "Swiggy"}
        ]
        # Max 3 buttons, could add 'Other' if we wanted but let's stick to 3
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_plan_selection(self, to: str, plans: List[Dict], lang: str = "en") -> Dict[str, Any]:
        """Show available plans as buttons."""
        body = get_string("onboard_plan_desc", lang=lang)
        # We can only show up to 3 buttons. We'll show the top 3 plans.
        buttons = []
        for plan in plans[:3]:
            buttons.append({
                "id": f"plan_{plan['plan_name']}_{plan['weekly_premium']}",
                "title": get_string("plan_select", lang=lang, plan=plan["display_name"], price=plan["weekly_premium"])
            })
        return await self.send_interactive_buttons(to, body, buttons)

    async def send_checkout_request(self, to: str, plan_display: str, price: int, lang: str = "en") -> Dict[str, Any]:
        """The 'Payment Gateway' step."""
        body = get_string("checkout_msg", lang=lang, plan=plan_display, price=price)
        buttons = [
            {"id": "pay_success", "title": get_string("pay_now", lang=lang)}
        ]
        return await self.send_interactive_buttons(to, body, buttons)

# Singleton
whatsapp_meta = WhatsAppMetaProvider()
