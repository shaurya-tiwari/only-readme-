

# 🛵 RideShield — Parametric AI Insurance for Gig Delivery Workers

> **"Claims are automatically initiated by the system. Delivery partners never file claims."**

A recharge-style, AI-powered parametric insurance system that protects gig delivery workers' income in real-time — triggered by rain, extreme heat, pollution, platform outages, and curfews — using multi-signal fraud detection, duplicate claim prevention, and zero-touch payouts.

---

## 🏛️ Deployment Note
This repository contains the full development codebase.

The deployed version is based on a cleaned and optimized build 
available here: [Ride-Shield-InsurTech-System](https://github.com/Gupta-Sarthak-358/Ride-Shield-InsurTech-System)

Both share identical core logic, with Repo B structured for production deployment.

---

## ✅ Requirement Coverage

| Requirement | Status |
|---|---|
| Weekly pricing model | ✔ Covered — formula, 4 plan tiers, worked example, corrected viability math |
| AI risk profiling | ✔ Covered — regression model with city, weather, social, forecast inputs |
| Parametric triggers (6 types) | ✔ Covered — rain, extreme heat, AQI, traffic, platform outage, social disruption |
| Zero-touch claim automation | ✔ Covered — system-generated claims, no worker action required |
| Fraud detection | ✔ Covered — anomaly scoring, cluster detection, duplicate prevention, trust system |
| Adversarial defense & anti-spoofing | ✔ Covered — GPS spoofing, device farms, API injection, timing abuse |
| Coverage exclusions | ✔ Defined — war, pandemic, self-inflicted, pre-existing, flood-aware handling |
| Analytics dashboard | ✔ Covered — worker + admin views with loss-ratio visibility |
| Payout processing | ✔ Covered — Razorpay sandbox + UPI simulator |
| Worker onboarding | ✔ Covered — registration, consent capture, risk scoring |
| Income-only scope | ✔ Enforced — no health, accident, or vehicle coverage |
| Regulatory & privacy framing | ✔ Covered — IRDAI sandbox qualification, testing scope, customer protection, post-sandbox path, DPDPA 2023 compliance |
| Official deliverables alignment | ✔ Covered — phase dates, demo videos, final pitch deck PDF |

---

## 📌 Table of Contents

1. [Requirement Coverage](#-requirement-coverage)
2. [Problem & Persona](#-problem--persona)
3. [Persona-Based Scenarios](#-persona-based-scenarios)
4. [System Workflow](#️-system-workflow)
5. [Weekly Premium Model](#-weekly-premium-model)
6. [Parametric Trigger Engine](#️-parametric-trigger-engine)
7. [AI/ML Integration](#-aiml-integration)
8. [Coverage Scope & Exclusions](#-coverage-scope--exclusions)
9. [Regulatory & Privacy Framing](#-regulatory--privacy-framing)
10. [Adversarial Defense & Anti-Spoofing](#️-adversarial-defense--anti-spoofing)
11. [Tech Stack](#-tech-stack)
12. [Repository Structure](#-repository-structure)
13. [Development Plan](#-development-plan)
14. [Analytics Dashboard](#-analytics-dashboard)
15. [Platform Justification](#-platform-justification-web)
16. [Innovation & Extras](#-innovation--extras)
17. [Challenges We Navigated](#️-challenges-we-navigated)
18. [What's Next](#-whats-next)
19. [Summary](#-summary)

---

## 🚨 Problem & Persona

### The Problem

Gig delivery workers lose **20–30% of their weekly income** due to disruptions beyond their control :

| Disruption Type | Examples |
|---|---|
| 🌧 Environmental | Heavy rain, flooding, extreme heat, AQI spikes |
| ⚡ Platform | App outages, low order density, dispatch throttling |
| 🚨 Social | Government curfews, local strikes, zone closures |

**Current Gap:**
- ❌ No income protection product exists for gig workers
- ❌ No real-time, automated compensation mechanism
- ❌ Traditional insurance is too slow, manual, and health/accident-focused
- ❌ Workers need cashflow continuity, not reimbursement after paperwork

### The Persona: Rahul

> Rahul is a 28-year-old Zomato delivery partner in Delhi. He owns a bike and works 8–10 hours daily. His income depends entirely on the number of deliveries he completes. One rainy afternoon or one 46°C heatwave can wipe out ₹300–₹400 from his day.

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

## 🎬 Persona-Based Scenarios

### Scenario 1 ✅ — Legitimate Claim (Rain + Traffic)

> *Delhi, Tuesday, 2:00 PM*

Rahul starts his shift at 10 AM. He completes 6 deliveries by 2 PM. Then heavy rainfall begins — measured at 48mm/hr, well past our 25mm/hr threshold. Congestion spikes and platform order density drops 70%.

**What the system does automatically:**
1. Weather API detects rainfall crossing threshold in South Delhi
2. Rahul's GPS confirms he was active in the affected zone *before* disruption
3. Platform data shows order density collapsed in his area
4. Multi-signal validation confirms event is real (confidence: 0.87)
5. Movement pattern confirms Rahul was genuinely working — delivery stops, speed variance, restaurant pickups
6. Duplicate check: no existing claim for this event → new claim created
7. Fraud score: 0.18 → clean
8. **Claim auto-generated. ₹280 credited to wallet in 90 seconds.**

Rahul receives a notification: *"Heavy rain detected in your zone. ₹280 income protection credited."*

---

### Scenario 2 ❌ — Fraud Attempt (Fake GPS + Cluster)

> *Delhi, Same Tuesday*

Vikram appears in the same geofence as 23 other claimants at the same timestamp. He has been completely stationary for 6 hours. No delivery-stop patterns. No pre-event activity. IP address doesn't match his registered device location.

**What the system does:**
1. Cluster detection fires: 23 users, same 500m zone, same timestamp
2. Vikram's movement pattern shows zero delivery stops, zero speed variance
3. IP geolocation mismatches GPS location
4. No pre-disruption delivery activity detected
5. Fraud score: 0.81 → **Claim rejected automatically**
6. Trusted workers within the same cluster who have valid prior activity are still approved — smart filtering, not blanket rejection

---

### Scenario 3 ⚠️ — Edge Case (Curfew, Ambiguous Activity)

> *Delhi, Friday evening — Section 144 imposed at 6 PM*

Arun is in the affected zone, but he had almost zero verified deliveries in the 4 hours before the curfew. He's a new user with no claim history.

**What the system does:**
1. Social disruption detected via admin flag + normalized mass inactivity pattern
2. Arun's pre-disruption activity is near-zero — weak worker-side evidence
3. Trust score is low (new user, no history, no prior valid claims)
4. Final score: 0.54 → **Claim sent to 24-hour admin review queue**
5. Admin dashboard shows Arun's case with all signals visible
6. Decision made within SLA — not left in limbo

> This preserves the zero-touch promise for approved claims while being honest about borderline cases. Zero-touch means *workers* don't file — it doesn't mean the system never flags ambiguity.

---

## ⚙️ System Workflow

```
[1] Worker Onboarding
    └── Name, city, platform, income, hours
    └── Consent captured (location tracking, device verification)
    └── Risk score generated
    └── Weekly plan recommended & purchased
    └── 24-hour activation waiting period begins
         ↓
[2] Continuous Monitoring (Real-Time)
    └── Weather APIs → Rain, Heat, AQI
    └── Traffic APIs → Congestion index
    └── Platform signals → Order density, outage detection
    └── Social signals → Admin flags + normalized inactivity patterns
         ↓
[3] Disruption Detected
    └── Parametric trigger threshold crossed
    └── Affected zone identified
    └── Active insured workers in zone filtered
         ↓
[4] Multi-Signal Validation
    └── Event confidence scored (API + behavioral + historical)
    └── Worker activity verified (GPS, speed, delivery stops)
    └── Fraud detection model runs
    └── Cluster fraud check
    └── Duplicate claim check (event deduplication)
         ↓
[5] Claim Auto-Generated (Zero-Touch)
    └── Existing event claim extended OR new claim created
    └── Income loss calculated with peak-hour adjustment
    └── No action required from worker
         ↓
[6] Decision Engine
    └── final_score = f(disruption, confidence, fraud, trust)
    └── Score → Instant / Delayed (24hr SLA) / Rejected
         ↓
[7] Payout Execution
    └── Channel 1: In-app wallet credit (Razorpay sandbox)
    └── Channel 2: UPI direct transfer simulation (Pro Max plan)
    └── Notification pushed to worker
    └── Full audit trail with transaction ID logged
```

> ⚠️ **Zero-touch design is intentional.** Rahul never opens the app to file a claim. The system acts on his behalf the moment a validated disruption is confirmed. Workers buy coverage and stay active — everything else is automated.

---

## 💰 Weekly Premium Model

### Why Weekly?

Gig workers don't receive monthly salaries. Their income is daily and volatile. A weekly recharge cycle matches their earnings rhythm — affordable, flexible, and predictable. No long-term lock-in, no EMIs, no paperwork.

### Premium Formula

```
weekly_premium = base_price × plan_factor × risk_score
```

| Variable | Description |
|---|---|
| `base_price` | Minimum viable premium (₹29 for Basic) |
| `plan_factor` | Coverage tier multiplier (1.0 → 2.5) |
| `risk_score` | AI-calculated score ∈ [0,1] based on city, weather, disruption history, forecast |

### Risk Score Inputs

```
risk_score = f(
    city_base_risk,          // Delhi = high (AQI + traffic + density + heat)
    historical_weather,      // last 30-day disruption frequency
    social_instability,      // curfew/strike history for this zone
    platform_reliability,    // outage frequency in area
    forecast_risk            // next 48-hour weather + AQI forecast
)
```

### Risk Score Calibration

The score is relative, not a literal probability. Anchored to real-world interpretation:

```
0.10 = Bengaluru, dry week, no disruption forecast
0.40 = Delhi, normal winter week
0.60 = Delhi, active monsoon week
0.85 = Mumbai, peak flood season + festival-heavy week
1.00 = theoretical maximum, not expected in normal operations
```

This makes the score interpretable to judges, workers, and admin reviewers.

### Plans

| Plan | Weekly Premium | Coverage Cap | Triggers Covered |
|---|---|---|---|
| 🟢 Basic Protect | ₹29–₹39 | ₹300 | Platform outage only |
| 🟡 Smart Protect | ₹35–₹55 | ₹600 | Rain + Heat + AQI + Traffic + Platform |
| 🔴 Assured Plan | ₹59–₹79 | ₹800 | All triggers + guaranteed minimum payout floor |
| 🟣 Pro Max | ₹89–₹109 | ₹1,000 | All triggers + predictive protection + fastest payout |

> 💡 **Why Basic covers only platform outage:** Rain and heat are the most frequent triggers. A rational worker buying the cheapest plan to get the most common coverage creates adverse selection. Basic is the entry-level trust builder — weather-linked income protection starts at Smart. We accept a tighter margin on Basic to drive enrollment, knowing a portion of workers upgrade after their first positive experience.

### Example Calculation

```
Rahul selects Smart Protect
base_price = ₹39
plan_factor = 1.5
risk_score = 0.6 (Delhi, monsoon week)

weekly_premium = 39 × 1.5 × 0.6 = ₹35.10 → rounded to ₹35/week
```

> Premium movement is capped at ±20% week-over-week to prevent pricing shock.

### Viability Basis

The critical insight: not every insured worker is affected by every city-level event.

```
City-level payable disruptions/month:       ~2.5
Fraction of insured workers affected/event: ~0.45
Claim approval rate:                        ~0.60
Average approved payout:                    ~₹150

Expected monthly payout per worker:
    2.5 × 0.45 × 0.60 × ₹150 = ₹101.25/month

Smart Protect premium:
    ₹35/week × 4 = ₹140/month

Loss ratio:
    101.25 / 140 = 0.72 → 72%

Gross margin:
    ~28% → covers ops, fraud leakage, reserves, payment processing
```

This is a realistic and defensible loss ratio for parametric microinsurance. The per-event worker coverage fraction is the variable that makes pooling work — identical to how all insurance functions.

Higher-risk weeks (monsoon, heat waves) → `risk_score` rises → premium rises automatically. Lower-risk weeks → premium drops → workers stay enrolled.

### Adverse Selection Controls

Workers should not be able to cherry-pick only forecast-heavy weeks:

1. **24-hour activation delay** — newly purchased coverage activates 24 hours after purchase, preventing buy-after-forecast gaming
2. **Forecast-aware pricing** — `risk_score` incorporates the same public forecast horizon workers can see, so the premium already reflects predicted disruptions
3. **Optional minimum enrollment** — higher tiers (Assured, Pro Max) can require 2-week minimum continuous enrollment

---

## 🌩️ Parametric Trigger Engine

### What is Parametric Insurance?

Unlike traditional insurance (which reimburses actual documented losses), parametric insurance pays out automatically when a **measurable external condition** crosses a predefined threshold — no claim filing, no loss documentation, no investigation.

### Trigger Table

| Trigger | Condition | Source |
|---|---|---|
| 🌧 Rain | Rainfall > 25mm/hr | OpenWeather API |
| 🔥 Extreme Heat | Temperature > 44°C | OpenWeather API |
| 🌫 AQI | AQI > 300 (Hazardous) | AQI API / CPCB |
| 🚧 Traffic | Congestion index > 0.75 | HERE Maps / TomTom |
| ⚡ Platform Outage | Order density drop > 60% in zone | Platform simulation |
| 🚨 Social Disruption | Admin flag OR normalized mass inactivity | Admin panel + inference |

### 🌊 Flood-Aware Event Continuation

Flooding is distinct from live rainfall. Streets remain waterlogged and unsafe for hours or days after rain stops. Workers can't deliver — but the rain trigger may have expired.

RideShield handles this through **sustained event continuation**: if activity levels and order density remain suppressed in a zone even after rainfall drops below threshold, the system keeps the event open. The claim extends rather than closing prematurely. What matters is operational impact, not whether it's raining right now.

### Multi-Trigger Disruption Score

When multiple triggers fire simultaneously, the system calculates a composite score:

```
disruption_score =
    0.20 × rain_signal +
    0.15 × heat_signal +
    0.15 × AQI_signal +
    0.15 × traffic_signal +
    0.20 × platform_signal +
    0.15 × social_signal
```

This prevents over-payment for mild single-signal events and enables proportional payouts for compound disruptions (e.g., rain + traffic + curfew stacking).

### Event Confidence Layer

Not all API signals are equally reliable. Each trigger carries a confidence weight:

```
event_confidence =
    0.50 × API_reliability +
    0.30 × behavioral_consistency +     // mass inactivity validates event
    0.20 × historical_match             // does this match past disruption patterns?
```

> If no external API is available (e.g., no curfew API exists), social events are detected through **normalized behavioral inference** — see below.

### Social Disruption Detection Guardrails

Raw mass inactivity is too noisy. Late-night hours, festival days, and lunch lulls produce natural drops that aren't disruptions. RideShield normalizes against expected baselines:

```
inactivity_ratio = current_active / expected_active_for(hour, day, zone)
if inactivity_ratio < 0.60:    // 40%+ drop vs expected
    flag_social_disruption()
```

This is a one-line conceptual change that dramatically improves inference credibility. A 50% activity drop at 2 AM is normal. A 50% drop at 7 PM dinner rush is a signal.

---

## 🧠 AI/ML Integration

### 1. Risk Scoring Model (Pricing)
- **What it does:** Calculates `risk_score` per worker per week based on city, zone, season, disruption history, and forecast data
- **Why:** Enables fair, dynamic pricing — Delhi monsoon week costs more than a dry winter week in Bengaluru
- **ML approach:** Regression model trained on weather + disruption history data

### 2. Fraud Detection Model
- **What it does:** Computes `fraud_score ∈ [0,1]` by analyzing multiple behavioral and contextual signals
- **Signals used:**
  - GPS movement realism (impossible distances, missing delivery stops)
  - Device/IP consistency
  - Activity before disruption (was worker actually working?)
  - Cluster co-location (many users, same spot, same time)
  - Social event cross-validation (curfew claimed but no prior activity)
  - Duplicate claim patterning
- **ML approach:** Anomaly detection + rule-based scoring hybrid
- **Formula:**
```
fraud_score = w1×movement + w2×ip_mismatch + w3×inactivity +
              w4×cluster_flag + w5×social_mismatch + w6×duplicate_attempt
```

### 3. Cluster Fraud Detection
- **What it does:** Groups claim attempts by geofence + timestamp. If >N users from the same 500m zone fire at the same moment, cluster fraud is flagged
- **Why:** Coordinated fraud rings are the highest-risk attack vector for parametric systems
- **Smart filtering:** Not all cluster users are rejected — those with valid prior activity and high trust scores are still approved

### 4. Duplicate Claim Prevention

The problem statement explicitly requires this. RideShield is **event-centric**, not trigger-fire-centric:

```
Deduplication Logic:
- Each (worker_id, event_id, trigger_type) tuple can generate at most ONE claim
- event_id = trigger_type + zone + start_timestamp (rounded to 1-hour window)
- If a disruption spans multiple hours, the existing claim is EXTENDED
- Subsequent trigger fires for the same event UPDATE the claim duration
  rather than creating a new payout
- One event → one claim → one payout (adjusted for total verified duration)
```

This prevents the system from paying a worker three times for a rainstorm that lasts 3 hours across three trigger windows.

### 5. Trust Score System
- **What it does:** Builds a long-term behavioral profile per worker
- **How trust is earned:** Consistent claim history, no prior fraud flags, stable device fingerprint, long account tenure
- **Effect:** High-trust workers get fraud score reduction
```
adjusted_fraud = max(0, fraud_score - (0.2 × trust_score))
```

### 6. Decision Engine

Combines all signals into a single payout decision:

```
final_score =
    0.35 × disruption_score +
    0.25 × event_confidence +
    0.25 × (1 - adjusted_fraud) +
    0.15 × trust_score
```

> ⚠️ **Design note:** Trust is intentionally counted twice — once inside the fraud adjustment and once as its own 15% weight. This is deliberate, not a bug. High-trust workers *should* have meaningful advantage on borderline scores. A worker who has been reliable for 6 months deserves more leniency than a day-old account.

| Score Range | Decision |
|---|---|
| > 0.70 | 💸 Instant payout |
| 0.50–0.70 | ⏳ Delayed — enters 24-hour admin review queue |
| < 0.50 | ❌ Rejected |

Delayed claims are not left in limbo. They enter a visible queue on the admin dashboard with a **24-hour SLA**. The admin sees all signals, the final score breakdown, and the specific reason for delay.

### 7. Income Loss Calculation

```
income_per_hour = final_verified_income / working_hours
payout = income_per_hour × disruption_duration_hours × peak_multiplier(hour_of_day)
```

**Peak multiplier** accounts for the reality that gig income is not uniform — a disruption during lunch rush (12–2 PM) or dinner rush (7–10 PM) costs 2–3x more than one at 3 PM:

```
peak_multiplier:
    7–10 PM  → 1.5x
    12–2 PM  → 1.3x
    All other hours → 1.0x
```

**Constraints:**
- `payout ≤ plan_coverage_cap`
- `payout ≤ city_avg_income × 1.5` (anti-inflation cap)
- `final_income = weighted(0.3 × self_reported, 0.5 × platform_data, 0.2 × behavioral)`

Self-reported income is never the primary signal. Platform order data and behavioral inference anchor the real number.

### 8. Predictive Pricing (Pro Max Plan)
- Forecasts weather, AQI, and heat for next 24–48 hours
- Notifies workers of upcoming high-risk periods
- Allows advance coverage activation
- Premium adjustment capped at ±20% to prevent pricing shock

---

## 📋 Coverage Scope & Exclusions

### What RideShield Covers

RideShield covers **income loss only** — specifically, verified working hours lost because an external, measurable disruption made delivery work impossible or materially less productive.

| Covered Event | Trigger Condition | Payout Basis |
|---|---|---|
| Heavy rainfall | > 25mm/hr in worker's active zone | Income per hour × downtime × peak multiplier |
| Extreme heat | > 44°C in worker's active zone | Income per hour × downtime × peak multiplier |
| Hazardous AQI | AQI > 300 in worker's zone | Income per hour × downtime × peak multiplier |
| Severe traffic disruption | Congestion index > 0.75 | Income per hour × verified idle hours |
| Platform outage | Order density drop > 60% in zone | Income per hour × outage duration |
| Civic disruption | Curfew / strike — inferred or admin-flagged | Income per hour × restricted hours |
| Flooding / waterlogging | Sustained post-rain operational suppression | Income per hour × verified downtime |

### Standard Exclusions

The following are **explicitly excluded** from all RideShield plans:

| Exclusion Category | Examples | Reason |
|---|---|---|
| **Health & Medical** | Illness, injury, hospitalisation, COVID | Outside income-loss scope; separate products exist |
| **Vehicle & Asset** | Bike damage, punctures, theft, repairs | Not income loss from external disruption |
| **Acts of War** | Armed conflict, civil war, military operations | Systemic catastrophic risk, uninsurable |
| **Pandemic / Epidemic** | Government-mandated lockdowns > 7 days | Requires separate IRDAI regulatory treatment |
| **Pre-existing Events** | Coverage purchased after disruption already began | Anti-adverse-selection rule (24-hour delay enforces this) |
| **Self-inflicted Disruption** | Worker chose not to work, personal reasons | No eligible external trigger crossed threshold |
| **Unverified Activity** | No credible pre-event delivery activity | Fraud/eligibility filter — inactive workers cannot claim |
| **Non-trigger Infrastructure** | Routine construction, scheduled power cuts | Not a parametric trigger in current model |
| **Income Beyond Plan Cap** | Payouts capped at purchased plan's limit | Basic ₹300 · Smart ₹600 · Assured ₹800 · Pro Max ₹1,000 |

### Pandemic / Extended Lockdown Policy

Standard lockdowns (< 48 hours) are covered as civic disruptions. Extended government-mandated shutdowns exceeding 7 consecutive days fall outside the parametric model because:
1. Pooled risk becomes catastrophic and unsustainable at weekly premium rates
2. IRDAI mandates separate regulatory treatment for pandemic-linked income loss
3. The system flags this via admin override and suspends new policy issuance until resolved

> **Scope guarantee:** RideShield will never pay out for health treatment, vehicle repair, or any loss not directly caused by a measurable external disruption exceeding a defined threshold. This is enforced at the decision engine level, not just the policy level.

---

## 🏛️ Regulatory & Privacy Framing

### IRDAI Regulatory Sandbox Positioning

RideShield is designed to align with the **Insurance Regulatory and Development Authority of India (IRDAI) Regulatory Sandbox** framework for insurance innovation. Our system introduces concepts that do not fit neatly into existing product categories — which is exactly what the sandbox exists for.

#### Why Sandbox?

Three core design decisions push RideShield outside traditional insurance product templates:

- **Parametric payouts** — event-triggered, no manual claims filed
- **AI-driven dynamic pricing** — weekly premiums recalculated using real-time risk signals
- **Zero-touch automation** — financial decisions made without human adjudication for approved claims

These require controlled testing and regulatory sign-off before full-scale commercial deployment.

#### Sandbox Qualification

RideShield qualifies under multiple sandbox innovation categories simultaneously:

| Sandbox Category | RideShield Innovation |
|---|---|
| **Product Innovation** | Income-only parametric protection for gig workers — a product class that does not currently exist in the Indian market |
| **Distribution Innovation** | Recharge-style weekly purchase cycle instead of annual or monthly policy issuance |
| **Underwriting Innovation** | AI-based dynamic risk scoring using weather, AQI, traffic, platform, and social signals |
| **Claims Innovation** | Automated, zero-touch claim generation and payout without worker-initiated filing |

#### Testing Scope (Sandbox Phase)

The sandbox deployment would be intentionally constrained:

| Constraint | Scope |
|---|---|
| Geography | Single city — Delhi (highest disruption density and data availability) |
| User group | Controlled cohort of active delivery partners across 2–3 zones |
| Payout volume | Capped weekly payout pool to limit financial exposure during validation |
| Policy count | Maximum active policies capped per sandbox phase |
| API layer | Simulated and real API mix — weather (real), platform data (simulated), payments (sandbox) |
| Duration | 6–12 month sandbox window per IRDAI guidelines |

#### Customer Protection Measures

IRDAI sandbox products must demonstrate explicit consumer safeguards. RideShield provides:

| Protection | Implementation |
|---|---|
| Fraud prevention before payout | Multi-signal fraud detection, cluster analysis, and duplicate claim prevention run before any money moves |
| Hard payout caps | Every plan has a defined weekly coverage ceiling — no uncapped exposure |
| Explicit exclusions | Health, vehicle, war, pandemic, self-inflicted, and pre-existing events are excluded at the decision engine level |
| Full audit trail | Every claim decision is logged with signal breakdown, confidence score, fraud score, and payout justification |
| Claim explainability | Workers see *why* a claim was approved, delayed, or rejected — no opaque decisions |
| Dispute pathway | Delayed claims enter a 24-hour admin review queue with SLA tracking |
| Data privacy compliance | Location and behavioral data used only for claim validation — never sold or shared beyond insurer and regulator |

#### Compliance Artifacts

Our architecture is specifically built to **generate** the documentation IRDAI sandbox evaluation requires:

- **Event logs** — timestamped record of every trigger fire, threshold crossing, and zone impact
- **Claim decision logs** — full signal decomposition for every approve / delay / reject decision
- **Loss-ratio reporting** — real-time premium vs payout ratio by city and plan tier, surfaced in the admin dashboard
- **Fraud detection audit** — flagged claims, cluster alerts, duplicate attempts, and resolution outcomes
- **Worker consent records** — onboarding consent capture with purpose-specific disclosure

#### Post-Sandbox Path

If validated during the sandbox phase:

| Milestone | Action |
|---|---|
| Regulatory transition | Apply for full IRDAI product license based on sandbox performance data |
| API integration | Replace simulated platform APIs with real Zomato / Swiggy / Blinkit data feeds |
| Payment integration | Move from Razorpay sandbox to live UPI and wallet payouts |
| Geographic expansion | Multi-city rollout with locally calibrated `base_risk` profiles |
| Insurer partnership | Position RideShield as white-label infrastructure for licensed insurance providers |

> 💡 RideShield is designed not just as a hackathon prototype, but as a system that can realistically transition into a regulated insurance product. The sandbox path is part of the architecture, not an afterthought.

---

### 🔐 DPDPA 2023 — Data Privacy Compliance

RideShield continuously processes personal and behavioral data — GPS traces, device fingerprints, movement patterns, and income signals. Under the **Digital Personal Data Protection Act (DPDPA) 2023**, we implement the following controls:

| Privacy Control | Implementation |
|---|---|
| **Consent at onboarding** | Workers are explicitly informed that location, device, and movement data are collected and used for claim validation, fraud prevention, and pricing |
| **Purpose limitation** | GPS, device fingerprint, and behavioral data are used *only* for pricing, claim validation, fraud detection, and regulatory compliance — no secondary use |
| **Data minimization** | Only signals necessary for claim validation are collected. Raw GPS traces are retained for a limited verification window, then aggregated or deleted |
| **Retention policy** | Raw location data is purged after the verification window. Aggregated analytics data is retained for model training and regulatory reporting |
| **Worker transparency** | The dashboard shows why each claim was approved, delayed, or rejected. Workers can see what data informed the decision |
| **No third-party sale** | Personal claim-validation data is never sold or shared with third parties beyond the insurer and regulators |
| **Access rights** | Workers can request a summary of data held about them, consistent with DPDPA provisions |

> ⚠️ Privacy is a product constraint, not a compliance checkbox. Every data collection decision in RideShield is tied to a specific functional purpose — and that purpose is documented in the consent flow, the audit trail, and this section.

---

## 🛡️ Adversarial Defense & Anti-Spoofing

Parametric insurance without manual claim filing is uniquely vulnerable to adversarial attacks. Unlike traditional insurance (where a human reviews every claim), our system makes financial decisions autonomously — which means the fraud surface is fundamentally different. This section documents our specific attack surface and defenses.

### Attack Vector Map

| Attack Type | Description | How It Manifests |
|---|---|---|
| **GPS Spoofing** | Fake location broadcast to appear active in disrupted zone | Worker shows movement in rain zone but is actually 20km away |
| **Device Farms** | Multiple fake accounts operated from one device/IP | 10 accounts, 1 device, 1 IP, claiming simultaneously |
| **API Injection** | Manipulating weather/AQI API calls to fake a trigger | MITM attack returning false rainfall readings |
| **Coordinated Claim Rings** | Organised groups filing at identical timestamps from one area | 23 users, same 500m geofence, same timestamp |
| **Synthetic Activity** | Scripted GPS traces simulating delivery movement | Regular speed patterns, no stop variance, no delivery-stop signature |
| **Policy Timing Abuse** | Buying coverage only after a disruption has been detected | Purchase timestamp vs disruption detection timestamp |
| **Income Inflation** | Overstating self-reported income to inflate payouts | Self-reported ₹2,000/day vs platform data showing ₹600/day |
| **Duplicate Claims** | Same worker collecting multiple payouts for one event | Same rainstorm, multiple trigger windows, multiple payouts |

### Defense Architecture

**Layer 1 — Signal Authenticity**

We never trust a single data source for any financial decision:
```
event_confidence =
    0.50 × API_reliability_score    // cross-validated against 2+ sources
    0.30 × behavioral_consistency   // mass worker inactivity independently confirms event
    0.20 × historical_match         // does this match past disruption patterns for this zone?
```
A single compromised API cannot trigger a payout. Both API signals AND behavioral evidence must agree.

**Layer 2 — GPS & Movement Anti-Spoofing**

Standard GPS spoofing produces telltale signatures our model detects:
- **Speed anomalies:** Real delivery riders show speed variance (0–40km/h with stops). Spoofed traces are unnaturally regular.
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
            # Smart filter: trusted workers with history get benefit of doubt
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
- **24-hour activation delay** prevents buy-after-forecast gaming
- Grace period: 5-minute buffer for legitimate edge cases (worker was in onboarding flow when disruption started)

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

**Layer 7 — Duplicate Claim Prevention**

Event-centric deduplication ensures one event = one claim per worker:
- Claims keyed on `(worker_id, event_id, trigger_type)`
- Multi-hour events extend existing claims rather than creating new ones
- Repeat trigger fires update duration, not payout count

### Trust Score System

Every worker builds a trust score over time that modulates fraud sensitivity:
```
trust_score ∈ [0, 1]
adjusted_fraud = max(0, fraud_score - (0.2 × trust_score))

// High-trust workers get benefit of doubt on borderline claims
// New accounts face stricter scrutiny automatically
```

Trust is earned through: consistent claim history, no prior fraud flags, stable device fingerprint, and long account tenure.

### Known Limitations & Honest Acknowledgements

We are not claiming this system is fraud-proof. Sophisticated adversaries can adapt. Known gaps:

- **Phase 2 gap:** Accelerometer cross-checking requires mobile SDK not yet built
- **Phase 2 gap:** Real device fingerprinting requires native app (currently web-only)
- **Adversarial ML risk:** If fraud patterns become public, attackers may learn to mimic valid delivery behavior
- **Mitigation:** Fraud model is designed for continuous retraining on new flag data; thresholds are not public-facing

---

## 🧱 Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | React.js (Web) | Fast development, component reuse, responsive dashboards |
| Backend | FastAPI (Python) | High performance, async support, ML-friendly ecosystem |
| Database | PostgreSQL | Relational data for workers, policies, claims, events, audit trails |
| Weather API | OpenWeatherMap | Real-time rainfall, temperature, and heat data |
| AQI API | WAQI / CPCB | Delhi-specific pollution data |
| Traffic API | TomTom / HERE Maps | Congestion index per zone |
| Payments | Razorpay Sandbox | Simulated instant wallet credits |
| Payments (alt) | UPI Simulator | Direct bank transfer simulation for Pro Max plan |
| ML Models | Scikit-learn | Risk scoring (regression), fraud detection (anomaly + rules) |
| Hosting | Vercel (Frontend) + Render (Backend) | Free tier, fast deployment for demo |
| Maps/Geo | Leaflet.js | Zone visualization, heatmaps, and GPS validation |

---

## 📁 Repository Structure

The repository is organized as a monorepo with clear separation between frontend, backend, ML, simulations, and testing. Structured from Phase 1 to signal engineering maturity.

```
rideshield/
├── README.md
├── .env.example                    # Environment variable template
├── docker-compose.yml             # Local dev stack
├── alembic.ini                    # Database migration config
│
├── backend/                       # FastAPI application
│   ├── requirements.txt
│   ├── main.py
│   ├── api/
│   │   ├── workers.py             # Onboarding, profile, risk score, consent
│   │   ├── policies.py            # Plan creation, weekly premium engine
│   │   ├── claims.py              # Auto-claim generation, deduplication, decision
│   │   └── payouts.py             # Razorpay + UPI payout execution
│   ├── core/
│   │   ├── trigger_engine.py      # Real-time disruption monitoring (6 triggers)
│   │   ├── fraud_detector.py      # 7-layer fraud scoring + cluster + dedup
│   │   ├── decision_engine.py     # final_score computation + payout routing
│   │   └── income_verifier.py     # Multi-source income validation + peak multiplier
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
│   └── src/
│       ├── pages/
│       │   ├── Onboarding.jsx     # Worker registration + consent + plan selection
│       │   ├── Dashboard.jsx      # Worker: claims, earnings, alerts, trust
│       │   └── AdminPanel.jsx     # Insurer: fraud stats, loss ratio, disruption map
│       ├── components/
│       │   ├── DisruptionMap.jsx   # Leaflet.js zone heatmap
│       │   ├── ClaimStatus.jsx    # Real-time claim progress tracker
│       │   └── PremiumCalculator.jsx
│       └── api/                   # Axios API client wrappers
│
├── simulations/                   # API mock servers for dev
│   ├── weather_mock.py            # OpenWeather API simulator (rain + heat)
│   ├── platform_mock.py           # Order density simulator
│   ├── conftest.py                # Simulation test config
│   └── scenarios/
│       ├── legitimate_rain.json   # Demo scenario 1
│       ├── fraud_cluster.json     # Demo scenario 2
│       └── curfew_edge_case.json  # Demo scenario 3
│
├── tests/                         # Test suite
│   ├── test_claim_dedup.py        # Duplicate claim prevention tests
│   ├── test_trigger_engine.py     # Trigger threshold tests
│   ├── test_fraud_detector.py     # Fraud scoring tests
│   └── test_decision_engine.py    # Final score + routing tests
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI pipeline placeholder
│
└── docs/
    ├── architecture.md
    ├── api_reference.md
    └── pitch_deck_outline.md      # Structure for Phase 3 final pitch deck PDF
```

> Phase 1 delivers: `README.md`, `.env.example`, folder structure, `requirements.txt`, `docker-compose.yml` skeleton, and `alembic.ini`. All module files exist as stubs with docstrings. Phase 2 fills them with working code.

---

## 🗓️ Development Plan

Aligned to the **official DEVTrails 2026 dates and deliverables**.

### Phase 1 (March 4–20): Foundation ✅ COMPLETE

- [x] Problem research and persona definition
- [x] System architecture design
- [x] Risk model and fraud model logic design
- [x] 6 parametric triggers defined (including heat and flood handling)
- [x] Coverage exclusions and catastrophic-risk limits
- [x] Adversarial defense strategy documented
- [x] Regulatory (IRDAI) and privacy (DPDPA) framing
- [x] Viability math with corrected loss ratio
- [x] README and full documentation
- [x] Repository folder structure with stubs
- [x] Prototype wireframes (minimal UI)

### Phase 2 (March 21 – April 4): Core Executable Flow

**Must demonstrate:**
- ✅ Registration process
- ✅ Insurance policy management
- ✅ Dynamic premium calculation
- ✅ Claims management
- ✅ 2-minute demo video

**Planned implementation:**
- [ ] Worker onboarding API (with consent capture)
- [ ] Policy creation and weekly premium engine
- [ ] Parametric trigger monitoring service (simulated APIs)
- [ ] Claim auto-generation with event deduplication
- [ ] Basic fraud rules (sufficient for safe demo flow)
- [ ] Payout routing (wallet credit simulation)
- [ ] Core worker dashboard (React)
- [ ] 📹 2-minute demo video

### Phase 3 (April 5 – April 17): Advanced Fraud, Dashboard, & Judging Assets

**Must deliver:**
- ✅ Advanced fraud detection (GPS spoofing, fake weather claims)
- ✅ Instant payout system (simulated)
- ✅ Intelligent dashboard (worker + admin)
- ✅ 5-minute demo video
- ✅ Final pitch deck (PDF)

**Planned implementation:**
- [ ] Advanced cluster fraud + duplicate claim prevention (ML-enhanced)
- [ ] Razorpay sandbox payout integration
- [ ] Admin dashboard (loss ratio, disruption map, forecast, review queue)
- [ ] Worker dashboard polish (trust score, claim explainability)
- [ ] Predictive pricing module (24–48hr forecast)
- [ ] Demo scenario runner (3 pre-built scenarios)
- [ ] End-to-end testing
- [ ] 📹 5-minute demo video
- [ ] 📄 Final pitch deck PDF (persona, AI architecture, business viability)

---

## 📊 Analytics Dashboard

### Worker Dashboard

Every worker sees a personal weekly summary tied to their active plan:

| Metric | Description |
|---|---|
| Active plan & expiry | Current plan name, coverage cap, activation date, days remaining |
| Weekly earnings protected | Total income shielded by active coverage this week |
| Claims this week | Count of auto-triggered claims + status (instant / delayed / rejected) |
| Payout history | Last 4 weeks of credited amounts with timestamps and transaction IDs |
| Disruption alerts | Live feed — active triggers in the worker's zone right now |
| Trust score indicator | Visual badge showing account standing + how it affects review sensitivity |
| Claim explainability | Why each claim was approved, delayed, or rejected — no black boxes |

### Admin / Insurer Dashboard

Operational, financial, and predictive metrics for the insurance operator:

| Metric | Description |
|---|---|
| Total active policies | Count of weekly plans currently in force, broken down by plan tier |
| Claims volume | Daily/weekly claim count with approve / delay / reject breakdown |
| Fraud rate | % of claims flagged, cluster alerts with zone + timestamp detail |
| **Loss ratio** | Premium vs payout by city and plan tier — the core viability signal |
| Disruption map | Heatmap of active triggers across zones in real-time |
| Next-week forecast | Predicted high-risk zones and expected claim load based on weather + AQI |
| Review queue | Delayed claims with 24-hour SLA tracking and full signal visibility |
| Worker activity index | Aggregate movement data showing city-wide delivery activity levels |
| Duplicate claim log | Deduplication events showing merged/extended claims |

> Both dashboards are built in Phase 3 using React + recharts, backed by the same PostgreSQL claims and events tables used by the payout engine. The admin dashboard is where business viability, fraud prevention, and operational control become visible to judges.

---

## 📱 Platform Justification: Web

We chose a **web platform** over mobile for the following reasons:

1. **Demo-first:** A web dashboard is faster to build and easier to demo during judging — no APK install required
2. **Admin panel requirement:** The fraud analytics and loss-ratio dashboard is better suited to a browser interface
3. **Responsive design:** Works on phone browsers without a separate mobile build
4. **Real-world note:** A production version would be a lightweight mobile app or WhatsApp bot — but for this phase, web enables the most complete demo of both worker and admin flows

---

## 🚀 Innovation & Extras

### 1. Zero-Touch Claims (Core Innovation)
No gig worker should have to file a claim after a bad day. Our system acts on their behalf. The worker's only job is to buy a weekly plan — everything else is automated. This is the defining design decision of RideShield.

### 2. Social Disruption Detection Without APIs
Curfews and strikes often have no API. We detect them through **normalized behavioral inference**: if activity drops 40%+ below expected levels for that hour/day/zone combination — without weather or platform cause — a social disruption is flagged. This makes the system resilient to data gaps.

### 3. Flood-Aware Event Continuation
Persistent waterlogging matters more to workers than whether rain is actively falling. RideShield keeps events open through sustained inactivity and order-density suppression, even after the rain trigger technically expires.

### 4. Duplicate Claim Prevention
Event-centric architecture ensures one disruption produces one claim per worker, regardless of how many trigger windows it spans. Claims extend rather than multiply.

### 5. Peak-Hour Income Sensitivity
A disruption at 8 PM dinner rush costs more than one at 3 PM. The peak multiplier ensures payouts reflect actual earning potential lost.

### 6. Novel Trigger Space
RideShield can be extended beyond standard weather/platform triggers for delivery-specific disruptions:
- **GRAP Stage IV delivery bans** — Delhi restricts two-wheeler deliveries during severe pollution episodes
- **Festival restaurant closure clusters** — if 5+ partner restaurants in a zone close unexpectedly, order availability drops even without weather
- **Event-night dispatch suppression** — IPL match nights or large public gatherings cause platform-level allocation changes

These are areas for later phases or post-hackathon expansion, but they demonstrate the system's extensibility.

### 7. Failure Handling
| Failure | System Response |
|---|---|
| Weather API down | Use last known data + flag for manual review |
| Missing GPS data | Delay claim, request retry |
| Inconsistent signals | Partial payout + audit log |
| Platform API unavailable | Fallback to order density heuristic |

### 8. Scalability Path
- Multi-platform ready (Swiggy, Dunzo, Blinkit) — same system, different `platform_id`
- Multi-city support — each city gets a calibrated `base_risk` profile
- Extensible trigger system — new disruption types added as new weighted signals

### 9. Sandbox-Ready Architecture
Most hackathon insurance projects ignore regulation entirely. RideShield is built to generate the audit trails, loss-ratio reports, claim explainability logs, and consent records that an IRDAI sandbox application actually requires. The regulatory path is part of the product design, not a slide added the night before judging.

---

## ⚠️ Challenges We Navigated

Building an automated financial system without human intervention in the loop surfaced problems we hadn't anticipated at the start.

**Viability math had to be defensible.** The hardest business-design correction was the loss ratio. Early math showed 161% loss ratio because we forgot the per-event worker coverage fraction. Not every worker in Delhi gets rained on during every rain event. Once we factored in geographic coverage fraction (~45% of insured workers affected per event), the loss ratio dropped to a sustainable 72% — with 28% gross margin for ops, fraud leakage, and reserves.

**Signal fusion across unreliable sources.** No single API is trustworthy enough to trigger a financial payout on its own. We designed an event confidence layer that cross-validates across API reliability, mass behavioral patterns, and historical disruption data — so a single bad API response can't incorrectly trigger or block a claim.

**Fraud in a zero-touch system.** Removing manual claim filing eliminates friction for honest users — but also removes the human check that catches fraud. We addressed this with 7 defense layers: GPS validation, delivery-stop patterns, device binding, cluster detection, temporal abuse prevention, income verification, and duplicate claim deduplication. The system has to be suspicious by default without being unfair to legitimate workers.

**Social events have no API.** Curfews, strikes, and sudden zone closures — some of the most impactful disruptions — have no structured data source. We solved this with normalized behavioral inference: comparing current activity against expected baselines for that hour, day, and zone. Raw inactivity thresholds were too noisy — normalizing against expected patterns was the key insight.

**Zero-touch ≠ zero review.** We initially designed the system as fully autonomous for all claims. Scenario 3 (the curfew edge case) forced us to acknowledge that borderline cases exist. The solution: instant payout for high-confidence claims, a bounded 24-hour admin review queue for ambiguous ones. Workers never file claims, but the insurer retains oversight for edge cases.

**Regulation and privacy are product constraints, not afterthoughts.** Any credible parametric insurance concept in India needs IRDAI sandbox positioning and DPDPA compliance. We built these in from the start rather than bolting them on as appendices.

---

## 🔮 What's Next

Phase 1 is architecture and documentation. The next two phases build and polish the product against the official timeline.

**Phase 2 priorities (by April 4):**
- Build the complete onboard → insure → detect → validate → pay loop
- Implement event deduplication early — it affects both fraud prevention and payout correctness
- Deliver the 2-minute demo video showing core flow

**Phase 3 priorities (by April 17):**
- Surface loss ratio, forecast risk, and review queue metrics in the admin dashboard
- Build advanced cluster and duplicate-claim defenses with ML enhancement
- Prepare the **final pitch deck PDF** around three axes: worker need, fraud-aware AI architecture, and weekly pricing viability
- Deliver the 5-minute demo video and package the demo around a clear story

**Beyond the hackathon:**
- **Mobile-first interface or WhatsApp onboarding** — Rahul shouldn't need a browser
- **Real platform API integration** — replace simulated data with actual Zomato/Swiggy/Blinkit signals
- **Multi-city expansion** — locally calibrated risk profiles (Delhi monsoon ≠ Bengaluru rain ≠ Mumbai flood)
- **Advanced predictive models** — week-ahead risk forecasting for better plan selection
- **Insurer partnerships** — RideShield as white-label infrastructure for insurance providers serving the gig economy

> The long-term goal is simple: no gig worker should experience income loss without immediate, automated financial protection.

---

## 🏁 Summary

**RideShield** is not a simple "if rain then pay" system — and we didn't build it that way.

We built a multi-signal AI pipeline that:
- 📡 Monitors **6 disruption categories** in real-time (rain, heat, AQI, traffic, platform, social)
- ✅ Validates events across behavioral, API, and historical signals
- 🛡️ Detects individual fraud, coordinated rings, and duplicate claims before a single rupee moves
- 💰 Calculates fair income loss using verified, multi-source data with peak-hour sensitivity
- ⚡ Issues zero-touch payouts in under 2 minutes
- 📊 Surfaces loss ratios, fraud rates, and predictive analytics for insurer oversight
- 🏛️ Designed for IRDAI Regulatory Sandbox qualification with defined testing scope, customer protection measures, compliance artifacts, and a clear post-sandbox commercialization path — plus full DPDPA 2023 data privacy compliance

All wrapped in an affordable, weekly recharge model that fits how delivery partners actually earn — because we designed it around Rahul, not around what's convenient for an insurer.

> *Built for Rahul. Designed for every gig worker who loses income because the world didn't cooperate.* 🛵
