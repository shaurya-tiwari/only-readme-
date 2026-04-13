# RideShield Architecture Reference

This is the repo-local architecture note for the current working-repo system.

It focuses on what is implemented now.

## Current Architecture Shape

RideShield is a layered web application with:
- a React frontend
- a FastAPI backend
- PostgreSQL persistence
- mixed real and simulated disruption inputs
- real incident, claim, review, and payout orchestration inside the app

The key product rule is unchanged:
- workers do not manually file claims
- the system creates claims from validated disruption incidents

## Stable Runtime Boundary

### Signal layer

Current provider posture:
- weather
  - real via OpenWeather with safe fallback
- AQI
  - real via OpenWeather with safe fallback
- traffic
  - real via TomTom with safe fallback
- platform disruption
  - behavioral provider-style telemetry engine

Signal runtime support also includes:
- snapshot persistence
- source/freshness visibility
- observational shadow diff persistence for weather/AQI/traffic

### Real product core

The core runtime remains real within the application:
- trigger evaluation
- incident creation and extension
- claim generation
- fraud scoring
- trust-aware decisioning
- payout routing
- admin review flow
- scheduler-driven monitoring
- deterministic demo-story execution
- exploratory Scenario Lab execution through the same trigger/claim engine

## Backend Layers

### API layer

Current route groups:
- auth
- workers
- policies
- triggers
- events
- claims
- payouts
- analytics
- health
- locations

### Core decision layer

Current core services:
- `backend/core/trigger_engine.py`
- `backend/core/claim_processor.py`
- `backend/core/fraud_detector.py`
- `backend/core/decision_engine.py`
- `backend/core/income_verifier.py`
- `backend/core/payout_executor.py`
- `backend/core/trigger_scheduler.py`
- `backend/core/session_auth.py`
- `backend/core/risk_scorer.py`
- `backend/core/premium_calculator.py`

### Data layer

The database stores:
- workers
- policies
- incidents and events
- claims
- payouts
- trust state
- audit logs
- geography records for cities and zones

## End-To-End Flow

```text
Provider signals -> trigger engine -> zone incident
-> eligible workers filtered
-> fraud + trust + payout-aware decisioning
-> approve / review / reject
-> payout or admin action
```

Important runtime behavior:
- incidents are grouped by disruption window
- overlapping trigger evidence contributes to one incident story
- the system avoids stacked same-window payouts for the same worker

## Decisioning Model

RideShield is not a raw rules-only flow and not a self-learning system.

Current decision behavior combines:
- disruption context
- fraud score
- worker trust score
- decision confidence
- payout exposure

### Weak vs strong suspicious signals

Weak signals such as:
- movement anomaly
- weak pre-event activity
- event confidence

should not behave like hard fraud evidence on their own.

The decision layer is tuned so:
- clean, trusted claims can pass through the zero-touch lane
- ambiguous claims move to bounded manual review
- harder suspicious patterns can still be rejected

## Zero-Touch And Review Design

The product is built around two lanes:

### Zero-touch lane

Used for low-risk claims where the system has enough signal support to act automatically.

### Review lane

Used for ambiguity, not as the default path.

The admin queue is incident-centric and operationally prioritized using:
- wait time
- payout exposure
- urgency
- confidence
- primary review driver

Explainability is surfaced directly in the admin product through:
- next decision context
- queue pressure
- review driver summaries
- confidence and reason fields

## Frontend Surface Split

Current major surfaces:
- `Home.jsx`
- `Auth.jsx`
- `Onboarding.jsx`
- `HowItWorks.jsx`
- `Dashboard.jsx`
- `AdminPanel.jsx`
- `DemoRunner.jsx`
- `ScenarioLab.jsx`
- `IntelligenceOverview.jsx`

Functional split:
- worker dashboard = worker-facing claims and policy view
- admin panel = operational decision and oversight surface
- demo runner = locked deterministic storytelling surface
- scenario lab = exploratory simulation and batch-testing surface
- intelligence page = system interpretation and model context surface

## Geography And Auth

### Geography

Current supported cities:
- Delhi
- Mumbai
- Bengaluru
- Chennai

Backend geography is DB-backed.

Current rule:
- `zone_id` is the backend source of truth
- legacy `city` and `zone` strings remain for display and compatibility

### Auth

Current auth shape:
- worker and admin sessions are separated
- httpOnly cookies are the primary browser auth path
- bearer token support remains available for API tooling and tests

## Runtime Observability

Current local observability includes:
- runtime diagnostics during development
- scheduler state in health and admin analytics
- split runtime endpoints:
  - `/config/runtime`
  - `/health/signals`
  - `/health/diagnostics`
- compatibility timing breakdowns on `/health/config`

These logs are local diagnostics for:
- trigger cadence
- signal values
- incident creation vs extension
- claim volume
- payout totals

## Current Boundaries

This architecture note does not claim:
- production payout rail integration
- partner-native platform telemetry
- production-safe isolation for Scenario Lab generated records

It does claim the current working repo now includes:
- real weather/AQI/traffic providers with safe fallback
- behavioral platform telemetry
- deterministic DemoRunner stories
- exploratory Scenario Lab
- decomposed analytics and health/runtime surfaces

## Related Docs

- [Phase 2 current state](PHASE2_CURRENT_STATE.md)
- [Workflow guide](workflow_guide.md)
- [Developer notes](DevNotes.md)
- [Phase 3 roadmap](Phase3_Roadmap.md)
