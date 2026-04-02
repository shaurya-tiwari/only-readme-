# RideShield Architecture Reference

This is the repo-local architecture note for the current implementation.
It is intentionally shorter and more operational than the root `Architecture.md`.

## Current Architecture Shape

RideShield is a layered system with:
- a React frontend
- a FastAPI backend
- PostgreSQL persistence
- simulated disruption inputs
- real policy, incident, claim, payout, and scheduler logic
- runtime ML services with explicit fallback paths

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

### Core runtime layer
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

### ML and forecast layer
Current runtime additions:
- `backend/core/risk_model_service.py`
- `backend/core/fraud_model_service.py`
- `backend/core/forecast_engine.py`
- `backend/ml/risk_model.py`
- `backend/ml/fraud_model.py`
- `backend/ml/features/risk_features.py`
- `backend/ml/features/fraud_features.py`
- `backend/ml/explainability.py`

### Data layer
- PostgreSQL-backed worker, policy, event, claim, payout, trust, audit, and geography models
- DB-backed cities and zones
- zone threshold profiles and zone risk profiles

## Current Decisioning Truth

### Real today
- trigger evaluation
- incident creation and extension
- claim generation
- payout execution
- scheduler loop
- audit logging

### Hybrid ML today
- risk scoring uses ML-first behavior with safe fallback
- premium calculation surfaces expose ML-derived risk metadata
- forecast analytics use the forecast engine plus risk-model-backed projections
- fraud scoring blends rule signals and fraud-model output with fallback

### Still rule-controlled today
- the final approve, delay, and reject thresholds in `decision_engine.py`
- most operational thresholds and scheduler behavior
- payout rail behavior, which is still sandboxed and simulated

## Claims Model

RideShield is incident-centric, not trigger-stack-centric.

Meaning:
- one incident window should produce one claim path per worker
- overlapping trigger signals are evidence on one incident
- they are not separate stacked payouts for the same lost window

This is reflected in:
- trigger engine behavior
- grouped claim views
- admin review queue grouping
- payout execution rules

## Auth And Session Model

Current auth shape:
- signed session payloads are generated in `backend/core/session_auth.py`
- worker and admin logins both return a token and set an httpOnly cookie
- protected APIs accept cookie or bearer token
- the frontend treats the cookie as the primary session transport
- local storage keeps only minimal role metadata for boot UX

## Geography Foundation

The repo has moved past hardcoded frontend-only geography.

Current rule:
- `zone_id` is the backend source of truth
- legacy `city` and `zone` strings remain for compatibility and display

Current supported cities:
- Delhi
- Mumbai
- Bengaluru
- Chennai

Current source-of-truth endpoints:
- `GET /api/locations/cities`
- `GET /api/locations/zones`
- `GET /api/locations/config`

## Frontend Surface Architecture

Current major pages:
- `Home.jsx`
- `Auth.jsx`
- `Onboarding.jsx`
- `HowItWorks.jsx`
- `IntelligenceOverview.jsx`
- `Dashboard.jsx`
- `AdminPanel.jsx`
- `DemoRunner.jsx`

Current surface split:
- worker dashboard = worker decision surface
- admin panel = operational decision surface
- demo runner = scenario control and cause-and-effect surface
- home, how-it-works, intelligence = explanation surfaces

## Analytics Architecture

Current analytics routes:
- `GET /api/analytics/admin-overview`
- `GET /api/analytics/forecast`
- `GET /api/analytics/zone-risk`
- `GET /api/analytics/models`

Current intent:
- `admin-overview` = KPI and oversight payload
- `forecast` = city or zone projection reads
- `zone-risk` = ranked city-zone view
- `models` = runtime model metadata and fallback state

## Runtime Observability

Current local observability includes:
- `logs/runtime/app_runtime.txt`
- `logs/runtime/trigger_cycles.txt`
- scheduler state in `/health/config`
- scheduler and model visibility in admin and intelligence surfaces

Use these to inspect:
- trigger cadence
- zone-level signal values
- incident create vs extend behavior
- claim volumes
- payout totals

## Security Posture

Current enforcement:
- worker and admin sessions are separated
- worker-owned routes enforce ownership checks
- analytics and policy utility routes remain admin-only
- auth endpoints are rate limited in memory with lazy cleanup
- CORS is origin-restricted
- baseline browser security headers are enabled

## Known Current Gaps

- fraud and risk model calibration still depend on synthetic or simplified training assumptions
- GPS spoofing and stronger telemetry realism are still not implemented
- runtime logs are plain text rather than structured JSON
- secrets hygiene in local development files still deserves tightening
- some dense decision surfaces still have room for spacing and hierarchy cleanup

## Next Architecture Step

The next meaningful technical step should be:
1. improve fraud-data realism and calibration
2. tighten dev secret handling
3. broaden admin and demo frontend coverage
4. improve structured runtime observability
5. revisit remaining threshold tuning after more realistic scenario data
