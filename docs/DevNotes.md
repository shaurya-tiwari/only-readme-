## RideShield Dev Notes

This file is the implementation baseline for the current repo, not a copy of the sprint markdowns. `Sprint_1.md`, `Sprint_2.md`, and `Sprint_3.md` were used as planning references, but the codebase has intentionally diverged where correctness, maintainability, Windows compatibility, and demo clarity required it.

### Latest Repo Notes

- Risk-model scaffolding and runtime risk-model service now exist.
- Forecast engine and analytics model-status endpoints now exist.
- Frontend includes model/risk/forecast visibility surfaces.
- Fraud ML is integrated into hybrid claim-path scoring with runtime fallback.
- The frontend now uses httpOnly cookie sessions with minimal role-only local metadata.
- Root audit notes were merged into this file and removed from the repo root:
  - `CODE_AUDIT_REPORT.md`
  - `FRONTEND_IMPROVEMENT_PLAN.md`
- Several local-only scratch files are intentionally ignored:
  - `DEMO_SCRIPT.md`
  - `test_model.py`
  - `test_phase2_ml_integration.py`
- ML artifact files under `backend/ml/artifacts/` are local outputs and should not be treated as committed source.

### Current Baseline

- Sprint 1 foundation is implemented and working.
- Sprint 2 engine/orchestration scope is implemented and working.
- Sprint 3 product/frontend scope is implemented and now extended beyond the original non-ML baseline.
- Current backend test status: `53 passed`.
- Current frontend test status: `60 passed`.
- Trigger monitoring now runs on a scheduler and can also be exercised manually through the demo runner and trigger APIs.
- Geography is no longer only a frontend/config constant problem. The repo now has a DB-backed geography foundation for the currently supported cities.

### Important Divergences From Sprint Markdown Files

#### 1. Datetime handling

The sprint markdowns use `datetime.utcnow()` or timezone-aware timestamps somewhat interchangeably.

Current repo rule:
- DB writes must use naive UTC values for columns declared as `DateTime` without timezone.
- Helper pattern used in API write paths:

```python
def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

Why:
- Prevents asyncpg errors like:
  - `can't subtract offset-naive and offset-aware datetimes`
- This already affected worker registration, policy flows, and seed data earlier.

Constraint for future Sprint 2 work:
- Do not reintroduce mixed aware/naive datetimes in any DB insert/update path.

#### 2. Pydantic style

The sprint markdowns use old-style `class Config`.

Current repo rule:
- Use Pydantic v2 config style:
  - `ConfigDict`
  - `SettingsConfigDict`

Why:
- The old style produced deprecation warnings in the current environment.

Constraint:
- Any new schemas or schema refactors must stay on Pydantic v2 style.

#### 3. Terminal and Windows readability

The sprint markdowns contain emoji-heavy logging and some mojibake-affected text.

Current repo rule:
- Keep runtime logs and scripts ASCII-safe and readable in Windows PowerShell.
- Use plain `INR` instead of rupee symbols in runtime text where needed.

Why:
- Earlier seed/startup output broke or rendered badly on the current machine.

Constraint:
- New scripts and log messages should stay Windows-safe unless there is a strong reason otherwise.

#### 4. SQL logging vs debug mode

The original flow effectively tied SQL echo noise to debug mode.

Current repo rule:
- `DEBUG` and `SQL_ECHO` are separate settings.

Why:
- We want application debug behavior without unreadable SQL spam in the terminal.

Constraint:
- Do not wire engine echo back to `DEBUG` directly.

#### 5. Docker/Postgres port mapping

Current repo runs the Docker Postgres host binding on `5433`, not `5432`.

Why:
- The user's machine had a local Windows PostgreSQL service already on `5432`.

Files already adapted:
- `docker-compose.yml`
- `.env`
- `.env.example`
- `alembic.ini`
- config/default DB wiring

Constraint:
- Do not revert host-side references back to `5432`.

#### 6. Simulation-only admin helpers

Current repo includes simulation/demo helpers that are not meant for production behavior:
- `POST /api/policies/activate-pending`
  - in simulation mode, acts as a demo-friendly activator
- `POST /api/policies/admin/force-activate`
  - simulation-only force activation

Why:
- Needed for Swagger/demo/testing without waiting 24 real hours.

Constraint:
- Keep these clearly scoped to simulation mode.
- Do not present them as production logic.

### Sprint 1 Notes

Sprint 1 is functionally complete for the current repo baseline:
- workers registration/profile/update/list
- policies plans/create/active/history
- risk scorer
- premium calculator
- seed script
- simulator layer
- health/config checks

Sprint 1 improvements already made beyond markdown:
- root-level venv workflow and Windows PowerShell dev script
- `.gitignore` for local-only markdown planning docs and env files
- readable startup output
- fixed dependency pin (`scikit-learn`)
- config hardening for bad env values such as `DEBUG=release`

### Sprint 2 Notes

Sprint 2 is structurally implemented:
- `backend/core/trigger_engine.py`
- `backend/core/fraud_detector.py`
- `backend/core/decision_engine.py`
- `backend/core/income_verifier.py`
- `backend/core/payout_executor.py`
- `backend/core/claim_processor.py`
- `backend/api/triggers.py`
- `backend/api/events.py`
- `backend/api/claims.py`
- `backend/api/payouts.py`
- `backend/schemas/event.py`
- `backend/schemas/claim.py`
- `backend/schemas/payout.py`
- `scripts/run_scenario.py`

Sprint 2 additions already adapted for the current codebase:
- richer event/claim/payout responses than the initial markdown copy
- simulation-only admin activation path
- seeded data with:
  - 2 active profiles
  - 2 pending profiles
- endpoint tests added for event/claim/payout detail and review flows
- direct fraud detector tests added
- scenario-outcome tests added
- scenario runner calibrated to create realistic legit/fraud/edge personas before activation
- trigger engine now derives a simple social/civic disruption signal instead of always returning `0.0`
- decision engine now applies a bounded fraud-flag penalty so:
  - legitimate claims can auto-approve
  - suspicious claims are pushed down appropriately
  - borderline cases still land in manual review instead of collapsing directly to rejection
- claim stats now use a realistic fraud threshold for `fraud_rate`

Current Sprint 2 verification state:
- backend tests: `28 passed`
- `python -m scripts.run_scenario` now yields the intended narrative:
  - Scenario 1 legitimate rain -> approved + payout
  - Scenario 2 fraud attempt -> rejected
  - Scenario 3 edge case -> delayed -> admin resolution

### Sprint 2 Completion Status

Sprint 2 backend is now complete for the current repo baseline.

Meaning:
- the backend/core-engine scope described in `Sprint_2.md` is implemented
- the implementation is adapted to the current repo constraints
- the scenario runner and tests now match the intended legit/fraud/edge narrative

What is still left is not Sprint 2 backend work. It is later-stage work from architecture / Sprint 3:
- frontend onboarding flow
- worker dashboard
- admin dashboard / analytics UI
- broader product polish outside the backend core

### Deferred Refactors

These are valid, but not part of Sprint 2 completion unless they become blockers.

#### PlanOption schema placement

Current issue:
- `PlanOption` lives in worker schema land but is also used by policy flows.

Possible cleanup:
- move it to a shared `schemas/plans.py`

Priority:
- medium

#### PremiumCalculator return structure

Current state:
- `calculate_all_plans()` returns a tuple

Possible cleanup:
- return a structured dict instead

Priority:
- low

#### Status strings vs enums

Current state:
- statuses like `active`, `pending`, `approved`, `delayed`, `rejected` are plain strings

Possible cleanup:
- convert to enums gradually

Priority:
- medium

#### Broad exception handling

Current state:
- a few routes/utilities still catch broad exceptions

Possible cleanup:
- tighten exception boundaries after behavior is stable

Priority:
- low to medium

### Working Rule For Future Sprint 2 Completion

When finishing Sprint 2:

1. Use the current repo behavior as the baseline.
2. Use `Sprint_2.md` as a feature/reference checklist, not as code to copy blindly.
3. Prefer correctness, readability, and testability over markdown literal parity.
4. Preserve:
   - naive UTC DB writes
   - Pydantic v2 config style
   - Windows-safe terminal output
   - separate `SQL_ECHO`
   - simulation-only gating for demo shortcuts

### Sprint 3 Current State

Sprint 3 is now past the initial scaffold stage and includes the first auth/session and logging pass.

Implemented frontend scaffold:
- `frontend/package.json`
- `frontend/vite.config.js`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.jsx`
- `frontend/src/App.jsx`
- `frontend/src/index.css`

Implemented API clients:
- `frontend/src/api/client.js`
- `frontend/src/api/health.js`
- `frontend/src/api/workers.js`
- `frontend/src/api/policies.js`
- `frontend/src/api/claims.js`
- `frontend/src/api/payouts.js`
- `frontend/src/api/events.js`
- `frontend/src/api/triggers.js`

Implemented pages:
- `frontend/src/pages/Auth.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Onboarding.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/AdminPanel.jsx`
- `frontend/src/pages/DemoRunner.jsx`

Implemented reusable components:
- navbar
- section header
- stat cards
- plan cards
- risk gauge
- trust badge
- active policy card
- claim list
- payout history
- event panel
- review queue
- scenario card
- protected route guard

Implemented Sprint 3 launcher scripts:
- `scripts/run_frontend.ps1`
- `scripts/run_frontend.sh`
- `scripts/run_all.ps1`
- `scripts/run_all.sh`

Launcher behavior:
- `run_frontend.*` starts the frontend and installs `node_modules` if missing
- `run_all.ps1` is the intended Windows entrypoint for full-stack local development
- `run_all.ps1` opens separate PowerShell windows for:
  - Docker + backend via `run_dev.ps1`
  - frontend via `run_frontend.ps1`
- `run_all.sh` provides the same high-level behavior for Bash environments

Sprint 3 implementation rules for the current repo:
- Use current backend payloads, not stale markdown payload assumptions.
- Keep frontend copy readable and cleaner than the raw sprint markdown text.
- Prefer route-level code splitting where it materially reduces bundle size.
- Keep demo-only backend endpoints visible in the UI as simulation helpers, not production behavior.
- Keep worker and admin access separated by session role and route boundary.

Frontend verification state:
- `cmd /c npm install` completed successfully in `frontend/`
- `cmd /c npm run build` completed successfully
- current frontend build uses:
  - Vite `6.4.1`
  - React route-level lazy loading

Sprint 3 auth/session additions:
- backend:
  - `backend/core/session_auth.py`
  - `backend/schemas/auth.py`
  - `backend/api/auth.py`
- frontend:
  - `frontend/src/api/auth.js`
  - `frontend/src/auth/session.js`
  - `frontend/src/auth/AuthContext.jsx`
  - `frontend/src/components/ProtectedRoute.jsx`
  - `frontend/src/pages/Auth.jsx`

Sprint 3 auth/session behavior now implemented:
- worker sign-in by phone
- admin sign-in with separate route and session role
- bearer-token session restore via `/api/auth/me`
- protected routes for worker/admin pages
- role-aware navbar and sign-out flow
- dashboard access can restore from session without relying only on a route param

Sprint 3 logging updates now implemented:
- request logging middleware in `backend/main.py`
- startup/shutdown moved to `logging`
- audit-log based business logging from prior backend work remains in place

Sprint 3 claim UX improvements now implemented:
- worker claim list groups same-window trigger claims into one disruption incident in the UI
- admin review queue groups same-window delayed claims into one incident card
- review actions still operate on underlying individual claims
- decision engine now applies narrow auto-approve / auto-reject shortcuts for clearly legitimate and clearly suspicious cases to reduce unnecessary manual review volume

Sprint 3 demo-data and navigation fixes now implemented:
- `scripts/seed_data.py` is now idempotent for the core demo workers:
  - workers are upserted by phone
  - trust scores are upserted by worker
  - demo policies are upserted by worker + plan
  - worker activity logs are refreshed instead of duplicated
- rerunning the seed script now updates the same four demo workers instead of failing on duplicate phones
- `/auth` and `/onboarding` now redirect logged-in users away from anonymous entry flows
- home page CTA and copy now adapt to:
  - anonymous users
  - signed-in workers
  - signed-in admins
- worker dashboard now falls back to sign-in when the worker record is missing instead of sending the user back to onboarding

Test isolation fix now implemented:
- backend tests no longer use the live dev database
- config is environment-aware:
  - `ENV=dev` -> `.env`
  - `ENV=test` -> `.env.test`
- `.env.test` points to `rideshield_test_db`
- `backend/tests/conftest.py` sets `ENV=test` before importing app/database modules
- test fixture now refuses to drop tables unless the configured database URL contains `test`
- isolated PostgreSQL test database created:
  - `rideshield_test_db`

Incident-level claim fix now implemented:
- trigger engine now creates one hourly zone incident event instead of one active event per trigger
- incident metadata stores:
  - `fired_triggers`
  - `trigger_details`
  - signal snapshot
- claim processor now creates one claim per worker per incident event
- overlapping triggers in the same window no longer create stacked same-window claims for the same worker
- duplicate detection now checks `worker_id + event_id` instead of `worker_id + event_id + trigger_type`

Demo runner repeatability improvement now implemented:
- trigger check accepts an optional `demo_run_id`
- in simulation mode, explicit demo runs can force fresh incidents instead of silently extending the previous run
- frontend Demo Runner now sends a unique `demo_run_id` on each run

Incident-level UI follow-up now implemented:
- grouped claim utilities now surface actual incident triggers from claim decision breakdown instead of only showing a generic synthetic incident type

Sprint 3 parity improvements now implemented:
- periodic trigger scheduler
  - `backend/core/trigger_scheduler.py`
  - started from `backend/main.py`
  - interval configured by `TRIGGER_CHECK_INTERVAL_SECONDS`
  - visible in `/health/config` and admin analytics

### Geography Foundation Mini-Sprint

This was added after Sprint 3 completion to prevent Sprint 4 and Sprint 5 from being built on brittle hardcoded geography.

Implemented:
- DB-backed geography tables in `backend/db/models.py`:
  - `City`
  - `Zone`
  - `ZoneThresholdProfile`
  - `ZoneRiskProfile`
- `zone_id` / `city_id` support on workers
- `zone_id` support on events and worker activity
- location bootstrap and backfill service:
  - `backend/core/location_service.py`
- location routes:
  - `GET /api/locations/cities`
  - `GET /api/locations/zones`
  - `GET /api/locations/config`

Current geography rule:
- `zone_id` is the internal source of truth
- legacy `city` / `zone` strings remain for compatibility and display
- write paths must keep them synchronized

Backfill safety:
- old rows are backfilled strictly from `city` + `zone`
- unmapped rows are logged
- bootstrap/backfill raises loudly on mismatch instead of silently proceeding

Scheduler hardening:
- scheduler now reads active cities and zones from the DB first
- if DB geography is empty, it falls back to config bootstrap values
- active monitored zones are logged clearly

Frontend geography updates:
- onboarding, demo runner, and admin filters now fetch cities/zones from backend APIs
- hardcoded frontend geography constants are no longer the primary source of truth for those flows
- pages now include location-loading awareness so the UI does not render an empty world while data is still loading

Current supported cities in the bootstrap layer:
- Delhi
- Mumbai
- Bengaluru
- Chennai

Current seeded demo workers now cover multiple cities:
- Rahul Kumar
- Vikram Singh
- Arun Patel
- Priya Sharma
- Aman Verma
- Farhan Ali
- Sneha Iyer
- Neha Gupta
- Rohit Yadav

Verification after geography refactor:
- backend tests: `53 passed`
- frontend tests: `60 passed`
- in-process API smoke pass confirms the current route contracts for:
  - health
  - locations
  - auth
  - workers
  - policies
  - triggers
  - events
  - claims
  - payouts
  - analytics

Important current API contract notes:
- auth login returns `token`, not `access_token`
- protected routes accept the session cookie or `Authorization: Bearer <token>`
- policy plans route is `/api/policies/plans/{worker_id}`
- event detail route is `/api/events/detail/{event_id}`
- claim detail route is `/api/claims/detail/{claim_id}`
- worker claims route returns an object with a `claims` array, not a raw list
- admin analytics surface
  - `backend/api/analytics.py`
  - exposes:
    - active policies by plan/city
    - premiums in force
    - payouts in window
    - loss ratio
    - worker activity index
    - duplicate and event-extension audit log
    - scheduler state
    - next-week forecast snapshots from the forecast engine
- duplicate/extension visibility
  - trigger engine now writes `event_extended` audit logs
  - claim processor now writes `duplicate_detected` audit logs
- richer admin panel
  - disruption heat-view component
  - duplicate claim log
  - forecast panel
  - scheduler visibility
  - stronger KPI coverage
- richer worker-facing explainability
  - dedicated claim status component
  - richer claim detail panel wired to incident triggers and score breakdown
- onboarding parity improvement
  - premium calculator/formula surface added to plan selection step
- repo-structure parity files added
  - `.github/workflows/ci.yml`
  - `docs/api_reference.md`
  - `docs/pitch_deck_outline.md`
  - `docs/architecture.md`

Current verification state after this pass:
- backend tests: `33 passed`
- frontend build: successful

Current remaining Sprint 3 gaps:
- admin panel is still chart-heavy and can be optimized further for dev load speed
- disruption map is a zone heat-view, not a full Leaflet geographic map yet
- next-week forecast is currently rule-based, not ML-driven
- demo video and pitch deck artifacts themselves are not produced inside the repo yet
- local asset `publicIMG/` is still intentionally untracked and should be included in the next Sprint 3 push

Current completion read:
- Sprint 1 backend foundation: complete
- Sprint 2 backend engine and scenario flow: complete
- Sprint 3 product layer: functionally complete for the current non-ML scope, with remaining work mostly in polish, performance, and judging assets

### Product Readiness Notes

Current product state is best described as:
- system-complete
- product-not-fully-explained

Important interpretation:
- the trigger engine is real
- the decisioning pipeline is real
- the payout pipeline is real
- only the environment inputs are mocked

That means the current architecture is sound:
- mocked input layer
- real core engine
- real orchestration
- real frontend product surface

The main remaining weakness is no longer backend correctness. It is perception and clarity.

#### 1. Explainability needs stronger surfacing

The system already computes and stores:
- disruption score
- fraud score
- final score
- covered triggers
- incident triggers
- decision explanation

What still matters:
- the UI should keep making these reasons obvious, especially for approved, delayed, and rejected outcomes
- users should not have to infer why the system acted

Working rule:
- every important claim outcome should answer:
  - what happened
  - why this worker was affected
  - why it was approved, delayed, or rejected

#### 2. Demo runner should keep showing cause and effect

The backend currently works by:
- changing scenario inputs in the simulators
- letting the real trigger engine evaluate thresholds
- creating or extending incidents
- processing claims and payouts

The UI should keep making that chain explicit so it does not feel like a magic button that directly creates claims.

Preferred narrative pattern:
- scenario changes signals
- signals cross thresholds
- incident is created or extended
- workers are filtered
- claims are decided
- payouts or review follow

#### 3. Scheduler visibility matters

The 5-minute scheduler now exists and is active in the backend.

But product trust improves when the UI makes the monitoring loop feel alive.

Useful visibility points:
- last run time
- next run expectation
- total run count
- whether monitoring is active or disabled

This is now partially visible through:
- `/health/config`
- admin analytics

This is now also surfaced in the frontend demo runner with:
- monitoring active or disabled
- last run
- next run
- interval seconds
- explicit reminder that the scheduler is the background monitoring path and the demo runner is an admin override

#### 4. Core architectural win to preserve

The most important product correctness improvement already made:
- move from trigger-centric same-window claims to incident-centric claim handling

That rule must be preserved:
- one disruption window should not stack multiple payable claims for the same worker
- triggers are evidence on the incident, not separate payouts for the same lost hours

### Latest Transparency Pass

Further Sprint 3 polish now implemented:
- demo runner cause-effect storytelling
  - each scenario result now explains:
    - which signals crossed thresholds
    - whether an incident was created or extended
    - how many claims were processed
    - how decisions split across approved, delayed, and rejected
- worker-facing claim list now uses simpler reasoning language per incident
- event panel now explains that multiple crossed signals are merged into one incident

Current verification state after this final transparency pass:
- backend tests: `33 passed`
- frontend build: successful

### Immediate Next Step

Continue Sprint 3 implementation and polish:
- reduce manual-review noise and improve grouped claim/review UX
- refine worker dashboard and admin panel behavior from real API responses
- tighten admin/demo UX and narrative flow
- then push Sprint 3 together with `publicIMG/`

### Multi-City Demo Update

The backend was already city-agnostic across the configured profiles, but the demo layer was still too Delhi-centric.

Updated:
- `scripts/seed_data.py`
  - now includes demo personas across all currently supported cities:
    - Delhi
    - Mumbai
    - Bengaluru
    - Chennai
- `frontend/src/pages/DemoRunner.jsx`
  - now supports city selection instead of hardcoding Delhi
  - demo workers are created in the selected city and zone
  - trigger snapshots and scenario runs are refreshed per selected city
- `frontend/src/pages/AdminPanel.jsx`
  - now supports city filtering instead of showing Delhi-only map data
- `frontend/src/components/DisruptionMap.jsx`
  - now includes zone coordinates for Mumbai and Chennai in addition to Delhi and Bengaluru

Important constraint:
- this multi-city pass intentionally stays within the cities and zones already supported by `backend/config.py`
- the broader CSV example with Kolkata, Jaipur, Lucknow, Hyderabad, Ahmedabad, and Pune would require adding those cities to validation, risk profiles, mock baselines, and frontend constants first

### Geography Foundation Mini-Sprint

The repo now has a proper DB-backed geography layer so Sprint 4 and Sprint 5 do not build on hardcoded location constants.

Implemented:
- new geography tables and migration:
  - `cities`
  - `zones`
  - `zone_threshold_profiles`
  - `zone_risk_profiles`
  - plus `zone_id` / `city_id` references added to legacy entities
- new location bootstrap service:
  - creates/refreshes geography from current configured cities
  - backfills `zone_id` references from legacy string fields
  - fails loudly if unmapped rows are found during backfill
- source-of-truth rule:
  - `zone_id` is now the internal source of truth
  - legacy `city` / `zone` strings remain for compatibility and display
- scheduler hardening:
  - scheduler now reads active cities/zones from DB
  - falls back to config if DB geography is empty
  - logs monitored zones explicitly
- new location APIs:
  - `GET /api/locations/cities`
  - `GET /api/locations/zones`
  - `GET /api/locations/config`
- frontend now loads locations from backend APIs in:
  - onboarding
  - demo runner
  - admin city filter

Important guardrails that were intentionally added:
- backfill is strict and logs unmapped rows before raising
- seed data now bootstraps geography because seed is now bootstrap config, not just demo data
- frontend includes loading-aware location fetches so geography does not briefly appear empty

Verification after geography refactor:
- backend tests: `53 passed`
- frontend tests: `60 passed`

### Current Frontend Surface Update

The repo now includes a more substantial frontend structure pass beyond the earlier Sprint 3 scaffold.

Implemented:
- protected application shell
  - `frontend/src/components/AppFrame.jsx`
  - fixed sidebar
  - top utility bar
  - mobile bottom navigation for authenticated routes
- public explanation pages
  - `frontend/src/pages/HowItWorks.jsx`
  - `frontend/src/pages/IntelligenceOverview.jsx`
- app-level rendering guard
  - `frontend/src/components/ErrorBoundary.jsx`
- refreshed token system and typography
  - `frontend/tailwind.config.js`
  - `frontend/src/index.css`
- worker dashboard improvements
  - trust score gauge
  - denser incident-aligned claims presentation
  - stronger nearby alert severity treatment
- admin dashboard improvements
  - integrity log
  - city and zone filters
  - stronger scheduler and health framing
- demo runner improvements
  - sequential activity log timestamps
  - stronger cause-and-effect framing

Current frontend correctness fixes after that pass:
- worker dashboard hook-order crash fixed in `frontend/src/pages/Dashboard.jsx`
- `/intelligence` shell title fixed in `frontend/src/components/AppFrame.jsx`
- shared formatters hardened in `frontend/src/utils/formatters.js`

Current frontend backlog still acknowledged:
- search is stateful but not wired to real filtering yet
- document-title coverage is partial, not complete
- disruption map is still a stylized static surface, not a full geographic map
- mobile spacing still deserves a focused polish pass

### Runtime Logging Update

The backend now writes local plain-text runtime logs to:
- `logs/runtime/app_runtime.txt`
- `logs/runtime/trigger_cycles.txt`

Purpose:
- review scheduler behavior over time
- inspect zone-level signals and triggers
- review incident create/extend behavior
- review claim generation, duplicates, and payout totals

Implementation files:
- `backend/core/runtime_logging.py`
- `backend/main.py`
- `backend/core/trigger_scheduler.py`
- `backend/core/claim_processor.py`

Working rule:
- runtime logs are local diagnostics
- they are intentionally ignored by git

### Security Hardening Update

Confirmed audit fixes now implemented:
- worker, claim, and payout detail/history endpoints require an authenticated session
- worker sessions are restricted to their own records; admin sessions retain oversight access
- auth endpoints now apply baseline in-memory rate limiting
- CORS now uses configured frontend origins instead of wildcard `*`
- baseline browser security headers are applied in backend middleware
- admin password and session secret are env-backed instead of relying on source defaults
- manual delayed-claim approval now uses the stored `final_payout`
- payout execution no longer rewrites `claim.final_payout`
- policy activation reads use row locking
- `POST /api/policies/expire-old` is now admin-guarded
- frontend session metadata stores role only and clears legacy `workerId`
- admin health KPI is derived from live scheduler state, not a static percentage

### Audit Archive Update (2026-04-02)

This section absorbs the earlier root audit artifacts:
- `CODE_AUDIT_REPORT.md`
- `FRONTEND_IMPROVEMENT_PLAN.md`

They are intentionally folded into `docs/DevNotes.md` so the repo keeps one implementation-facing audit history instead of multiple drifting summary files.

Snapshot after the audit hardening pass:
- backend tests: `53 passed`
- frontend tests: `60 passed`
- auth model: httpOnly cookie primary, bearer fallback for Swagger/tests
- fraud posture: hybrid rule + ML scoring with runtime fallback
- frontend session storage: role-only metadata, no persisted worker identifier key

Highest-priority findings that were confirmed and fixed:
- payout executor no longer overwrites `claim.final_payout`
- delayed-claim manual approval now pays `final_payout` before falling back to `calculated_payout`
- active-policy read path now uses row locking before activating pending policies
- `POST /api/policies/expire-old` now requires an admin session
- forecast incident pressure now respects 7-day and 30-day windows
- in-memory auth rate limiter now prunes stale keys instead of growing indefinitely
- frontend onboarding no longer persists `workerId` in local storage
- auth session metadata in local storage is reduced to role-only information
- auth-page `401` handling no longer redirects the user from `/auth` back to `/auth?reason=session_expired`
- admin health now reflects scheduler state instead of a fake `99.98%` KPI

Audit items that were already resolved by the branch before the merge:
- login handlers in `Auth.jsx` already had explicit `catch` handling
- worker dashboard ownership redirect already existed in `ProtectedRoute`
- public pages were no longer blocked behind a global app-wide boot spinner

Residual backlog that still matters after the audit:
- move more local secrets and convenience credentials out of committed dev config paths
- broaden frontend coverage further into admin/demo surfaces such as `DemoRunner` and `IntelligenceOverview`
- improve fraud and risk calibration realism for non-synthetic operating data
- move runtime logging toward structured JSON if production observability becomes a priority
- keep tightening dense admin/dashboard surface hierarchy where needed
