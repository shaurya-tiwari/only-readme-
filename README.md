# RideShield

RideShield is a Phase 2 demo of parametric income protection for gig delivery workers.
It watches disruption signals, creates claims automatically for affected workers, and routes each claim through fraud-aware approval, review, or rejection without requiring the worker to file anything.

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
- ML support: scikit-learn based risk and fraud services with runtime fallback
- Demo inputs: local mock simulation modules

## Setup

### Prerequisites

- Python 3.11+
- Node.js and npm
- Docker Desktop

### Configure Environment

Copy `.env.example` to `.env` and set at minimum:

- `SESSION_SECRET`
- `ADMIN_PASSWORD`
- `CORS_ALLOWED_ORIGINS` if your frontend origin differs from local defaults

### Install Backend Dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### Start The Stack

```powershell
.\scripts\run_all.ps1
```

This launches:

- frontend: `http://localhost:3000`
- backend docs: `http://localhost:8000/docs`

### Seed Demo Data

```powershell
.\venv\Scripts\python.exe -m scripts.seed_data
```

### Optional Manual Startup

Backend:

```powershell
.\scripts\run_dev.ps1
```

Frontend:

```powershell
.\scripts\run_frontend.ps1
```

## Phase 3

Phase 3 is reserved for work outside this stable demo snapshot: real provider integrations, stronger fraud calibration, and more production-grade payout and observability layers.

See `docs/DevNotes.md` for concise implementation notes and `docs/Phase3_Roadmap.md` for future scope.
