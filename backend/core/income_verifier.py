"""
Income verification and payout calculation.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Worker, WorkerActivity
from backend.utils.time import utc_now_naive


def _d(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class IncomeVerifier:
    PEAK_MULTIPLIERS = {
        7: Decimal("1.0"), 8: Decimal("1.0"), 9: Decimal("1.0"), 10: Decimal("1.0"), 11: Decimal("1.1"),
        12: Decimal("1.3"), 13: Decimal("1.3"), 14: Decimal("1.1"), 15: Decimal("1.0"), 16: Decimal("1.0"),
        17: Decimal("1.1"), 18: Decimal("1.2"), 19: Decimal("1.5"), 20: Decimal("1.5"), 21: Decimal("1.5"),
        22: Decimal("1.3"), 23: Decimal("1.0"), 0: Decimal("1.0"), 1: Decimal("1.0"), 2: Decimal("1.0"),
        3: Decimal("1.0"), 4: Decimal("1.0"), 5: Decimal("1.0"), 6: Decimal("1.0"),
    }

    # Platform-specific income adjustments reflecting earning dynamics per platform
    PLATFORM_MULTIPLIERS = {
        "zomato": Decimal("1.00"),
        "swiggy": Decimal("1.05"),
        "zepto": Decimal("1.15"),     # Quick-commerce → higher per-stop
        "amazon": Decimal("0.90"),    # Heavier parcels, lower density
        "dunzo": Decimal("0.95"),
        "blinkit": Decimal("1.10"),
    }

    async def verify_income(self, db: AsyncSession, worker: Worker) -> Dict:
        self_reported = _d(worker.self_reported_income)
        platform_income = _d(await self._get_platform_income(db, worker))
        behavioral_income = _d(await self._get_behavioral_income(db, worker))
        verified = self_reported * Decimal("0.3") + platform_income * Decimal("0.5") + behavioral_income * Decimal("0.2")

        # Apply platform-specific multiplier
        platform_key = (worker.platform or "").lower().strip()
        platform_mult = self.PLATFORM_MULTIPLIERS.get(platform_key, Decimal("1.0"))
        verified = verified * platform_mult

        city_avg = _d(settings.CITY_RISK_PROFILES.get(worker.city, {}).get("avg_daily_income", 800))
        city_cap = city_avg * Decimal("1.5")
        final_income = min(verified, city_cap)
        working_hours = max(_d(worker.working_hours or 8), Decimal("1"))
        income_per_hour = final_income / working_hours
        return {
            "self_reported": float(self_reported.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "platform_estimated": float(platform_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "behavioral_estimated": float(behavioral_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "weighted_income": float(verified.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "platform": platform_key,
            "platform_multiplier": float(platform_mult),
            "city_avg": float(city_avg),
            "city_cap": float(city_cap),
            "cap_applied": verified > city_cap,
            "final_daily_income": float(final_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "working_hours": float(working_hours),
            "income_per_hour": float(income_per_hour.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
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
        estimated = (Decimal(str(delivery_count_7day)) / Decimal("7") if delivery_count_7day > 0 else Decimal("20")) * Decimal("32")
        if delivery_count_7day == 0:
            estimated = _d(worker.self_reported_income or 800) * Decimal("0.9")
        return float(estimated)

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
            return float(_d(worker.self_reported_income or 800) * Decimal("0.85"))

        delivery_stops = sum(1 for activity in activities if activity.has_delivery_stop)
        days = max(1, (utc_now_naive() - cutoff).days)
        return float((Decimal(str(delivery_stops)) / Decimal(str(days))) * Decimal("32"))

    def get_peak_multiplier(self, hour: int) -> float:
        return float(self.PEAK_MULTIPLIERS.get(hour, Decimal("1.0")))

    async def calculate_payout(self, db: AsyncSession, worker: Worker, policy, disruption_hours: float, event_hour: int) -> Dict:
        income_data = await self.verify_income(db, worker)
        income_per_hour = Decimal(str(income_data["income_per_hour"]))
        operating_cost_factor = max(Decimal("0.5"), min(_d(settings.OPERATING_COST_FACTOR), Decimal("1.0")))
        net_income_per_hour = income_per_hour * operating_cost_factor
        peak_mult = self.PEAK_MULTIPLIERS.get(event_hour, Decimal("1.0"))
        raw_payout = net_income_per_hour * Decimal(str(disruption_hours)) * peak_mult
        coverage_cap = _d(policy.coverage_cap)
        capped_payout = min(raw_payout, coverage_cap)
        city_daily_cap = Decimal(str(income_data["city_cap"]))
        final_payout = max(Decimal("0"), min(capped_payout, city_daily_cap))
        return {
            "income_verification": income_data,
            "income_per_hour": float(income_per_hour.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "net_income_per_hour": float(net_income_per_hour.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "operating_cost_factor": float(operating_cost_factor),
            "disruption_hours": float(Decimal(str(disruption_hours))),
            "peak_multiplier": float(peak_mult),
            "event_hour": event_hour,
            "raw_payout": float(raw_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "coverage_cap": float(coverage_cap),
            "plan_cap_applied": raw_payout > coverage_cap,
            "city_cap_applied": capped_payout > city_daily_cap,
            "final_payout": float(final_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        }


income_verifier = IncomeVerifier()
