# RideShield Dev Notes

This file is the concise implementation note for the frozen Phase 2 repo.

## Phase 2 Baseline

- Mock disruption inputs drive the demo.
- The runtime claim flow inside the app is real:
  - scheduler monitoring
  - incident creation and extension
  - claim generation
  - fraud scoring
  - decision routing
  - payout execution
  - admin review

## Key Architecture Decisions

- Keep the signal layer isolated from claims logic so provider changes do not require a claims rewrite later.
- Treat incidents, not individual trigger fires, as the payout unit.
- Use DB-backed geography, with `zone_id` as the internal source of truth.
- Keep the demo runner on the same decision path as the scheduler by changing inputs, not bypassing decisions.

## Signal Pipeline

1. Mock weather, AQI, traffic, platform, or civic conditions cross thresholds.
2. The trigger engine creates or extends a zone incident.
3. Eligible workers are filtered by policy and location.
4. The decision engine evaluates disruption context, fraud score, trust score, confidence, and payout exposure.
5. The system approves, delays, or rejects the claim.
6. Approved claims move through payout execution.

## Decision Logic

- The system is incident-centric to avoid duplicate same-window payouts.
- Decisioning is not rules-only and not self-learning.
- Approval behavior combines disruption evidence, worker trust, fraud signals, confidence, and payout-aware logic.

## Weak Vs Strong Signals

- Weak indicators such as limited pre-event activity, low event confidence, or a minor movement anomaly should not reject a claim by themselves.
- Mixed or stronger suspicious patterns are what justify review or rejection.

## Zero-Touch Design

- Workers do not file claims manually.
- Clean claims should pass through the automatic lane.
- Manual review is a bounded lane for ambiguity, not the default operating mode.

## Phase Boundary

- Phase 2 claims only the stable mock-based product.
- Real providers, learning pipelines, and production payout rails belong in Phase 3.
