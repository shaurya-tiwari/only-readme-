# RideShield API Reference

This repo keeps the detailed implementation in FastAPI Swagger at `/docs`.

## Core API groups

- `Health`
  - `/health`
  - `/health/db`
  - `/health/config`
- `Auth`
  - `/api/auth/worker/login`
  - `/api/auth/admin/login`
  - `/api/auth/me`
  - `/api/auth/logout`
- `Workers`
  - `/api/workers/register`
  - `/api/workers/`
  - `/api/workers/me/{worker_id}`
  - `/api/workers/risk-score/{worker_id}`
- `Policies`
  - `/api/policies/plans/{worker_id}`
  - `/api/policies/create`
  - `/api/policies/active/{worker_id}`
  - `/api/policies/history/{worker_id}`
  - `/api/policies/activate-pending`
  - `/api/policies/admin/force-activate`
- `Triggers`
  - `/api/triggers/check`
  - `/api/triggers/status`
  - `/api/triggers/scenario/{scenario}`
  - `/api/triggers/reset`
- `Events`
  - `/api/events/active`
  - `/api/events/history`
  - `/api/events/detail/{event_id}`
  - `/api/events/zone/{zone_name}`
- `Claims`
  - `/api/claims/worker/{worker_id}`
  - `/api/claims/detail/{claim_id}`
  - `/api/claims/review-queue`
  - `/api/claims/resolve/{claim_id}`
  - `/api/claims/stats`
- `Payouts`
  - `/api/payouts/worker/{worker_id}`
  - `/api/payouts/detail/{payout_id}`
  - `/api/payouts/stats`
- `Analytics`
  - `/api/analytics/admin-overview`

## Recommended local verification flow

1. Start the stack with `.\scripts\run_all.ps1` or the separate backend/frontend scripts.
2. Open Swagger at `http://localhost:8000/docs`.
3. Sign in on the frontend at `http://localhost:3000/auth`.
4. Run the demo scenarios from `http://localhost:3000/demo`.
