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

Phase 3 also needs to solve a structural problem:
- the system is already becoming smarter than its current organization
- intelligence must now be made more understandable, more layered, and easier to promote safely

That means the next upgrades are not only about APIs or better scoring. They are also about:
- graded uncertainty behavior instead of one review fallback
- scenario-level reasoning for clusters instead of one penalty bucket
- policy structure instead of growing conditional sprawl
- product translation that compresses meaning instead of exposing raw state

Important operating reality:
- a well-architected simulation can still starve if thresholds are realistic but signal inputs rarely cross them
- without enough event and claim traffic, memory, replay, and calibration become underfed
- Phase 3 therefore needs controlled stimulus, not only realistic baseline behavior

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

Why this matters operationally:
- today, many borderline claims in the `0.40-0.60` score range still go to manual review
- Wave 1 memory lets the system prove which of those were actually safe after human review
- once enough similar delayed-but-legit rows exist, later waves can safely carve out new zero-touch lanes instead of lowering thresholds blindly

Data discipline rule to add:
- store and tag memory rows by evidence quality:
  - `synthetic`
  - `seeded`
  - `manual_reviewed`
  - later `organic`
- calibration and promotion should trust `manual_reviewed` and `organic` evidence first
- synthetic or seeded rows are useful for iteration, replay, and edge-case coverage, but should not dominate promotion decisions

Concrete example:
- current claim:
  - final score `0.58`
  - payout `INR 86`
  - trust is decent
  - only weak flags such as `movement` and `pre_activity`
  - system decision = `delayed`
- later manual review result:
  - final label = `legit`
- after many similar examples are stored:
  - analytics can show that this weak-signal, low-payout pattern is mostly legitimate
  - policy and model calibration can safely move that pattern into a future zero-touch lane

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

Important interpretation rule:
- the first Wave 2 question is not "how many claims were reviewed?"
- it is "which reviewed patterns later turned out to be safe, and why did the system hesitate?"
- that is how manual-review volume gets reduced without weakening fraud controls

Additional operational rule:
- analytics should distinguish between:
  - real quiet periods
  - simulation starvation
  - deliberately injected scenario traffic
- otherwise the team may confuse "stable system" with "system received no meaningful work"

Additional decision-surface rule:
- stop reading the gray band as one scalar threshold problem
- future analytics should explain review concentration through:
  - score band
  - payout exposure
  - trust level
  - signal family
  - uncertainty case
  - cluster context

Policy-health additions:
- add rule-impact ranking so the system can identify:
  - top false-review contributors by rule
  - top replay-drag contributors by rule
  - top friction-causing surfaces
- add policy-health metrics such as:
  - friction score
  - automation efficiency
  - rule concentration
  - surface imbalance
- treat early analytics as provisional when evidence is still dominated by:
  - synthetic traffic
  - seeded scenarios
  - low sample size

Important interpretation guardrail:
- measurable rules will surface uncomfortable truths
- some rules that look correct and pass tests may still do bad operational work
- do not delete or relax them on first sight
- validate impact using:
  - sample size
  - replay lift/drag
  - evidence quality
  - scenario balance

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

Critical cluster upgrade:
- stop treating `cluster` as one signal
- model cluster as a possible scenario narrative
- begin decomposing cluster context into features such as:
  - `cluster_size`
  - `cluster_density`
  - `avg_trust_in_cluster`
  - `pre_activity_density`
  - `activity_variance`
  - `payout_mean`
  - `event_overlap_strength`
- classify clusters into types such as:
  - `shelter_cluster`
  - `fraud_ring`
  - `coincidence_cluster`
  - `mixed_cluster`
- route from `cluster_type -> decision_weight`, not `cluster -> panic`
- finish the purge of direct raw-cluster pressure from the main score path so cluster becomes context-first, not a second hidden source of truth

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

Graded uncertainty handling to add:
- uncertainty should not collapse into one action
- future routing should distinguish between:
  - low payout + low confidence -> safe micro auto-approve when evidence allows
  - high payout + low confidence -> review
  - contradiction -> review
  - missing critical data -> delay and retry
- uncertainty types such as `silent_conflict`, `core_contradiction`, and later data-quality cases should drive different behaviors, not only one queue

Operational uncertainty rule:
- each uncertainty case should resolve through one intended behavior path
- overlap should be treated as a policy-definition problem, not normal behavior

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

### P. Controlled Simulation Traffic And Scenario Injection

Phase 3 needs explicit stimulus modes so the policy engine does not sit idle waiting for rare threshold-crossing events.

Add:
- baseline mode:
  - realistic thresholds
  - low event frequency
  - sanity-check behavior
- simulation pressure mode:
  - forced or probabilistic trigger overrides
  - high-volume, diverse claim traffic
  - stress testing for policy, replay, and review routing
- scenario mode:
  - targeted cluster-heavy, gray-band, ambiguity, and fraud-ring cases
  - deterministic cause-and-effect evaluation
- replay amplification mode:
  - perturb stored decision-memory rows
  - generate structured synthetic variants for calibration exploration

Why this matters:
- no triggers -> no events -> no claims -> no decisions -> no learning
- realistic thresholds alone can leave the system architecturally strong but empirically starved
- the team needs controlled chaos, not only realistic calm

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

### M. Policy Architecture And Decision Layering

Phase 3 should not keep expanding as scattered special-case branches.

Add:
- a documented decision policy map with explicit layers:
  - Fraud Layer
  - Strong Approve Layer
  - Micro Payout Safe Lane
  - Ambiguity Resolver
  - Review Fallback
- each policy rule should belong to one layer only
- replay and explainability should report which layer resolved the claim
- future implementation should move toward a policy-driven rule structure instead of opaque conditional sprawl
- each resolved decision should eventually log:
  - `policy_layer`
  - `rule_id`
  - rule-specific rationale

Why this matters:
- it keeps decision growth understandable
- it makes rules more versionable and replay-friendly
- it reduces overlap and hidden contradiction across approval/review lanes
- it turns architecture from a documentation idea into an enforceable system contract

Important warning:
- Phase 3 currently has policy layers as a design direction, not yet as a fully enforced execution contract
- until code can answer "which layer decided this claim?", the architecture is still only partially realized

Next-stage governance work to add:
- define rule metadata as a maintained contract:
  - purpose
  - surface
  - risk expectation
- use policy metadata in analytics, not only logs
- identify which rules and surfaces create the most friction before changing thresholds
- prevent policy fragmentation by pruning or consolidating low-value micro-rules over time

### N. Product Translation And Trust Engineering

Phase 3 product work should not only hide internal complexity. It should compress meaning into clear user-facing narratives.

Worker-message rule:
- every worker message should answer:
  - what happened
  - what the system is doing
  - what happens next

Examples of the intended direction:
- not raw internal language like `cluster`, `uncertainty band`, or `noise overload`
- instead:
  - "Rain disrupted your work."
  - "We are confirming activity in your area."
  - "This usually completes within 2 hours."

Admin-message rule:
- admins should see the pattern, historical tendency, recommendation, and exposure
- they should not have to parse repeated raw signal spam to understand the case

### O. Promotion Unit Definition

Phase 3 promotion should be based on vertical slices, not backend-only advancement.

Define one promotion unit as:
- backend logic change
- replay impact report
- test coverage
- UI mapping
- product copy
- demo narrative

If one of these is missing, the slice is not ready for promotion into the deployed repo.

Promotion evidence rule to add:
- calibration promotion should require a minimum body of trustworthy review evidence
- suggested initial guardrail:
  - at least `30` `manual_reviewed` examples for the pattern being relaxed
  - false-review rate improves in replay
  - fraud leakage does not materially spike
- this evidence bar can become stricter as the system approaches deployed promotion

Additional governance rule:
- do not promote a change just because one rule or surface looks bad in early analytics
- require:
  - enough evidence quality
  - enough sample size
  - replay context
  - product translation readiness

### Q. Policy Health And Introspection

Phase 3 now needs explicit policy governance, not only decision governance.

Add:
- rule-impact ranking
- surface-level friction tracking
- rule concentration analysis
- surface imbalance detection
- replay drag and replay lift by rule and surface
- operator-safe summaries of which policy areas are causing unnecessary review

Why this matters:
- once rules are measurable, the team can stop tuning blindly
- policy health becomes the control system for future calibration

Important caution:
- measurable policy does not mean trustworthy policy by default
- early results can still be distorted by synthetic-heavy traffic or scenario imbalance
- policy health should guide investigation, not trigger instant rule deletion

## Suggested Execution Order

To keep Phase 3 coherent, execute it in this order:

1. Learning/data memory and observability backbone
2. Risk-wrapper explainability and uncertainty routing
3. Fraud hardening using stored feedback, not just synthetic assumptions
4. Worker/admin explainability, product translation, and product-surface completion
5. Real-provider integration in shadow-safe mode
6. Adaptive thresholds, graded uncertainty behavior, and confidence calibration improvements
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
