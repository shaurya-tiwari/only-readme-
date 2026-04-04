# RideShield Phase 2 Current State

> **RideShield is a parametric income protection system that automatically detects disruption events, evaluates claim legitimacy, and ensures fair, explainable payouts for gig workers.**

This document describes what the repo does today. It does not cover future integration work or later learning pipelines.

## 💡 Design Architecture: Real-World Resilience & Fairness

While the system fulfills all mandatory Phase 2 requirements (Zero-touch Claims, Dynamic AI Pricing, Parametric Automation, Fraud Detection), we designed a heavily resilient architecture that behaves correctly under real-world pressure. The architecture is designed to scale across cities and signal layers, built around several core enterprise constraints:

- **Determinism & Consistency:** Our internal mechanics ensure decisions are reproducible. The same external inputs and behavioral history will ALWAYS result in the exact same payout. There is no randomness in payouts—the system is fully deterministic and reproducible, prioritizing trust over cleverness.
- **Graceful Degradation:** A production system must be resilient to partial data failure. The system continues decision-making even under partial signal failure. While simulated in Phase 2, our architecture is built to seamlessly manage dual integrations (Mock/Live). If a live API drops, the backend intelligently falls back to heuristic baselines rather than collapsing the pipeline.
- **Fairness as a Constraint:** We actively balance aggressive fraud prevention with protecting legitimate earners from false rejection. For example, our **Nuanced Cluster Fraud** blocks spoofing rings but uses trust-scoring to securely pay reliable workers caught in the radius. Our **Anti-Inflation Income Defenses** establish safe payout caps at `1.5x` city averages to protect the operational pool while ensuring true earners are made whole.
- **Explainability as a Feature:** In insurance, a black-box AI means instant distrust. We explicitly surface explainability as a core feature. Borderline ambiguous claims are routed to an Admin SLA queue where human operators can audit the exact mathematical split of fraud risk vs validation. Our system is intentionally not a black box.
- **Modeling Continuity, Not Isolated Events:** We model continuous reality, not isolated API boundaries. **Flood-Aware Event Continuation** ensures an event stays open while streets remain waterlogged, even if live rain drops below threshold. Similarly, our **Event-Centric Duplicate Handling** doesn't lazily reject sequential triggers; instead, it seamlessly extends the duration of the unified geographic event.
- **Operating Cost Deduction (Net Profit Mapping):** We deliberately engineered the payout to map to true net profit. When a worker is grounded by disruptions, they aren't burning petrol. The algorithm automatically applies an `operating_cost_factor` (e.g., deducting 15% to `0.85`), removing the moral hazard of idle profitability.
- **Peak-Hour Decision Matrices:** We map dynamic multipliers to replacing income drastically higher during prime dinner rushes (7-10 PM) compared to an afternoon lull, matching real gig economy unit economics.

## What Is Working Now

### Zero-touch claims flow

- Workers register, buy a weekly plan, and stay active.
- When a validated disruption affects their zone, the backend creates the claim automatically.
- Clean claims move through a zero-touch approval path without requiring the worker to file anything.

### Signal-driven disruption detection

- Weather, AQI, traffic, and platform conditions are mock-driven in Phase 2.
- The backend still runs a real trigger loop, incident grouping, and claim creation flow on top of those signals.

### Fraud-aware decision engine

- Claim decisions combine disruption context, fraud scoring, trust score, confidence, and payout exposure.
- Lower-risk claims can auto-approve.
- Borderline cases are delayed into review instead of being rejected by default.

### Admin dashboard with explainability

- The admin surface shows the review queue, next recommended decision, queue pressure, confidence, and top review drivers.
- Explainability is part of the product surface, not hidden only in logs.

## How It Works

1. A worker registers, gives consent, and buys a weekly policy.
2. Mock disruption signals are monitored by the scheduler.
3. When thresholds are crossed, the system creates or extends an incident for the affected zone.
4. Eligible workers inside that incident are scored with trust, fraud, and payout-aware decision logic.
5. Claims are approved automatically, delayed into review, or rejected with reasons.

## Local Setup

### Prerequisites

- Python with a local `venv`
- Node.js and npm
- Docker Desktop

### Configure environment

Create `.env` from `.env.example` and set at minimum:
- `SESSION_SECRET`
- `ADMIN_PASSWORD`

The local stack expects PostgreSQL through Docker on host port `5433`.

### Start the stack

Windows PowerShell:

```powershell
.\scripts\run_all.ps1
```

That opens:
- backend docs at `http://localhost:8000/docs`
- frontend app at `http://localhost:3000`

### Seed demo data

```powershell
.\venv\Scripts\python.exe -m scripts.seed_data
```

### Manual startup if needed

Backend:

```powershell
.\scripts\run_dev.ps1
```

Frontend:

```powershell
.\scripts\run_frontend.ps1
```

## Demo Flow For Judges

1. Start the stack and seed demo data.
2. Open `http://localhost:3000/auth`.
3. Sign in as admin using the credentials from your local `.env`.
4. Open the Demo Runner and create a demo worker in a chosen city.
5. Run a disruption scenario such as heavy rain or platform outage.
6. Open the Admin Panel and show:
   - manual review queue
   - next recommended decision
   - confidence and review pressure
   - top review drivers
7. Optionally sign in as a worker to show onboarding, policy purchase, and worker-side claim visibility.

## What Phase 2 Does Not Claim

- Real weather, AQI, traffic, or partner integrations
- Automated learning or retraining from review outcomes
- Production payout rail integrations
- Experimental future integrations

## Related Docs

- [Architecture reference](architecture.md)
- [Workflow guide](workflow_guide.md)
- [Developer notes](DevNotes.md)
- [Phase 3 roadmap](Phase3_Roadmap.md)
