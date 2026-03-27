# 🛵 RideShield — Parametric AI Insurance for Gig Delivery Workers

> **"Claims are automatically initiated by the system. Delivery partners never file claims."**

A recharge-style, AI-powered parametric insurance system that protects Zomato delivery partners' income in real-time — triggered by rain, pollution, platform outages, and curfews — using multi-signal fraud detection and zero-touch payouts.

---

## ✅ Requirement Coverage

| Requirement | Status |
|---|---|
| Weekly pricing model | ✔ Covered — formula, 4 plan tiers, worked example |
| AI risk profiling | ✔ Covered — regression model, city + weather + social inputs |
| Parametric triggers (5 types) | ✔ Covered — rain, AQI, traffic, platform, social |
| Zero-touch claim automation | ✔ Covered — no worker action required, system-initiated |
| Fraud detection | ✔ Covered — anomaly scoring, cluster detection, trust system |
| Adversarial defense & anti-spoofing | ✔ Covered — GPS spoofing, device farms, API injection defenses |
| Coverage exclusions | ✔ Defined — war, pandemic, self-inflicted, pre-existing exclusions |
| Analytics dashboard | ✔ Covered — worker + admin views with defined metrics |
| Payout processing | ✔ Covered — Razorpay sandbox + UPI simulator |
| Worker onboarding | ✔ Covered — workflow step 1, risk score on signup |
| Income-only scope | ✔ Enforced — no health, accident, or vehicle coverage |

---

## 📌 Table of Contents

1. [Requirement Coverage](#-requirement-coverage)
2. [Problem & Persona](#-problem--persona)
3. [Persona-Based Scenario](#-persona-based-scenario)
4. [System Workflow](#-system-workflow)
5. [Weekly Premium Model](#-weekly-premium-model)
6. [Parametric Triggers](#-parametric-trigger-engine)
7. [AI/ML Integration](#-aiml-integration)
8. [Coverage Scope & Exclusions](#-coverage-scope--exclusions)
9. [Adversarial Defense & Anti-Spoofing](#️-adversarial-defense--anti-spoofing-strategy)
10. [Tech Stack](#-tech-stack)
11. [Repository Structure](#-repository-structure)
12. [Development Plan](#-development-plan)
13. [Analytics Dashboard](#-analytics-dashboard)
14. [Platform Justification](#-platform-justification-web)
15. [Innovation & Extras](#-innovation--extras)
16. [Challenges We Navigated](#️-challenges-we-navigated)
17. [What's Next](#-whats-next)
18. [Summary](#-summary)

---

## 🚨 Problem & Persona

### The Problem
Gig delivery workers lose **20–30% of their weekly income** due to disruptions beyond their control:

| Disruption Type | Examples |
|---|---|
| 🌧 Environmental | Heavy rain, extreme heat, AQI spikes |
| ⚡ Platform | App outages, low order density |
| 🚨 Social | Government curfews, local strikes, zone closures |

**Current Gap:**
- ❌ No income protection product exists for gig workers
- ❌ No real-time, automated compensation mechanism
- ❌ Traditional insurance is too slow, manual, and health/accident-focused

### The Persona: Rahul

> Rahul is a 28-year-old Zomato delivery partner in Delhi. He owns a bike and works 8–10 hours daily. His income depends entirely on the number of deliveries he completes. One rainy afternoon can wipe out ₹300–₹400 from his day.

| Attribute | Value |
|---|---|
| City | Delhi |
| Platform | Zomato |
| Earnings per delivery | ₹25–₹40 |
| Deliveries per hour | 2–3 |
| Average daily income | ₹800–₹1,000 |
| Working hours | 8–10 hrs/day |

**What Rahul needs:** A simple, affordable, automatic safety net that pays him when the world makes it impossible to work — without paperwork, without waiting, without filing anything.

---

## 🎬 Persona-Based Scenario

### Scenario 1 ✅ — Legitimate Claim (Rain + Traffic)

> *Delhi, Tuesday, 2:00 PM*

Rahul starts his shift at 10 AM. He completes 6 deliveries in 2 hours. At 2 PM, heavy rainfall begins — measured at 48mm/hr, exceeding our 25mm/hr threshold.

**What the system does automatically:**
1. Weather API detects rainfall crossing threshold
2. Rahul's GPS confirms he was active in the affected zone before disruption
3. Platform data shows order density dropped 70% in his area
4. Multi-signal validation confirms event is real (confidence: 0.87)
5. Movement pattern confirms Rahul was genuinely trying to work
6. Fraud score: 0.18 → clean
7. **Claim auto-generated. ₹280 credited to wallet in 90 seconds.**

Rahul receives a notification: *"Heavy rain detected. ₹280 income protection credited."*

---

### Scenario 2 ❌ — Fraud Attempt (Fake GPS + No Activity)

> *Delhi, Same Tuesday*

Another user, Vikram, registers from the same location as Rahul. He has been completely stationary for 6 hours. He's part of a cluster of 23 users from the same 500m radius all triggering claims at the same timestamp.

**What the system does:**
1. Cluster detection fires: 23 users, same geofence, same timestamp
2. Vikram's movement pattern shows zero delivery stops
3. Speed data shows no bike movement
4. IP address mismatches registered device
5. Fraud score: 0.81 → **Claim rejected automatically**

---

### Scenario 3 ⚠️ — Edge Case (Curfew, Ambiguous Activity)

> *Delhi, Friday evening — Section 144 imposed*

A curfew is declared at 6 PM. Arun claims income loss. However, Arun had zero deliveries logged in the 4 hours before the curfew — suggesting he wasn't working that day.

**What the system does:**
1. Social event detected via admin flag + mass inactivity pattern
2. Arun's pre-disruption activity is near-zero
3. Confidence score is valid, but trust score is low (new user, no history)
4. Final score: 0.54 → **Claim delayed for manual review**

---

## ⚙️ System Workflow

```
[1] Worker Onboarding
    └── Name, city, platform, income, hours
    └── Risk score generated
    └── Weekly plan recommended & purchased
         ↓
[2] Continuous Monitoring (Real-Time)
    └── Weather APIs → Rain, AQI, Heat
    └── Platform signals → Outage detection
    └── Social signals → Curfew flags, inactivity patterns
         ↓
[3] Disruption Detected
    └── Parametric trigger threshold crossed
    └── Affected zone identified
    └── Active workers in zone filtered
         ↓
[4] Multi-Signal Validation
    └── Event confidence scored (API + behavioral + historical)
    └── Worker activity verified (GPS, speed, delivery stops)
    └── Fraud detection model runs
    └── Cluster fraud check
         ↓
[5] Claim Auto-Generated (Zero-Touch)
    └── Income loss calculated automatically
    └── No action required from worker
         ↓
[6] Decision Engine
    └── final_score = f(disruption, confidence, fraud, trust)
    └── Score → Instant / Delayed / Rejected
         ↓
[7] Payout Execution
    └── Channel 1: In-app wallet credit (Razorpay sandbox simulation)
    └── Channel 2: UPI direct transfer simulation (for Pro Max plan)
    └── Notification pushed to worker
    └── Claim logged with full audit trail + transaction ID
```

> ⚠️ **Zero-touch design is intentional.** Rahul never opens the app to file a claim. The system acts on his behalf the moment a valid disruption is detected.

---

## 💰 Weekly Premium Model

### Why Weekly?
Gig workers don't receive monthly salaries. Their income is daily and volatile. A weekly recharge cycle matches their earnings rhythm — affordable, flexible, and predictable.

### Premium Formula

```
weekly_premium = base_price × plan_factor × risk_score
```

| Variable | Description |
|---|---|
| `base_price` | Minimum viable premium (₹29 for Basic) |
| `plan_factor` | Coverage tier multiplier (1.0 → 2.5) |
| `risk_score` | AI-calculated score ∈ [0,1] based on city, weather history, disruption frequency |

### Risk Score Inputs
```
risk_score = f(
    city_base_risk,          // Delhi = high (AQI + traffic + density)
    historical_weather,      // last 30-day disruption frequency
    social_instability,      // curfew/strike history
    platform_reliability     // outage frequency in area
)
```

### Plans

| Plan | Weekly Premium | Coverage Cap | Triggers Covered |
|---|---|---|---|
| 🟢 Basic Protect | ₹29–₹39 | ₹300 | Rain + Platform outage |
| 🟡 Smart Protect | ₹49–₹69 | ₹600 | Rain + AQI + Traffic |
| 🔴 Assured Plan | ₹79–₹99 | ₹800 | All triggers + guaranteed min payout |
| 🟣 Pro Max | ₹109–₹129 | ₹1,000 | All triggers + predictive protection + instant payout |

### Example Calculation
```
Rahul selects Smart Protect
base_price = ₹39
plan_factor = 1.5
risk_score = 0.6 (Delhi, monsoon week)

weekly_premium = 39 × 1.5 × 0.6 = ₹35.10 → rounded to ₹35/week
```

> Premium is capped at a ±20% change week-over-week to prevent pricing shock.

### Viability Basis

A natural question: *how does ₹29–₹35/week cover a ₹300 claim?*

The answer is standard risk pooling — not every worker files a claim every week:

```
Delhi avg payable disruptions:  ~2–3 events/month
Average payout per event:       ~₹150 (disruption_duration × income_per_hour)
Claim approval rate:            ~60% (fraud + ineligibility filter)

Expected monthly payout/worker: 2.5 events × ₹150 × 0.60 = ₹225/month
Worker pays (Smart Protect):    ₹35/week × 4 = ₹140/month

Pool sustainability:
- ~40% of active policy holders have no payable disruption in a given week
- Their premiums subsidise the 60% who do — identical to how all insurance works
- Higher-risk weeks (monsoon) → risk_score rises → premium rises automatically
```

The weekly model also reduces adverse selection: workers can't buy coverage *only* during predicted rain weeks because the premium adjusts upward the moment the forecast worsens.

---

## 🌩️ Parametric Trigger Engine

### What is Parametric Insurance?
Unlike traditional insurance (which reimburses actual documented losses), parametric insurance pays out automatically when a **measurable external condition** crosses a predefined threshold — no claim filing, no investigation.

### Trigger Table

| Trigger | Condition | Source |
|---|---|---|
| 🌧 Rain | Rainfall > 25mm/hr | OpenWeather API |
| 🌫 AQI | AQI > 300 (Hazardous) | AQI API / CPCB |
| 🚧 Traffic | Congestion index > 0.75 | HERE Maps / TomTom |
| ⚡ Platform Outage | Order density drop > 60% in zone | Platform simulation |
| 🚨 Social Event | Admin flag OR mass inactivity pattern | Admin panel + inference |

### Multi-Trigger Disruption Score

When multiple triggers fire simultaneously, the system calculates a composite score:

```
disruption_score =
    0.25 × weather_signal +
    0.20 × AQI_signal +
    0.15 × traffic_signal +
    0.20 × platform_signal +
    0.20 × social_signal
```

This prevents over-payment for mild single events and enables proportional payouts for compound disruptions (e.g., rain + traffic + curfew).

### Event Confidence Layer

Not all API signals are equally reliable. Each trigger carries a confidence weight:

```
event_confidence =
    0.50 × API_reliability +
    0.30 × behavioral_consistency +  // mass inactivity validates event
    0.20 × historical_match           // does this match past patterns?
```

> If no external API is available (e.g., no curfew API exists), social events are detected through **mass inactivity patterns** — if 40%+ of workers in a zone go offline simultaneously, a social disruption is inferred.

---

## 🧠 AI/ML Integration

### 1. Risk Scoring Model (Pricing)
- **What it does:** Calculates `risk_score` per worker per week based on city, zone, season, and historical disruption data
- **Why:** Enables fair, dynamic pricing — Delhi monsoon week costs more than a dry winter week
- **ML approach:** Regression model trained on weather + disruption history data

### 2. Fraud Detection Model
- **What it does:** Computes `fraud_score ∈ [0,1]` by analyzing multiple behavioral and contextual signals
- **Signals used:**
  - GPS movement pattern (impossible distance, no delivery stops)
  - Device/IP consistency
  - Activity before disruption (was worker actually working?)
  - Cluster co-location (many users, same spot, same time)
  - Social event cross-validation (curfew claimed but no prior activity)
- **ML approach:** Anomaly detection + rule-based scoring hybrid
- **Formula:**
```
fraud_score = w1×movement + w2×ip_mismatch + w3×inactivity +
              w4×cluster_flag + w5×social_mismatch
```

### 3. Cluster Fraud Detection
- **What it does:** Groups claim attempts by geofence + timestamp. If >N users from the same 500m zone file at the same moment, cluster fraud is flagged
- **Why:** Coordinated fraud rings are the highest-risk attack vector for parametric systems
- **Smart filtering:** Not all cluster users are rejected — those with valid prior activity are still approved

### 4. Trust Score System
- **What it does:** Builds a long-term behavioral profile per worker
- **Effect:** High-trust workers (consistent history, no flags) get fraud score reduction
```
adjusted_fraud = fraud_score - (0.2 × trust_score)
```

### 5. Decision Engine
Combines all signals into a single payout decision:
```
final_score =
    0.35 × disruption_score +
    0.25 × event_confidence +
    0.25 × (1 - fraud_score) +
    0.15 × trust_score
```

| Score Range | Decision |
|---|---|
| > 0.70 | 💸 Instant payout |
| 0.50–0.70 | ⏳ Delayed (review queue) |
| < 0.50 | ❌ Rejected |

### 6. Income Loss Calculation
```
income_per_hour = final_verified_income / working_hours
payout = income_per_hour × disruption_duration_hours

Constraints:
- payout ≤ plan_coverage_cap
- payout ≤ city_avg_income × 1.5   // anti-inflation cap
- final_income = weighted(self_reported, platform_data, behavioral)
```

### 7. Predictive Pricing (Pro Max Plan)
- Forecasts weather and AQI for next 24–48 hours
- Notifies workers of upcoming high-risk periods
- Allows advance coverage activation
- Premium adjustment capped at ±20% to prevent pricing shock

---

## 📋 Coverage Scope & Exclusions

### What RideShield Covers

RideShield covers **income loss only** — specifically, verified working hours lost because an external, measurable disruption made delivery work impossible or impractical.

| Covered Event | Trigger Condition | Payout Basis |
|---|---|---|
| Heavy rainfall | > 25mm/hr in worker's active zone | Income per hour × downtime hours |
| Hazardous AQI | AQI > 300 in worker's zone | Income per hour × downtime hours |
| Severe traffic disruption | Congestion index > 0.75 | Income per hour × verified idle hours |
| Platform outage | Order density drop > 60% in zone | Income per hour × outage duration |
| Civic disruption | Curfew / strike inferred or admin-flagged | Income per hour × restricted hours |

### Standard Exclusions

The following are **explicitly excluded** from all RideShield plans:

| Exclusion Category | Examples | Reason |
|---|---|---|
| **Health & Medical** | Illness, injury, hospitalisation, COVID | Outside income-loss scope; separate health products exist |
| **Vehicle & Asset** | Bike damage, punctures, theft, repairs | Not income loss from external disruption |
| **Acts of War** | Armed conflict, civil war, military operations | Systemic, uninsurable, outside parametric model |
| **Pandemic / Epidemic** | Government-mandated lockdowns lasting > 7 days | Catastrophic pooled risk — triggers separate IRDAI framework |
| **Pre-existing Conditions** | Worker registered after disruption already began | Anti-adverse-selection rule |
| **Self-inflicted Disruption** | Worker chose not to work, unrelated personal reasons | No external trigger crossed threshold |
| **Unverified Activity** | Worker shows no prior delivery activity in the disrupted period | Fraud filter — inactive workers cannot claim |
| **Infrastructure Failure** | Power cuts, road construction (non-emergency) | Not a parametric trigger in current model |
| **Income Beyond Plan Cap** | Payouts are capped at the purchased plan's coverage limit | Basic ₹300 · Smart ₹600 · Assured ₹800 · Pro Max ₹1,000 |

### Pandemic / Extended Lockdown Policy

Standard lockdowns (< 48 hours) are covered as civic disruptions. Extended government-mandated shutdowns exceeding 7 consecutive days fall outside the parametric model because:
1. Pooled risk becomes catastrophic and unsustainable at weekly premium rates
2. IRDAI mandates separate regulatory treatment for pandemic-linked income loss
3. The system flags this via admin override and suspends new policy issuance until resolved

> **Scope guarantee:** RideShield will never pay out for health treatment, vehicle repair, or any loss not directly caused by a measurable external disruption exceeding a defined threshold. This is enforced at the decision engine level, not just the policy level.

---

## 🛡️ Adversarial Defense & Anti-Spoofing Strategy

Parametric insurance without manual claim filing is uniquely vulnerable to adversarial attacks. Unlike traditional insurance (where a human reviews every claim), our system makes financial decisions autonomously — which means the fraud surface is fundamentally different. This section documents our specific attack surface and defenses.

### Attack Vector Map

| Attack Type | Description | How It Manifests |
|---|---|---|
| **GPS Spoofing** | Fake location broadcast to appear active in disrupted zone | Worker shows movement in rain zone but is actually 20km away |
| **Device Farms** | Multiple fake accounts operated from one device/IP | 10 accounts, 1 device, 1 IP, claiming simultaneously |
| **API Injection** | Manipulating our weather/AQI API calls to fake a trigger | MITM attack returning false rainfall readings |
| **Coordinated Claim Rings** | Organised groups filing at identical timestamps from one area | 23 users, same 500m geofence, same timestamp |
| **Synthetic Activity** | Scripted GPS traces simulating delivery movement | Regular speed patterns, no stop variance, no delivery-stop signature |
| **Policy Timing Abuse** | Buying coverage only after a disruption has been detected | Purchase timestamp vs disruption detection timestamp |
| **Income Inflation** | Overstating self-reported income to inflate payouts | Self-reported ₹2,000/day vs platform data showing ₹600/day |

### Defense Architecture

**Layer 1 — Signal Authenticity**

We never trust a single data source for any financial decision:
```
event_confidence =
    0.50 × API_reliability_score    // cross-validated against 2+ weather sources
    0.30 × behavioral_consistency   // mass worker inactivity independently confirms event
    0.20 × historical_match         // does this match past disruption patterns for this zone?
```
A single compromised API cannot trigger a payout. Both API signals AND behavioral evidence must agree.

**Layer 2 — GPS & Movement Anti-Spoofing**

Standard GPS spoofing produces telltale signatures our model detects:
- **Speed anomalies:** Real delivery riders show speed variance (0–40km/h with stops). Spoofed traces are often too regular.
- **Stop pattern analysis:** Legitimate deliveries show micro-stops (restaurant pickup, doorstep drop). Spoofed movement has none.
- **Accelerometer cross-check (Phase 3):** Device motion sensor data must match GPS velocity. Stationary accelerometer + moving GPS = spoofing flag.
- **Zone consistency:** Worker must have been active in the disrupted zone *before* the disruption began, not just during it.

**Layer 3 — Device & Identity Binding**
```
device_trust_score = f(
    device_fingerprint_consistency,   // same device across sessions
    ip_geolocation_match,             // IP location matches GPS location
    sim_card_stability,               // SIM changes are flagged
    account_age                       // new accounts get lower base trust
)
```
Multiple accounts on one device are flagged immediately. IP address is cross-checked against claimed GPS zone.

**Layer 4 — Cluster Fraud Detection**

The most dangerous attack vector is coordinated rings:
```python
# Pseudocode — implemented in fraud detection module
def detect_cluster_fraud(claims, window_seconds=300, radius_meters=500):
    groups = group_by_geofence_and_time(claims, radius_meters, window_seconds)
    for group in groups:
        if len(group) > CLUSTER_THRESHOLD:  # default: 5+
            flag_for_review(group)
            # Smart filter: users with prior valid claim history get benefit of doubt
            for claim in group:
                if claim.worker.trust_score > 0.7 and claim.worker.claim_history > 3:
                    approve_with_audit(claim)
                else:
                    reject_with_reason(claim, "cluster_fraud_flag")
```

**Layer 5 — Temporal Attack Prevention**

Policy timing abuse is stopped at the data layer:
- Premium purchase timestamp is recorded at second precision
- Disruption detection timestamp is recorded when threshold is first crossed
- **Hard rule:** Policy purchased *after* disruption detection timestamp → ineligible for that event
- Grace period: 5-minute buffer for legitimate edge cases (worker was in onboarding flow)

**Layer 6 — Income Verification Anti-Inflation**
```
final_income = weighted(
    0.3 × user_self_report,
    0.5 × platform_order_data,    // ground truth where available
    0.2 × behavioral_inference    // delivery frequency × avg fare estimate
)
final_income = min(final_income, city_avg_daily_income × 1.5)  // hard cap
```
Self-reported income above 1.5× the city average is automatically capped. Platform order data (simulated in Phase 2, real in Phase 3) provides independent verification.

### Trust Score System

Every worker builds a trust score over time that modulates fraud sensitivity:

```
trust_score ∈ [0, 1]
adjusted_fraud_threshold = base_threshold - (0.2 × trust_score)

// High-trust workers get benefit of doubt on borderline claims
// New accounts face stricter scrutiny automatically
```

Trust is earned through: consistent claim history, no prior fraud flags, stable device fingerprint, and long account tenure.

### Known Limitations & Honest Acknowledgements

We are not claiming this system is fraud-proof. Sophisticated adversaries can adapt. Known gaps:

- **Phase 2 gap:** Accelerometer cross-checking requires mobile SDK not yet built
- **Phase 2 gap:** Real device fingerprinting requires native app (currently web-only)
- **Adversarial ML risk:** If fraud patterns become public, attackers may learn to mimic valid delivery behavior
- **Mitigation:** Fraud model is retrained continuously on new flag data; thresholds are not public

---



| Layer | Technology | Reason |
|---|---|---|
| Frontend | React.js (Web) | Fast development, component reuse, responsive dashboard |
| Backend | FastAPI (Python) | High performance, async support, ML-friendly |
| Database | PostgreSQL | Relational data for workers, policies, claims, transactions |
| Weather API | OpenWeatherMap | Real-time rainfall and temperature data |
| AQI API | WAQI / CPCB | Delhi-specific pollution data |
| Traffic API | TomTom / HERE Maps | Congestion index per zone |
| Payments | Razorpay Sandbox | Simulated instant wallet credits |
| Payments (alt) | UPI Simulator | Direct bank transfer simulation for Pro Max plan |
| ML Models | Scikit-learn | Risk scoring, fraud detection |
| Hosting | Vercel (Frontend) + Render (Backend) | Free tier, fast deployment for demo |
| Maps/Geo | Leaflet.js | Zone visualization and GPS validation |

---

## 📁 Repository Structure

The repository is organized as a monorepo with clear separation between frontend, backend, and ML components. This structure is in place from Phase 1 to ensure the build phases proceed without restructuring.

```
rideshield/
├── README.md
├── .env.example                    # Environment variable template
├── docker-compose.yml             # Local dev stack (Phase 2)
│
├── backend/                       # FastAPI application
│   ├── requirements.txt
│   ├── main.py
│   ├── api/
│   │   ├── workers.py             # Onboarding, profile, risk score
│   │   ├── policies.py            # Plan creation, weekly premium engine
│   │   ├── claims.py              # Auto-claim generation, decision engine
│   │   └── payouts.py             # Razorpay + UPI payout execution
│   ├── core/
│   │   ├── trigger_engine.py      # Real-time disruption monitoring
│   │   ├── fraud_detector.py      # 6-signal fraud scoring + cluster detection
│   │   ├── decision_engine.py     # final_score computation + payout routing
│   │   └── income_verifier.py     # Multi-source income validation
│   ├── ml/
│   │   ├── risk_model.py          # Weekly premium risk scoring (regression)
│   │   ├── fraud_model.py         # Anomaly detection (Isolation Forest)
│   │   └── train/                 # Training scripts + saved model artifacts
│   └── db/
│       ├── models.py              # SQLAlchemy ORM models
│       └── migrations/            # Alembic migration scripts
│
├── frontend/                      # React.js web application
│   ├── package.json
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Onboarding.jsx     # Worker registration + plan selection
│   │   │   ├── Dashboard.jsx      # Worker: claims, earnings, alerts
│   │   │   └── AdminPanel.jsx     # Insurer: fraud stats, disruption map
│   │   ├── components/
│   │   │   ├── DisruptionMap.jsx  # Leaflet.js zone heatmap
│   │   │   ├── ClaimStatus.jsx    # Real-time claim progress
│   │   │   └── PremiumCalculator.jsx
│   │   └── api/                   # Axios API client wrappers
│
├── simulations/                   # API mock servers for Phase 2 dev
│   ├── weather_mock.py            # OpenWeather API simulator
│   ├── platform_mock.py           # Zomato order density simulator
│   └── scenarios/
│       ├── legitimate_rain.json   # Demo scenario 1
│       ├── fraud_cluster.json     # Demo scenario 2
│       └── curfew_edge_case.json  # Demo scenario 3
│
└── docs/
    ├── architecture.md
    └── api_reference.md
```

> Phase 1 delivers: `README.md`, `.env.example`, folder structure, `requirements.txt`, and `docker-compose.yml` skeleton. All module files exist as stubs with docstrings. Phase 2 fills them with working code.

---

## 🗓️ Development Plan

### Phase 1 (March 4–20): Foundation ✅ COMPLETE
- [x] Problem research and persona definition
- [x] System architecture design
- [x] Risk model and fraud model logic design
- [x] README and documentation
- [x] Repository folder structure (see Repository Structure section)
- [x] Coverage exclusions defined
- [x] Adversarial defense strategy documented
- [ ] Prototype wireframes (minimal UI)

### Phase 2 (March 21 – April ~10): Core Build
- [ ] Worker onboarding API
- [ ] Policy creation and weekly premium engine
- [ ] Parametric trigger monitoring service (simulated APIs)
- [ ] Fraud detection module (ML model + rules)
- [ ] Claim auto-generation engine
- [ ] Decision engine implementation
- [ ] Basic worker dashboard (React)

### Phase 3 (April ~11–30): Polish & Demo
- [ ] Admin dashboard (fraud stats, cluster alerts, analytics)
- [ ] Razorpay sandbox payment integration
- [ ] Predictive pricing module
- [ ] Demo scenario runner (3 pre-built scenarios)
- [ ] End-to-end testing
- [ ] Final video walkthrough

---

## 📊 Analytics Dashboard

### Worker Dashboard
Every worker sees a personal weekly summary tied to their active plan:

| Metric | Description |
|---|---|
| Active plan & expiry | Current plan name, coverage cap, days remaining |
| Weekly earnings protected | Total income shielded by active coverage this week |
| Claims this week | Count of auto-triggered claims + their status (instant / delayed / rejected) |
| Payout history | Last 4 weeks of credited amounts with timestamps |
| Disruption alerts | Live feed — active triggers in the worker's zone right now |
| Trust score indicator | Visual badge showing account standing (affects fraud leniency) |

### Admin / Insurer Dashboard
Operational and predictive metrics for the insurance operator:

| Metric | Description |
|---|---|
| Total active policies | Count of weekly plans currently in force, broken down by plan tier |
| Claims volume | Daily/weekly claim count with approve / delay / reject breakdown |
| Fraud rate | % of claims flagged, cluster alerts with zone + timestamp |
| Payout vs premium ratio | Loss ratio per plan tier — viability signal for pricing |
| Disruption map | Heatmap of active triggers across Delhi zones in real-time |
| Next-week forecast | Predicted high-risk zones based on weather + AQI forecast (Pro Max feature) |
| Worker activity index | Aggregate movement data showing city-wide delivery activity levels |

> Both dashboards are built in Phase 3 using React + recharts, backed by the same PostgreSQL claims and events tables used by the payout engine.

---

## 📱 Platform Justification: Web

We chose a **web platform** over mobile for the following reasons:

1. **Demo-first:** A web dashboard is faster to build and easier to demo during judging — no APK install required
2. **Admin panel requirement:** The fraud and analytics dashboard is better suited to a browser interface
3. **Responsive design:** Works on phone browsers without a separate mobile build
4. **Real-world note:** A production version would be a lightweight mobile app or WhatsApp bot — but for this phase, web enables the most complete demo

---

## 🚀 Innovation & Extras

### 1. Zero-Touch Claims (Core Innovation)
No gig worker should have to file a claim after a bad day. Our system acts on their behalf. The worker's only job is to buy a weekly plan — everything else is automated.

### 2. Social Disruption Detection Without APIs
Curfews and strikes often have no API. We detect them through **mass behavioral inference**: if 40%+ of workers in a zone go offline simultaneously without weather or platform cause, a social disruption is flagged. This makes the system resilient to data gaps.

### 3. Multi-Source Income Verification
Self-reported income is never trusted alone:
```
final_income = weighted(
    0.3 × user_self_report,
    0.5 × platform_order_data,   // simulated
    0.2 × behavioral_inference   // from delivery patterns
)
final_income ≤ city_avg × 1.5    // anti-fraud cap
```

### 4. Failure Handling
| Failure | System Response |
|---|---|
| Weather API down | Use last known data + flag for manual review |
| Missing GPS data | Delay claim, request retry |
| Inconsistent signals | Partial payout + audit log |
| Platform API unavailable | Fallback to order density heuristic |

### 5. Scalability Path
- Multi-platform ready (Swiggy, Dunzo, Blinkit) — same system, different `platform_id`
- Multi-city support — each city gets a calibrated `base_risk` profile
- Extensible trigger system — new disruption types added as new weighted signals

---

## ⚠️ Challenges We Navigated

Building an automated financial system without human intervention in the loop surfaced problems we hadn't anticipated at the start.

**Signal fusion across unreliable sources.** No single API is trustworthy enough to trigger a financial payout on its own. We designed an event confidence layer that cross-validates across API reliability, mass behavioral patterns, and historical disruption data — so a single bad API response can't incorrectly trigger or block a claim.

**Fraud in a zero-touch system.** Removing manual claim filing eliminates friction for honest users — but also removes the human check that catches fraud. We addressed this by building fraud detection directly into the pipeline: GPS validation, delivery stop patterns, cluster detection for coordinated rings, and a trust score that builds over time. The system has to be suspicious by default without being unfair to legitimate workers.

**Social events have no API.** Curfews, strikes, and sudden zone closures — some of the most impactful disruptions — have no structured data source. We solved this with behavioral inference: if 40%+ of workers in a zone go offline simultaneously without a weather or platform cause, the system infers a social disruption. It's not perfect, but it's defensible and resilient to data gaps.

**Making ₹35 cover ₹300 claims.** The economics had to actually work. We grounded the pricing model in disruption frequency data: at ~2–3 payable events per month, 60% approval rate, and ~₹150 average payout, the expected monthly liability per worker is ~₹225. A ₹140/month premium pool across all active workers is sustainable through standard risk pooling — the ~40% of workers with no disruption in a given week subsidise those who do.

---

## 🔮 What's Next

Phase 1 is architecture and documentation. The next two phases build and polish the product. Beyond the hackathon, we see a clear path to a deployable system:

- **Mobile-first interface or WhatsApp onboarding** — Rahul shouldn't need a browser. A lightweight app or WhatsApp-based flow would make plan purchase and payout notification frictionless on any phone.
- **Real platform API integration** — replace our simulated order density data with actual delivery platform signals from Zomato, Swiggy, or Blinkit via partner APIs.
- **Multi-city expansion** — each city gets a locally calibrated `base_risk` profile. Delhi monsoon ≠ Bengaluru rain ≠ Mumbai flood. The model is designed to scale this way.
- **Advanced predictive risk models** — move from 48-hour weather forecasts to week-ahead risk forecasting, enabling workers to make better decisions about which plan to buy before a high-disruption week.
- **Insurer partnerships** — RideShield is designed to run as white-label infrastructure for insurance providers who want to serve the gig economy without building the automation layer themselves.

> The long-term goal is simple: no gig worker should experience income loss without immediate, automated financial protection.

---

## 🏁 Summary

**RideShield** is not a simple "if rain then pay" system — and we didn't build it that way.

We built a multi-signal AI pipeline that:
- Monitors 5 disruption categories in real-time
- Validates events across behavioral, API, and historical signals
- Detects individual and coordinated fraud before a single rupee moves
- Calculates fair income loss using verified, multi-source data
- Issues zero-touch payouts in under 2 minutes

All wrapped in an affordable, weekly recharge model that fits how delivery partners actually earn — because we designed it around Rahul, not around what's convenient for an insurer.

> *Built for Rahul. Designed for every gig worker who loses income because the world didn't cooperate.*

1