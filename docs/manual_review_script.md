# RideShield Manual Review Checklist

Use this checklist to review the current Sprint 1, Sprint 2, and Sprint 3 product behavior end to end.

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

- [ ] Confirm the seeded worker phones are:
  - Rahul: `+919876543210`
  - Vikram: `+919876543211`
  - Arun: `+919876543212`
  - Priya: `+919876543213`

## 3. Worker Sign-In Review

- [ ] Open `http://localhost:3000/auth`
- [ ] Sign in as worker with `+919876543210`
- [ ] Confirm redirect to `/dashboard`
- [ ] Confirm the dashboard shows:
  - [ ] active policy
  - [ ] trust badge
  - [ ] grouped incidents
  - [ ] payout history
  - [ ] nearby disruption events
- [ ] Refresh the page
- [ ] Confirm the session persists
- [ ] Open `/onboarding`
- [ ] Confirm logged-in worker is redirected away
- [ ] Open `/`
- [ ] Confirm the home page reflects logged-in worker state

## 4. Worker Onboarding Review

- [ ] Sign out
- [ ] Open `/onboarding`
- [ ] Register a new worker
- [ ] Confirm the onboarding flow shows:
  - [ ] worker registration fields
  - [ ] risk score
  - [ ] available plans
  - [ ] premium formula panel
- [ ] Purchase a plan
- [ ] Confirm the completion state appears
- [ ] Open `/dashboard`
- [ ] Confirm the new worker dashboard loads

## 5. Admin Sign-In Review

- [ ] Open `/auth`
- [ ] Switch to admin sign-in
- [ ] Sign in with:
  - username: `admin`
  - password: `rideshield-admin`
- [ ] Confirm redirect to `/admin`
- [ ] Confirm the admin panel shows:
  - [ ] KPI cards
  - [ ] decision chart
  - [ ] event panel
  - [ ] review queue
  - [ ] disruption heat-view
  - [ ] duplicate or extension log
  - [ ] forecast panel
  - [ ] scheduler state

## 6. Demo Runner Review

- [ ] While signed in as admin, open `/demo`
- [ ] Click `Create demo worker`
- [ ] Run `Heavy Rain`
- [ ] Confirm the result card updates
- [ ] Confirm claim and payout totals update
- [ ] Run the same scenario again
- [ ] Confirm the demo run still produces a fresh run instead of silently doing nothing
- [ ] Click `Reset simulators`

## 7. Manual Review Queue Review

- [ ] Use a scenario that produces delayed claims
- [ ] Open `/admin`
- [ ] Confirm the review queue shows:
  - [ ] grouped incident card
  - [ ] trigger list
  - [ ] fraud score
  - [ ] final score
  - [ ] review deadline
- [ ] Approve one delayed claim
- [ ] Confirm the queue refreshes
- [ ] Reject one delayed claim
- [ ] Confirm the queue refreshes again

## 8. Duplicate And Extension Review

- [ ] Run the same scenario repeatedly without a full reset where incident extension is expected
- [ ] Open `/admin`
- [ ] Confirm the duplicate or extension log shows:
  - [ ] duplicate stopped
  - [ ] incident extended
  - [ ] zone context
  - [ ] trigger context

## 9. Scheduler Review

- [ ] Open backend docs or call `GET /health/config`
- [ ] Confirm scheduler fields show:
  - [ ] enabled or disabled state
  - [ ] interval seconds
  - [ ] run count
  - [ ] last started time
  - [ ] last finished time

## 10. API Spot Checks

- [ ] Verify these endpoints in Swagger:
  - [ ] `GET /health`
  - [ ] `GET /health/db`
  - [ ] `GET /api/workers/`
  - [ ] `GET /api/events/active`
  - [ ] `GET /api/events/history`
  - [ ] `GET /api/claims/stats`
  - [ ] `GET /api/payouts/stats`
  - [ ] `GET /api/analytics/admin-overview`

## 11. Final Acceptance

Mark the manual review as passed only if all of the following are true:

- [ ] worker auth and session restore work
- [ ] admin auth and session restore work
- [ ] onboarding works end to end
- [ ] policy purchase works
- [ ] scheduler is visible and understandable
- [ ] demo runner works repeatedly
- [ ] grouped incidents appear on worker side
- [ ] delayed claims can be resolved on admin side
- [ ] payouts and analytics update correctly
