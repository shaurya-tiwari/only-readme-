# RideShield Pitch Deck Outline

## 1. Problem

- Gig delivery workers lose income during rain, heat, AQI spikes, traffic collapse, platform outages, and civic disruption.
- Traditional insurance is too manual and too slow for income continuity.

## 2. Product

- Weekly parametric income protection.
- Zero-touch claims: the system detects, validates, decides, and pays.

## 3. Persona Story

- Rahul: legitimate disruption and instant payout.
- Vikram: suspicious attempt rejected.
- Arun: borderline case delayed and reviewed inside SLA.

## 4. Architecture

- Worker onboarding and weekly plan purchase.
- Trigger engine checking signals on a fixed schedule.
- Event-centric claim generation.
- Fraud detection, decision engine, payout executor, audit trail.

## 5. Dashboard Story

- Worker dashboard: active policy, grouped incidents, payouts, trust, explainability.
- Admin dashboard: queue, payout metrics, loss-ratio view, disruption heatmap, duplicate log, scheduler state.

## 6. Business Viability

- Weekly premiums
- Coverage caps
- Loss-ratio framing
- Simulation-first sandbox approach

## 7. Roadmap

- Sprint 1: backend foundation
- Sprint 2: trigger, fraud, decision, payout engine
- Sprint 3: product UI, auth/session, analytics, demo runner
- Sprint 4+: ML training artifacts, predictive models, deeper forecasting
