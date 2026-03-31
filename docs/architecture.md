# RideShield Architecture Reference

The canonical architecture document currently lives at the repo root in [Architecture.md](../Architecture.md).

This file exists so the repository structure described in the README is present in the codebase during Sprint 3.

## Current implementation summary

- FastAPI backend with worker, policy, trigger, event, claim, payout, auth, and analytics routes
- PostgreSQL-backed event-centric claim flow
- Periodic trigger scheduler with configurable 5-minute interval
- React frontend with worker, admin, and demo surfaces
- Additional public explanation surfaces for policy and intelligence
- Simulation helpers for repeatable demos and review flows

## Geography foundation

The current repo has moved beyond purely hardcoded geography.

Current architecture shape:
- cities and zones are bootstrapped into the database
- zone threshold profiles and zone risk profiles are data-backed
- worker, event, and activity flows can resolve zones through DB records
- scheduler reads active DB geography first, with config fallback during bootstrap

Design rule:
- `zone_id` is the backend source of truth
- legacy `city` and `zone` strings remain as compatibility/display fields during transition

Current supported geography:
- Delhi
- Mumbai
- Bengaluru
- Chennai

This is intentionally a minimal structured base for later Sprint 4 and Sprint 5 work. It is not yet a full GIS or nationwide rollout system.

## Frontend Surface Notes

Current frontend architecture now includes:
- a protected authenticated shell
  - sidebar
  - utility header
  - mobile bottom navigation
- page-level separation between:
  - worker dashboard
  - admin operations
  - demo runner
  - how-it-works explanation
  - intelligence overview

Current design rule:
- use the Stitch references as layout and tone guidance
- keep RideShield product behavior and copy as the source of truth
- prefer structured React components over raw Stitch HTML translation

## Runtime Observability

Current repo also includes local runtime text logging for review sessions:
- `logs/runtime/app_runtime.txt`
- `logs/runtime/trigger_cycles.txt`

These logs are intended for local diagnosis of:
- scheduler cadence
- trigger cycles
- incident creation and extension
- claim generation
- payout movement
