"""
Income verification and payout calculation.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Worker, WorkerActivity


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IncomeVerifier:
    PEAK_MULTIPLIERS = {
        7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.1,
        12: 1.3, 13: 1.3, 14: 1.1, 15: 1.0, 16: 1.0,
        17: 1.1, 18: 1.2, 19: 1.5, 20: 1.5, 21: 1.5,
        22: 1.3, 23: 1.0, 0: 1.0, 1: 1.0, 2: 1.0,
        3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0,
    }

    async def verify_income(self, db: AsyncSession, worker: Worker) -> Dict:
        self_reported = float(worker.self_reported_income or 0)
        platform_income = await self._get_platform_income(db, worker)
        behavioral_income = await self._get_behavioral_income(db, worker)
        verified = 0.3 * self_reported + 0.5 * platform_income + 0.2 * behavioral_income
        city_avg = settings.CITY_RISK_PROFILES.get(worker.city, {}).get("avg_daily_income", 800)
        city_cap = city_avg * 1.5
        final_income = min(verified, city_cap)
        working_hours = float(worker.working_hours or 8)
        income_per_hour = final_income / max(working_hours, 1)
        return {
            "self_reported": round(self_reported, 2),
            "platform_estimated": round(platform_income, 2),
            "behavioral_estimated": round(behavioral_income, 2),
            "weighted_income": round(verified, 2),
            "city_avg": city_avg,
            "city_cap": city_cap,
            "cap_applied": verified > city_cap,
            "final_daily_income": round(final_income, 2),
            "working_hours": working_hours,
            "income_per_hour": round(income_per_hour, 2),
        }

    async def _get_platform_income(self, db: AsyncSession, worker: Worker) -> float:
        cutoff = utc_now_naive() - timedelta(days=7)
        delivery_count_7day = (
            await db.execute(
                select(func.count(WorkerActivity.id)).where(
                    and_(
                        WorkerActivity.worker_id == worker.id,
                        WorkerActivity.has_delivery_stop.is_(True),
                        WorkerActivity.recorded_at >= cutoff,
                    )
                )
            )
        ).scalar() or 0
        estimated = (delivery_count_7day / 7 if delivery_count_7day > 0 else 20) * 32
        if delivery_count_7day == 0:
            estimated = float(worker.self_reported_income or 800) * 0.9
        return estimated

    async def _get_behavioral_income(self, db: AsyncSession, worker: Worker) -> float:
        cutoff = utc_now_naive() - timedelta(days=3)
        activities = (
            await db.execute(
                select(WorkerActivity).where(
                    and_(
                        WorkerActivity.worker_id == worker.id,
                        WorkerActivity.recorded_at >= cutoff,
                    )
                )
            )
        ).scalars().all()
        if not activities:
            return float(worker.self_reported_income or 800) * 0.85

        delivery_stops = sum(1 for activity in activities if activity.has_delivery_stop)
        days = max(1, (utc_now_naive() - cutoff).days)
        return (delivery_stops / days) * 32

    def get_peak_multiplier(self, hour: int) -> float:
        return self.PEAK_MULTIPLIERS.get(hour, 1.0)

    async def calculate_payout(self, db: AsyncSession, worker: Worker, policy, disruption_hours: float, event_hour: int) -> Dict:
        income_data = await self.verify_income(db, worker)
        income_per_hour = income_data["income_per_hour"]
        peak_mult = self.get_peak_multiplier(event_hour)
        raw_payout = income_per_hour * disruption_hours * peak_mult
        coverage_cap = float(policy.coverage_cap)
        capped_payout = min(raw_payout, coverage_cap)
        city_daily_cap = income_data["city_cap"]
        final_payout = round(max(0, min(capped_payout, city_daily_cap)))
        return {
            "income_verification": income_data,
            "income_per_hour": round(income_per_hour, 2),
            "disruption_hours": disruption_hours,
            "peak_multiplier": peak_mult,
            "event_hour": event_hour,
            "raw_payout": round(raw_payout, 2),
            "coverage_cap": coverage_cap,
            "plan_cap_applied": raw_payout > coverage_cap,
            "city_cap_applied": capped_payout > city_daily_cap,
            "final_payout": final_payout,
        }


income_verifier = IncomeVerifier()
