# RideShield Pitch Deck Outline

Use this outline for the current repo state, not the older sprint markdown claims.

## 1. Problem

- Gig delivery workers lose income from:
  - rain
  - heat
  - AQI
  - traffic collapse
  - platform outage
  - civic disruption
- Traditional claims-based insurance is too slow and too manual for weekly income continuity

## 2. Product

- Weekly parametric income protection
- Zero-touch claim generation
- Incident-centric decisioning
- Automatic payout or bounded manual review

## 3. Persona Story

- legitimate worker: instant approval and payout
- suspicious worker: delayed or rejected
- borderline worker: routed to review queue with explanation

## 4. System Architecture

- worker onboarding and weekly policy purchase
- trigger engine and scheduler
- incident creation and extension
- hybrid fraud scoring with ML fallback
- decision engine and payout executor
- DB-backed geography and audit trail
- admin and worker explainability surfaces

## 5. Current ML Story

- risk model:
  - integrated with fallback
  - used for worker risk and premium metadata
- forecast engine:
  - integrated into analytics
  - exposed in admin and intelligence surfaces
- fraud ML:
  - integrated into runtime fraud scoring
  - blended with rule signals
  - surfaced in claim detail and admin review

Keep this section honest:
- model fallback is still part of the runtime design
- fraud calibration is still demo-grade rather than production-calibrated

## 6. Worker Surface Story

- active policy
- decision-first dashboard
- claim explanation
- payout history
- risk score and contributing factors

## 7. Admin Surface Story

- review queue
- next decision
- KPI overview
- live scheduler health
- disruption feed
- forecast horizon
- model status
- policy utility controls

## 8. Demo Story

- create demo worker
- run scenario
- show signals crossing thresholds
- show incident creation
- show claim decision
- show payout or review outcome

## 9. Business Viability

- weekly premium framing
- coverage caps
- loss ratio
- simulated but auditable operating model

## 10. What Is Real vs Simulated

### Real now
- decision pipeline
- scheduler
- claims and payouts
- admin and worker surfaces
- risk-model service
- fraud-model-assisted scoring
- forecast engine
- cookie-based session model

### Simulated now
- weather, AQI, traffic, and platform source feeds
- payout rail as sandbox/demo behavior
- telemetry realism and fraud-data realism

## 11. Next Technical Step

- improve fraud and risk calibration realism
- tighten secrets and operational hygiene
- expand frontend coverage on admin and demo surfaces
- improve structured runtime logging
