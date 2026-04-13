"""Fraud detection pipeline for automated claim review."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Dict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.fraud_model_service import fraud_model_service
from backend.db.models import Claim, Event, FraudLog, Policy, Worker, WorkerActivity
from backend.utils.time import utc_now_naive


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

    async def compute_fraud_score(
        self,
        db: AsyncSession,
        worker: Worker,
        event: Event,
        policy: Policy,
        trust_score: float,
    ) -> Dict:
        duplicate_signal, recent_claims_count = await self._check_duplicate(db, worker, event)
        movement_signal, activity_count = await self._check_movement(db, worker, event)
        device_signal, account_age_days = self._check_device(worker)
        cluster_signal, cluster_claims_count = await self._check_cluster(db, event, trust_score)
        timing_signal, policy_age_hours = self._check_timing(event, policy)
        income_inflation_signal, income_ratio = self._check_income_inflation(worker)
        pre_activity_signal, pre_activity_count = await self._check_pre_activity(db, worker, event)

        signals = {
            "duplicate": duplicate_signal,
            "movement": movement_signal,
            "device": device_signal,
            "cluster": cluster_signal,
            "timing": timing_signal,
            "income_inflation": income_inflation_signal,
            "pre_activity": pre_activity_signal,
        }
        flags = [key for key, value in signals.items() if value > 0.5]
        rule_fraud_score = round(min(1.0, sum(self.WEIGHTS[key] * value for key, value in signals.items())), 3)

        ml_context = {
            "duplicate_signal": duplicate_signal,
            "movement_signal": movement_signal,
            "device_signal": device_signal,
            "cluster_signal": cluster_signal,
            "timing_signal": timing_signal,
            "income_inflation_signal": income_inflation_signal,
            "pre_activity_signal": pre_activity_signal,
            "trust_score": trust_score,
            "account_age_days": account_age_days,
            "income_ratio": income_ratio,
            "activity_count": max(activity_count, pre_activity_count),
            "recent_claims_count": recent_claims_count,
            "cluster_claims_count": cluster_claims_count,
            "policy_age_hours": policy_age_hours,
            "event_severity_norm": min(1.0, float(event.severity or 0.5) / 2.0),
            "event_confidence_norm": min(1.0, float(event.event_confidence or 0.5)),
        }
        ml_result = fraud_model_service.score(ml_context)
        ml_fraud_score = (
            float(ml_result["ml_fraud_score"])
            if ml_result.get("ml_fraud_score") is not None
            else rule_fraud_score
        )
        raw_fraud_score = round((0.6 * rule_fraud_score) + (0.4 * ml_fraud_score), 3)
        adjusted_fraud = round(max(0.0, raw_fraud_score - (0.2 * trust_score)), 3)

        db.add(
            FraudLog(
                worker_id=worker.id,
                fraud_type="hybrid_ml_check",
                confidence=Decimal(str(adjusted_fraud)),
                signals={
                    "raw_scores": signals,
                    "flags": flags,
                    "rule_fraud_score": rule_fraud_score,
                    "ml_fraud_score": ml_result.get("ml_fraud_score"),
                    "fraud_probability": ml_result.get("fraud_probability"),
                    "blended_fraud_score": raw_fraud_score,
                    "adjusted_fraud_score": adjusted_fraud,
                    "ml_features": ml_result.get("features"),
                    "top_factors": ml_result.get("top_factors"),
                    "model_version": ml_result.get("model_version"),
                    "fallback_used": ml_result.get("fallback_used"),
                },
                action_taken="scored",
            )
        )
        return {
            "raw_fraud_score": raw_fraud_score,
            "rule_fraud_score": rule_fraud_score,
            "ml_fraud_score": round(ml_fraud_score, 3),
            "fraud_probability": ml_result.get("fraud_probability"),
            "adjusted_fraud_score": adjusted_fraud,
            "trust_score": trust_score,
            "trust_adjustment": round(0.2 * trust_score, 3),
            "signals": signals,
            "flags": flags,
            "ml_features": ml_result.get("features", {}),
            "top_factors": ml_result.get("top_factors", []),
            "model_version": ml_result.get("model_version", "rule-based"),
            "fallback_used": ml_result.get("fallback_used", True),
            "ml_confidence": ml_result.get("confidence", 0.0),
            "last_error": ml_result.get("last_error"),
            "is_suspicious": adjusted_fraud > 0.5,
            "is_high_risk": adjusted_fraud > 0.7,
        }

    async def _check_duplicate(self, db: AsyncSession, worker: Worker, event: Event) -> tuple[float, int]:
        count = (
            await db.execute(
                select(func.count(Claim.id)).where(
                    and_(
                        Claim.worker_id == worker.id,
                        Claim.event_id == event.id,
                        Claim.trigger_type == event.event_type,
                    )
                )
            )
        ).scalar() or 0
        recent_count = (
            await db.execute(
                select(func.count(Claim.id)).where(
                    and_(
                        Claim.worker_id == worker.id,
                        Claim.created_at >= event.started_at - timedelta(days=14),
                    )
                )
            )
        ).scalar() or 0
        return (1.0 if count > 0 else 0.0, int(recent_count))

    async def _check_movement(self, db: AsyncSession, worker: Worker, event: Event) -> tuple[float, int]:
        lookback = event.started_at - timedelta(hours=2)
        activities = (
            await db.execute(
                select(WorkerActivity).where(
                    and_(
                        WorkerActivity.worker_id == worker.id,
                        WorkerActivity.recorded_at >= lookback,
                        WorkerActivity.recorded_at <= event.started_at,
                    )
                ).order_by(WorkerActivity.recorded_at)
            )
        ).scalars().all()
        if not activities:
            return (0.0, 0)
        speeds = [float(activity.speed_kmh or 0) for activity in activities]
        score = 0.0

        # Existing checks
        if len(speeds) > 1 and max(speeds) - min(speeds) < 3:
            score += 0.3
        if not any(activity.has_delivery_stop for activity in activities):
            score += 0.35
        if any(speed > 80 for speed in speeds):
            score += 0.25
        if event.zone not in {activity.zone for activity in activities}:
            score += 0.2

        # Enhanced: velocity-between-pings (haversine distance / time)
        max_implied_velocity = 0.0
        for i in range(1, len(activities)):
            prev, curr = activities[i - 1], activities[i]
            if prev.latitude and prev.longitude and curr.latitude and curr.longitude:
                dist_km = self._haversine_km(
                    float(prev.latitude), float(prev.longitude),
                    float(curr.latitude), float(curr.longitude),
                )
                dt_seconds = (curr.recorded_at - prev.recorded_at).total_seconds()
                if dt_seconds > 0:
                    velocity_kmh = (dist_km / dt_seconds) * 3600
                    max_implied_velocity = max(max_implied_velocity, velocity_kmh)

        if max_implied_velocity > 500:
            score += 0.8  # Teleportation-class anomaly
        elif max_implied_velocity > 150:
            score += 0.5  # Impossible ground velocity

        # Enhanced: static coordinate detection
        if len(activities) >= 3:
            lats = [float(a.latitude) for a in activities if a.latitude is not None]
            lons = [float(a.longitude) for a in activities if a.longitude is not None]
            if lats and lons:
                lat_spread = max(lats) - min(lats)
                lon_spread = max(lons) - min(lons)
                has_delivery_claims = any(a.has_delivery_stop for a in activities)
                # All coords within 0.00005° AND claiming deliveries = static spoof
                if lat_spread < 0.00005 and lon_spread < 0.00005 and has_delivery_claims:
                    score += 0.6

        return (min(1.0, score), len(activities))

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance between two points in kilometers."""
        import math
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _check_device(self, worker: Worker) -> tuple[float, int]:
        score = 0.0
        age_days = 0
        if not worker.device_fingerprint:
            score += 0.2
        if not worker.ip_address:
            score += 0.1
        if worker.created_at:
            age_days = (utc_now_naive() - worker.created_at).days
            score += 0.3 if age_days < 2 else 0.15 if age_days < 7 else 0.0
        return (min(1.0, score), age_days)

    async def _check_cluster(self, db: AsyncSession, event: Event, trust_score: float) -> tuple[float, int]:
        window_start = event.started_at - timedelta(minutes=5)
        window_end = event.started_at + timedelta(minutes=5)
        cluster_size = (
            await db.execute(
                select(func.count(Claim.id)).where(
                    and_(
                        Claim.trigger_type == event.event_type,
                        Claim.created_at >= window_start,
                        Claim.created_at <= window_end,
                    )
                )
            )
        ).scalar() or 0
        threshold = settings.CLUSTER_FRAUD_THRESHOLD
        if cluster_size > threshold:
            score = 0.2 if trust_score > 0.7 else 0.5 if trust_score > 0.4 else 0.85
            return (score, int(cluster_size))
        return (0.15 if cluster_size >= threshold // 2 else 0.0, int(cluster_size))

    def _check_timing(self, event: Event, policy: Policy) -> tuple[float, float]:
        score = 0.0
        policy_age_hours = max(0.0, (event.started_at - policy.purchased_at).total_seconds() / 3600)
        if policy.purchased_at > event.started_at:
            score += 0.8
        if policy.activates_at > event.started_at:
            score += 0.9
        if abs((event.started_at - policy.purchased_at).total_seconds()) < 7200 and policy.purchased_at < event.started_at:
            score += 0.2
        return (min(1.0, score), round(policy_age_hours, 2))

    def _check_income_inflation(self, worker: Worker) -> tuple[float, float]:
        if not worker.self_reported_income:
            return (0.1, 1.0)
        ratio = float(worker.self_reported_income) / settings.CITY_RISK_PROFILES.get(worker.city, {}).get(
            "avg_daily_income",
            800,
        )
        if ratio > 2.0:
            return (0.8, ratio)
        if ratio > 1.5:
            return (0.4, ratio)
        return (0.15 if ratio > 1.2 else 0.0, ratio)

    async def _check_pre_activity(self, db: AsyncSession, worker: Worker, event: Event) -> tuple[float, int]:
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
            return (0.8, int(activity_count))
        if activity_count < 3:
            return (0.4, int(activity_count))
        return (0.15 if activity_count < 5 else 0.0, int(activity_count))


fraud_detector = FraudDetector()
