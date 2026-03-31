"""
Trigger engine for disruption monitoring and affected worker discovery.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.db.models import AuditLog, Event, Worker, Zone
from simulations.aqi_mock import aqi_simulator
from simulations.platform_mock import platform_simulator
from simulations.traffic_mock import traffic_simulator
from simulations.weather_mock import weather_simulator


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TriggerEngine:
    """Fetches signals, evaluates thresholds, creates events, and finds workers."""

    THRESHOLDS = {
        "rain": {"field": "rainfall_mm_hr", "threshold": settings.RAIN_THRESHOLD_MM, "weight": 0.20, "source": "openweather"},
        "heat": {"field": "temperature_c", "threshold": settings.HEAT_THRESHOLD_C, "weight": 0.15, "source": "openweather"},
        "aqi": {"field": "aqi_value", "threshold": settings.AQI_THRESHOLD, "weight": 0.15, "source": "waqi"},
        "traffic": {"field": "congestion_index", "threshold": settings.TRAFFIC_THRESHOLD, "weight": 0.15, "source": "tomtom"},
        "platform_outage": {"field": "order_density_drop", "threshold": settings.PLATFORM_OUTAGE_THRESHOLD, "weight": 0.20, "source": "platform_sim"},
        "social": {"field": "normalized_inactivity", "threshold": settings.SOCIAL_INACTIVITY_THRESHOLD, "weight": 0.15, "source": "behavioral"},
    }

    async def fetch_all_signals(self, zone: str, city: str = "delhi") -> Dict:
        weather = weather_simulator.get_weather(zone)
        aqi = aqi_simulator.get_aqi(zone, city)
        traffic = traffic_simulator.get_traffic(zone)
        platform = platform_simulator.get_platform_status(zone)
        social_signal = self._calculate_social_signal(weather, traffic, platform)

        return {
            "rain": weather.get("rainfall_mm_hr", 0),
            "heat": weather.get("temperature_c", 0),
            "aqi": aqi.get("aqi_value", 0),
            "traffic": traffic.get("congestion_index", 0),
            "platform_outage": platform.get("order_density_drop", 0),
            "social": social_signal,
            "raw_data": {"weather": weather, "aqi": aqi, "traffic": traffic, "platform": platform},
        }

    def thresholds_for_zone(self, zone: Zone | None = None) -> Dict:
        if zone and zone.threshold_profile:
            profile = zone.threshold_profile
            return {
                "rain": {"field": "rainfall_mm_hr", "threshold": float(profile.rain_threshold_mm), "weight": 0.20, "source": "openweather"},
                "heat": {"field": "temperature_c", "threshold": float(profile.heat_threshold_c), "weight": 0.15, "source": "openweather"},
                "aqi": {"field": "aqi_value", "threshold": float(profile.aqi_threshold), "weight": 0.15, "source": "waqi"},
                "traffic": {"field": "congestion_index", "threshold": float(profile.traffic_threshold), "weight": 0.15, "source": "tomtom"},
                "platform_outage": {"field": "order_density_drop", "threshold": float(profile.platform_outage_threshold), "weight": 0.20, "source": "platform_sim"},
                "social": {"field": "normalized_inactivity", "threshold": float(profile.social_inactivity_threshold), "weight": 0.15, "source": "behavioral"},
            }
        return self.THRESHOLDS

    def _calculate_social_signal(self, weather: Dict, traffic: Dict, platform: Dict) -> float:
        """
        Approximate a civic-disruption signal from behavioral collapse.
        Phase 2 keeps this rule-based; Phase 3 can replace it with a proper activity baseline.
        """
        platform_drop = float(platform.get("order_density_drop", 0) or 0)
        traffic_congestion = float(traffic.get("congestion_index", 0) or 0)
        weather_scenario = weather.get("scenario")
        platform_scenario = platform.get("scenario")

        if platform_scenario == "platform_outage" and platform_drop >= settings.SOCIAL_INACTIVITY_THRESHOLD:
            return round(min(1.0, platform_drop + (0.1 if traffic_congestion >= settings.TRAFFIC_THRESHOLD else 0.0)), 2)

        if weather_scenario == "monsoon" and platform_drop >= 0.5:
            return round(min(1.0, platform_drop), 2)

        return 0.0

    def evaluate_thresholds(self, signals: Dict, thresholds: Dict | None = None) -> List[str]:
        active_thresholds = thresholds or self.THRESHOLDS
        return [
            trigger_type
            for trigger_type, config in active_thresholds.items()
            if isinstance(signals.get(trigger_type, 0), (int, float))
            and signals.get(trigger_type, 0) >= config["threshold"]
        ]

    def calculate_disruption_score(self, signals: Dict, thresholds: Dict | None = None) -> float:
        active_thresholds = thresholds or self.THRESHOLDS
        score = 0.0
        for trigger_type, config in active_thresholds.items():
            raw = signals.get(trigger_type, 0)
            if not isinstance(raw, (int, float)):
                continue
            threshold = config["threshold"]
            normalized = 0.0 if threshold == 0 else max(0.0, min(1.0, (raw - threshold * 0.5) / threshold))
            score += config["weight"] * normalized
        return round(min(1.0, score), 3)

    def calculate_event_confidence(self, signals: Dict, fired_triggers: List[str], zone: str) -> float:
        api_score = min(1.0, len(fired_triggers) / 3)
        platform_drop = signals.get("platform_outage", 0)
        behavioral_score = min(1.0, platform_drop / 0.5) if platform_drop > 0.2 else 0.3
        return round((0.50 * api_score) + (0.30 * behavioral_score) + (0.20 * 0.7), 3)

    def calculate_severity(self, signals: Dict, fired_triggers: List[str], thresholds: Dict | None = None) -> float:
        active_thresholds = thresholds or self.THRESHOLDS
        if not fired_triggers:
            return 0.0
        severities = []
        for trigger in fired_triggers:
            value = signals.get(trigger, 0)
            threshold = active_thresholds[trigger]["threshold"]
            if threshold > 0:
                severities.append(min(2.0, value / threshold))
        return round(sum(severities) / len(severities), 3) if severities else 0.0

    async def get_or_create_event(
        self,
        db: AsyncSession,
        zone: Zone,
        fired_triggers: List[str],
        signals: Dict,
        disruption_score: float,
        event_confidence: float,
        thresholds: Dict | None = None,
        demo_run_id: str | None = None,
    ) -> Tuple[List[Event], int, int]:
        now = utc_now_naive()
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        incident_type = fired_triggers[0] if len(fired_triggers) == 1 else "compound_disruption"
        active_thresholds = thresholds or self.THRESHOLDS
        severity = self.calculate_severity(signals, fired_triggers, thresholds=active_thresholds)
        trigger_details = {
            trigger_type: {
                "raw_value": signals.get(trigger_type, 0),
                "threshold": active_thresholds[trigger_type]["threshold"],
                "source": active_thresholds[trigger_type]["source"],
            }
            for trigger_type in fired_triggers
        }
        representative_raw = max((float(signals.get(trigger_type, 0) or 0) for trigger_type in fired_triggers), default=0.0)
        representative_threshold = min((active_thresholds[trigger_type]["threshold"] for trigger_type in fired_triggers), default=0.0)
        api_source = "multi_source" if len(fired_triggers) > 1 else active_thresholds[fired_triggers[0]]["source"]

        existing = None
        if not (settings.SIMULATION_MODE and demo_run_id):
            existing = (
                await db.execute(
                    select(Event).where(
                        and_(
                            Event.zone_id == zone.id,
                            Event.status == "active",
                            Event.started_at >= hour_start,
                        )
                    )
                )
            ).scalar_one_or_none()

        if existing:
            existing.severity = Decimal(str(max(float(existing.severity or 0), severity)))
            existing.raw_value = Decimal(str(representative_raw))
            existing.threshold = Decimal(str(representative_threshold))
            existing.disruption_score = Decimal(str(max(float(existing.disruption_score or 0), disruption_score)))
            existing.event_confidence = Decimal(str(max(float(existing.event_confidence or 0), event_confidence)))
            existing.updated_at = now
            existing.event_type = incident_type
            existing.api_source = api_source
            existing.metadata_json = {
                **(existing.metadata_json or {}),
                "last_update": now.isoformat(),
                "fired_triggers": sorted(set((existing.metadata_json or {}).get("fired_triggers", []) + fired_triggers)),
                "trigger_details": {
                    **((existing.metadata_json or {}).get("trigger_details") or {}),
                    **trigger_details,
                },
                "signals_snapshot": {k: v for k, v in signals.items() if k != "raw_data" and isinstance(v, (int, float))},
            }
            db.add(
                AuditLog(
                    entity_type="event",
                    entity_id=existing.id,
                    action="event_extended",
                    details={
                        "zone": zone.slug,
                        "city": zone.city_ref.slug,
                        "event_type": incident_type,
                        "fired_triggers": fired_triggers,
                        "disruption_score": disruption_score,
                        "event_confidence": event_confidence,
                    },
                )
            )
            return [existing], 0, 1

        event = Event(
            event_type=incident_type,
            zone_id=zone.id,
            zone=zone.slug,
            city=zone.city_ref.slug,
            started_at=now,
            severity=Decimal(str(severity)),
            raw_value=Decimal(str(representative_raw)),
            threshold=Decimal(str(representative_threshold)),
            disruption_score=Decimal(str(disruption_score)),
            event_confidence=Decimal(str(event_confidence)),
            api_source=api_source,
            status="active",
            metadata_json={
                "signals_snapshot": {k: v for k, v in signals.items() if k != "raw_data" and isinstance(v, (int, float))},
                "fired_triggers": fired_triggers,
                "trigger_details": trigger_details,
                "created_by": "trigger_engine",
                "demo_run_id": demo_run_id,
            },
        )
        db.add(event)
        await db.flush()
        db.add(
            AuditLog(
                entity_type="event",
                entity_id=event.id,
                action="created",
                details={
                    "event_type": incident_type,
                    "zone": zone.slug,
                    "fired_triggers": fired_triggers,
                    "disruption_score": disruption_score,
                    "event_confidence": event_confidence,
                },
            )
        )
        return [event], 1, 0

    async def find_affected_workers(self, db: AsyncSession, zone: Zone, fired_triggers: List[str]) -> List[Dict]:
        now = utc_now_naive()
        workers = (
            await db.execute(
                select(Worker)
                .options(selectinload(Worker.policies), selectinload(Worker.trust_score), selectinload(Worker.claims))
                .where(and_(Worker.zone_id == zone.id, Worker.status == "active"))
            )
        ).scalars().all()

        affected = []
        for worker in workers:
            active_policy = None
            for policy in worker.policies:
                if policy.status == "active" and policy.activates_at <= now <= policy.expires_at:
                    active_policy = policy
                    break
            if not active_policy:
                for policy in worker.policies:
                    if policy.status == "pending" and policy.activates_at <= now <= policy.expires_at:
                        policy.status = "active"
                        active_policy = policy
                        break
            if not active_policy:
                continue
            covered_triggers = [t for t in fired_triggers if t in active_policy.triggers_covered]
            if not covered_triggers:
                continue
            affected.append(
                {
                    "worker": worker,
                    "policy": active_policy,
                    "covered_triggers": covered_triggers,
                    "fired_triggers": fired_triggers,
                    "trust_score": float(worker.trust_score.score) if worker.trust_score else 0.1,
                }
            )
        return affected

    async def end_stale_events(self, db: AsyncSession, max_age_hours: int = 6) -> int:
        cutoff = utc_now_naive() - timedelta(hours=max_age_hours)
        stale_events = (
            await db.execute(select(Event).where(and_(Event.status == "active", Event.updated_at < cutoff)))
        ).scalars().all()
        for event in stale_events:
            event.status = "ended"
            event.ended_at = utc_now_naive()
        return len(stale_events)


trigger_engine = TriggerEngine()
