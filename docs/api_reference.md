# RideShield API Reference

The detailed schemas live in FastAPI Swagger at `/docs`.
This file is the repo-local contract map for the current implementation on `main`.

## Route Groups

### Health
- `GET /health`
- `GET /health/db`
- `GET /config/runtime`
- `GET /health/signals`
- `GET /health/diagnostics`
- `GET /health/config`

### Auth
- `POST /api/auth/worker/login`
- `POST /api/auth/admin/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Locations
- `GET /api/locations/cities`
- `GET /api/locations/zones`
- `GET /api/locations/config`

### Workers
- `POST /api/workers/register`
- `GET /api/workers/`
- `GET /api/workers/me/{worker_id}`
- `PUT /api/workers/me/{worker_id}`
- `GET /api/workers/risk-score/{worker_id}`

### Policies
- `GET /api/policies/plans/{worker_id}`
- `POST /api/policies/create`
- `GET /api/policies/active/{worker_id}`
- `GET /api/policies/history/{worker_id}`
- `POST /api/policies/expire-old`
- `POST /api/policies/activate-pending`
- `POST /api/policies/admin/force-activate`

### Triggers
- `POST /api/triggers/check`
- `GET /api/triggers/status`
- `POST /api/triggers/scenario/{scenario}`
- `POST /api/triggers/demo-scenario/{scenario_id}`
- `POST /api/triggers/lab-run`
- `POST /api/triggers/reset`

### Events
- `GET /api/events/active`
- `GET /api/events/history`
- `GET /api/events/detail/{event_id}`
- `GET /api/events/zone/{zone_name}`

### Claims
- `GET /api/claims/worker/{worker_id}`
- `GET /api/claims/detail/{claim_id}`
- `GET /api/claims/review-queue`
- `POST /api/claims/resolve/{claim_id}`
- `GET /api/claims/stats`

### Payouts
- `GET /api/payouts/worker/{worker_id}`
- `GET /api/payouts/detail/{payout_id}`
- `GET /api/payouts/stats`

### Analytics
- `GET /api/analytics/admin-overview`
- `GET /api/analytics/admin-forecast`
- `GET /api/analytics/overview`
- `GET /api/analytics/forecast`
- `GET /api/analytics/zone-risk`
- `GET /api/analytics/models`

## Access Model

### Session transport
- Login endpoints return a signed `token`.
- Login endpoints also set the `rideshield_session` httpOnly cookie.
- Protected APIs accept either the cookie or `Authorization: Bearer <token>`.
- The frontend uses the cookie as the primary auth path.
- Frontend local storage keeps only role metadata for boot UX. It does not persist the auth token or worker PII.

### Worker-owned routes
- `GET /api/workers/me/{worker_id}`
- `PUT /api/workers/me/{worker_id}`
- `GET /api/workers/risk-score/{worker_id}`
- `GET /api/claims/worker/{worker_id}`
- `GET /api/claims/detail/{claim_id}`
- `GET /api/payouts/worker/{worker_id}`
- `GET /api/payouts/detail/{payout_id}`

Worker sessions are restricted to their own records. Admin sessions retain oversight access.

### Admin-only routes
- `GET /api/workers/`
- `POST /api/policies/expire-old`
- `POST /api/policies/activate-pending`
- `POST /api/policies/admin/force-activate`
- `GET /api/claims/review-queue`
- `POST /api/claims/resolve/{claim_id}`
- `GET /api/claims/stats`
- `GET /api/payouts/stats`
- `GET /api/analytics/admin-overview`
- `GET /api/analytics/admin-forecast`
- `GET /api/analytics/overview`
- `GET /api/analytics/zone-risk`
- `GET /api/analytics/models`
- `POST /api/triggers/lab-run`

## Important Contract Notes

### Worker registration
- `POST /api/workers/register` requires:
  - `name`
  - `phone`
  - `password`
  - `city`
  - `platform`
  - `self_reported_income`
  - `working_hours`
  - `consent_given`
- `zone` is schema-optional, but the current onboarding flow expects a valid zone from the DB-backed geography APIs.
- Valid location selectors should come from:
  - `GET /api/locations/cities`
  - `GET /api/locations/zones`

### Policies
- `GET /api/policies/plans/{worker_id}` is the source of truth for detailed pricing.
- The plans payload can include:
  - premium calculation metadata
  - ML fallback state from risk scoring
  - top risk factors
- `GET /api/policies/active/{worker_id}` may activate an eligible pending policy during the read path.
- `POST /api/policies/expire-old` is admin-only.

### Claims and payouts
- RideShield is incident-centric, not trigger-stack-centric.
- One worker should flow through one claim path per incident window.
- Claim detail exposes both fraud and payout explainability.
- Manual claim approval now pays using the stored `final_payout`, not the uncapped `calculated_payout`.

### Analytics
- `admin-overview` is the main admin KPI payload.
- It returns:
  - policy and payout KPIs
  - duplicate claim audit visibility
  - scheduler state
- `admin-overview` no longer carries `next_week_forecast` inline.
- `admin-forecast` is the forecast-only payload and is cached for `300s`.
- `overview` is a compatibility alias to `admin-overview`.
- `forecast` supports city-level and zone-level reads.
- `zone-risk` is city-scoped.
- `models` returns runtime status for:
  - risk model
  - fraud model
  - forecast engine

### Health and runtime diagnostics
- `/health` is the fast liveness route.
- `/health/db` is the database connectivity route.
- `/config/runtime` returns stable runtime configuration:
  - cities
  - zone map
  - thresholds
  - plans
- `/health/signals` returns signal-provider source/freshness status.
- `/health/diagnostics` returns scheduler and shadow-diff internals.
- `/health/config` remains as a compatibility aggregate and now includes timing breakdowns:
  - `runtime`
  - `signals`
  - `diagnostics`

### Demo and lab execution
- `demo-scenario/{scenario_id}` is the deterministic product-story path used by the locked DemoRunner.
- `lab-run` is the exploratory Scenario Lab path.
- Both reuse the shared trigger/claim engine.
- Scenario Lab currently writes simulation-only local records in the working environment and should not be treated as production telemetry.

## Current ML Truth

- Risk ML: integrated with safe fallback.
- Forecast engine: integrated and exposed through analytics.
- Fraud ML: integrated into hybrid fraud scoring with rule fallback.

That means:
- pricing and worker risk surfaces expose model metadata
- claim fraud decisions expose model version, fallback state, probability, and top factors
- admin and intelligence pages expose forecast and model status in live runtime views

## Recommended Local Verification

1. Start the stack with `.\scripts\run_all.ps1`
2. Open Swagger at `http://localhost:8000/docs`
3. Sign in on the frontend at `http://localhost:3000/auth`
4. Verify:
   - worker onboarding
   - active policy and worker dashboard
   - delayed-claim admin resolution
   - admin overview health and scheduler state
   - analytics forecast and model endpoints
