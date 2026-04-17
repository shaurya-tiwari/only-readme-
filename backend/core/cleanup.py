from datetime import timedelta
from sqlalchemy import delete
from backend.db.session import async_session_maker
from backend.db.models import SignalSnapshot
from backend.utils.time import utc_now_naive

RETENTION_HOURS = 24

async def cleanup_old_snapshots():
    async with async_session_maker() as db:
        cutoff = utc_now_naive() - timedelta(hours=RETENTION_HOURS)
        await db.execute(
            delete(SignalSnapshot).where(
                SignalSnapshot.captured_at < cutoff
            )
        )
        await db.commit()
