# RideShield Manual Review Checklist

Use this checklist to validate the current repo manually after local startup.

## 1. Start The Stack

- [ ] Run:

```powershell
.\scripts\run_all.ps1
```

- [ ] Confirm frontend is available at `http://localhost:3000`
- [ ] Confirm backend docs are available at `http://localhost:8000/docs`

## 2. Seed Demo Data

- [ ] Run:

```powershell
.\venv\Scripts\python.exe -m scripts.seed_data
```

- [ ] Confirm demo workers exist

## 3. Worker Auth Review

- [ ] Open `/auth`
- [ ] Try invalid worker credentials
- [ ] Confirm the page shows an inline toast error instead of silently redirecting
- [ ] Sign in as a valid worker
- [ ] Refresh the page
- [ ] Confirm the session persists
- [ ] Confirm local storage contains only `rideshield.session_meta` role metadata
- [ ] Confirm local storage does not contain `rideshield.workerId`

## 4. Worker Dashboard Review

- [ ] Confirm `/dashboard` loads
- [ ] Confirm the dashboard shows:
  - [ ] active policy
  - [ ] decision panel and selected claim
  - [ ] risk score card
  - [ ] payout history
  - [ ] nearby alerts

## 5. Onboarding Review

- [ ] Sign out
- [ ] Open `/onboarding`
- [ ] Register a new worker
- [ ] Confirm the flow shows:
  - [ ] registration fields
  - [ ] backend-driven city and zone selectors
  - [ ] risk score
  - [ ] available plans
  - [ ] premium explanation
  - [ ] detailed plan catalog pricing
- [ ] Change city
- [ ] Confirm zones refresh without refetching the full city list repeatedly
- [ ] Purchase a plan
- [ ] Confirm completion state appears
- [ ] Confirm onboarding does not persist `rideshield.workerId`

## 6. Admin Review

- [ ] Open `/auth`
- [ ] Sign in as admin
- [ ] Confirm redirect to `/admin`
- [ ] Confirm the admin panel shows:
  - [ ] KPI cards
  - [ ] textual health status, not a fake percentage
  - [ ] review queue
  - [ ] next decision panel
  - [ ] scheduler state
  - [ ] model status
  - [ ] disruption feed
  - [ ] integrity preview
  - [ ] forecast horizon
  - [ ] disruption map
- [ ] Change city filter
- [ ] Confirm review and supporting panels react to the filter
- [ ] Change zone filter
- [ ] Confirm the same

## 7. Intelligence Review

- [ ] Open `/intelligence`
- [ ] Confirm the page shows:
  - [ ] scheduler posture
  - [ ] monitored cities
  - [ ] KPI interpretation text
  - [ ] forecast bands
  - [ ] threshold notes
- [ ] Confirm loss ratio reads as a percentage and includes interpretation
- [ ] Confirm forecast bands use:
  - [ ] low
  - [ ] guarded
  - [ ] elevated
  - [ ] critical

## 8. Demo Runner Review

- [ ] Open `/demo`
- [ ] Click `Create demo worker`
- [ ] Confirm worker creation succeeds without a 422 validation error
- [ ] Run `Heavy Rain`
- [ ] Confirm result summary updates
- [ ] Confirm live activity log updates
- [ ] Confirm signal snapshots update
- [ ] Run another scenario
- [ ] Confirm the result card updates again
- [ ] Click `Reset simulators`

## 9. Review Queue Flow

- [ ] Use a scenario that produces delayed claims
- [ ] Open `/admin`
- [ ] Confirm the queue shows grouped incident context
- [ ] Approve a delayed claim
- [ ] Confirm queue refresh
- [ ] Confirm payout uses the stored final payout amount
- [ ] Reject a delayed claim
- [ ] Confirm queue refresh again

## 10. Analytics And Policy Admin Spot Checks

- [ ] In Swagger, verify:
  - [ ] `GET /api/analytics/admin-overview`
  - [ ] `GET /api/analytics/forecast`
  - [ ] `GET /api/analytics/zone-risk`
  - [ ] `GET /api/analytics/models`
  - [ ] `POST /api/policies/expire-old`
- [ ] Confirm admin-only routes reject unauthenticated calls
- [ ] Confirm `models` shows:
  - [ ] risk model status
  - [ ] fraud model status
  - [ ] version fields
  - [ ] metrics when available

## 11. Final Acceptance

Mark manual review as passed only if all are true:

- [ ] worker auth works
- [ ] admin auth works
- [ ] onboarding works end to end
- [ ] session restore works without leaking worker identifiers to local storage
- [ ] admin health reflects real scheduler state
- [ ] demo worker creation works
- [ ] admin filters affect the actual decision surface
- [ ] claims and payouts update correctly
- [ ] admin-only utility routes are guarded
- [ ] no obvious white-on-light or collapsed-card regressions remain
