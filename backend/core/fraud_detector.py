"""
Fraud detection pipeline for automated claim review.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Claim, Event, FraudLog, Policy, Worker, WorkerActivity


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FraudDetector:
    WEIGHTS = {
        "duplicate": 0.10,
        "movement": 0.20,
        "device": 0.15,
        "cluster": 0.20,
        "timing": 0.10,
        "income_inflation": 0.10,
        "pre_activity": 0.15,
    }

    async def compute_fraud_score(self, db: AsyncSession, worker: Worker, event: Event, policy: Policy, trust_score: float) -> Dict:
        signals = {
            "duplicate": await self._check_duplicate(db, worker, event),
            "movement": await self._check_movement(db, worker, event),
            "device": self._check_device(worker),
            "cluster": await self._check_cluster(db, event, trust_score),
            "timing": self._check_timing(event, policy),
            "income_inflation": self._check_income_inflation(worker),
            "pre_activity": await self._check_pre_activity(db, worker, event),
        }
        flags = [key for key, value in signals.items() if value > 0.5]
        raw_fraud_score = round(min(1.0, sum(self.WEIGHTS[key] * value for key, value in signals.items())), 3)
        adjusted_fraud = round(max(0.0, raw_fraud_score - (0.2 * trust_score)), 3)
        db.add(
            FraudLog(
                worker_id=worker.id,
                fraud_type="comprehensive_check",
                confidence=Decimal(str(adjusted_fraud)),
                signals={"raw_scores": signals, "flags": flags, "adjusted_fraud_score": adjusted_fraud},
                action_taken="scored",
            )
        )
        return {
            "raw_fraud_score": raw_fraud_score,
            "adjusted_fraud_score": adjusted_fraud,
            "trust_score": trust_score,
            "trust_adjustment": round(0.2 * trust_score, 3),
            "signals": signals,
            "flags": flags,
            "is_suspicious": adjusted_fraud > 0.5,
            "is_high_risk": adjusted_fraud > 0.7,
        }

    async def _check_duplicate(self, db: AsyncSession, worker: Worker, event: Event) -> float:
        count = (
            await db.execute(
                select(func.count(Claim.id)).where(
                    and_(Claim.worker_id == worker.id, Claim.event_id == event.id, Claim.trigger_type == event.event_type)
                )
            )
        ).scalar() or 0
        return 1.0 if count > 0 else 0.0

    async def _check_movement(self, db: AsyncSession, worker: Worker, event: Event) -> float:
        lookback = event.started_at - timedelta(hours=2)
        activities = (
            await db.execute(
                select(WorkerActivity).where(
                    and_(
                        WorkerActivity.worker_id == worker.id,
                        WorkerActivity.recorded_at >= lookback,
                        WorkerActivity.recorded_at <= event.started_at,
                    )
                )
            )
        ).scalars().all()
        if not activities:
            return 0.7
        speeds = [float(activity.speed_kmh or 0) for activity in activities]
        score = 0.0
        if len(speeds) > 1 and max(speeds) - min(speeds) < 3:
            score += 0.3
        if not any(activity.has_delivery_stop for activity in activities):
            score += 0.35
        if any(speed > 80 for speed in speeds):
            score += 0.25
        if event.zone not in {activity.zone for activity in activities}:
            score += 0.2
        return min(1.0, score)

    def _check_device(self, worker: Worker) -> float:
        score = 0.0
        if not worker.device_fingerprint:
            score += 0.2
        if not worker.ip_address:
            score += 0.1
        if worker.created_at:
            age_days = (utc_now_naive() - worker.created_at).days
            score += 0.3 if age_days < 2 else 0.15 if age_days < 7 else 0.0
        return min(1.0, score)

    async def _check_cluster(self, db: AsyncSession, event: Event, trust_score: float) -> float:
        window_start = event.started_at - timedelta(minutes=5)
        window_end = event.started_at + timedelta(minutes=5)
        cluster_size = (
            await db.execute(
                select(func.count(Claim.id)).where(
                    and_(Claim.trigger_type == event.event_type, Claim.created_at >= window_start, Claim.created_at <= window_end)
                )
            )
        ).scalar() or 0
        threshold = settings.CLUSTER_FRAUD_THRESHOLD
        if cluster_size > threshold:
            return 0.2 if trust_score > 0.7 else 0.5 if trust_score > 0.4 else 0.85
        return 0.15 if cluster_size > threshold // 2 else 0.0

    def _check_timing(self, event: Event, policy: Policy) -> float:
        score = 0.0
        if policy.purchased_at > event.started_at:
            score += 0.8
        if policy.activates_at > event.started_at:
            score += 0.9
        if abs((event.started_at - policy.purchased_at).total_seconds()) < 7200 and policy.purchased_at < event.started_at:
            score += 0.2
        return min(1.0, score)

    def _check_income_inflation(self, worker: Worker) -> float:
        if not worker.self_reported_income:
            return 0.1
        ratio = float(worker.self_reported_income) / settings.CITY_RISK_PROFILES.get(worker.city, {}).get("avg_daily_income", 800)
        if ratio > 2.0:
            return 0.8
        if ratio > 1.5:
            return 0.4
        return 0.15 if ratio > 1.2 else 0.0

    async def _check_pre_activity(self, db: AsyncSession, worker: Worker, event: Event) -> float:
        lookback = event.started_at - timedelta(hours=4)
        activity_count = (
            await db.execute(
                select(func.count(WorkerActivity.id)).where(
                    and_(
                        WorkerActivity.worker_id == worker.id,
                        WorkerActivity.recorded_at >= lookback,
                        WorkerActivity.recorded_at <= event.started_at,
                    )
                )
            )
        ).scalar() or 0
        if activity_count == 0:
            return 0.8
        if activity_count < 3:
            return 0.4
        return 0.15 if activity_count < 5 else 0.0


fraud_detector = FraudDetector()
