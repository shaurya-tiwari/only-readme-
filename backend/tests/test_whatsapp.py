import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock

from backend.main import app
from backend.core.whatsapp_flow_manager import FlowState

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_full_whatsapp_onboarding_flow(client):
    """Test the full onboarding and mock payment flow."""
    phone = "919000000000"
    
    # 1. Start with greeting -> Lang Selection
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "text",
                                    "text": {"body": "hi"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_meta.whatsapp_meta.send_lang_selection") as mock_lang:
        await client.post("/api/whatsapp/webhook", json=payload)
        mock_lang.assert_called_once_with(phone)

    # 2. Select English -> Welcome Menu
    payload_en = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "lang_en"}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_meta.whatsapp_meta.send_welcome_message") as mock_welcome:
        await client.post("/api/whatsapp/webhook", json=payload_en)
        mock_welcome.assert_called_once_with(phone, lang="en")

    # 3. Click Start -> Ask Name
    payload_start = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "start"}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_meta.whatsapp_meta.ask_onboard_name") as mock_name:
        await client.post("/api/whatsapp/webhook", json=payload_start)
        mock_name.assert_called_once_with(phone, lang="en")

    # 4. Provide Name -> City Selection
    payload_name = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "text",
                                    "text": {"body": "John Doe"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_meta.whatsapp_meta.send_city_selection") as mock_city:
        await client.post("/api/whatsapp/webhook", json=payload_name)
        mock_city.assert_called_once_with(phone, name="John Doe", lang="en")

    # 5. Select City -> Platform Selection
    payload_city = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "city_delhi"}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_meta.whatsapp_meta.send_platform_selection") as mock_plat:
        await client.post("/api/whatsapp/webhook", json=payload_city)
        mock_plat.assert_called_once_with(phone, lang="en")

    # 6. Select Platform -> Plan Selection
    payload_plat = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "plat_uber"}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    mock_plans = {
        "plans": [{"plan_name": "smart", "display_name": "Smart", "weekly_premium": 199}],
        "risk_score": 0.5,
        "zone_id": "z1",
        "city_id": "c1",
        "zone_slug": "delhi-p1"
    }
    
    with patch("backend.providers.whatsapp_onboarding_service.whatsapp_onboarding.get_plans_for_city", return_value=mock_plans), \
         patch("backend.providers.whatsapp_meta.whatsapp_meta.send_plan_selection") as mock_plan_ui:
        await client.post("/api/whatsapp/webhook", json=payload_plat)
        mock_plan_ui.assert_called_once()

    # 7. Select Plan -> Checkout
    payload_plan = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "plan_smart_199"}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_meta.whatsapp_meta.send_checkout_request") as mock_checkout:
        await client.post("/api/whatsapp/webhook", json=payload_plan)
        mock_checkout.assert_called_once()

    # 8. Mock Payment -> DB Creation & Success Msg
    payload_pay = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "pay_success"}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with patch("backend.providers.whatsapp_onboarding_service.whatsapp_onboarding.finalize_onboarding", return_value={"success": True}) as mock_finalize, \
         patch("backend.providers.whatsapp_meta.whatsapp_meta.send_text_message") as mock_success:
        await client.post("/api/whatsapp/webhook", json=payload_pay)
        mock_finalize.assert_called_once()
        mock_success.assert_called_once()
        args, _ = mock_success.call_args
        assert "Payment Successful" in args[1] or "भुगतान सफल" in args[1]
