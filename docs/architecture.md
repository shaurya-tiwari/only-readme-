# RideShield Architecture Reference

The canonical architecture document currently lives at the repo root in [Architecture.md](../Architecture.md).

This file exists so the repository structure described in the README is present in the codebase during Sprint 3.

## Current implementation summary

- FastAPI backend with worker, policy, trigger, event, claim, payout, auth, and analytics routes
- PostgreSQL-backed event-centric claim flow
- Periodic trigger scheduler with configurable 5-minute interval
- React frontend with worker, admin, and demo surfaces
- Simulation helpers for repeatable demos and review flows
