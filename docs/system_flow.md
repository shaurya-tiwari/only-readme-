# RideShield — Demo & System Runbook

This document provides a hands-on guide to running and evaluating the RideShield system. It covers demo credentials and access, system workflows, admin and worker interactions, and what is real vs simulated in the current build.

> For system design, architecture, and product rationale, see the [main README](../README.md).

> **Robustness & Explainability**: Model robustness is achieved using controlled synthetic scaling and edge-case injection, ensuring strong generalization while maintaining explainability through a policy-driven decision layer.

---

## 🔑 Demo Access

### 🌐 Live Production Demo

The live production build is deployed at **[https://ride-shield-hazel.vercel.app](https://ride-shield-hazel.vercel.app)**.

- **Frontend URL**: [https://ride-shield-hazel.vercel.app](https://ride-shield-hazel.vercel.app)
- **Admin Username**: `admin`
- **Admin Password**: `admin-integrity-212`

### 💻 Local Development Setup

Run the full stack locally via `.\scripts\run_all.ps1` to test the deeper ML integration.

**Local Admin Dashboard:**
- **Username**: `admin`
- **Password**: `rideshield-local-admin`

Navigate to `/auth` and authenticate using the credentials above.

### 👷 Sample Worker Accounts

Use these credentials to authenticate as a worker and evaluate active policies, claim flows, and payout behavior.

| Worker Name | Phone Number | Password | Profile Type |
| :--- | :--- | :--- | :--- |
| **Rahul Kumar** | `+919876543210` | `rahul1234` | Active Legit |
| **Vikram Singh** | `+919876543211` | `vikram1234` | Pending Fraud |
| **Arun Patel** | `+919876543212` | `arun1234` | Pending Edge |
| **Priya Sharma** | `+919876543213` | `priya1234` | Active Multi |
| **Aman Verma** | `+919876543214` | `aman1234` | Mumbai Active |
| **Farhan Ali** | `+919876543215` | `farhan1234` | Mumbai High Trust |
| **Sneha Iyer** | `+919876543216` | `sneha1234` | Chennai Active |
| **Neha Gupta** | `+919876543217` | `neha1234` | Chennai High Trust |
| **Rohit Yadav** | `+919876543218` | `rohit1234` | Bengaluru Pending |

> [!WARNING]
> This is a demo environment. Credentials are shared for evaluation purposes only.

---

## Key Capabilities

- Zero-touch claim generation from validated disruption events
- Multi-signal decision engine (disruption, fraud, trust, confidence)
- Event-centric claim handling with deduplication
- Hybrid fraud detection (ML + rule-based fallback)
- Worker and admin dashboards with full decision explainability
- **WhatsApp Conversational Interface** for low-friction onboarding and proactive alerts

---

## How It Works

At its core, RideShield transforms real-world disruptions into validated financial outcomes without requiring worker intervention.

1. A worker registers, gives consent, and buys a weekly plan.
2. The scheduler monitors mock disruption signals for supported cities and zones.
3. When thresholds are crossed, the system creates or extends an incident for the affected zone.
4. Eligible workers inside that incident are evaluated using disruption context, fraud score, trust score, confidence, and payout exposure.
5. The claim is approved automatically, delayed for review, or rejected with reasons.
6. Approved claims move to payout execution and appear in the worker and admin surfaces.

---

## Demo Flow

1. Start the stack and seed demo data.
2. Navigate to `/auth` and sign in.
3. Sign in as admin using the credentials above.
4. Open the Demo Runner and create a demo worker in a chosen city.
5. Run a scenario such as heavy rain, fraud cluster, or curfew edge case.
6. Open the Admin Panel and show the review queue, decision context, confidence, and incident outcomes.
7. Optionally sign in as a worker to show onboarding, active policy, claim visibility, and payout history.

---

## Tech Stack

- **Frontend:** React, Vite, Tailwind CSS, Recharts
- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL
- **Machine Learning:** scikit-learn models (RandomForest and GradientBoosting)
- **WhatsApp Integration:** Meta WhatsApp Cloud API (v19.0)
- **Demo inputs:** local mock simulation modules

---

## System Reality (What's Real vs Simulated)

### ✅ Integrated Now

- weekly policy purchase and activation
- trigger monitoring and scheduler
- incident-centric claim generation
- payout execution
- DB-backed geography
- risk-model-backed risk surface with fallback
- detailed premium metadata from the plans API
- hybrid fraud scoring with ML + rule fallback
- forecast analytics and model-status endpoints
- cookie-based auth with bearer fallback for Swagger/tests
- **WhatsApp-based worker onboarding & status checks**
- **Proactive WhatsApp disruption alerts**

### ⚙️ Still Simulated or Simplified

- external disruption feeds
- payout rails
- synthetic fraud-model training data
- device or GPS telemetry realism
- local runtime diagnostics

---

## Operating Loop

```
Observe signals → detect incident → verify policy → score claim → pay or review
```

**Core product rule:**
- workers do not file claims manually
- the system generates claims from validated incidents

---

## Current System Shape

### Simulated inputs
- `simulations/weather_mock.py`
- `simulations/aqi_mock.py`
- `simulations/traffic_mock.py`
- `simulations/platform_mock.py`

### Real core engine
- `backend/core/trigger_engine.py`
- `backend/core/claim_processor.py`
- `backend/core/fraud_detector.py`
- `backend/core/decision_engine.py`
- `backend/core/income_verifier.py`
- `backend/core/payout_executor.py`

### ML and forecast layer
- `backend/core/risk_model_service.py`
- `backend/core/fraud_model_service.py`
- `backend/core/forecast_engine.py`
- `backend/ml/risk_model.py`
- `backend/ml/fraud_model.py`
- `backend/ml/features/risk_features.py`
- `backend/ml/features/fraud_features.py`
- `backend/ml/explainability.py`

### Frontend surfaces
- worker onboarding
- worker dashboard
- admin oversight
- demo runner
- how-it-works explainer
- intelligence overview

---

## Local Setup

### 1. Start the full stack

```powershell
.\scripts\run_all.ps1
```

This starts Docker Postgres, FastAPI backend, and Vite frontend.

### 2. Seed demo data

```powershell
.\venv\Scripts\python.exe -m scripts.seed_data
```

### 3. Access the application

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

---

## Auth And Roles

### Worker
- Navigate to `/auth` and sign in
- phone + password session
- httpOnly cookie is the primary frontend auth path
- sees onboarding, dashboard, payouts, claims, and risk context

### Admin
- Navigate to `/auth` and sign in
- separate admin session
- sees admin oversight, intelligence page, demo runner, and review queue

### API note
- protected APIs accept either the session cookie or `Authorization: Bearer <token>`
- the frontend stores only role metadata locally for session boot UX

---

## Worker Workflow

### New worker
1. Navigate to `/onboarding`
2. Register worker profile with city, zone, platform, and consent
3. Receive risk score and recommended plan
4. Load the detailed plan catalog from `/api/policies/plans/{worker_id}`
5. Buy weekly plan
6. Open the worker dashboard explicitly after sign-in

### Returning worker
1. Navigate to `/auth` and sign in
2. Review:
   - active policy
   - claim decision cluster
   - payouts
   - risk score and explanation
   - payout breakdown with operating-cost adjustment
   - fraud review context when a claim is delayed
   - nearby incidents
232: 
233: ### WhatsApp Worker (Conversational)
234: 1. Send "hi" to the RideShield WhatsApp number
235: 2. Follow the automated flow to register (name, city, platform)
236: 3. Select a plan and "pay" via simulated checkout
237: 4. Check policy status anytime by sending "status"
238: 5. Receive proactive push alerts when a disruption is detected in your zone

---

## Admin Workflow

1. Sign in as admin
2. Navigate to `/admin`
3. Review:
   - KPI strip
   - health status derived from real scheduler state
   - review queue and next decision
   - scheduler state
   - model status
   - incident feed
   - integrity preview
   - forecast horizon
   - disruption map
4. Use city and zone filters to narrow the decision surface
5. Resolve delayed claims when present

Admin utility routes also exist for:
- pending policy activation
- force activation in simulation
- expiring stale policies

---

## Demo Runner Workflow

1. Sign in as admin
2. Navigate to `/demo`
3. Select city
4. Click `Create demo worker` if needed
5. Run a scenario
6. Review:
   - result summary
   - live activity log
   - cause-and-effect flow
   - signal snapshots
7. Reset simulators when done

**Notes:**
- demo worker creation sends the full worker registration payload, including password
- demo failures surface inline in the page instead of failing silently

---

## Intelligence Overview Workflow

Navigate to `/intelligence` as the explanation surface.

It is for:
- scheduler posture
- monitored geography
- trigger layers
- fraud, trust, and decision relationships
- current system indicators
- forecast bands and KPI interpretation
- risk and fraud model status and metrics

It is not the same thing as the admin decision queue.

---

## Geography Rule

Current supported cities:
- Delhi
- Mumbai
- Bengaluru
- Chennai

Selectors should be driven from:
- `/api/locations/cities`
- `/api/locations/zones`

The frontend should not treat hardcoded city constants as the source of truth.

---

## Runtime Logs

Use local runtime diagnostics to inspect:
- scheduler runs
- zone-level signals
- trigger outcomes
- incident create vs extend behavior
- claim counts
- payout totals

---

## Useful Documentation

- [API Reference](api_reference.md)
- [Architecture](architecture.md)
- [Intelligence Layer](intelligence.md)
- [Future Roadmap](future_roadmap.md)
- [WhatsApp Integration](whatsapp_integration.md)
