from datetime import timedelta
from sqlalchemy import delete
from backend.config import settings
from backend.database import async_session_factory
from backend.db.models import SignalSnapshot
from backend.utils.time import utc_now_naive

async def cleanup_old_snapshots():
    async with async_session_factory() as db:
        retention_hours = settings.SIGNAL_SNAPSHOT_RETENTION_DAYS * 24
        cutoff = utc_now_naive() - timedelta(hours=retention_hours)
        await db.execute(
            delete(SignalSnapshot).where(
                SignalSnapshot.captured_at < cutoff
            )
        )
        await db.commit()
