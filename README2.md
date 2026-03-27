

# 🏗️ RideShield — Architecture Plan & Implementation Roadmap

> **Where we are:** Phase 1 complete (design + documentation). **Where we're going:** Working product by April 17.

---

## 📌 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [System Architecture Diagram](#-system-architecture-diagram)
3. [Data Flow Architecture](#-data-flow-architecture)
4. [Database Schema](#-database-schema)
5. [API Architecture](#-api-architecture)
6. [Trigger Engine Architecture](#-trigger-engine-architecture)
7. [Fraud Detection Pipeline](#-fraud-detection-pipeline)
8. [Decision Engine Architecture](#-decision-engine-architecture)
9. [ML Model Architecture](#-ml-model-architecture)
10. [Frontend Architecture](#-frontend-architecture)
11. [Payment Architecture](#-payment-architecture)
12. [Simulation Layer](#-simulation-layer)
13. [Phase 2 Sprint Plan](#-phase-2-sprint-plan-march-21--april-4)
14. [Phase 3 Sprint Plan](#-phase-3-sprint-plan-april-5--april-17)
15. [Day-by-Day Execution Calendar](#-day-by-day-execution-calendar)
16. [Testing Strategy](#-testing-strategy)
17. [Deployment Architecture](#-deployment-architecture)
18. [Demo Script Plan](#-demo-script-plan)
19. [Risk & Mitigation](#-risk--mitigation)
20. [Immediate Next Steps](#-immediate-next-steps)

---

![RideShield Architecture Diagram](publicIMG/Gemini_Generated_Image_romo4promo4promo.png)

## 🔷 Architecture Overview

RideShield is a **3-tier monorepo application** with clear separation between data ingestion, business logic, and presentation.

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                       │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│   │  Onboarding  │  │   Worker     │  │   Admin Dashboard    │ │
│   │    Flow      │  │  Dashboard   │  │  (Fraud + Analytics) │ │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│          │                 │                      │             │
├──────────┼─────────────────┼──────────────────────┼─────────────┤
│          │          API GATEWAY (FastAPI)          │             │
│          │                 │                      │             │
│   ┌──────▼───────┐  ┌─────▼────────┐  ┌─────────▼───────────┐ │
│   │  Workers API │  │  Claims API  │  │   Analytics API     │ │
│   │  Policies API│  │  Payouts API │  │   Fraud Review API  │ │
│   └──────┬───────┘  └─────┬────────┘  └─────────┬───────────┘ │
│          │                │                      │             │
├──────────┼────────────────┼──────────────────────┼─────────────┤
│          │         BUSINESS LOGIC LAYER           │             │
│          │                │                      │             │
│   ┌──────▼───────┐  ┌────▼─────────┐  ┌────────▼──────────┐  │
│   │   Risk       │  │  Trigger     │  │  Fraud Detection  │  │
│   │   Scoring    │  │  Engine      │  │  Pipeline         │  │
│   └──────┬───────┘  └────┬─────────┘  └────────┬──────────┘  │
│          │               │                      │             │
│          │         ┌─────▼─────────┐            │             │
│          │         │   Decision    ◄────────────┘             │
│          │         │   Engine      │                          │
│          │         └─────┬─────────┘                          │
│          │               │                                    │
│   ┌──────▼───────┐  ┌───▼──────────┐  ┌───────────────────┐ │
│   │   Income     │  │   Payout     │  │   Audit Logger    │ │
│   │   Verifier   │  │   Executor   │  │                   │ │
│   └──────────────┘  └──────────────┘  └───────────────────┘ │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│                        DATA LAYER                             │
│                                                               │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│   │  PostgreSQL  │  │  External    │  │   ML Model        │ │
│   │  Database    │  │  APIs        │  │   Artifacts       │ │
│   └──────────────┘  └──────────────┘  └───────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Core Design Principles

| Principle | Implementation |
|---|---|
| **Event-driven** | Triggers fire → claims generated → payouts executed. No polling from workers. |
| **Event-centric dedup** | One event = one claim per worker. Extensions, not duplicates. |
| **Multi-signal validation** | No financial decision based on a single data source. |
| **Audit everything** | Every decision logged with full signal decomposition. |
| **Fail safe** | Missing data → delay claim, never auto-reject without evidence. |
| **Stateless API** | Backend is stateless. All state lives in PostgreSQL. |

---

## 🔄 Data Flow Architecture

### Flow 1: Worker Onboarding
```
Worker fills form
    → POST /api/workers/register
    → Validate inputs
    → Generate risk_score (ML model)
    → Store worker record
    → Return recommended plans with calculated premiums
    → Worker selects plan
    → POST /api/policies/create
    → Store policy (status: PENDING, activates in 24hrs)
    → Return confirmation + activation timestamp
```

### Flow 2: Disruption Detection → Claim → Payout
```
Scheduler runs every 5 minutes
    → Fetch weather data (rain, heat) for all active zones
    → Fetch AQI data for all active zones
    → Fetch traffic data for all active zones
    → Check platform order density per zone
    → Check social disruption signals

For each zone where ANY threshold is crossed:
    → Create or update Event record
    → Calculate disruption_score (weighted multi-signal)
    → Calculate event_confidence
    → Identify all active insured workers in zone

    For each affected worker:
        → Check: existing claim for this event? → EXTEND, don't duplicate
        → Check: policy active? (past 24hr activation window?)
        → Check: worker had pre-disruption activity?
        → Run fraud_detection(worker, event)
        → Run decision_engine(disruption, confidence, fraud, trust)

        If final_score > 0.70:
            → Calculate payout (income × hours × peak_multiplier)
            → Apply caps (plan cap, city cap)
            → Execute payout (Razorpay sandbox / UPI sim)
            → Log audit trail
            → Push notification

        If final_score 0.50–0.70:
            → Queue for 24hr admin review
            → Log with full signal breakdown

        If final_score < 0.50:
            → Reject with reason
            → Log audit trail
```

### Flow 3: Admin Review (Delayed Claims)
```
Admin opens dashboard
    → GET /api/claims/review-queue
    → Sees delayed claims with signal breakdown
    → Reviews evidence (GPS, activity, event data)
    → POST /api/claims/{id}/resolve (approve/reject)
    → If approved → trigger payout
    → If rejected → log reason
    → SLA tracking: 24hr from queue entry
```

---

## 🗄️ Database Schema

### Entity Relationship Overview

```
Workers ──1:N──> Policies ──1:N──> Claims ──1:1──> Payouts
                                      │
Events ──1:N──> Claims               │
                                      │
Workers ──1:1──> TrustScores         │
                                      │
Claims ──1:N──> AuditLogs           │
Events ──1:N──> AuditLogs
```

### Table Definitions

```sql
-- ============================================
-- WORKERS TABLE
-- ============================================
CREATE TABLE workers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    phone           VARCHAR(15) UNIQUE NOT NULL,
    city            VARCHAR(50) NOT NULL,
    zone            VARCHAR(50),
    platform        VARCHAR(50) NOT NULL,          -- zomato, swiggy, etc.
    self_reported_income DECIMAL(10,2),             -- daily income claimed
    working_hours   DECIMAL(4,1),                  -- avg hours/day
    device_fingerprint VARCHAR(255),
    ip_address      VARCHAR(45),
    consent_given   BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP,
    risk_score      DECIMAL(3,2),                  -- 0.00 to 1.00
    status          VARCHAR(20) DEFAULT 'active',  -- active, suspended, banned
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- POLICIES TABLE
-- ============================================
CREATE TABLE policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       UUID REFERENCES workers(id),
    plan_name       VARCHAR(50) NOT NULL,           -- basic, smart, assured, promax
    plan_factor     DECIMAL(3,1) NOT NULL,
    weekly_premium  DECIMAL(8,2) NOT NULL,
    coverage_cap    DECIMAL(8,2) NOT NULL,
    triggers_covered TEXT[] NOT NULL,                -- array of trigger types
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, active, expired
    purchased_at    TIMESTAMP DEFAULT NOW(),
    activates_at    TIMESTAMP NOT NULL,             -- purchased_at + 24 hours
    expires_at      TIMESTAMP NOT NULL,             -- activates_at + 7 days
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- EVENTS TABLE (Disruptions)
-- ============================================
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(50) NOT NULL,           -- rain, heat, aqi, traffic, platform, social
    zone            VARCHAR(50) NOT NULL,
    city            VARCHAR(50) NOT NULL,
    started_at      TIMESTAMP NOT NULL,
    ended_at        TIMESTAMP,                      -- NULL = still active
    severity        DECIMAL(3,2),                   -- 0.00 to 1.00
    raw_value       DECIMAL(10,2),                  -- actual measurement (mm/hr, °C, AQI, etc.)
    threshold       DECIMAL(10,2),                  -- threshold that was crossed
    disruption_score DECIMAL(3,2),
    event_confidence DECIMAL(3,2),
    api_source      VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'active',   -- active, ended, invalidated
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Composite index for deduplication
CREATE UNIQUE INDEX idx_event_dedup
    ON events(event_type, zone, date_trunc('hour', started_at));

-- ============================================
-- CLAIMS TABLE
-- ============================================
CREATE TABLE claims (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       UUID REFERENCES workers(id),
    policy_id       UUID REFERENCES policies(id),
    event_id        UUID REFERENCES events(id),
    trigger_type    VARCHAR(50) NOT NULL,
    disruption_hours DECIMAL(4,1),
    income_per_hour DECIMAL(8,2),
    peak_multiplier DECIMAL(3,1) DEFAULT 1.0,
    calculated_payout DECIMAL(8,2),
    final_payout    DECIMAL(8,2),                   -- after caps applied
    disruption_score DECIMAL(3,2),
    event_confidence DECIMAL(3,2),
    fraud_score     DECIMAL(3,2),
    trust_score     DECIMAL(3,2),
    final_score     DECIMAL(3,2),
    status          VARCHAR(20) NOT NULL,            -- approved, delayed, rejected
    rejection_reason TEXT,
    review_deadline TIMESTAMP,                       -- for delayed claims (24hr SLA)
    reviewed_by     VARCHAR(100),                    -- admin who reviewed
    reviewed_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Deduplication constraint
CREATE UNIQUE INDEX idx_claim_dedup
    ON claims(worker_id, event_id, trigger_type);

-- ============================================
-- PAYOUTS TABLE
-- ============================================
CREATE TABLE payouts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID REFERENCES claims(id),
    worker_id       UUID REFERENCES workers(id),
    amount          DECIMAL(8,2) NOT NULL,
    channel         VARCHAR(20) NOT NULL,            -- wallet, upi
    transaction_id  VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'pending',   -- pending, completed, failed
    initiated_at    TIMESTAMP DEFAULT NOW(),
    completed_at    TIMESTAMP
);

-- ============================================
-- TRUST SCORES TABLE
-- ============================================
CREATE TABLE trust_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       UUID UNIQUE REFERENCES workers(id),
    score           DECIMAL(3,2) DEFAULT 0.10,       -- starts low for new users
    total_claims    INTEGER DEFAULT 0,
    approved_claims INTEGER DEFAULT 0,
    fraud_flags     INTEGER DEFAULT 0,
    account_age_days INTEGER DEFAULT 0,
    device_stability DECIMAL(3,2) DEFAULT 0.50,
    last_updated    TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- FRAUD LOGS TABLE
-- ============================================
CREATE TABLE fraud_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID REFERENCES claims(id),
    worker_id       UUID REFERENCES workers(id),
    fraud_type      VARCHAR(50) NOT NULL,            -- gps_spoof, cluster, duplicate, etc.
    confidence      DECIMAL(3,2),
    signals         JSONB,                           -- full signal decomposition
    action_taken    VARCHAR(20),                     -- flagged, rejected, approved_with_audit
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- AUDIT LOGS TABLE
-- ============================================
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     VARCHAR(50) NOT NULL,            -- claim, event, payout, policy
    entity_id       UUID NOT NULL,
    action          VARCHAR(50) NOT NULL,            -- created, updated, approved, rejected
    details         JSONB,                           -- full context snapshot
    performed_by    VARCHAR(100) DEFAULT 'system',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- WORKER ACTIVITY TABLE (for behavioral validation)
-- ============================================
CREATE TABLE worker_activity (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       UUID REFERENCES workers(id),
    zone            VARCHAR(50) NOT NULL,
    latitude        DECIMAL(10,7),
    longitude       DECIMAL(10,7),
    speed_kmh       DECIMAL(5,1),
    has_delivery_stop BOOLEAN DEFAULT FALSE,
    recorded_at     TIMESTAMP DEFAULT NOW()
);

-- Index for fast zone + time lookups
CREATE INDEX idx_activity_zone_time
    ON worker_activity(zone, recorded_at);

CREATE INDEX idx_activity_worker_time
    ON worker_activity(worker_id, recorded_at);
```

---

## 🔌 API Architecture

### Base URL Structure
```
Production:  https://api.rideshield.dev/v1
Development: http://localhost:8000/v1
```

### Endpoint Map

#### Workers API (`/api/workers`)
```
POST   /register              → Create worker profile + generate risk score
GET    /me                    → Get current worker profile
PUT    /me                    → Update worker details
GET    /me/activity           → Get recent activity log
GET    /me/trust-score        → Get trust score breakdown
```

#### Policies API (`/api/policies`)
```
GET    /plans                 → List available plans with calculated premiums
POST   /create                → Purchase a weekly plan
GET    /active                → Get worker's active policy
GET    /history               → Get past policies
```

#### Claims API (`/api/claims`)
```
GET    /my-claims             → Worker's claim history
GET    /{id}                  → Claim detail with full signal breakdown
GET    /review-queue          → Admin: delayed claims awaiting review
POST   /{id}/resolve          → Admin: approve or reject delayed claim
```

#### Events API (`/api/events`)
```
GET    /active                → Currently active disruption events
GET    /history               → Past events with outcomes
GET    /zone/{zone_id}        → Events in a specific zone
```

#### Payouts API (`/api/payouts`)
```
GET    /my-payouts            → Worker's payout history
GET    /{id}                  → Payout detail with transaction ID
```

#### Analytics API (`/api/analytics`)
```
GET    /dashboard/worker      → Worker dashboard metrics
GET    /dashboard/admin       → Admin dashboard metrics
GET    /loss-ratio            → Loss ratio by plan and city
GET    /fraud-stats           → Fraud detection statistics
GET    /forecast              → Next-week risk forecast
```

#### Trigger API (`/api/triggers`) — Internal
```
POST   /check                 → Manual trigger check (for testing)
GET    /status                → Current trigger status across all zones
```

### Request/Response Examples

**POST /api/workers/register**
```json
// Request
{
    "name": "Rahul Kumar",
    "phone": "+919876543210",
    "city": "delhi",
    "zone": "south_delhi",
    "platform": "zomato",
    "self_reported_income": 900,
    "working_hours": 9,
    "consent_given": true
}

// Response
{
    "worker_id": "uuid-here",
    "risk_score": 0.58,
    "recommended_plan": "smart_protect",
    "available_plans": [
        {
            "name": "basic_protect",
            "weekly_premium": 31,
            "coverage_cap": 300,
            "triggers": ["platform_outage"]
        },
        {
            "name": "smart_protect",
            "weekly_premium": 35,
            "coverage_cap": 600,
            "triggers": ["rain", "heat", "aqi", "traffic", "platform_outage"]
        }
    ],
    "activation_delay_hours": 24,
    "message": "Your coverage will activate 24 hours after purchase."
}
```

**Auto-generated Claim Notification (Push)**
```json
{
    "type": "claim_approved",
    "claim_id": "uuid-here",
    "event_type": "rain",
    "zone": "south_delhi",
    "disruption_hours": 2.5,
    "payout_amount": 280,
    "payout_channel": "wallet",
    "transaction_id": "txn_abc123",
    "final_score": 0.82,
    "message": "Heavy rain detected in your zone. ₹280 income protection credited."
}
```

---

## ⚡ Trigger Engine Architecture

The trigger engine is the heartbeat of RideShield. It runs continuously, checks external conditions, and fires events when thresholds are crossed.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                 TRIGGER SCHEDULER                    │
│              (runs every 5 minutes)                  │
│                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │ Weather │ │   AQI   │ │ Traffic │ │ Platform │ │
│  │ Checker │ │ Checker │ │ Checker │ │ Checker  │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘ │
│       │           │           │            │        │
│       ▼           ▼           ▼            ▼        │
│  ┌──────────────────────────────────────────────┐   │
│  │          THRESHOLD EVALUATOR                  │   │
│  │                                               │   │
│  │  Rain > 25mm/hr?          ✓ → fire           │   │
│  │  Temp > 44°C?             ✓ → fire           │   │
│  │  AQI > 300?               ✓ → fire           │   │
│  │  Congestion > 0.75?       ✓ → fire           │   │
│  │  Order density drop > 60%? ✓ → fire          │   │
│  │  Normalized inactivity?    ✓ → fire          │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│                     ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │          EVENT MANAGER                        │   │
│  │                                               │   │
│  │  Existing event for this zone + type + hour?  │   │
│  │     YES → update severity, extend duration    │   │
│  │     NO  → create new event record             │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│                     ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │     AFFECTED WORKER IDENTIFIER                │   │
│  │                                               │   │
│  │  Find all workers WHERE:                      │   │
│  │    - policy.status = 'active'                 │   │
│  │    - policy.activates_at < NOW()              │   │
│  │    - worker.zone = event.zone                 │   │
│  │    - trigger_type IN policy.triggers_covered  │   │
│  │    - no existing claim for this event         │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│                     ▼                                │
│           CLAIM GENERATION PIPELINE                  │
└─────────────────────────────────────────────────────┘
```

### Implementation

```python
# backend/core/trigger_engine.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx

class TriggerEngine:
    """
    Core trigger monitoring engine.
    Runs every 5 minutes via scheduler.
    Checks all 6 trigger types across all active zones.
    """

    THRESHOLDS = {
        "rain": {"field": "rainfall_mm_hr", "threshold": 25.0, "source": "openweather"},
        "heat": {"field": "temperature_c", "threshold": 44.0, "source": "openweather"},
        "aqi": {"field": "aqi_value", "threshold": 300, "source": "waqi"},
        "traffic": {"field": "congestion_index", "threshold": 0.75, "source": "tomtom"},
        "platform_outage": {"field": "order_density_drop", "threshold": 0.60, "source": "platform_sim"},
        "social": {"field": "normalized_inactivity", "threshold": 0.60, "source": "behavioral"}
    }

    async def run_check_cycle(self, zones: List[str]):
        """Main entry point — called by scheduler every 5 minutes."""
        for zone in zones:
            signals = await self.fetch_all_signals(zone)
            fired_triggers = self.evaluate_thresholds(signals)

            if fired_triggers:
                disruption_score = self.calculate_disruption_score(signals)
                event_confidence = self.calculate_event_confidence(signals, zone)
                event = await self.get_or_create_event(zone, fired_triggers, signals)
                affected_workers = await self.find_affected_workers(zone, fired_triggers)

                for worker in affected_workers:
                    await self.initiate_claim_pipeline(worker, event, disruption_score, event_confidence)

    async def fetch_all_signals(self, zone: str) -> Dict:
        """Fetch data from all external sources for a zone."""
        weather = await self.fetch_weather(zone)
        aqi = await self.fetch_aqi(zone)
        traffic = await self.fetch_traffic(zone)
        platform = await self.fetch_platform_density(zone)
        social = await self.calculate_social_signal(zone)

        return {
            "rain": weather.get("rainfall_mm_hr", 0),
            "heat": weather.get("temperature_c", 0),
            "aqi": aqi.get("aqi_value", 0),
            "traffic": traffic.get("congestion_index", 0),
            "platform_outage": platform.get("order_density_drop", 0),
            "social": social.get("normalized_inactivity", 0)
        }

    def evaluate_thresholds(self, signals: Dict) -> List[str]:
        """Return list of trigger types that crossed their thresholds."""
        fired = []
        for trigger_type, config in self.THRESHOLDS.items():
            if signals.get(trigger_type, 0) >= config["threshold"]:
                fired.append(trigger_type)
        return fired

    def calculate_disruption_score(self, signals: Dict) -> float:
        """Weighted composite disruption score."""
        weights = {
            "rain": 0.20, "heat": 0.15, "aqi": 0.15,
            "traffic": 0.15, "platform_outage": 0.20, "social": 0.15
        }
        score = 0.0
        for trigger_type, weight in weights.items():
            raw = signals.get(trigger_type, 0)
            threshold = self.THRESHOLDS[trigger_type]["threshold"]
            # Normalize: how far past threshold (0 = at threshold, 1 = 2x threshold)
            normalized = min(1.0, max(0.0, (raw - threshold * 0.5) / threshold))
            score += weight * normalized
        return round(min(1.0, score), 2)

    def calculate_event_confidence(self, signals: Dict, zone: str) -> float:
        """How confident are we this event is real?"""
        api_reliability = self.get_api_reliability_score(signals)
        behavioral = self.get_behavioral_consistency(zone)
        historical = self.get_historical_match(zone, signals)

        confidence = (0.50 * api_reliability +
                     0.30 * behavioral +
                     0.20 * historical)
        return round(confidence, 2)

    async def calculate_social_signal(self, zone: str) -> Dict:
        """Normalized social disruption detection."""
        current_active = await self.get_current_active_workers(zone)
        expected_active = await self.get_expected_active(zone)  # hour + day + zone baseline

        if expected_active == 0:
            return {"normalized_inactivity": 0}

        inactivity_ratio = current_active / expected_active
        # Invert: high inactivity = high signal
        normalized = max(0, 1.0 - inactivity_ratio)
        return {"normalized_inactivity": round(normalized, 2)}
```

---

## 🛡️ Fraud Detection Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                FRAUD DETECTION PIPELINE                  │
│                                                          │
│  Input: worker + event + claim attempt                   │
│                                                          │
│  ┌─────────────────┐                                    │
│  │ Layer 1: Dedup  │ → Same (worker, event, type)?      │
│  │                 │   YES → extend existing claim       │
│  │                 │   NO  → continue                    │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Layer 2: GPS    │ → Speed anomalies?                 │
│  │  Validation     │ → Missing delivery stops?          │
│  │                 │ → Zone consistency (pre-event)?     │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Layer 3: Device │ → Device fingerprint match?        │
│  │  Binding        │ → IP geolocation match?            │
│  │                 │ → Multiple accounts same device?    │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Layer 4: Cluster│ → >5 users same geofence + time?   │
│  │  Detection      │ → Smart filter: trust history       │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Layer 5: Timing │ → Policy purchased after event?    │
│  │  Abuse          │ → Within 24hr activation window?    │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Layer 6: Income │ → Self-report vs platform data     │
│  │  Verification   │ → Cap at 1.5× city average        │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Layer 7: Trust  │ → Reduce fraud_score for trusted   │
│  │  Adjustment     │ → adjusted = fraud - (0.2 × trust) │
│  └────────┬────────┘                                    │
│           ▼                                              │
│  OUTPUT: adjusted_fraud_score ∈ [0, 1]                  │
└─────────────────────────────────────────────────────────┘
```

### Implementation

```python
# backend/core/fraud_detector.py

class FraudDetector:
    """
    7-layer fraud detection pipeline.
    Returns adjusted_fraud_score in [0, 1].
    """

    WEIGHTS = {
        "movement": 0.20,
        "ip_mismatch": 0.15,
        "inactivity": 0.20,
        "cluster": 0.20,
        "timing": 0.10,
        "income_inflation": 0.10,
        "duplicate": 0.05
    }

    async def compute_fraud_score(self, worker, event, claim_attempt) -> dict:
        """Run all fraud layers and return composite score."""

        signals = {
            "movement": await self.check_movement(worker, event),
            "ip_mismatch": await self.check_device_binding(worker),
            "inactivity": await self.check_pre_event_activity(worker, event),
            "cluster": await self.check_cluster_fraud(worker, event),
            "timing": self.check_timing_abuse(worker, event),
            "income_inflation": await self.check_income(worker),
            "duplicate": await self.check_duplicate(worker, event)
        }

        raw_fraud_score = sum(
            self.WEIGHTS[key] * value
            for key, value in signals.items()
        )

        trust_score = await self.get_trust_score(worker.id)
        adjusted_fraud = max(0, raw_fraud_score - (0.2 * trust_score))

        # Log everything for audit
        await self.log_fraud_analysis(worker, event, signals, raw_fraud_score, adjusted_fraud)

        return {
            "raw_fraud_score": round(raw_fraud_score, 2),
            "adjusted_fraud_score": round(adjusted_fraud, 2),
            "trust_score": trust_score,
            "signals": signals,
            "flags": [k for k, v in signals.items() if v > 0.5]
        }

    async def check_duplicate(self, worker, event) -> float:
        """Check if worker already has a claim for this event."""
        existing = await db.claims.find_one(
            worker_id=worker.id,
            event_id=event.id,
            trigger_type=event.event_type
        )
        if existing:
            return 1.0  # definite duplicate
        return 0.0

    async def check_cluster_fraud(self, worker, event) -> float:
        """Detect coordinated claim rings."""
        claims_in_window = await db.claims.find(
            zone=event.zone,
            created_at__gte=event.started_at - timedelta(minutes=5),
            created_at__lte=event.started_at + timedelta(minutes=5)
        )

        if len(claims_in_window) > 5:
            # Smart filter: trusted workers get benefit of doubt
            if worker.trust_score > 0.7 and worker.total_claims > 3:
                return 0.2  # low flag despite cluster
            return 0.9  # high flag

        return 0.0

    async def check_movement(self, worker, event) -> float:
        """Validate GPS movement realism."""
        activity = await db.worker_activity.find(
            worker_id=worker.id,
            recorded_at__gte=event.started_at - timedelta(hours=2)
        )

        if not activity:
            return 0.8  # no movement data at all

        speeds = [a.speed_kmh for a in activity]
        has_stops = any(a.has_delivery_stop for a in activity)
        speed_variance = max(speeds) - min(speeds) if speeds else 0

        score = 0.0
        if not has_stops:
            score += 0.4           # no delivery stop pattern
        if speed_variance < 5:
            score += 0.3           # suspiciously uniform speed
        if max(speeds) > 80:
            score += 0.3           # impossible delivery speed

        return min(1.0, score)
```

---

## 🧠 Decision Engine Architecture

```python
# backend/core/decision_engine.py

class DecisionEngine:
    """
    Combines all signals into a single payout decision.
    Trust intentionally counted twice — in fraud adjustment AND as direct weight.
    """

    async def decide(self, disruption_score, event_confidence, fraud_result, worker) -> dict:
        adjusted_fraud = fraud_result["adjusted_fraud_score"]
        trust_score = fraud_result["trust_score"]

        final_score = (
            0.35 * disruption_score +
            0.25 * event_confidence +
            0.25 * (1 - adjusted_fraud) +
            0.15 * trust_score
        )

        if final_score > 0.70:
            decision = "approved"
        elif final_score >= 0.50:
            decision = "delayed"
        else:
            decision = "rejected"

        return {
            "final_score": round(final_score, 2),
            "decision": decision,
            "breakdown": {
                "disruption_component": round(0.35 * disruption_score, 3),
                "confidence_component": round(0.25 * event_confidence, 3),
                "fraud_component": round(0.25 * (1 - adjusted_fraud), 3),
                "trust_component": round(0.15 * trust_score, 3)
            },
            "review_deadline": (
                datetime.utcnow() + timedelta(hours=24)
                if decision == "delayed" else None
            )
        }

    async def calculate_payout(self, worker, event, policy) -> dict:
        """Calculate income loss with peak multiplier and caps."""
        verified_income = await self.verify_income(worker)
        income_per_hour = verified_income / worker.working_hours
        disruption_hours = self.calculate_disruption_hours(event)
        peak_mult = self.get_peak_multiplier(event.started_at.hour)

        raw_payout = income_per_hour * disruption_hours * peak_mult
        capped_payout = min(raw_payout, policy.coverage_cap)

        # City average cap
        city_avg_cap = await self.get_city_avg_income(worker.city) * 1.5
        final_payout = min(capped_payout, city_avg_cap)

        return {
            "income_per_hour": round(income_per_hour, 2),
            "disruption_hours": disruption_hours,
            "peak_multiplier": peak_mult,
            "raw_payout": round(raw_payout, 2),
            "plan_cap_applied": raw_payout > policy.coverage_cap,
            "city_cap_applied": capped_payout > city_avg_cap,
            "final_payout": round(final_payout, 2)
        }

    def get_peak_multiplier(self, hour: int) -> float:
        """Peak hour income sensitivity."""
        if 19 <= hour <= 22:    # dinner rush
            return 1.5
        elif 12 <= hour <= 14:  # lunch rush
            return 1.3
        return 1.0

    async def verify_income(self, worker) -> float:
        """Multi-source income verification."""
        self_reported = worker.self_reported_income
        platform_data = await self.get_platform_income(worker)  # simulated
        behavioral = await self.infer_behavioral_income(worker)

        verified = (0.3 * self_reported +
                   0.5 * platform_data +
                   0.2 * behavioral)

        city_cap = await self.get_city_avg_income(worker.city) * 1.5
        return min(verified, city_cap)
```

---

## 🤖 ML Model Architecture

### Model 1: Risk Scoring (Premium Pricing)

```python
# backend/ml/risk_model.py

"""
Risk Scoring Model
- Purpose: Calculate risk_score for weekly premium pricing
- Input: city, zone, season, weather forecast, disruption history
- Output: risk_score ∈ [0, 1]
- Approach: Gradient Boosting Regressor
- Training data: Historical weather + disruption frequency per zone
"""

from sklearn.ensemble import GradientBoostingRegressor
import joblib

class RiskModel:

    FEATURES = [
        "city_base_risk",           # 0.3 (bengaluru) to 0.8 (delhi)
        "month_risk",               # seasonal pattern
        "rain_forecast_7day",       # mm expected
        "heat_forecast_7day",       # days above 44°C expected
        "aqi_avg_30day",            # recent pollution trend
        "disruption_count_30day",   # events in last 30 days
        "social_instability_index", # curfew/strike history
        "platform_outage_rate"      # outage frequency
    ]

    def __init__(self):
        self.model = None

    def train(self, X, y):
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X, y)
        joblib.dump(self.model, "ml/train/risk_model.pkl")

    def predict(self, features: dict) -> float:
        if self.model is None:
            self.model = joblib.load("ml/train/risk_model.pkl")

        X = [[features.get(f, 0) for f in self.FEATURES]]
        score = self.model.predict(X)[0]
        return round(max(0.05, min(1.0, score)), 2)

    def calculate_premium(self, risk_score, base_price, plan_factor) -> int:
        raw = base_price * plan_factor * risk_score
        return max(int(round(raw)), base_price)  # never below base
```

### Model 2: Fraud Detection (Anomaly)

```python
# backend/ml/fraud_model.py

"""
Fraud Detection Model
- Purpose: Identify anomalous claim patterns
- Input: Movement features, device features, temporal features
- Output: anomaly_score ∈ [0, 1]
- Approach: Isolation Forest + rule-based hybrid
- Training: Self-supervised on historical claim data
"""

from sklearn.ensemble import IsolationForest
import numpy as np

class FraudModel:

    FEATURES = [
        "speed_variance",
        "delivery_stop_count",
        "pre_event_active_minutes",
        "device_consistency_score",
        "ip_geo_distance_km",
        "cluster_size",
        "account_age_days",
        "prior_fraud_flags"
    ]

    def __init__(self):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42
        )

    def predict_anomaly(self, features: dict) -> float:
        X = np.array([[features.get(f, 0) for f in self.FEATURES]])
        # IsolationForest: -1 = anomaly, 1 = normal
        raw_score = self.model.decision_function(X)[0]
        # Normalize to [0, 1] where 1 = most anomalous
        normalized = max(0, min(1, 0.5 - raw_score))
        return round(normalized, 2)
```

### Training Data Strategy

Since real delivery data isn't available, we generate **synthetic training data** based on documented patterns:

```python
# backend/ml/train/generate_training_data.py

def generate_risk_training_data(n_samples=5000):
    """
    Generate synthetic risk scoring data.
    Based on documented weather patterns, disruption frequencies,
    and city risk profiles from our README research.
    """
    cities = {
        "delhi": {"base": 0.65, "monsoon_boost": 0.25, "heat_boost": 0.20},
        "mumbai": {"base": 0.60, "monsoon_boost": 0.30, "heat_boost": 0.10},
        "bengaluru": {"base": 0.30, "monsoon_boost": 0.15, "heat_boost": 0.05},
        "chennai": {"base": 0.50, "monsoon_boost": 0.25, "heat_boost": 0.15}
    }
    # ... generate features with realistic noise
    # Target: disruption_probability for that week


def generate_fraud_training_data(n_samples=3000):
    """
    Generate synthetic fraud patterns.
    90% legitimate patterns, 10% fraudulent.
    Fraud patterns include:
    - Zero movement + claim filed
    - Cluster co-location
    - Device/IP mismatch
    - Post-event policy purchase
    """
    # ... generate with known fraud signatures
```

---

## 🎨 Frontend Architecture

### Component Tree

```
App
├── Router
│   ├── /onboarding → OnboardingPage
│   │   ├── RegistrationForm
│   │   ├── ConsentCheckbox
│   │   ├── RiskScoreDisplay
│   │   ├── PlanSelector
│   │   │   └── PremiumCalculator
│   │   └── PaymentConfirmation
│   │
│   ├── /dashboard → WorkerDashboard
│   │   ├── ActivePlanCard
│   │   ├── ClaimsFeed
│   │   │   └── ClaimStatusBadge
│   │   ├── PayoutHistory
│   │   ├── DisruptionAlerts
│   │   │   └── LiveTriggerIndicator
│   │   ├── TrustScoreBadge
│   │   └── WeeklyEarningsChart
│   │
│   ├── /admin → AdminDashboard
│   │   ├── KPICards (active policies, claims, fraud rate, loss ratio)
│   │   ├── DisruptionMap (Leaflet.js)
│   │   ├── ClaimsTable
│   │   │   └── ClaimDetailModal (signal breakdown)
│   │   ├── ReviewQueue
│   │   │   └── ReviewActionButtons
│   │   ├── FraudStatsPanel
│   │   ├── LossRatioChart
│   │   ├── ForecastPanel
│   │   └── WorkerActivityIndex
│   │
│   └── /demo → DemoRunner
│       ├── ScenarioSelector (3 pre-built)
│       ├── TimelineVisualizer
│       └── SignalBreakdownView
│
└── Shared Components
    ├── Navbar
    ├── NotificationToast
    ├── LoadingSpinner
    └── ErrorBoundary
```

### Key Pages — What They Show

**Onboarding Page**
```
┌─────────────────────────────────────┐
│  🛵 RideShield                      │
│                                     │
│  Register for Income Protection     │
│                                     │
│  Name:     [_______________]        │
│  Phone:    [_______________]        │
│  City:     [Delhi ▼       ]        │
│  Zone:     [South Delhi ▼ ]        │
│  Platform: [Zomato ▼      ]        │
│  Daily Income: [₹900      ]        │
│  Hours/Day:    [9          ]        │
│                                     │
│  ☑ I consent to location tracking   │
│    for claim validation             │
│                                     │
│  [Calculate My Risk Score →]        │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Your Risk Score: 0.58       │   │
│  │ ████████████░░░░░░░░        │   │
│  │ Moderate risk — Delhi zone  │   │
│  └─────────────────────────────┘   │
│                                     │
│  Recommended: Smart Protect ₹35/wk │
│                                     │
│  ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ Basic  │ │ Smart  │ │Assured │ │
│  │ ₹31/wk │ │ ₹35/wk │ │ ₹62/wk │ │
│  │ ₹300cap│ │ ₹600cap│ │ ₹800cap│ │
│  └────────┘ └────────┘ └────────┘ │
│                                     │
│  [Purchase Plan →]                  │
│  Activates: March 22, 2:00 PM      │
└─────────────────────────────────────┘
```

**Worker Dashboard**
```
┌─────────────────────────────────────┐
│  Welcome, Rahul           Trust: ⭐⭐⭐ │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Active Plan: Smart Protect   │  │
│  │ Coverage: ₹600 cap           │  │
│  │ Expires: March 28            │  │
│  │ [Renew Plan]                 │  │
│  └──────────────────────────────┘  │
│                                     │
│  ⚡ LIVE ALERTS                     │
│  ┌──────────────────────────────┐  │
│  │ 🌧 Rain warning: South Delhi │  │
│  │   42mm/hr — threshold: 25mm  │  │
│  │   Status: Active since 2 PM  │  │
│  └──────────────────────────────┘  │
│                                     │
│  📊 This Week                       │
│  Claims: 2 approved, 0 delayed     │
│  Payouts: ₹280 + ₹180 = ₹460      │
│  Income protected: ₹460 / ₹600 cap │
│                                     │
│  💰 Payout History                  │
│  ┌──────────────────────────────┐  │
│  │ Mar 18  Rain   ₹280  ✅     │  │
│  │ Mar 16  AQI    ₹180  ✅     │  │
│  │ Mar 12  Rain   ₹150  ✅     │  │
│  │ Mar 9   —      —     —      │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## 💳 Payment Architecture

```
┌───────────────────────────────────────────┐
│              PAYOUT EXECUTOR               │
│                                           │
│  Input: approved claim + final_payout     │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ Plan type check:                    │  │
│  │   Basic/Smart/Assured → Wallet      │  │
│  │   Pro Max → UPI direct transfer     │  │
│  └────────────┬────────────────────────┘  │
│               │                           │
│        ┌──────┴──────┐                    │
│        ▼             ▼                    │
│  ┌──────────┐  ┌──────────┐              │
│  │ Razorpay │  │   UPI    │              │
│  │ Sandbox  │  │ Simulator│              │
│  │          │  │          │              │
│  │ wallet   │  │ direct   │              │
│  │ credit   │  │ transfer │              │
│  └────┬─────┘  └────┬─────┘              │
│       │              │                    │
│       ▼              ▼                    │
│  ┌──────────────────────────────────┐    │
│  │ Generate transaction_id          │    │
│  │ Log to payouts table             │    │
│  │ Update claim status              │    │
│  │ Push notification to worker      │    │
│  │ Write audit log                  │    │
│  └──────────────────────────────────┘    │
└───────────────────────────────────────────┘
```

```python
# backend/api/payouts.py

class PayoutExecutor:
    """Handles payout execution via Razorpay sandbox or UPI simulator."""

    async def execute(self, claim, worker, policy):
        if policy.plan_name == "promax":
            result = await self.upi_transfer(worker, claim.final_payout)
        else:
            result = await self.wallet_credit(worker, claim.final_payout)

        payout = await db.payouts.create(
            claim_id=claim.id,
            worker_id=worker.id,
            amount=claim.final_payout,
            channel=result["channel"],
            transaction_id=result["transaction_id"],
            status="completed"
        )

        await self.push_notification(worker, claim, payout)
        await self.write_audit_log(payout)
        return payout

    async def wallet_credit(self, worker, amount):
        """Razorpay sandbox wallet credit."""
        # In production: actual Razorpay API call
        # In demo: simulated with realistic delay
        txn_id = f"wallet_{uuid4().hex[:12]}"
        return {"channel": "wallet", "transaction_id": txn_id}

    async def upi_transfer(self, worker, amount):
        """UPI direct transfer simulation."""
        txn_id = f"upi_{uuid4().hex[:12]}"
        return {"channel": "upi", "transaction_id": txn_id}
```

---

## 🎭 Simulation Layer

Since we don't have real Zomato/weather APIs in sandbox, we build realistic simulators:

```python
# simulations/weather_mock.py

"""
Weather API Simulator
Returns realistic weather data for Delhi zones.
Can be forced into specific scenarios for demo.
"""

class WeatherSimulator:

    ZONES = {
        "south_delhi": {"lat": 28.52, "lon": 77.22},
        "north_delhi": {"lat": 28.70, "lon": 77.10},
        "east_delhi": {"lat": 28.63, "lon": 77.30},
        "west_delhi": {"lat": 28.65, "lon": 77.05}
    }

    def __init__(self, scenario=None):
        self.scenario = scenario  # override for demo

    def get_weather(self, zone: str) -> dict:
        if self.scenario == "heavy_rain":
            return {
                "rainfall_mm_hr": 48.0,
                "temperature_c": 28.0,
                "humidity": 95,
                "wind_speed_kmh": 35
            }
        elif self.scenario == "extreme_heat":
            return {
                "rainfall_mm_hr": 0.0,
                "temperature_c": 46.5,
                "humidity": 15,
                "wind_speed_kmh": 8
            }
        else:
            # Realistic random variation
            return self._generate_realistic(zone)
```

```python
# simulations/platform_mock.py

"""
Platform Order Density Simulator
Simulates Zomato order density per zone.
Can simulate outages and demand drops.
"""

class PlatformSimulator:

    def get_order_density(self, zone: str) -> dict:
        if self.scenario == "platform_outage":
            return {
                "orders_per_hour": 5,         # normally ~50
                "density_drop_percent": 0.90,
                "active_restaurants": 3        # normally ~30
            }
        # ... realistic generation
```

### Pre-Built Demo Scenarios

```json
// simulations/scenarios/legitimate_rain.json
{
    "name": "Scenario 1: Legitimate Rain Claim",
    "description": "Rahul is active, rain hits, system auto-pays",
    "steps": [
        {"time": "10:00", "action": "rahul_starts_shift", "deliveries": 6},
        {"time": "14:00", "action": "rain_starts", "rainfall_mm": 48},
        {"time": "14:05", "action": "trigger_fires", "type": "rain"},
        {"time": "14:05", "action": "order_density_drops", "drop": 0.70},
        {"time": "14:06", "action": "claim_generated", "fraud_score": 0.18},
        {"time": "14:06", "action": "decision_approved", "final_score": 0.82},
        {"time": "14:07", "action": "payout_credited", "amount": 280}
    ]
}
```

---

## 📅 Phase 2 Sprint Plan (March 21 – April 4)

> **Goal:** Working end-to-end flow: Onboard → Insure → Detect → Validate → Pay
> **Deliverable:** Executable code + 2-minute demo video

### Sprint 1 (March 21–25): Backend Foundation — 5 days

| Day | Task | Output |
|---|---|---|
| **Day 1** (Mar 21) | Project setup: FastAPI scaffold, PostgreSQL setup, Alembic init, .env config | Running `main.py` with health check endpoint |
| **Day 2** (Mar 22) | Database models + migrations for all 8 tables | All tables created, relationships verified |
| **Day 3** (Mar 23) | Workers API: `/register`, `/me` + Risk score calculation (rule-based first, ML later) | Worker registration working end-to-end |
| **Day 4** (Mar 24) | Policies API: `/plans`, `/create`, `/active` + Premium calculation with 24hr activation | Plan purchase working, premium formula verified |
| **Day 5** (Mar 25) | Simulation layer: weather mock, platform mock, scenario loader | Simulated APIs returning realistic data |

### Sprint 2 (March 26–30): Core Engine — 5 days

| Day | Task | Output |
|---|---|---|
| **Day 6** (Mar 26) | Trigger engine: threshold evaluation + event creation/extension | Triggers firing correctly from simulated data |
| **Day 7** (Mar 27) | Fraud detector: Layers 1–4 (dedup, GPS, device, cluster) — rule-based | Fraud scoring working, test cases passing |
| **Day 8** (Mar 28) | Decision engine: final_score calculation + approve/delay/reject routing | End-to-end: trigger → fraud check → decision |
| **Day 9** (Mar 29) | Income verifier + payout calculator (peak multiplier, caps) | Correct payout amounts verified |
| **Day 10** (Mar 30) | Payout executor: Razorpay sandbox simulation + audit logging | Full pipeline: trigger → claim → payout |

### Sprint 3 (March 31 – April 4): Frontend + Demo — 5 days

| Day | Task | Output |
|---|---|---|
| **Day 11** (Mar 31) | React setup + Onboarding page (registration form, plan selector) | Working onboarding flow |
| **Day 12** (Apr 1) | Worker Dashboard (active plan, claims feed, payout history) | Dashboard showing real data from API |
| **Day 13** (Apr 2) | Connect frontend ↔ backend, end-to-end testing | Full flow works in browser |
| **Day 14** (Apr 3) | Bug fixes, edge cases, demo scenario testing | All 3 scenarios run cleanly |
| **Day 15** (Apr 4) | **📹 Record 2-minute demo video** | Video uploaded |

### Phase 2 Definition of Done

```
✅ Worker can register and see risk score
✅ Worker can purchase a weekly plan
✅ Trigger engine detects simulated disruptions
✅ Claims are auto-generated (zero-touch)
✅ Basic fraud checks run before payout
✅ Payout is credited with transaction ID
✅ Worker dashboard shows claims and payouts
✅ 2-minute demo video recorded and submitted
```

---

## 📅 Phase 3 Sprint Plan (April 5 – April 17)

> **Goal:** Advanced fraud, admin dashboard, polish, judging assets
> **Deliverables:** Advanced fraud detection, dashboard, 5-min video, pitch deck PDF

### Sprint 4 (April 5–9): Advanced Fraud + Admin — 5 days

| Day | Task | Output |
|---|---|---|
| **Day 16** (Apr 5) | ML fraud model: train Isolation Forest on synthetic data | Trained model artifact saved |
| **Day 17** (Apr 6) | ML risk model: train GBR on synthetic disruption data | Dynamic risk scoring replacing rules |
| **Day 18** (Apr 7) | Advanced fraud layers: timing abuse, income verification, trust score | Full 7-layer fraud pipeline |
| **Day 19** (Apr 8) | Admin dashboard: KPI cards, claims table, review queue | Admin can see and act on delayed claims |
| **Day 20** (Apr 9) | Admin dashboard: Disruption map (Leaflet.js), loss ratio chart | Heatmap and analytics visible |

### Sprint 5 (April 10–13): Polish + Predictive — 4 days

| Day | Task | Output |
|---|---|---|
| **Day 21** (Apr 10) | Fraud stats panel, duplicate claim log, cluster alert view | Admin sees full fraud picture |
| **Day 22** (Apr 11) | Predictive pricing: forecast display, next-week risk zones | Pro Max feature working |
| **Day 23** (Apr 12) | Worker dashboard polish: trust badge, claim explainability, alerts | Worker sees why decisions were made |
| **Day 24** (Apr 13) | Demo scenario runner: all 3 scenarios with timeline visualization | Scenarios runnable from UI |

### Sprint 6 (April 14–17): Judging Assets — 4 days

| Day | Task | Output |
|---|---|---|
| **Day 25** (Apr 14) | End-to-end testing, bug fixes, edge case handling | System stable |
| **Day 26** (Apr 15) | **📄 Build final pitch deck PDF** | PDF ready |
| **Day 27** (Apr 16) | **📹 Record 5-minute demo video** | Video ready |
| **Day 28** (Apr 17) | Final submission: code, video, pitch deck, README | ✅ Submitted |

### Phase 3 Definition of Done

```
✅ ML-based fraud model replacing pure rules
✅ ML-based risk model for dynamic premium pricing
✅ Full 7-layer fraud pipeline with trust system
✅ Admin dashboard with loss ratio, fraud stats, review queue
✅ Disruption heatmap showing active zones
✅ Worker dashboard with claim explainability
✅ Predictive risk forecast visible
✅ All 3 demo scenarios work end-to-end
✅ Pitch deck PDF covers persona + AI architecture + viability
✅ 5-minute demo video recorded and submitted
✅ README final and complete
```

---

## 📆 Day-by-Day Execution Calendar

```
MARCH 2025
═══════════════════════════════════════════════════════
Mon    Tue    Wed    Thu    Fri    Sat    Sun
                                  21     22     23
                                  Setup  DB     Workers
                                  FastAPI Models API

24     25     26     27     28     29     30
Policy Sims   Trigger Fraud  Decision Income  Payout
API    Layer  Engine Detect  Engine  Verify  Exec

31
React
Onboarding

APRIL 2025
═══════════════════════════════════════════════════════
Mon    Tue    Wed    Thu    Fri    Sat    Sun
       1      2      3      4
       Worker Connect Bugs   📹 2-MIN
       Dash   E2E    Fix    VIDEO
                             ─── PHASE 2 DONE ───

       ─── PHASE 3 STARTS ───
7      8      9      10     11     12     13
ML     ML     Admin  Admin  Fraud  Predict Demo
Fraud  Risk   Dash   Map+   Stats  Pricing Scenar
Model  Model  Queue  Loss          Forecast ios

14     15     16     17
E2E    📄PITCH 📹5-MIN ✅
Test   DECK   VIDEO  SUBMIT
                      ─── PHASE 3 DONE ───
```

---

## 🧪 Testing Strategy

### Test Categories

```
tests/
├── test_workers.py           # Registration, risk score, consent
├── test_policies.py          # Plan creation, premium calculation, activation delay
├── test_trigger_engine.py    # Threshold evaluation, event dedup, zone filtering
├── test_fraud_detector.py    # All 7 layers individually + combined
├── test_claim_dedup.py       # Duplicate prevention, event extension
├── test_decision_engine.py   # Score calculation, routing, edge cases
├── test_income_verifier.py   # Multi-source verification, caps
├── test_payouts.py           # Payout execution, audit logging
├── test_scenarios.py         # Full scenario 1, 2, 3 end-to-end
└── test_api_integration.py   # API endpoint integration tests
```

### Critical Test Cases

```python
# test_claim_dedup.py

def test_same_event_does_not_create_duplicate_claim():
    """Worker should get ONE claim per event, not multiple."""
    worker = create_test_worker()
    event = create_rain_event(zone="south_delhi")

    claim1 = process_claim(worker, event)
    claim2 = process_claim(worker, event)  # same event fires again

    assert claim1.id == claim2.id  # same claim, extended
    assert count_claims(worker) == 1

def test_different_events_create_separate_claims():
    """Two different events should create two claims."""
    worker = create_test_worker()
    rain_event = create_rain_event(zone="south_delhi", hour=14)
    heat_event = create_heat_event(zone="south_delhi", hour=14)

    claim1 = process_claim(worker, rain_event)
    claim2 = process_claim(worker, heat_event)

    assert claim1.id != claim2.id
    assert count_claims(worker) == 2


# test_decision_engine.py

def test_high_trust_high_confidence_approves():
    result = decide(disruption=0.8, confidence=0.85, fraud=0.1, trust=0.9)
    assert result["decision"] == "approved"
    assert result["final_score"] > 0.70

def test_high_fraud_rejects():
    result = decide(disruption=0.8, confidence=0.85, fraud=0.9, trust=0.1)
    assert result["decision"] == "rejected"
    assert result["final_score"] < 0.50

def test_new_user_borderline_delays():
    result = decide(disruption=0.6, confidence=0.7, fraud=0.4, trust=0.1)
    assert result["decision"] == "delayed"
    assert result["review_deadline"] is not None


# test_trigger_engine.py

def test_rain_below_threshold_does_not_fire():
    signals = {"rain": 20.0}  # below 25mm threshold
    fired = evaluate_thresholds(signals)
    assert "rain" not in fired

def test_multiple_triggers_fire_together():
    signals = {"rain": 30.0, "aqi": 350, "traffic": 0.80}
    fired = evaluate_thresholds(signals)
    assert set(fired) == {"rain", "aqi", "traffic"}
```

---

## 🚀 Deployment Architecture

### Development (Local)
```
docker-compose up
├── backend:   localhost:8000  (FastAPI + Uvicorn)
├── frontend:  localhost:3000  (React dev server)
├── database:  localhost:5432  (PostgreSQL)
└── pgadmin:   localhost:5050  (DB management)
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://rideshield:password@db:5432/rideshield
      - OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}
      - RAZORPAY_KEY=${RAZORPAY_KEY}
      - SIMULATION_MODE=true
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=rideshield
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=rideshield
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  pgadmin:
    image: dpage/pgadmin4
    ports:
      - "5050:80"
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@rideshield.dev
      - PGADMIN_DEFAULT_PASSWORD=admin

volumes:
  pgdata:
```

### Production (Demo)
```
Vercel  ← Frontend (React build)
  │
  ├── API calls
  ▼
Render  ← Backend (FastAPI + Gunicorn)
  │
  ├── Database connection
  ▼
Render PostgreSQL  ← Managed database
```

### Environment Variables
```env
# .env.example

# Database
DATABASE_URL=postgresql://rideshield:password@localhost:5432/rideshield

# External APIs
OPENWEATHER_API_KEY=your_key_here
WAQI_API_KEY=your_key_here
TOMTOM_API_KEY=your_key_here

# Payments
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx

# Application
SIMULATION_MODE=true
TRIGGER_CHECK_INTERVAL_SECONDS=300
ACTIVATION_DELAY_HOURS=24
CLUSTER_FRAUD_THRESHOLD=5

# ML Models
RISK_MODEL_PATH=ml/train/risk_model.pkl
FRAUD_MODEL_PATH=ml/train/fraud_model.pkl
```

---

## 🎬 Demo Script Plan

### 2-Minute Demo (Phase 2) — Core Flow

```
0:00–0:15  Problem statement + Rahul intro (voiceover)
0:15–0:40  Onboarding: register, see risk score, buy Smart Protect plan
0:40–1:00  Show: trigger engine detecting rain in South Delhi
1:00–1:20  Show: claim auto-generated, fraud check passes
1:20–1:40  Show: payout credited to wallet, notification pushed
1:40–2:00  Show: worker dashboard with claim and payout visible
```

### 5-Minute Demo (Phase 3) — Full System

```
0:00–0:30  Problem + persona + why parametric insurance
0:30–1:30  Scenario 1: Rahul's legitimate rain claim (full flow)
1:30–2:30  Scenario 2: Vikram's fraud attempt → rejected
2:30–3:15  Scenario 3: Arun's edge case → delayed → admin review
3:15–4:00  Admin dashboard: loss ratio, disruption map, fraud stats
4:00–4:30  Predictive pricing, trust system, duplicate prevention
4:30–5:00  Business viability (72% loss ratio), scalability, what's next
```

---

## ⚠️ Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| External API rate limits | Medium | Medium | Use simulation layer as primary during dev. Real APIs for final demo only. |
| PostgreSQL setup issues | Low | High | Docker handles this. Fallback: SQLite for rapid dev. |
| ML model performance | Medium | Low | Start with rule-based scoring. ML replaces rules in Phase 3. |
| Frontend complexity | Medium | Medium | Start with minimal viable UI. Polish in Phase 3. |
| Time overrun | High | High | Strict daily targets. Cut predictive pricing before cutting core flow. |
| Demo failure during recording | Medium | High | Record in segments. Have backup recording ready. |
| Razorpay sandbox issues | Low | Low | Pure simulation fallback with fake transaction IDs. |

### What to Cut If Behind Schedule

Priority order — cut from bottom first:

```
MUST HAVE (never cut):
  ✅ Worker registration + risk score
  ✅ Plan purchase + premium calculation
  ✅ Trigger detection → claim generation
  ✅ Basic fraud check
  ✅ Payout execution
  ✅ Worker dashboard (basic)
  ✅ 2-min demo video

SHOULD HAVE (cut last):
  🟡 Admin dashboard
  🟡 ML-based fraud model
  🟡 ML-based risk model
  🟡 Disruption heatmap
  🟡 5-min demo video
  🟡 Pitch deck PDF

NICE TO HAVE (cut first):
  🟢 Predictive pricing
  🟢 Demo scenario runner UI
  🟢 Trust score visualization
  🟢 Forecast panel
```

---

## 🏃 Immediate Next Steps

### Tomorrow (Day 1 — March 21)

```
Morning:
  □ Create rideshield/ project directory
  □ Initialize git repo
  □ Set up FastAPI project with main.py
  □ Install dependencies (requirements.txt)
  □ Configure .env with database URL
  □ Set up docker-compose.yml
  □ Verify: docker-compose up → backend + db running

Afternoon:
  □ Create Alembic config (alembic init)
  □ Write first model: Workers table
  □ Run first migration
  □ Create health check endpoint: GET /health → {"status": "ok"}
  □ Verify: can hit endpoint from browser

Evening:
  □ Write remaining 7 table models
  □ Run all migrations
  □ Verify: all tables exist in PostgreSQL
  □ Commit: "Day 1: Project scaffold + database schema"
```

### The Week After That

```
Day 2: Workers API complete
Day 3: Policies API complete
Day 4: Simulation layer
Day 5: Trigger engine
Day 6: Fraud detector
Day 7: Decision engine
Day 8: Payout executor
Day 9: React onboarding
Day 10: React dashboard
```

> **The single most important rule:** End every day with a working commit. Never go to sleep with broken code on `main`. If a feature isn't done, stub it and commit what works.

---

## 🏁 Architecture Summary

```
What we're building:
  → A real-time parametric insurance system

How it works:
  → Monitor → Detect → Validate → Score → Pay → Log

What makes it work:
  → Multi-signal validation (never trust one source)
  → Event-centric deduplication (one event = one claim)
  → 7-layer fraud defense (from GPS to clusters)
  → Peak-aware income calculation
  → Auditable decision trails

What we ship:
  → Phase 2: Working core flow + 2-min video
  → Phase 3: Advanced fraud + admin dashboard + 5-min video + pitch deck

How we know it works:
  → 3 demo scenarios covering legitimate, fraudulent, and edge cases
  → 72% loss ratio demonstrating financial viability
  → Full audit trail for every decision
```

> **Start building. Day 1 is March 21. The architecture is done. The plan is done. Now execute.** 🚀