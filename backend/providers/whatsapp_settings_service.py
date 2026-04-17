import json
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import async_session_factory
from backend.db.models import SystemStatus

logger = logging.getLogger("rideshield.whatsapp")

class WhatsAppSettingsService:
    """
    Manages user-specific WhatsApp settings (like language) using the SystemStatus KV table.
    """
    
    @staticmethod
    def _make_key(phone: str) -> str:
        return f"wa_user:{phone}"

    async def get_user_lang(self, phone: str) -> str:
        """Get the user's preferred language, defaulting to 'en'."""
        key = self._make_key(phone)
        async with async_session_factory() as session:
            stmt = select(SystemStatus).where(SystemStatus.key == key)
            result = await session.execute(stmt)
            status = result.scalar_one_or_none()
            if status and isinstance(status.value, dict):
                return status.value.get("lang", "en")
        return "en"

    async def set_user_lang(self, phone: str, lang: str) -> None:
        """Set the user's preferred language."""
        key = self._make_key(phone)
        async with async_session_factory() as session:
            stmt = select(SystemStatus).where(SystemStatus.key == key)
            result = await session.execute(stmt)
            status = result.scalar_one_or_none()
            
            settings = status.value if status and isinstance(status.value, dict) else {}
            settings["lang"] = lang
            
            if status:
                status.value = settings
            else:
                new_status = SystemStatus(key=key, value=settings)
                session.add(new_status)
            
            await session.commit()
            logger.info(f"Updated WhatsApp language for {phone} to {lang}")

whatsapp_settings = WhatsAppSettingsService()
