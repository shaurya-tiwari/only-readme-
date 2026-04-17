# 🏗️ RideShield — Architecture

## 🔷 Architecture Overview

RideShield is a **3-tier monorepo application** with clear separation between data ingestion, business logic, and presentation.

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                       │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │  Onboarding  │  │   Worker     │  │   Admin Dashboard    │  │
│   │    Flow      │  │  Dashboard   │  │  (Fraud + Analytics) │  │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│          │                 │                      │             │
│   ┌──────▼───────────┐     │                      │             │
│   │ WhatsApp Webhook │     │                      │             │
│   └──────────┬───────┘     │                      │             │
│              │             │                      │             │
├──────────┼─────────────────┼──────────────────────┼─────────────┤
│          │          API GATEWAY (FastAPI)          │            │
│          │                 │                      │             │
│   ┌──────▼───────┐  ┌─────▼────────┐  ┌─────────▼───────────┐   │
│   │  Workers API │  │  Claims API  │  │   Analytics API     │   │
│   │  Policies API│  │  Payouts API │  │   Fraud Review API  │   │
│   └──────┬───────┘  └─────┬────────┘  └─────────┬───────────┘   │
│          │                │                      │              │
├──────────┼────────────────┼──────────────────────┼──────────────┤
│          │         BUSINESS LOGIC LAYER           │             │
│          │                │                      │              │
│   ┌──────▼───────┐  ┌────▼─────────┐  ┌────────▼──────────┐     │
│   │   Risk       │  │  Trigger     │  │  Fraud Detection  │     │
│   │   Scoring    │  │  Engine      │  │  Pipeline         │     │
│   └──────┬───────┘  └────┬─────────┘  └────────┬──────────┘     │
│          │               │                      │               │
│          │         ┌─────▼─────────┐            │               │
│          │         │   Decision    ◄────────────┘               │
│          │         │   Engine      │                            │
│          │         └─────┬─────────┘                            │
│          │               │                                      │
│   ┌──────▼───────┐  ┌───▼──────────┐  ┌───────────────────┐     │
│   │   Income     │  │   Payout     │  │   Audit Logger    │     │
│   │   Verifier   │  │   Executor   │  │                   │     │
│   └──────────────┘  └──────────────┘  └───────────────────┘     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                               │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│   │  PostgreSQL  │  │  External    │  │   ML Model        │     │
│   │  Database    │  │  APIs        │  │   Artifacts       │     │
│   └──────┬───────┘  └──────┬───────┘  └───────────────────┘     │
│          │                 │                                    │
│          │          ┌──────▼───────┐                            │
│          │          │ Meta WA API  │                            │
│          │          └──────────────┘                            │
└──────────┼─────────────────┼────────────────────────────────────┘
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

### Deployment Note: Railway Schema Bootstrap

The scheduler heartbeat now depends on a lightweight `system_status` table in PostgreSQL.
If a Railway database is behind the current ORM shape or has Alembic lineage drift, run:

```bash
python scripts/ensure_system_status_table.py
```

This script is idempotent and only bootstraps `system_status` plus the default `scheduler_state` row.

### Deployment Note: Vercel Proxy

For production, the frontend only talks to `/api/proxy`.
The Vercel serverless proxy then forwards requests to Railway.

`vercel.json` rewrite (hardcoded - env vars not supported in rewrites):

```json
{
  "source": "/api/proxy/:path*",
  "destination": "https://ride-shield-backend-production.up.railway.app/:path*"
}
```

`VITE_API_URL` should not be set in Vercel for this architecture.

---

## ⚡ Core Components

### 1. Trigger Engine


```
┌─────────────────────────────────────────────────────┐
│                 TRIGGER SCHEDULER                   │
│              (runs every 5 minutes)                 │
│                                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐   │
│  │ Weather │ │   AQI   │ │ Traffic │ │ Platform │   │
│  │ Checker │ │ Checker │ │ Checker │ │ Checker  │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘   │
│       │           │           │            │        │
│       ▼           ▼           ▼            ▼        │
│  ┌──────────────────────────────────────────────┐   │
│  │          THRESHOLD EVALUATOR                 │   │
│  │                                              │   │
│  │  Rain > 25mm/hr?          ✓ → fire           │   │
│  │  Temp > 44°C?             ✓ → fire           │   │
│  │  AQI > 300?               ✓ → fire           │   │
│  │  Congestion > 0.75?       ✓ → fire           │   │
│  │  Order density drop > 60%? ✓ → fire          │   │
│  │  Normalized inactivity?    ✓ → fire          │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │          EVENT MANAGER                        │  │
│  │                                               │  │
│  │  Existing event for this zone + type + hour?  │  │
│  │     YES → update severity, extend duration    │  │
│  │     NO  → create new event record             │  │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │     AFFECTED WORKER IDENTIFIER               │   │
│  │                                              │   │
│  │  Find all workers WHERE:                     │   │
│  │    - policy.status = 'active'                │   │
│  │    - policy.activates_at < NOW()             │   │
│  │    - worker.zone = event.zone                │   │
│  │    - trigger_type IN policy.triggers_covered │   │
│  │    - no existing claim for this event        │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│           CLAIM GENERATION PIPELINE                 │
└─────────────────────────────────────────────────────┘
```

### 2. Fraud Detection Pipeline


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

### 3. Decision Engine


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

