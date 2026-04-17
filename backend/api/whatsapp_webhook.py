import logging
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse

from backend.config import settings
from backend.providers.whatsapp_meta import whatsapp_meta
from backend.providers.whatsapp_settings_service import whatsapp_settings
from backend.providers.whatsapp_data_service import whatsapp_data
from backend.providers.whatsapp_onboarding_service import whatsapp_onboarding
from backend.core.whatsapp_flow_manager import whatsapp_flow, FlowState
from backend.utils import whatsapp_helpers
from backend.utils.whatsapp_localization import get_string

logger = logging.getLogger("rideshield.whatsapp")

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return hub_challenge
    
    logger.warning("WhatsApp webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()
    logger.info(f"WhatsApp Webhook Payload: {payload}")
    
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            
            for message in messages:
                sender_phone = message.get("from")
                msg_text = whatsapp_helpers.get_message_text(message)
                button_id = whatsapp_helpers.get_button_reply_id(message)
                
                lang = await whatsapp_settings.get_user_lang(sender_phone)
                session = whatsapp_flow.get_session(sender_phone)
                
                logger.debug(f"WA processing: {sender_phone} | State: {session['state']} | Button: {button_id} | Text: {msg_text}")
                
                # --- Shared Handlers ---
                
                # Language Selection
                if button_id and button_id.startswith("lang_"):
                    chosen_lang = "hi" if button_id == "lang_hi" else "en"
                    await whatsapp_settings.set_user_lang(sender_phone, chosen_lang)
                    whatsapp_flow.set_state(sender_phone, FlowState.MAIN_MENU)
                    await whatsapp_meta.send_welcome_message(sender_phone, lang=chosen_lang)
                    continue

                # Greeting
                if whatsapp_helpers.is_greeting(msg_text) or button_id == "restart":
                    await whatsapp_meta.send_lang_selection(sender_phone)
                    whatsapp_flow.set_state(sender_phone, FlowState.LANG_SELECTION)
                    continue

                # --- State Dependent Logic ---

                state = session["state"]

                # 1. Main Menu
                if state == FlowState.MAIN_MENU:
                    if button_id == "start":
                        await whatsapp_meta.ask_onboard_name(sender_phone, lang=lang)
                        whatsapp_flow.set_state(sender_phone, FlowState.ONBOARD_NAME)
                    elif button_id == "status":
                        await handle_status_check(sender_phone, lang)
                
                # 2. Capture Name
                elif state == FlowState.ONBOARD_NAME:
                    if msg_text:
                        name = msg_text.strip()
                        whatsapp_flow.update_data(sender_phone, "name", name)
                        await whatsapp_meta.send_city_selection(sender_phone, name=name, lang=lang)
                        whatsapp_flow.set_state(sender_phone, FlowState.ONBOARD_CITY)

                # 3. Capture City
                elif state == FlowState.ONBOARD_CITY:
                    if button_id and button_id.startswith("city_"):
                        city_slug = button_id.replace("city_", "")
                        whatsapp_flow.update_data(sender_phone, "city_slug", city_slug)
                        await whatsapp_meta.send_platform_selection(sender_phone, lang=lang)
                        whatsapp_flow.set_state(sender_phone, FlowState.ONBOARD_PLATFORM)

                # 4. Capture Platform
                elif state == FlowState.ONBOARD_PLATFORM:
                    if button_id and button_id.startswith("plat_"):
                        platform = button_id.replace("plat_", "")
                        whatsapp_flow.update_data(sender_phone, "platform", platform)
                        
                        # Fetch plans based on city
                        city_slug = session["data"]["city_slug"]
                        plan_data = await whatsapp_onboarding.get_plans_for_city(city_slug)
                        
                        if "error" in plan_data:
                            await whatsapp_meta.send_text_message(sender_phone, f"Sorry, we don't support {city_slug} yet.")
                            whatsapp_flow.set_state(sender_phone, FlowState.MAIN_MENU)
                        else:
                            whatsapp_flow.update_data(sender_phone, "risk_score", plan_data["risk_score"])
                            whatsapp_flow.update_data(sender_phone, "zone_id", plan_data["zone_id"])
                            whatsapp_flow.update_data(sender_phone, "city_id", plan_data["city_id"])
                            whatsapp_flow.update_data(sender_phone, "zone_slug", plan_data["zone_slug"])
                            
                            await whatsapp_meta.send_plan_selection(sender_phone, plan_data["plans"], lang=lang)
                            whatsapp_flow.set_state(sender_phone, FlowState.ONBOARD_PLAN)

                # 5. Capture Plan
                elif state == FlowState.ONBOARD_PLAN:
                    if button_id and button_id.startswith("plan_"):
                        # format: plan_{plan_name}_{price}
                        # Use split and join to handle plan_names that might contain underscores
                        parts = button_id.split("_")
                        price = int(float(parts[-1]))
                        plan_name = "_".join(parts[1:-1])
                        
                        whatsapp_flow.update_data(sender_phone, "plan", plan_name)
                        whatsapp_flow.update_data(sender_phone, "price", price)
                        
                        # Generate temp password for demo
                        temp_password = "rs_" + str(uuid.uuid4().hex[:6])
                        whatsapp_flow.update_data(sender_phone, "password", temp_password)
                        
                        plan_display = plan_name.replace("_", " ").title()
                        await whatsapp_meta.send_checkout_request(sender_phone, plan_display, price, lang=lang)
                        whatsapp_flow.set_state(sender_phone, FlowState.ONBOARD_PAYMENT)

                # 6. Mock Payment Success
                elif state == FlowState.ONBOARD_PAYMENT:
                    if button_id == "pay_success":
                        result = await whatsapp_onboarding.finalize_onboarding(sender_phone, session["data"])
                        if result["success"]:
                            success_msg = get_string(
                                "pay_success", 
                                lang=lang, 
                                name=session["data"]["name"],
                                phone=sender_phone,
                                password=session["data"]["password"]
                            )
                            await whatsapp_meta.send_text_message(sender_phone, success_msg)
                            whatsapp_flow.set_state(sender_phone, FlowState.COMPLETED)
                        else:
                            await whatsapp_meta.send_text_message(sender_phone, "Something went wrong. Please try again later.")
                            whatsapp_flow.set_state(sender_phone, FlowState.MAIN_MENU)

    return {"status": "success"}

async def handle_status_check(sender_phone: str, lang: str):
    """Fetch status from DB and reply localized."""
    status_info = await whatsapp_data.get_worker_status(sender_phone)
    
    if not status_info["found"]:
        # Instead of just role selection, let's guide them to full onboarding if they want
        await whatsapp_meta.send_text_message(sender_phone, get_string("status_inactive", lang=lang))
        await whatsapp_meta.send_welcome_message(sender_phone, lang=lang)
        return

    status_map = {
        "active": get_string("status_active", lang=lang),
        "pending": get_string("status_pending", lang=lang),
        "inactive": get_string("status_inactive", lang=lang),
    }
    
    risk_text = "Low" if status_info["risk_score"] < 0.4 else "Moderate" if status_info["risk_score"] < 0.7 else "High"
    
    response = (
        f"{get_string('status_header', lang=lang)}\n\n"
        f"{status_map.get(status_info['status'], status_info['status'])}\n"
        f"{get_string('coverage', lang=lang)}: ₹{status_info['coverage_cap']:.0f}\n"
        f"{get_string('risk_level', lang=lang)}: {risk_text}\n\n"
        f"{get_string('stay_safe', lang=lang)}"
    )
    
    await whatsapp_meta.send_text_message(sender_phone, response)
