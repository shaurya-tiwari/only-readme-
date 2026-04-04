# RideShield

RideShield is a Phase 2 demo of parametric income protection for gig delivery workers.
It watches disruption signals, creates claims automatically for affected workers, and routes each claim through fraud-aware approval, review, or rejection without requiring the worker to file anything.

> **Robustness & Explainability**: We improved model robustness using controlled synthetic scaling and edge-case injection, ensuring strong generalization while maintaining explainability through a policy-driven decision layer.

## 🔑 Quick Access / Demo Credentials

> **Important Deployment Note**: RideShield operates two parallel environments for the submission. 
> 1. **Live Deployment (Repo B)**: The stable production build available to judges.
> 2. **Local Development (This Repo)**: The engineering environment used for advanced ML training, edge cases, and deterministic testing.

---

### 🌐 Live Production Demo (Deployed Repo B)
If you are evaluating the deployed live website, use these credentials.
- **Frontend URL**: [https://ride-shield-hazel.vercel.app](https://ride-shield-hazel.vercel.app)
- **Admin Username**: `admin`
- **Admin Password**: `admin-integrity-212` *(The deployed repo uses the hardened Phase 2 credentials).*

---

### 💻 Local Development Demo (This Repo)
If you are running the system locally via `run_all.ps1` to test the deeper ML integration, access it at `http://localhost:3000/auth`.

**🛡️ Local Admin Dashboard**
- **Username**: `admin`
- **Password**: `rideshield-local-admin` *(The local dev environment has a separate staging password).*

**👷 Local Worker Dashboard (Sample Credentials)**
Use these credentials to sign in locally as a worker to view active policies, protection narrative, and payout history.

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

## Key Features

- Zero-touch claims for validated disruption events
- Weekly plan purchase and activation flow
- Mock-based weather, AQI, traffic, platform, and civic disruption inputs
- Incident-centric claim handling to avoid stacked same-window payouts
- Fraud-aware decisioning with trust, confidence, and payout exposure signals
- Worker dashboard, admin review surface, and demo runner

## How It Works

1. A worker registers, gives consent, and buys a weekly plan.
2. The scheduler monitors mock disruption signals for supported cities and zones.
3. When thresholds are crossed, the system creates or extends an incident for the affected zone.
4. Eligible workers inside that incident are evaluated using disruption context, fraud score, trust score, confidence, and payout exposure.
5. The claim is approved automatically, delayed for review, or rejected with reasons.
6. Approved claims move to payout execution and appear in the worker and admin surfaces.

## Demo Flow

1. Start the stack and seed demo data.
2. Open `http://localhost:3000/auth`.
3. Sign in as admin using the credentials from `.env`.
4. Open the Demo Runner and create a demo worker in a chosen city.
5. Run a scenario such as heavy rain, fraud cluster, or curfew edge case.
6. Open the Admin Panel and show the review queue, decision context, confidence, and incident outcomes.
7. Optionally sign in as a worker to show onboarding, active policy, claim visibility, and payout history.

## Tech Stack

- Frontend: React, Vite, Tailwind CSS, Recharts
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- Machine Learning: scikit-learn models (RandomForest and GradientBoosting) generating deterministic probabilistic scores for fraud and Risk, bounded by a strict Policy-driven logic. Models are pre-trained on intelligently constrained synthetic data (50k limit) with injected edge cases, keeping generalization gaps tight (< 2%).
- Demo inputs: local mock simulation modules

## Phase 3

Phase 3 is reserved for work outside this stable demo snapshot: real provider integrations, stronger fraud calibration, and more production-grade payout and observability layers.

---

# RideShield Workflow Guide

This guide is the practical runbook for the current repo.
It focuses on:
- how to run the stack
- what each role can do
- what is real today
- what is still simulated or simplified

## Operating Loop

```text
Observe signals -> detect incident -> verify policy -> score claim -> pay or review
```

Important product rule:
- workers do not file claims manually
- the system generates claims from validated incidents

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

## Current Truth

### Integrated now
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

### Still simulated or simplified
- external disruption feeds
- payout rails
- synthetic fraud-model training data
- device or GPS telemetry realism
- local runtime diagnostics

## Local Setup

### 1. Start the full stack

```powershell
.\scripts\run_all.ps1
```

This starts:
- Docker Postgres
- FastAPI backend
- Vite frontend

### 2. Seed demo data

```powershell
.\venv\Scripts\python.exe -m scripts.seed_data
```

### 3. Open the app

- frontend: `http://localhost:3000`
- backend docs: `http://localhost:8000/docs`

## Auth And Roles

### Worker
- sign in at `/auth`
- phone + password session
- httpOnly cookie is the primary frontend auth path
- sees onboarding, dashboard, payouts, claims, and risk context

### Admin
- sign in at `/auth`
- separate admin session
- sees admin oversight, intelligence page, demo runner, and review queue

### API note
- protected APIs accept either the session cookie or `Authorization: Bearer <token>`
- the frontend stores only role metadata locally for session boot UX

## Worker Workflow

### New worker
1. Open `/onboarding`
2. Register worker profile with city, zone, platform, and consent
3. Receive risk score and recommended plan
4. Load the detailed plan catalog from `/api/policies/plans/{worker_id}`
5. Buy weekly plan
6. Open the worker dashboard explicitly after sign-in

### Returning worker
1. Open `/auth`
2. Sign in
3. Review:
   - active policy
   - claim decision cluster
   - payouts
   - risk score and explanation
   - payout breakdown with operating-cost adjustment
   - fraud review context when a claim is delayed
   - nearby incidents

## Admin Workflow

1. Sign in as admin
2. Open `/admin`
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

## Demo Runner Workflow

1. Sign in as admin
2. Open `/demo`
3. Select city
4. Click `Create demo worker` if needed
5. Run a scenario
6. Review:
   - result summary
   - live activity log
   - cause-and-effect flow
   - signal snapshots
7. Reset simulators when done

Notes:
- demo worker creation sends the full worker registration payload, including password
- demo failures should surface inline in the page instead of failing silently

## Intelligence Overview Workflow

Use `/intelligence` as the explanation surface.

It is for:
- scheduler posture
- monitored geography
- trigger layers
- fraud, trust, and decision relationships
- current system indicators
- forecast bands and KPI interpretation
- risk and fraud model status and metrics

It is not the same thing as the admin decision queue.

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

## Runtime Logs

Use local runtime diagnostics to inspect:
- scheduler runs
- zone-level signals
- trigger outcomes
- incident create vs extend behavior
- claim counts
- payout totals

## Useful Docs

- `docs/api_reference.md`
- `docs/manual_review_script.md`
- `docs/pitch_deck_outline.md`
- `docs/SPRINT_4A_EXECUTION.md`
- `docs/DevNotes.md`
