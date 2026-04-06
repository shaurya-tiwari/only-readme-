# Phase 3 Roadmap

This document lists work that is intentionally out of scope for the current Phase 2 submission.

Phase 2 stays focused on the stable mock-based product:
- mock disruption inputs
- real incident and claim orchestration inside the app
- fraud-aware review flow
- admin explainability for demo and operator use

Everything below is future work.

## Executive Philosophy For Phase 3

Phase 3 should turn RideShield from a strong mock-driven demo system into a feedback-driven, better-instrumented operating system for income protection.

The upgrade loop should be:

`prediction -> decision -> human feedback -> stored -> retrain -> evaluate -> deploy`

Better models should come from better system memory, cleaner measurement, stronger explainability, and safer promotion rules, not from random threshold tweaking.

## Tier 1: Core Intelligence Backbone (Must Do)

Tier 1 establishes the closed feedback loop required for any meaningful model improvement.

### B. Learning And Data Pipeline

Phase 3 should add structured memory for decisions and outcomes. This is the foundation of the ML upgrade loop: learning from messy, real-world decisions rather than synthetic comfort zones.

Planned areas:
- a `training_events` or decision-log table
- storing the feature snapshot precisely as seen at decision time
- capturing the automated system decision against the final human admin verdict (ground truth)
- data validation and anomaly filtering before retraining
- offline supervised retraining workflows rather than automatic self-learning
- evaluation and comparison before any model deployment

Additional work to add:
- store `model_version`, `decision_policy_version`, and relevant signal snapshot references with each logged decision
- store the final claim outcome separately from the original automated routing decision
- capture manual review reasons, resolution latency, payout amount, and whether the case was ultimately legit or fraudulent
- preserve frozen feature snapshots so later retraining does not depend on recomputed or mutated context
- create replayable training datasets from resolved claims rather than rebuilding training rows from current state
- add data-quality checks for missing features, contradictory labels, and stale context before any retraining step

### F. Observability And Analytics Expansion

Phase 3 should improve how the system measures its own behavior, ensuring it is auditable instead of flying blind post-deployment.

Planned areas:
- model and rule drift detection (is distribution changing over time?)
- false review rate tracking (are we over-sending legitimate claims to the admin queue?)
- stronger zero-touch and auto-approval tracking (are auto-approvals legitimately safe?)
- better long-window operational summaries
- richer admin analytics for queue behavior and decision quality

Additional work to add:
- review-driver distribution by hour, day, city, and zone
- queue-pressure tracking with SLA breach visibility and oldest-incident age
- duplicate-prevention and claim-extension analytics as explicit system health metrics
- cluster-alert frequency and repeat-offender visibility over time
- route-level metrics for approve, delay, reject, and manual-override rates
- model and policy version visibility in admin analytics so results can be tied to the exact active logic
- operator-facing summaries such as:
  - top review drivers
  - weak-signal overlap share
  - low-trust share
  - payout exposure currently held in review
- health rollups for demo and operator views, not only backend logs

## Tier 2: Real-World Hardening (High Value)

### C. Advanced Fraud Detection

Phase 3 should move beyond the current hybrid baseline. Fraud models break if engineered blindly; they must learn from real operational patterns.

Planned areas:
- stronger feature engineering based on real usage patterns
- fraud-pattern learning from real operating data (repeated location anomalies, timing inconsistencies)
- better separation of weak and strong suspicious signals
- threshold calibration based on review outcomes

Additional work to add:
- a formal weak-vs-strong signal taxonomy so mild indicators do not stack into accidental panic
- payout-weighted fraud routing so low-value borderline claims are not treated like high-value suspicious ones
- stronger cluster-ring learning using real duplicate, co-location, and timing abuse history
- calibration studies around false reviews, false rejects, and trusted-worker friction
- trust-evolution logic that is measured against outcomes instead of manually assumed to be correct
- confidence-aware fraud review bands so the system routes ambiguity intentionally rather than over-delaying by default

### A. Real Provider Integration

Phase 3 should replace the mock signal layer with real external providers. Improved input fidelity directly improves model reliability.

Planned areas:
- live weather APIs (OpenWeather)
- live AQI APIs (WAQI)
- live traffic APIs (TomTom)
- replacing mock providers without rewriting the claim flow
- provider rate limiting
- fallback behavior gracefully degrading when providers are unavailable
- stale-data handling and freshness rules

Additional work to add:
- explicit provider abstraction with provider client, normalizer, snapshot writer, and aggregator separation
- persisted signal snapshots so forecasting, explainability, and replay do not depend on the latest network call only
- shadow-mode comparison between mock and real provider outputs before cutover
- diff persistence for provider disagreement, not just logs
- confidence and quality metadata attached to normalized signals
- DB-backed platform telemetry first, before any true partner ingestion exists
- structured replay tests using stored raw payloads to debug threshold and incident behavior
- explicit source-mode reporting in admin and intelligence views:
  - mock
  - shadow
  - real
  - fallback

## Tier 3: System Adaptation And Polish

### D. System Adaptation

Phase 3 should make the system better at adapting to operating pressure. Moving from static logic to adaptive systems.

Planned areas:
- dynamic thresholds based on queue pressure (tensing uncertainty bands if SLAs breach)
- stronger confidence calibration routing uncertain cases to admin queues
- better use of review feedback to reduce unnecessary delays
- safer automation bands for approve, review, and reject behavior

Additional work to add:
- asymmetric uncertainty bands for the densest gray-area decisions, especially around risk and confidence
- deterministic explainability for risk outputs instead of opaque raw scores
- configurable threshold extraction in `backend/config.py` so uncertainty routing is tunable without editing core logic
- explicit automation confidence bands for:
  - safe auto-approve
  - uncertain review
  - risky reject
- queue-pressure response that changes review sensitivity safely rather than letting backlog compound blindly
- stronger contradiction handling for cases where signals disagree sharply
- preserving zero-touch automation for clear claims while pushing only true ambiguity into review

### E. Payout Integration (Simulated)

Phase 3 should make payout handling feel more product-complete while still staying safe for demo use.

Planned areas:
- mock payment gateway integration
- clearer instant payout flow
- richer payout status tracking
- improved payout notifications and audit visibility

Additional work to add:
- wallet-credit and UPI-style simulated payout paths aligned to plan-level behavior
- payout retry, failure, and reversal visibility in the payout timeline
- better worker-facing payout notifications and payout-history explainability
- stronger transaction trail visibility in audit and admin views
- payout-state surfaces that are demo-safe but look operationally believable

## Additional Phase 3 Work Missing From The Current Base Plan

The following items are also justified by the later sprint plans, the root architecture plan, the root README, and the V2 wrapper plan. They should be part of Phase 3 even though they were not called out explicitly in the first roadmap draft.

### G. Risk Model Wrapper, Explainability, And Uncertainty Routing

The V2 wrapper plan should be absorbed into Phase 3 as a concrete execution track.

Add:
- deterministic, human-readable risk explainability instead of unstable model-internal noise
- normalized reason contribution logic so top reasons stay mathematically coherent
- configurable uncertainty thresholds for risk and confidence
- hard fraud overrides so obvious fraud bypasses ambiguity bands
- explicit ambiguity routing for borderline risk ranges under low confidence
- strict cap on the number of reasons surfaced to keep dashboards readable

Why this matters:
- it makes the model understandable
- it makes review routing predictable
- it reduces blind dependence on raw model outputs

### H. Worker And Admin Product Surface Completion

Phase 3 is not only backend intelligence. The product surfaces also need the missing visibility layers from the later sprint plans.

Add on the admin side:
- richer review queue ergonomics
- loss ratio analytics
- fraud distribution and top-flag panels
- disruption heat view / zone risk surfaces
- forecast panels
- duplicate-claim log
- cluster-alert view
- system health summary
- queue pressure and review-driver insight modules

Add on the worker side:
- trust profile detail
- claim explainability breakdown
- notification feed
- audit trail visibility
- predictive pricing / next-week premium projection
- mini signal dashboard for transparency

Why this matters:
- the product should show what the system knows
- explainability should live in the UI, not only in backend logs

### I. Demo Runner And Scenario Storytelling

The root architecture and later sprint docs make it clear that the scenario system is part of the Phase 3 story, not just a dev convenience.

Add:
- timeline visualization for scenario execution
- clearer cause-and-effect storytelling from signal change to claim outcome
- quick path from scenario results into worker and admin surfaces
- demo system health visibility
- stronger city-aware scenario support
- realistic demo history population so dashboards are not empty during judged demos
- scripted full-demo runner for repeatable recordings and rehearsals

Why this matters:
- Phase 3 judging depends on explaining the system, not just running it

### J. Testing And Validation Expansion

The current roadmap mentions evaluation, but it should be more explicit about testing scope.

Add:
- destructive edge-case tests for contradiction and ambiguity routing
- regression tests for uncertainty bands and confidence logic
- scenario replay tests for legitimate, fraudulent, and ambiguous cases
- provider contract tests once real integrations start
- replay harnesses for stored raw payloads and stored decision events
- end-to-end demo-flow tests covering:
  - onboarding
  - scenario trigger
  - claim creation
  - review routing
  - payout visibility

Suggested edge-case suite from the wrapper plan:
- the core contradiction
- the too-perfect state
- noise overload
- silent conflict

### K. Judging Assets And Submission Polish

The root architecture plan and README both make Phase 3 responsible for more than engineering.

Add:
- 5-minute demo video planning and scripted capture
- final pitch deck PDF with:
  - persona
  - zero-touch flow
  - fraud-aware architecture
  - pricing viability
  - explainability
  - roadmap
- realistic demo data generation so recorded flows are populated and stable
- a polished README and docs pass at the end of Phase 3 so the story matches the built system

Why this matters:
- Phase 3 is the submission and storytelling layer, not just the engineering layer

### L. Architecture Guardrails To Preserve During Phase 3

The root architecture plan contains several rules that should be preserved as non-negotiable while Phase 3 expands the system.

Keep these guardrails:
- event-centric claims, not trigger-centric payout multiplication
- multi-signal validation before financial action
- fail-safe review rather than unsupported hard rejection
- auditability for every important decision
- stateless backend behavior with database-backed truth
- geography and zone logic staying tied to the DB-backed location layer

These are not optional polish items. They are the stability rules that keep Phase 3 from weakening the Phase 2 core.

## Suggested Execution Order

To keep Phase 3 coherent, execute it in this order:

1. Learning/data memory and observability backbone
2. Risk-wrapper explainability and uncertainty routing
3. Fraud hardening using stored feedback, not just synthetic assumptions
4. Worker/admin explainability and product-surface completion
5. Real-provider integration in shadow-safe mode
6. Adaptive thresholds and confidence calibration improvements
7. Simulated payout-flow polish
8. Demo-history generation, full demo runner, 5-minute video, and pitch deck

## Repo Workflow For Phase 3

Phase 3 should be built in the working repo first.

Recommended repo model:
- working repo = build surface
- deployed repo = curated promotion surface

Process:
1. Build and validate each Phase 3 slice in the working repo.
2. Keep new paths behind safe defaults so the stable mock-based flow stays intact.
3. Update docs and tests in the working repo as each slice stabilizes.
4. Promote only reviewed, stable slices into the deployed repo.
5. Re-run verification and live sanity checks in the deployed repo before any push.

Important notes:
- do not move half-done provider work into the deployed repo
- do not move raw ML experiment artifacts into the deployed repo
- do not claim learning or real-provider capability before the supporting system memory and evaluation loop actually exist

## Phase 3 Guiding Rule

Phase 3 should expand the system carefully:
- keep the current stable Phase 2 flow intact
- build the systemic feedback constraints that logically justify every ML upgrade
- evaluate new behavior in controlled conditions before deployment
- avoid presenting future architecture as already implemented
