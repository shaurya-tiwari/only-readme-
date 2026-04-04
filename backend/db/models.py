"""SQLAlchemy ORM models for RideShield."""

import uuid
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime,
    ForeignKey, Text, Index, UniqueConstraint, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from backend.database import Base
from backend.utils.time import utc_now_naive


def generate_uuid():
    return uuid.uuid4()


class Worker(Base):
    """Delivery worker profile."""
    __tablename__ = "workers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    city_id = Column(UUID(as_uuid=True), ForeignKey("cities.id"), nullable=True, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True, index=True)
    city = Column(String(50), nullable=False, index=True)
    zone = Column(String(50), nullable=True)
    platform = Column(String(50), nullable=False)
    self_reported_income = Column(Numeric(10, 2), nullable=True)
    working_hours = Column(Numeric(4, 1), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)
    risk_score = Column(Numeric(4, 3), nullable=True)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # Relationships
    policies = relationship("Policy", back_populates="worker", lazy="selectin")
    claims = relationship("Claim", back_populates="worker", lazy="selectin")
    trust_score = relationship("TrustScore", back_populates="worker", uselist=False, lazy="selectin")
    activity_logs = relationship("WorkerActivity", back_populates="worker", lazy="selectin")
    city_ref = relationship("City", back_populates="workers", lazy="selectin")
    zone_ref = relationship("Zone", back_populates="workers", lazy="selectin")

    def __repr__(self):
        return f"<Worker {self.name} ({self.city})>"


class Policy(Base):
    """Weekly insurance policy."""
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    plan_name = Column(String(50), nullable=False)
    plan_display_name = Column(String(100), nullable=False)
    base_price = Column(Numeric(8, 2), nullable=False)
    plan_factor = Column(Numeric(3, 1), nullable=False)
    risk_score_at_purchase = Column(Numeric(4, 3), nullable=False)
    weekly_premium = Column(Numeric(8, 2), nullable=False)
    coverage_cap = Column(Numeric(8, 2), nullable=False)
    triggers_covered = Column(ARRAY(String), nullable=False)
    status = Column(String(20), default="pending", index=True)
    purchased_at = Column(DateTime, default=utc_now_naive)
    activates_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)

    # Relationships
    worker = relationship("Worker", back_populates="policies")
    claims = relationship("Claim", back_populates="policy", lazy="selectin")

    @hybrid_property
    def is_active(self):
        now = utc_now_naive()
        return (
            self.status == "active" and
            self.activates_at <= now <= self.expires_at
        )

    @is_active.expression
    def is_active(cls):
        from sqlalchemy import and_, cast, Boolean
        now = utc_now_naive()
        return and_(
            cls.status == "active",
            cls.activates_at <= now,
            cls.expires_at >= now,
        )

    def __repr__(self):
        return f"<Policy {self.plan_name} for worker {self.worker_id}>"


class Event(Base):
    """Disruption event detected by trigger engine."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_type = Column(String(50), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True, index=True)
    zone = Column(String(50), nullable=False, index=True)
    city = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    severity = Column(Numeric(4, 3), nullable=True)
    raw_value = Column(Numeric(10, 2), nullable=True)
    threshold = Column(Numeric(10, 2), nullable=True)
    disruption_score = Column(Numeric(4, 3), nullable=True)
    event_confidence = Column(Numeric(4, 3), nullable=True)
    api_source = Column(String(100), nullable=True)
    status = Column(String(20), default="active", index=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # Relationships
    claims = relationship("Claim", back_populates="event", lazy="selectin")
    zone_ref = relationship("Zone", back_populates="events", lazy="selectin")

    __table_args__ = (
        Index("idx_event_zone_type_time", "event_type", "zone", "started_at"),
    )

    def __repr__(self):
        return f"<Event {self.event_type} in {self.zone}>"


class Claim(Base):
    """Auto-generated insurance claim."""
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    trigger_type = Column(String(50), nullable=False)
    disruption_hours = Column(Numeric(4, 1), nullable=True)
    income_per_hour = Column(Numeric(8, 2), nullable=True)
    peak_multiplier = Column(Numeric(3, 1), default=1.0)
    calculated_payout = Column(Numeric(8, 2), nullable=True)
    final_payout = Column(Numeric(8, 2), nullable=True)
    disruption_score = Column(Numeric(4, 3), nullable=True)
    event_confidence = Column(Numeric(4, 3), nullable=True)
    fraud_score = Column(Numeric(4, 3), nullable=True)
    trust_score = Column(Numeric(4, 3), nullable=True)
    final_score = Column(Numeric(4, 3), nullable=True)
    decision_breakdown = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    review_deadline = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # Relationships
    worker = relationship("Worker", back_populates="claims")
    policy = relationship("Policy", back_populates="claims")
    event = relationship("Event", back_populates="claims")
    payout = relationship("Payout", back_populates="claim", uselist=False, lazy="selectin")

    __table_args__ = (
        UniqueConstraint("worker_id", "event_id", "trigger_type", name="uq_claim_dedup"),
    )

    def __repr__(self):
        return f"<Claim {self.status} for worker {self.worker_id}>"


class Payout(Base):
    """Payout record for approved claims."""
    __tablename__ = "payouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), unique=True, nullable=False)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    amount = Column(Numeric(8, 2), nullable=False)
    channel = Column(String(20), nullable=False)
    transaction_id = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")
    initiated_at = Column(DateTime, default=utc_now_naive)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    claim = relationship("Claim", back_populates="payout")

    def __repr__(self):
        return f"<Payout INR {self.amount} via {self.channel}>"


class TrustScore(Base):
    """Long-term behavioral trust profile per worker."""
    __tablename__ = "trust_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), unique=True, nullable=False)
    score = Column(Numeric(4, 3), default=0.100)
    total_claims = Column(Integer, default=0)
    approved_claims = Column(Integer, default=0)
    fraud_flags = Column(Integer, default=0)
    account_age_days = Column(Integer, default=0)
    device_stability = Column(Numeric(4, 3), default=0.500)
    last_updated = Column(DateTime, default=utc_now_naive)

    # Relationships
    worker = relationship("Worker", back_populates="trust_score")

    def __repr__(self):
        return f"<TrustScore {self.score} for worker {self.worker_id}>"


class FraudLog(Base):
    """Detailed fraud detection log per claim."""
    __tablename__ = "fraud_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    fraud_type = Column(String(50), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=True)
    signals = Column(JSONB, nullable=True)
    action_taken = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    def __repr__(self):
        return f"<FraudLog {self.fraud_type} for worker {self.worker_id}>"


class AuditLog(Base):
    """Immutable audit trail for all system decisions."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(JSONB, nullable=True)
    performed_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=utc_now_naive)

    __table_args__ = (
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type}>"


class SignalSnapshot(Base):
    """Normalized signal payload captured from a provider cycle."""
    __tablename__ = "signal_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    city = Column(String(50), nullable=False, index=True)
    zone = Column(String(80), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)
    provider = Column(String(100), nullable=False)
    source_mode = Column(String(20), nullable=False, default="mock")
    captured_at = Column(DateTime, nullable=False, index=True)
    normalized_metrics = Column(JSONB, nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    quality_score = Column(Numeric(4, 3), nullable=False)
    quality_breakdown = Column(JSONB, nullable=True)
    confidence_envelope = Column(JSONB, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    is_fallback = Column(Boolean, default=False)
    request_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    __table_args__ = (
        Index("idx_signal_snapshot_zone_type_time", "zone", "signal_type", "captured_at"),
        Index("idx_signal_snapshot_city_time", "city", "captured_at"),
    )

    def __repr__(self):
        return f"<SignalSnapshot {self.signal_type} {self.zone} {self.captured_at}>"


class ShadowSignalDiff(Base):
    """Structured shadow-mode comparison persisted for review and alerting."""
    __tablename__ = "shadow_signal_diffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    city = Column(String(50), nullable=False, index=True)
    zone = Column(String(80), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)
    primary_provider = Column(String(100), nullable=False)
    shadow_provider = Column(String(100), nullable=False)
    compared_at = Column(DateTime, nullable=False, index=True)
    max_delta = Column(Numeric(8, 3), nullable=False)
    metric_deltas = Column(JSONB, nullable=False)
    threshold_crossed = Column(Boolean, default=False, nullable=False)
    alert_triggered = Column(Boolean, default=False, nullable=False)
    threshold_state = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    __table_args__ = (
        Index("idx_shadow_diff_zone_type_time", "zone", "signal_type", "compared_at"),
        Index("idx_shadow_diff_city_time", "city", "compared_at"),
    )

    def __repr__(self):
        return f"<ShadowSignalDiff {self.signal_type} {self.zone} {self.compared_at}>"


class WorkerActivity(Base):
    """GPS and movement data for behavioral validation."""
    __tablename__ = "worker_activity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True, index=True)
    zone = Column(String(50), nullable=False, index=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    speed_kmh = Column(Numeric(5, 1), nullable=True)
    has_delivery_stop = Column(Boolean, default=False)
    recorded_at = Column(DateTime, default=utc_now_naive)

    # Relationships
    worker = relationship("Worker", back_populates="activity_logs")
    zone_ref = relationship("Zone", back_populates="activity_logs", lazy="selectin")

    __table_args__ = (
        Index("idx_activity_zone_time", "zone", "recorded_at"),
        Index("idx_activity_worker_time", "worker_id", "recorded_at"),
    )

    def __repr__(self):
        return f"<WorkerActivity {self.worker_id} at {self.recorded_at}>"


class City(Base):
    """Supported city for worker onboarding and trigger monitoring."""
    __tablename__ = "cities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    zones = relationship("Zone", back_populates="city_ref", lazy="selectin")
    workers = relationship("Worker", back_populates="city_ref", lazy="selectin")

    def __repr__(self):
        return f"<City {self.slug}>"


class Zone(Base):
    """Operational zone within a city."""
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    city_id = Column(UUID(as_uuid=True), ForeignKey("cities.id"), nullable=False, index=True)
    slug = Column(String(80), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=False)
    active = Column(Boolean, default=True, index=True)
    centroid_lat = Column(Numeric(10, 7), nullable=True)
    centroid_lon = Column(Numeric(10, 7), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    city_ref = relationship("City", back_populates="zones", lazy="selectin")
    threshold_profile = relationship("ZoneThresholdProfile", back_populates="zone_ref", uselist=False, lazy="selectin")
    risk_profile = relationship("ZoneRiskProfile", back_populates="zone_ref", uselist=False, lazy="selectin")
    workers = relationship("Worker", back_populates="zone_ref", lazy="selectin")
    events = relationship("Event", back_populates="zone_ref", lazy="selectin")
    activity_logs = relationship("WorkerActivity", back_populates="zone_ref", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("city_id", "slug", name="uq_zone_city_slug"),
    )

    def __repr__(self):
        return f"<Zone {self.slug}>"


class ZoneThresholdProfile(Base):
    """Per-zone trigger thresholds."""
    __tablename__ = "zone_threshold_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False, unique=True, index=True)
    rain_threshold_mm = Column(Numeric(10, 2), nullable=False)
    heat_threshold_c = Column(Numeric(10, 2), nullable=False)
    aqi_threshold = Column(Integer, nullable=False)
    traffic_threshold = Column(Numeric(4, 3), nullable=False)
    platform_outage_threshold = Column(Numeric(4, 3), nullable=False)
    social_inactivity_threshold = Column(Numeric(4, 3), nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    zone_ref = relationship("Zone", back_populates="threshold_profile", lazy="selectin")


class ZoneRiskProfile(Base):
    """Per-zone pricing and risk defaults."""
    __tablename__ = "zone_risk_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False, unique=True, index=True)
    base_risk = Column(Numeric(4, 3), nullable=False)
    avg_daily_income = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    zone_ref = relationship("Zone", back_populates="risk_profile", lazy="selectin")
