<p align="center">
  <img src="banner.gif" width="100%" />
</p>

<h1 align="center">🛵 Parametric AI Insurance System</h1>

<p align="center">
  <strong>AI-powered income protection for gig workers</strong><br/>
  Designed for <strong>Zomato Delivery Partners</strong>
</p>

---

## 🚨 Problem Statement

Gig delivery workers face **20–30% income loss** due to unpredictable external factors:

* 🌧 Weather disruptions (rain, extreme heat, AQI spikes)
* ⚡ Platform instability (app outages, low order density)
* 🚨 Social disruptions (curfews, strikes, market closures)

### Current Gaps

* ❌ No structured income protection
* ❌ No real-time compensation mechanisms

---

## 🎯 Solution Overview

We present a **parametric AI-driven insurance system** that:

* Continuously monitors real-world disruption signals
* Quantifies income loss dynamically
* Triggers automated payouts with zero manual intervention
* Uses intelligent fraud detection to ensure system integrity

---

## ⚠️ Design Constraints

* ✔ Coverage strictly limited to **income loss only**
* ❌ No health, accident, or vehicle-related claims
* ✔ Mandatory **weekly pricing model** aligned with gig earnings cycles

---

## 👤 Target Persona

**Rahul — Zomato Delivery Partner (Delhi)**

* Earnings: ₹25–₹40 per delivery
* Throughput: 2–3 deliveries/hour
* Daily income: ₹800–₹1000

This persona reflects real-world gig economy behavior and risk exposure.

---

## 🌍 Disruption Landscape

### Environmental Factors

* Heavy rainfall
* Extreme temperatures
* Hazardous AQI levels

### Social Factors

* Government-imposed curfews
* Local strikes
* Zone/market closures

### Platform Factors

* Application outages
* Reduced demand density

**Impact:**

> Reduced working hours directly translate to **loss of income**

---

## ⚙️ System Architecture

The system operates as a **continuous decision pipeline**:

```
Onboarding → Risk Profiling → Policy Creation
        ↓
Real-Time Monitoring
        ↓
Disruption Detection
        ↓
Validation (Fraud + Activity)
        ↓
Claim Generation
        ↓
Decision Engine
        ↓
Instant / Delayed / Rejected Payout
```

---

## 🧾 Intelligent Onboarding

Captures:

* User identity and location
* Platform association
* Income patterns and working hours

Generates:

* Worker profile
* Initial risk score
* Personalized weekly policy

---

## 🧠 AI Risk Modeling

The system computes a dynamic **risk score (0–1)** based on:

* Geographic risk (e.g., AQI, traffic density)
* Historical weather patterns
* Frequency of disruptions
* Social instability indicators

---

## 💰 Dynamic Weekly Pricing

Premiums are calculated using a **risk-adjusted pricing model**:

```
weekly_premium = base_price + (risk_score × multiplier)
```

Ensuring fairness, scalability, and affordability for gig workers.

---

## 🌩️ Parametric Trigger Engine

The core of the system is a **real-time trigger detection engine**.

| Trigger Type | Condition                |
| ------------ | ------------------------ |
| Weather      | Rainfall above threshold |
| AQI          | AQI > 300                |
| Traffic      | High congestion          |
| Platform     | Outage detected          |
| Social       | Curfew or restriction    |

---

## 🔢 Disruption Intelligence

Multiple signals are aggregated into a unified disruption score:

```
disruption_score = weighted sum of environmental + social + platform signals
```

This ensures **context-aware decision making**, not binary triggers.

---

## 📡 Event Confidence Layer

Each detected event is validated using a **confidence score** derived from:

* Multi-source data verification
* API reliability
* Behavioral consistency

---

## 👨‍🔧 Worker Activity Validation

To ensure legitimacy, the system evaluates:

* Movement patterns (speed, route behavior)
* Delivery stop patterns
* Active working duration

---

## 🔍 Fraud Detection Engine

A multi-layered fraud detection system evaluates:

* Location anomalies
* Behavioral inconsistencies
* Inactivity patterns
* IP mismatches
* Cluster-based anomalies
* Social condition mismatches

### Social Fraud Example

> Curfew active + no prior activity → flagged as fraud

---

## 🧩 Cluster Fraud Detection

Detects coordinated fraud attempts:

```
Same location + same time + multiple users → cluster anomaly
```

---

## 💰 Income Loss Computation

Payouts are strictly based on **lost earning potential**:

```
income_per_hour = daily_income / working_hours

payout = income_per_hour × disruption_duration
```

---

## ⚖️ Decision Engine

Final decisions are made using a composite scoring model:

```
final_score = disruption + confidence + trust - fraud
```

| Score Range | Outcome           |
| ----------- | ----------------- |
| High        | 💸 Instant payout |
| Medium      | ⏳ Delayed payout  |
| Low         | ❌ Rejected        |

---

## 💳 Instant Payout Infrastructure

* Integrated with Razorpay (test/mock)
* Instant wallet-based credit
* Full transaction logging
* Retry & failure handling system

---

## 📊 System Dashboard

### Worker View

* Weekly premium
* Active coverage
* Earnings protected
* Claim status

### Admin View

* Total claims processed
* Fraud detection rate
* Cluster alerts
* Disruption analytics

---

## 🔮 Predictive Intelligence (Advanced)

The system incorporates **predictive modeling**:

* Forecasts disruptions (e.g., upcoming rain)
* Adjusts coverage proactively

---

## 🧪 Demonstration Scenarios

### Legitimate Case

Rain + verified activity → Instant payout

### Fraud Case

Fake GPS + inactivity → Rejected

### Curfew Case

No activity during restriction → Delayed / Rejected

---

## 🧠 System Vision

This is not a simple rule-based system.

> It is an **AI-driven financial decision engine** that continuously evaluates environmental, social, platform, and behavioral signals to protect gig worker income in real time.

---

## 🏁 Final Pitch

> A parametric insurance platform that safeguards gig workers’ income by automatically detecting disruptions and executing real-time, fraud-resistant payouts aligned with their weekly earning cycle.
