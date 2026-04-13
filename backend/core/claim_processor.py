"""Claim processor orchestrating the zero-touch claim pipeline."""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.decision_memory import record_claim_decision
from backend.core.decision_engine import decision_engine
from backend.core.fraud_detector import fraud_detector
from backend.core.income_verifier import income_verifier
from backend.core.location_service import location_service
from backend.core.payout_executor import payout_executor
from backend.core.trigger_engine import trigger_engine
from backend.db.models import AuditLog, Claim, Event, Policy, TrustScore, Worker
from backend.utils.time import utc_now_naive
from simulations.aqi_mock import aqi_simulator
from simulations.platform_mock import platform_simulator
from simulations.traffic_mock import traffic_simulator
from simulations.weather_mock import weather_simulator

logger = logging.getLogger("rideshield.cycles")

class ClaimProcessor:
    TRAFFIC_SOURCES = {"baseline", "simulation_pressure", "scenario", "replay_amplified"}

    def _normalize_traffic_source(self, traffic_source: str | None, scenario: str | None) -> str:
        normalized = str(traffic_source or ("scenario" if scenario else "baseline")).strip().lower()
        if normalized not in self.TRAFFIC_SOURCES:
            raise ValueError(f"Unsupported traffic_source '{normalized}'")
        return normalized

    async def _review_feedback_bias(
        self,
        db: AsyncSession,
        worker: Worker,
        fraud_flags: list[str],
        event: Event,
    ) -> dict:
        if not fraud_flags:
            return {
                "score_adjustment": 0.0,
                "confidence": 0.0,
                "approved_matches": 0,
                "rejected_matches": 0,
                "source": "manual_review_history",
            }

        reviewed_claims = (
            await db.execute(
                select(Claim)
                .where(
                    and_(
                        Claim.worker_id == worker.id,
                        Claim.reviewed_at.is_not(None),
                        Claim.created_at >= event.started_at - timedelta(days=45),
                    )
                )
                .order_by(Claim.reviewed_at.desc())
                .limit(15)
            )
        ).scalars().all()

        current_flags = set(fraud_flags)
        approved_matches = 0
        rejected_matches = 0
        approved_bias = 0.0
        rejected_bias = 0.0

        for reviewed_claim in reviewed_claims:
            breakdown = reviewed_claim.decision_breakdown or {}
            inputs = breakdown.get("inputs") if isinstance(breakdown, dict) else {}
            historical_flags = set(inputs.get("fraud_flags") or []) if isinstance(inputs, dict) else set()
            overlap = current_flags & historical_flags
            if not overlap:
                continue
            overlap_weight = len(overlap) / max(1, len(current_flags))
            if reviewed_claim.status == "approved":
                approved_matches += 1
                approved_bias += 0.04 * overlap_weight
            elif reviewed_claim.status == "rejected":
                rejected_matches += 1
                rejected_bias += 0.05 * overlap_weight

        score_adjustment = round(max(-0.08, min(0.08, approved_bias - rejected_bias)), 3)
        confidence = round(min(1.0, (approved_matches + rejected_matches) / 3), 3)
        return {
            "score_adjustment": score_adjustment,
            "confidence": confidence,
            "approved_matches": approved_matches,
            "rejected_matches": rejected_matches,
            "source": "manual_review_history",
        }

    async def _find_incident_window_claim(self, db: AsyncSession, worker: Worker, event: Event) -> Claim | None:
        hour_start = event.started_at.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        return (
            await db.execute(
                select(Claim)
                .join(Event, Claim.event_id == Event.id)
                .where(
                    and_(
                        Claim.worker_id == worker.id,
                        Claim.event_id != event.id,
                        Event.started_at >= hour_start,
                        Event.started_at < hour_end,
                    )
                )
                .order_by(Claim.created_at.desc())
            )
        ).scalars().first()

    async def run_trigger_cycle(
        self,
        db: AsyncSession,
        zones: Optional[List[str]] = None,
        city: str = "delhi",
        scenario: Optional[str] = None,
        demo_run_id: Optional[str] = None,
        traffic_source: Optional[str] = None,
        pressure_profile: Optional[str] = None,
    ) -> Dict:
        if not zones:
            zones = [zone.slug for zone in await location_service.get_active_zones(db, city_slug=city)]

        normalized_traffic_source = self._normalize_traffic_source(traffic_source, scenario)
        results = {
            "cycle_timestamp": utc_now_naive().isoformat(),
            "city": city,
            "scenario": scenario or "live",
            "traffic_source": normalized_traffic_source,
            "pressure_profile": pressure_profile,
            "demo_run_id": demo_run_id,
            "zones_checked": zones,
            "triggers_fired": {},
            "events_created": 0,
            "events_extended": 0,
            "claims_generated": 0,
            "claims_approved": 0,
            "claims_delayed": 0,
            "claims_rejected": 0,
            "claims_duplicate": 0,
            "total_payout": 0.0,
            "details": [],
        }

        if scenario:
            self._set_scenario(scenario)

        try:
            logger.info(
                "cycle_start city=%s scenario=%s demo_run_id=%s zones=%s",
                city,
                scenario or "live",
                demo_run_id or "none",
                ",".join(zones),
            )

            for zone in zones:
                zone_result = await self._process_zone(
                    db,
                    zone,
                    city,
                    demo_run_id=demo_run_id,
                    scenario=scenario,
                    traffic_source=normalized_traffic_source,
                    pressure_profile=pressure_profile,
                )
                results["details"].append(zone_result)
                results["triggers_fired"][zone] = zone_result["triggers_fired"]
                results["events_created"] += zone_result["events_created"]
                results["events_extended"] += zone_result["events_extended"]
                results["claims_generated"] += zone_result["claims_processed"]
                results["claims_approved"] += zone_result["claims_approved"]
                results["claims_delayed"] += zone_result["claims_delayed"]
                results["claims_rejected"] += zone_result["claims_rejected"]
                results["claims_duplicate"] += zone_result["claims_duplicate"]
                results["total_payout"] += zone_result["total_payout"]

            logger.info(
                "cycle_done city=%s events_created=%s events_extended=%s claims_generated=%s claims_approved=%s claims_delayed=%s claims_rejected=%s claims_duplicate=%s total_payout=%s",
                city,
                results["events_created"],
                results["events_extended"],
                results["claims_generated"],
                results["claims_approved"],
                results["claims_delayed"],
                results["claims_rejected"],
                results["claims_duplicate"],
                round(results["total_payout"], 2),
            )

            await db.flush()
            return results
        finally:
            if scenario:
                self._set_scenario("normal")

    async def _process_zone(
        self,
        db: AsyncSession,
        zone: str,
        city: str,
        demo_run_id: Optional[str] = None,
        scenario: Optional[str] = None,
        traffic_source: str = "baseline",
        pressure_profile: str | None = None,
    ) -> Dict:
        zone_result = {
            "zone": zone,
            "traffic_source": traffic_source,
            "pressure_profile": pressure_profile,
            "signals": {},
            "triggers_fired": [],
            "events_created": 0,
            "events_extended": 0,
            "claims_processed": 0,
            "claims_approved": 0,
            "claims_delayed": 0,
            "claims_rejected": 0,
            "claims_duplicate": 0,
            "total_payout": 0.0,
            "claim_details": [],
        }

        zone_record = await location_service.resolve_zone(db, city, zone)
        signals = await trigger_engine.fetch_all_signals(zone, city, db=db)
        zone_result["signals"] = {k: v for k, v in signals.items() if k != "raw_data" and isinstance(v, (int, float))}
        thresholds = trigger_engine.thresholds_for_zone(zone_record)
        fired = trigger_engine.evaluate_thresholds(signals, thresholds=thresholds)
        zone_result["triggers_fired"] = fired
        logger.info(
            "zone_signals city=%s zone=%s rain=%s heat=%s aqi=%s traffic=%s platform_outage=%s social=%s fired=%s",
            city,
            zone,
            zone_result["signals"].get("rain", 0),
            zone_result["signals"].get("heat", 0),
            zone_result["signals"].get("aqi", 0),
            zone_result["signals"].get("traffic", 0),
            zone_result["signals"].get("platform_outage", 0),
            zone_result["signals"].get("social", 0),
            ",".join(fired) if fired else "none",
        )
        if not fired:
            logger.info("zone_no_trigger city=%s zone=%s", city, zone)
            return zone_result

        disruption_score = trigger_engine.calculate_disruption_score(signals, thresholds=thresholds)
        event_confidence = trigger_engine.calculate_event_confidence(signals, fired, zone)
        events, created, extended = await trigger_engine.get_or_create_event(
            db, zone_record, fired, signals, disruption_score, event_confidence, thresholds=thresholds
            , demo_run_id=demo_run_id, traffic_source=traffic_source, scenario_name=scenario, pressure_profile=pressure_profile
        )
        zone_result["events_created"] = created
        zone_result["events_extended"] = extended

        affected_workers = await trigger_engine.find_affected_workers(db, zone_record, fired)
        for worker_info in affected_workers:
            for event in events:
                try:
                    claim_result = await self._process_worker_claim(
                        db=db,
                        worker=worker_info["worker"],
                        policy=worker_info["policy"],
                        event=event,
                        disruption_score=disruption_score,
                        event_confidence=event_confidence,
                        trust_score=worker_info["trust_score"],
                        covered_triggers=worker_info["covered_triggers"],
                        fired_triggers=worker_info["fired_triggers"],
                        traffic_source=traffic_source,
                    )
                except Exception as exc:
                    logger.warning(
                        "worker_claim_failed worker_id=%s event_id=%s error=%s",
                        str(worker_info["worker"].id),
                        str(event.id),
                        str(exc),
                    )
                    claim_result = {
                        "status": "error",
                        "payout_amount": 0,
                        "details": {"error": str(exc)},
                    }
                zone_result["claim_details"].append(claim_result)
                zone_result["claims_processed"] += 1
                if claim_result["status"] == "approved":
                    zone_result["claims_approved"] += 1
                    zone_result["total_payout"] += claim_result.get("payout_amount", 0)
                elif claim_result["status"] == "delayed":
                    zone_result["claims_delayed"] += 1
                elif claim_result["status"] == "rejected":
                    zone_result["claims_rejected"] += 1
                elif claim_result["status"] == "duplicate":
                    zone_result["claims_duplicate"] += 1
                elif claim_result["status"] == "error":
                    zone_result["claims_error"] = zone_result.get("claims_error", 0) + 1

        logger.info(
            "zone_outcome city=%s zone=%s events_created=%s events_extended=%s covered_workers=%s claims_processed=%s claims_approved=%s claims_delayed=%s claims_rejected=%s claims_duplicate=%s total_payout=%s",
            city,
            zone,
            zone_result["events_created"],
            zone_result["events_extended"],
            len(affected_workers),
            zone_result["claims_processed"],
            zone_result["claims_approved"],
            zone_result["claims_delayed"],
            zone_result["claims_rejected"],
            zone_result["claims_duplicate"],
            round(zone_result["total_payout"], 2),
        )

        return zone_result

    async def _process_worker_claim(
        self,
        db: AsyncSession,
        worker: Worker,
        policy: Policy,
        event: Event,
        disruption_score: float,
        event_confidence: float,
        trust_score: float,
        covered_triggers: list[str],
        fired_triggers: list[str],
        traffic_source: str = "baseline",
    ) -> Dict:
        result = {
            "worker_id": str(worker.id),
            "worker_name": worker.name,
            "event_id": str(event.id),
            "trigger_type": event.event_type,
            "status": None,
            "final_score": None,
            "fraud_score": None,
            "payout_amount": 0,
            "details": {},
        }

        # Policy expiry double-check (catches race between worker discovery and claim)
        now = utc_now_naive()
        grace_window = timedelta(hours=1)
        if policy.expires_at < (now - grace_window):
            if policy.status != "expired":
                policy.status = "expired"
            result["status"] = "rejected"
            result["details"] = {"message": "Policy expired before claim could be processed."}
            return result

        existing_claim = (
            await db.execute(
                select(Claim).where(
                    and_(
                        Claim.worker_id == worker.id,
                        Claim.event_id == event.id,
                    )
                )
            )
        ).scalar_one_or_none()
        if existing_claim:
            new_hours = decision_engine.estimate_disruption_hours(event.started_at, float(event.severity or 0.5))
            if new_hours > float(existing_claim.disruption_hours or 0):
                existing_claim.disruption_hours = Decimal(str(new_hours))
                existing_claim.updated_at = utc_now_naive()
            db.add(
                AuditLog(
                    entity_type="claim",
                    entity_id=existing_claim.id,
                    action="duplicate_detected",
                    details={
                        "worker_id": str(worker.id),
                        "worker_name": worker.name,
                        "duplicate_scope": "event",
                        "existing_claim_id": str(existing_claim.id),
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "zone": event.zone,
                        "covered_triggers": covered_triggers,
                        "incident_triggers": fired_triggers,
                    },
                )
            )
            result["status"] = "duplicate"
            result["details"] = {"message": "Claim already exists for this event. Extended if applicable."}
            return result

        incident_window_claim = await self._find_incident_window_claim(db, worker, event)
        if incident_window_claim:
            db.add(
                AuditLog(
                    entity_type="claim",
                    entity_id=incident_window_claim.id,
                    action="duplicate_detected",
                    details={
                        "worker_id": str(worker.id),
                        "worker_name": worker.name,
                        "duplicate_scope": "incident_window",
                        "existing_claim_id": str(incident_window_claim.id),
                        "existing_event_id": str(incident_window_claim.event_id),
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "zone": event.zone,
                        "incident_window_start": event.started_at.replace(
                            minute=0,
                            second=0,
                            microsecond=0,
                        ).isoformat(),
                        "covered_triggers": covered_triggers,
                        "incident_triggers": fired_triggers,
                    },
                )
            )
            result["status"] = "duplicate"
            result["details"] = {
                "message": "Claim already exists for this incident window.",
                "existing_claim_id": str(incident_window_claim.id),
            }
            return result

        fraud_result = await fraud_detector.compute_fraud_score(db, worker, event, policy, trust_score)
        review_feedback = await self._review_feedback_bias(db, worker, fraud_result["flags"], event)
        disruption_hours = decision_engine.estimate_disruption_hours(event.started_at, float(event.severity or 0.5))
        payout_calc = await income_verifier.calculate_payout(db, worker, policy, disruption_hours, event.started_at.hour)
        decision_result = decision_engine.decide(
            disruption_score,
            event_confidence,
            fraud_result,
            trust_score,
            feedback_result=review_feedback,
            payout_amount=payout_calc["final_payout"],
        )
        result["fraud_score"] = fraud_result["adjusted_fraud_score"]
        result["final_score"] = decision_result["final_score"]
        result["status"] = decision_result["decision"]
        decision_payload = {
            **decision_result,
            "traffic_source": traffic_source,
            "review_deadline": decision_result["review_deadline"].isoformat()
            if decision_result["review_deadline"]
            else None,
        }

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            event_id=event.id,
            trigger_type=event.event_type,
            disruption_hours=Decimal(str(disruption_hours)),
            income_per_hour=Decimal(str(payout_calc["income_per_hour"])),
            peak_multiplier=Decimal(str(payout_calc["peak_multiplier"])),
            calculated_payout=Decimal(str(payout_calc["raw_payout"])),
            final_payout=Decimal(str(payout_calc["final_payout"])),
            disruption_score=Decimal(str(disruption_score)),
            event_confidence=Decimal(str(event_confidence)),
            fraud_score=Decimal(str(fraud_result["adjusted_fraud_score"])),
            trust_score=Decimal(str(trust_score)),
            final_score=Decimal(str(decision_result["final_score"])),
            decision_breakdown=decision_payload,
            status=decision_result["decision"],
            review_deadline=decision_result["review_deadline"],
            created_at=utc_now_naive(),
        )
        claim.decision_breakdown = {
            **decision_payload,
            "covered_triggers": covered_triggers,
            "incident_triggers": fired_triggers,
            "payout_breakdown": {
                "income_per_hour": payout_calc.get("income_per_hour"),
                "net_income_per_hour": payout_calc.get("net_income_per_hour"),
                "operating_cost_factor": payout_calc.get("operating_cost_factor"),
                "peak_multiplier": payout_calc.get("peak_multiplier"),
                "disruption_hours": disruption_hours,
                "raw_payout": payout_calc.get("raw_payout"),
                "final_payout": payout_calc.get("final_payout"),
            },
            "fraud_model": {
                "rule_fraud_score": fraud_result.get("rule_fraud_score"),
                "ml_fraud_score": fraud_result.get("ml_fraud_score"),
                "fraud_probability": fraud_result.get("fraud_probability"),
                "confidence": fraud_result.get("ml_confidence"),
                "model_version": fraud_result.get("model_version"),
                "fallback_used": fraud_result.get("fallback_used"),
                "top_factors": fraud_result.get("top_factors", []),
            },
            "review_feedback": review_feedback,
        }
        if decision_result["decision"] == "rejected":
            claim.rejection_reason = decision_result["explanation"]
            claim.final_payout = Decimal("0")

        db.add(claim)
        await db.flush()
        await record_claim_decision(
            db=db,
            claim=claim,
            worker=worker,
            policy=policy,
            event=event,
            fraud_result=fraud_result,
            payout_calc=payout_calc,
            feedback_result=review_feedback,
            traffic_source=traffic_source,
        )
        db.add(
            AuditLog(
                entity_type="claim",
                entity_id=claim.id,
                action=f"created_{decision_result['decision']}",
                details={
                    "worker_id": str(worker.id),
                    "worker_name": worker.name,
                    "event_type": event.event_type,
                    "zone": event.zone,
                    "covered_triggers": covered_triggers,
                    "incident_triggers": fired_triggers,
                    "final_score": decision_result["final_score"],
                    "fraud_score": fraud_result["adjusted_fraud_score"],
                    "fraud_flags": fraud_result["flags"],
                    "fraud_model_version": fraud_result.get("model_version"),
                    "fraud_fallback_used": fraud_result.get("fallback_used"),
                    "fraud_top_factors": fraud_result.get("top_factors", []),
                    "payout": payout_calc["final_payout"] if decision_result["decision"] == "approved" else 0,
                },
            )
        )

        if decision_result["decision"] == "approved":
            try:
                payout_result = await payout_executor.execute(db, claim, worker, policy.plan_name, payout_calc["final_payout"])
            except Exception as exc:
                payout_result = await payout_executor.record_failed(
                    db,
                    claim,
                    worker,
                    policy.plan_name,
                    payout_calc["final_payout"],
                    str(exc),
                )
            result["payout_amount"] = payout_calc["final_payout"]
            result["details"]["payout"] = payout_result
            await self._update_trust_score(db, worker, approved=True)
        elif decision_result["decision"] == "rejected" and fraud_result["is_high_risk"]:
            await self._update_trust_score(db, worker, fraud_flag=True)

        return result

    async def _update_trust_score(self, db: AsyncSession, worker: Worker, approved: bool = False, fraud_flag: bool = False) -> None:
        trust = (await db.execute(select(TrustScore).where(TrustScore.worker_id == worker.id))).scalar_one_or_none()
        if not trust:
            return
        trust.total_claims = (trust.total_claims or 0) + 1
        if approved:
            trust.approved_claims = (trust.approved_claims or 0) + 1
            trust.score = Decimal(str(min(1.0, float(trust.score) + 0.02)))
        if fraud_flag:
            trust.fraud_flags = (trust.fraud_flags or 0) + 1
            trust.score = Decimal(str(max(0.0, float(trust.score) - 0.1)))
        if worker.created_at:
            trust.account_age_days = (utc_now_naive() - worker.created_at).days
        trust.last_updated = utc_now_naive()

    def _set_scenario(self, scenario: str) -> None:
        scenario_map = {
            "normal": {"weather": "normal", "aqi": "normal", "traffic": "normal", "platform": "normal"},
            "heavy_rain": {"weather": "heavy_rain", "aqi": "normal", "traffic": "severe", "platform": "platform_outage"},
            "extreme_heat": {"weather": "extreme_heat", "aqi": "moderate", "traffic": "normal", "platform": "normal"},
            "hazardous_aqi": {"weather": "normal", "aqi": "hazardous", "traffic": "normal", "platform": "low_demand"},
            "monsoon": {"weather": "monsoon", "aqi": "normal", "traffic": "gridlock", "platform": "platform_outage"},
            "platform_outage": {"weather": "normal", "aqi": "normal", "traffic": "normal", "platform": "platform_outage"},
            "compound_disaster": {"weather": "heavy_rain", "aqi": "hazardous", "traffic": "gridlock", "platform": "platform_outage"},
        }
        config = scenario_map.get(scenario, scenario_map["normal"])
        weather_simulator.set_scenario(config["weather"])
        aqi_simulator.set_scenario(config["aqi"])
        traffic_simulator.set_scenario(config["traffic"])
        platform_simulator.set_scenario(config["platform"])


claim_processor = ClaimProcessor()
