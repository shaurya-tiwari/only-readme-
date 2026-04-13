# Phase 3 Execution Plan

This document converts [Phase3_Roadmap.md](c:/Users/satvi/Desktop/RideShield_work/docs/Phase3_Roadmap.md) into a concrete execution plan.

The roadmap remains the source of truth for scope.

This plan defines:
- implementation order
- dependencies
- validation gates
- promotion workflow from the working repo into the deployed repo
- what to build first vs what to delay

## Objective

Complete Phase 3 without damaging the current Phase 2 system.

That means:
- keep the stable mock-based flow working
- add memory before retraining
- add observability before aggressive automation
- add real providers only after internal contracts are stable
- promote stable slices into the deployed repo instead of dragging the whole working repo forward

## Success Definition

Phase 3 is complete only when all of these are true:

- decision memory exists and stores feature snapshots, system decisions, final labels, and version metadata
- observability exists for drift, false reviews, zero-touch rate, queue pressure, and review-driver behavior
- explainability is deterministic enough to be trusted in product surfaces
- fraud and review logic use stored outcomes rather than only synthetic assumptions
- real provider integration exists behind safe source modes with snapshot persistence and shadow comparison
- worker, admin, and demo surfaces expose the new intelligence clearly
- the deployed repo receives only reviewed, stable slices
- docs, tests, and demo assets match what is actually implemented

## Working Model

Use the repos like this:

- working repo = build surface
- deployed repo = curated promotion surface

Rule:
- all Phase 3 work starts in the working repo
- nothing moves to the deployed repo until that slice is validated and documented

## Current Working-Repo Status

As of `2026-04-13`, the working repo has completed the core intent of Waves `0-5`, has meaningful Wave `5.5` governance and realism tooling, has started Wave `6` with real weather/AQI/traffic providers plus minimal shadow diff persistence, and has implemented a light Wave `7` operational credibility slice.

Current reality:
- working repo is the correct place for:
  - provider work
  - replay/calibration work
  - docs and design memory
  - operational polish before curated promotion
- deployed repo should still receive only narrow, validated slices
- backend is now at the point where further feature work should stay constrained; the next priorities are:
  - finish observation-only validation
  - finish docs
  - promote reviewed slices
  - continue demo/judge-facing cleanup
  - avoid reopening backend scope except for bug fixes, read-path hardening, and packaging

## Execution Principles

1. Do not start with real providers.
   - start with memory and observability

2. Do not start with automatic retraining.
   - Phase 3 learning is offline, controlled, and evaluated

3. Do not let unfinished provider paths become the default.
   - mock remains the safe baseline until promotion time

4. Do not let explainability become a vague marketing surface.
   - reasons must be deterministic and reproducible

5. Do not promote a mixed slice.
   - stable code, tests, docs, and product narrative move together

6. Do not treat uncertainty as one queue outcome.
   - uncertainty types should map to different behaviors based on payout, trust, contradiction, and data quality

7. Do not let policy logic grow as a jungle of unrelated branches.
   - every rule should belong to a documented policy layer

8. Do not leave core boundaries undefined.
   - payout, trust, and uncertainty guardrails must be explicit before calibration expands further

9. Do not assume realistic thresholds alone will generate enough data.
   - baseline calm is useful
   - but Phase 3 also needs controlled simulation traffic and scenario pressure

10. Do not overreact to early policy analytics.
   - measurable rules will expose friction quickly
   - but early findings can still be distorted by:
     - synthetic bias
     - low sample size
     - scenario imbalance
   - rule deletion or relaxation should follow impact ranking, not first-contact intuition
   - source comparison and contamination should be checked before any calibration conclusion is treated as truth
   - historical rows should be reannotated against the current policy before they are treated as structurally current evidence

11. Do not let realism research consume the demo plan.
   - simulation realism should improve until it is directionally trustworthy
   - but hackathon value still comes from:
     - clear product behavior
     - believable live signals
     - explainable zero-touch automation

## Execution Order

Phase 3 should be completed in the following order:

1. Wave 0: Program setup and guardrails
2. Wave 1: Decision memory and replay backbone
3. Wave 2: Observability and system-intelligence analytics
4. Wave 3: Risk-wrapper explainability and uncertainty routing
5. Wave 4: Fraud hardening from stored outcomes
6. Wave 5: Product-surface completion
7. Wave 5.5: Controlled simulation traffic and scenario injection
8. Wave 6: Real provider integration and snapshot pipeline
9. Wave 7: System adaptation and payout polish
10. Wave 8: Demo, judging assets, and promotion cleanup

## Wave 0: Program Setup And Guardrails

### Goal

Prepare the repos and constraints before adding new Phase 3 behavior.

### Deliverables

- confirm separate local test databases for working and deployed repos
- define feature-flag and source-mode conventions
- define promotion rules from working repo to deployed repo
- define decision logging schema before implementation starts
- define the policy map before deeper calibration expands
- define first hard guardrails for:
  - low payout
  - high payout
  - high trust
  - low confidence
- define naming/version rules:
  - `model_version`
  - `decision_policy_version`
  - `signal_snapshot_id`
  - `source_mode`

Policy map to define:
- Fraud Layer
- Strong Approve Layer
- Micro Payout Safe Lane
- Ambiguity Resolver
- Review Fallback

Policy execution contract to define:
- every decision should be traceable to:
  - `policy_layer`
  - `rule_id`
  - `decision_policy_version`

### Dependencies

- none

### Exit Criteria

- test isolation is stable
- feature-flag naming is documented
- promotion workflow is documented
- policy layers are documented
- first guardrail thresholds are documented
- no ambiguity remains about which repo is used for build vs promotion

### Promotion

- docs only if needed

## Wave 1: Decision Memory And Replay Backbone

### Goal

Create the system memory required for any meaningful learning.

### Deliverables

- `training_events` or `decision_log` table
- feature snapshot persistence at decision time
- stored automated decision vs final manual verdict
- payout amount, wait time, review reason, and final label capture
- model and decision-policy version capture
- raw replay/export utilities for retraining datasets

### Concrete Tasks

- add schema for decision memory
- log claim creation, auto-decision, manual resolution, and final outcome into one structured format
- freeze the exact feature vector and relevant signal references used at decision time
- add export scripts for training and evaluation datasets
- add replay harness for historical decision rows
- tag memory rows by evidence quality where possible:
  - `synthetic`
  - `seeded`
  - `manual_reviewed`
  - later `organic`

### Dependencies

- Wave 0 guardrails

### Exit Criteria

- every resolved claim can be reconstructed from stored memory
- automated decision and final label are separated cleanly
- replay/export works without recomputing live state
- tests cover:
  - logging on auto-approve
  - logging on auto-reject
  - logging on manual approve/reject
  - version metadata presence

### Promotion

- promote once schema, logging hooks, and tests are stable

### Why Wave 1 Comes Before Wave 2

Wave 1 exists so later policy improvement is evidence-based.

Example:
- a claim with:
  - final score around `0.58`
  - payout around `INR 86`
  - decent trust
  - only weak flags like `movement` and `pre_activity`
- may currently be delayed for review
- if the admin later approves it, Wave 1 preserves:
  - what the system saw
  - what the system decided
  - what the final human truth was

After many similar rows exist:
- Wave 2 can measure false-review-heavy patterns
- Wave 3 and Wave 4 can safely convert those patterns into better zero-touch routing

Without Wave 1:
- the team would only see a live delayed queue
- not the evidence needed to reduce manual review safely

## Wave 2: Observability And System-Intelligence Analytics

### Goal

Make the system capable of measuring its own behavior before changing policy aggressively.

### Deliverables

- drift metrics
- false review rate
- zero-touch rate
- auto-approval rate
- route-level counts for approve/delay/reject/manual override
- review-driver distribution
- queue pressure metrics
- duplicate and cluster metrics
- version-aware admin analytics

### Concrete Tasks

- add backend analytics queries for the new metrics
- surface admin-facing summaries for:
  - top review drivers
  - weak-signal overlap share
  - low-trust share
  - review exposure
- expose model/policy version in analytics payloads
- extend system-health and intelligence endpoints
- add pattern reports that explain the gray zone through:
  - score band
  - payout band
  - trust band
  - signal family
  - uncertainty case
  - cluster context
- add policy-health reporting for:
  - top friction-causing rules
  - top friction-causing surfaces
  - rule concentration
  - surface imbalance
  - replay lift and drag by surface

Wave 2 should explicitly answer:
- which delayed claims were later approved anyway
- which weak-signal combinations are causing unnecessary review
- which score bands are safe enough to narrow over time
- which policy rules are doing the most bad operational work despite looking correct in code

### Dependencies

- Wave 1 decision memory

### Exit Criteria

- last-hour and long-window analytics both work
- empty recent windows degrade gracefully to useful fallback summaries
- metrics are available in APIs and not only logs
- tests cover analytics aggregation correctness

### Promotion

- promote once analytics outputs are reliable and product-visible

## Wave 3: Risk-Wrapper Explainability And Uncertainty Routing

### Goal

Make risk and ambiguity handling deterministic, interpretable, and tunable.

### Deliverables

- deterministic explainability for risk outputs
- normalized contribution logic
- bounded top-reason output
- configurable uncertainty thresholds
- asymmetric ambiguity routing for borderline cases
- hard fraud override behavior
- graded uncertainty behavior instead of one generic review fallback
- explicit low/high guardrails for payout, trust, and confidence

### Concrete Tasks

- implement risk-wrapper reasoning layer
- define stable human-readable reason templates
- extract threshold config into central settings
- update decision engine to route ambiguous cases intentionally
- map uncertainty types to different actions, for example:
  - low payout + low confidence -> possible safe micro-lane
  - high payout + low confidence -> review
  - contradiction -> review
  - missing critical data -> delay/retry
- document and implement first explicit boundaries such as:
  - `LOW_PAYOUT_THRESHOLD`
  - `HIGH_PAYOUT_THRESHOLD`
  - `HIGH_TRUST_THRESHOLD`
  - `LOW_CONFIDENCE_THRESHOLD`
- add edge-case suite:
  - core contradiction
  - too-perfect state
  - noise overload
  - silent conflict

### Dependencies

- Wave 1 memory
- Wave 2 observability

### Exit Criteria

- the same inputs produce the same reasons every time
- ambiguous cases route consistently
- reasons stay concise and mathematically coherent
- key payout, trust, and confidence boundaries are explicit in config rather than implied in code
- tests cover threshold bands and contradiction handling

### Promotion

- promote after edge-case tests and UI consumption are stable

## Wave 4: Fraud Hardening From Stored Outcomes

### Goal

Improve fraud handling using resolved outcomes instead of synthetic intuition alone.

### Deliverables

- stronger feature engineering from stored decisions
- weak-vs-strong signal taxonomy
- payout-weighted risk routing
- improved cluster-ring learning
- calibration studies from review outcomes
- trust-evolution logic measured against truth
- cluster scenario decomposition instead of one cluster penalty
- removal of direct raw-cluster penalty thinking from the main routing model
- gray-band decomposition into multiple policy surfaces

### Concrete Tasks

- analyze stored review outcomes to identify false reviews and false rejects
- formalize weak vs strong indicators in code and docs
- revise scoring so weak signals do not stack into panic
- introduce payout-aware review routing for borderline claims
- split cluster reasoning into scenario semantics such as:
  - shelter cluster
  - fraud ring
  - coincidence cluster
  - mixed cluster
- decompose cluster context with features such as:
  - `cluster_size`
  - `cluster_density`
  - `avg_trust_in_cluster`
  - `pre_activity_density`
  - `activity_variance`
  - `payout_mean`
- replace direct cluster penalties with cluster-type evaluation where feasible:
  - classify cluster context first
  - then route based on cluster meaning
- split the `0.60-0.65` band into explicit sub-surfaces such as:
  - low-payout legit
  - mid-trust ambiguity
  - early fraud suspicion
  - cluster-sensitive gray routing
- compare pre- and post-change review rate and fraud catch rate
- finish the cluster transition so:
  - cluster affects routing only
  - cluster does not quietly influence score again

### Dependencies

- Wave 1 memory
- Wave 2 observability
- Wave 3 deterministic uncertainty routing

### Exit Criteria

- weak indicators no longer over-penalize clean claims
- payout-aware logic reduces unnecessary review volume
- calibration changes are measured against stored outcomes
- cluster behavior is explainable through cluster type, not only a raw penalty
- gray-band behavior is explainable through named sub-surfaces, not one pooled rule
- tests cover:
  - low-payout borderline approval
  - high-payout borderline review
  - weak-signal-only behavior
  - strong-signal escalation

### Promotion

- promote only if metrics show improved automation without unacceptable fraud drift

## Wave 5: Product-Surface Completion

### Goal

Expose the system’s intelligence clearly in worker, admin, and demo surfaces.

### Deliverables

- richer admin queue ergonomics
- loss ratio and fraud-distribution views
- duplicate and cluster views
- system health panel
- trust profile detail
- claim explainability detail
- notification feed
- audit trail visibility
- predictive pricing surface
- scenario timeline and cause-effect storytelling
- product-copy translation layer for worker and admin narratives
- policy-health summaries for admins:
  - friction score
  - automation efficiency
  - rule concentration
  - surface imbalance
- translated rule/surface friction summaries that avoid exposing raw engine IDs directly

### Concrete Tasks

- extend admin panel tabs and explainability surfaces
- extend worker dashboard trust, claim, audit, and pricing surfaces
- add demo runner timeline and system-health framing
- add realistic demo history generation for judging demos
- add scripted full-demo runner for repeatable flows
- make worker messages answer:
  - what happened
  - what the system is doing
  - what happens next
- compress admin explanations into:
  - pattern
  - recommendation
  - historical tendency
  - exposure
  instead of repeated signal spam
- translate rule and surface analytics for admins instead of exposing raw `rule_id` or engine-native labels directly
- keep raw policy metadata available for audit and debug surfaces only

### Dependencies

- Wave 2 analytics
- Wave 3 explainability outputs
- Wave 4 refined policy behavior

### Exit Criteria

- UI exposes the new signals without turning into unreadable clutter
- worker and admin surfaces both show consistent explanations
- worker copy contains no raw engine terminology that teaches the fraud model
- scenario runner clearly shows signal -> incident -> claim -> payout path
- product tests cover new critical UI paths
- admin policy-health surfaces explain friction in translated language, not raw registry jargon

### Promotion

- promote when the product story is coherent and demo-safe

## Wave 5.5: Controlled Simulation Traffic And Scenario Injection

### Goal

Keep the Phase 3 engine fed with enough diverse traffic to make replay, calibration, and cluster behavior meaningful.

### Deliverables

- baseline mode for realistic calm
- simulation pressure mode for high-volume traffic
- deterministic scenario mode for targeted pattern testing
- replay amplification mode for structured perturbation of stored cases
- mode visibility in analytics and demo tooling
- evidence-mix visibility in admin/intelligence surfaces so simulated traffic cannot be mistaken for baseline traffic
- named pressure profiles that shape scenario mix intentionally instead of using raw random pressure
- historical reannotation so older memory can be compared against the current policy without overwriting the original record

### Concrete Tasks

- add a dev-only trigger override or force-trigger probability path
- add scenario injection presets for:
  - gray-band cases
  - weak-signal overlap
  - cluster-heavy patterns
  - emerging fraud signals
- add replay amplification helpers that perturb payout, trust, and confidence safely
- expose the current simulation mode in admin/intelligence analytics
- ensure stored decision memory can distinguish:
  - natural baseline
  - forced simulation traffic
  - scenario-injected traffic
  - replay-amplified traffic
- add named pressure profiles such as:
  - `balanced_pressure`
  - `gray_band_heavy`
  - `fraud_pressure`
  - `clean_baseline`
- add source-comparison analytics for:
  - false-review rate by source
  - rule frequency by source
  - surface behavior by source
- add baseline-truth mode contract for calibration and promotion decisions
- add a governed experiment runner that mixes:
  - anchor rows
  - bounded replay amplification
  - scenario injection
- add experiment distribution governance for:
  - payout mix
  - trust mix
  - cluster-type mix
  - uncertainty-case mix
- move distribution shaping from passive measurement to guided sampling:
  - bias toward underfilled buckets
  - reject or penalize oversampled buckets
  - treat `max_gap <= 0.10` as the minimum realism bar before broad experiments are trusted
- treat cluster and uncertainty as relational targets, not simple labels:
  - generate correlated signal structures
  - let cluster type and uncertainty case emerge from the engine where possible
- add difficulty profiles so synthetic traffic does not become unrealistically easy:
  - easy
  - borderline
  - adversarial
- add baseline-comparison gates:
  - friction delta
  - automation delta
  - false auto-approval delta
- add source-alignment gating for:
  - outcome distribution
  - rule distribution
  - surface distribution
  - difficulty distribution
- add an executable promotion contract that blocks policy change unless all are true:
  - distribution realism passes
  - baseline comparison improves safely
  - fraud-risk delta stays within limit
  - sample size is sufficient
  - multi-source consistency holds
- add replay-gated safe backfill tooling for low-risk delayed claims

### Dependencies

- Wave 1 memory
- Wave 2 observability
- Wave 4 calibration work
- Wave 5 product surfaces if mode visibility is shown in UI

### Exit Criteria

- the team can generate meaningful decision traffic without waiting for rare natural triggers
- simulation pressure does not silently contaminate calm-baseline interpretation
- scenario mode can target gray-band and cluster behavior directly
- analytics can separate quiet baseline from forced traffic
- UI surfaces make the evidence mix visible enough that policy decisions are not made blindly from blended traffic
- source contamination is measurable, not guessed
- trusted baseline sources can be isolated when promotion or calibration decisions require cleaner evidence
- historical decision memory can be version-compared against the current policy before reuse in larger experiments
- gray-band behavior is split into explicit districts before broader stress experiments are trusted
- experiment reports can block themselves when realism or promotion-contract checks fail
- source behavior must stay close enough to baseline before broad synthetic runs are treated as credible
- demo-facing work should resume once realism becomes directionally trustworthy rather than waiting for perfect simulation

### Promotion

- keep this in the working repo until the stimulus modes are clearly isolated and safe

## Wave 6: Real Provider Integration And Snapshot Pipeline

### Goal

Replace the mock-only signal layer with a safe real-provider architecture.

### Deliverables

- provider abstraction
- normalizers
- snapshot persistence
- quality/confidence metadata
- shadow-mode comparison
- persisted provider diffs
- DB-backed platform telemetry path
- source-mode reporting in admin/intelligence surfaces

### Concrete Tasks

- wrap the current mock layer behind provider interfaces first
- add snapshot storage and retention behavior
- implement weather, AQI, and traffic real clients
- keep platform source DB-backed before partner integrations exist
- add shadow-mode comparison and diff persistence
- expose source mode and freshness in product surfaces

### Dependencies

- Wave 1 memory
- Wave 2 observability
- product readiness from Wave 5
- simulation safety understanding from Wave 5.5 if provider testing depends on scenario pressure

### Exit Criteria

- mock remains the safe default path
- snapshots persist canonical normalized signals
- shadow diffing works and is queryable
- real providers do not bypass the existing claim flow
- provider outages degrade safely

### Promotion

- promote only after shadow-mode validation is trustworthy

### Current Working-Repo Status

Implemented in the working repo:
- real weather provider
- real AQI provider
- real traffic provider
- behavioral platform telemetry provider behind `PLATFORM_SOURCE=db`
- safe fallback behavior for all three
- provider source/freshness visibility in health and product-facing surfaces
- minimal shadow diff persistence for live weather/AQI/traffic comparisons
- TomTom live traffic validation now works with an accepted API key
- scheduler interval protection now clamps upward in real-traffic mode to stay under the daily traffic budget
 - health/config decomposition now exists so hot frontend surfaces use:
   - `/config/runtime`
   - `/health/signals`
   - `/health/diagnostics`
 - legacy `/health/config` remains compatibility-only with timing breakdowns

Not yet finished:
- richer shadow diff trend/reporting surfaces
- deeper provider comparison governance outside the current persistence/query layer

## Wave 7: System Adaptation And Payout Polish

### Goal

Make the system behave better under operational pressure and improve payout realism.

### Deliverables

- queue-pressure-aware review sensitivity
- stronger confidence calibration
- safer automation bands
- contradiction handling under mixed signals
- richer mock payout lifecycle
- retry/failure/reversal visibility
- better payout notifications

### Concrete Tasks

- implement adaptive thresholding under queue pressure
- add automation confidence bands to decision outputs
- refine payout timeline states and transaction visibility
- expand audit and notification surfaces for payout behavior

### Dependencies

- Wave 2 analytics
- Wave 3 uncertainty routing
- Wave 4 calibration work
- Wave 6 provider/snapshot pipeline if adaptation depends on live data quality

### Exit Criteria

- queue pressure changes are measurable and bounded
- automation bands are understandable to operators
- payout flow feels complete without pretending to be production money movement
- regression tests cover queue-pressure behavior and payout-state transitions

### Promotion

- promote only after adaptation proves beneficial in metrics, not just intuition

### Current Working-Repo Status

Implemented as a deliberate light slice:
- payout lifecycle states:
  - `processing`
  - `completed`
  - `failed`
- failure-safe payout behavior
- operator-facing confidence bands
- review high-load mode visibility
- deterministic demo scenario wiring for:
  - `clean_legit`
  - `borderline_review`
  - `suspicious_activity`
 - deterministic DemoRunner split from exploratory Scenario Lab
 - Scenario Lab now supports:
   - city + zone selection
   - composed signal inputs
   - seeded worker-profile modes
   - single-run and batch-run execution
   - local preset save/load

Not yet implemented:
- deeper queue-pressure policy adaptation
- payout retry/reversal orchestration
- richer notification depth
- full operational adaptation loops

## Wave 8: Demo, Judging Assets, And Promotion Cleanup

### Goal

Package the finished Phase 3 system into a believable, polished submission state.

### Deliverables

- populated demo history
- scripted full demo flow
- 5-minute demo script
- final pitch deck PDF
- final README/doc cleanup
- promotion-ready deployed repo branch

### Concrete Tasks

- freeze demo scenarios and recording order
- generate stable seeded history for dashboards
- record the 5-minute demo against a repeatable script
- finalize pitch deck with:
  - persona
  - zero-touch system
  - fraud-aware architecture
  - pricing viability
  - explainability
  - roadmap
- run final docs pass across README, DevNotes, roadmap, and guides

### Dependencies

- all prior waves at promotion-ready quality

### Exit Criteria

- demo can be replayed consistently
- judging assets reflect actual implemented behavior
- deployed repo contains only stable, validated Phase 3 slices

### Promotion

- final promotion wave into deployed repo

## Validation Gates

Every wave should pass these gates before promotion:

### Engineering Gate

- backend tests green
- frontend tests green
- frontend build green
- no hidden placeholder path presented as complete
- replay results attached when the slice changes routing behavior
- policy analytics interpreted against evidence quality, not raw counts alone
- experiment-driven routing changes must show:
  - distribution realism
  - baseline comparison
  - gate outcome
  - executable promotion-contract outcome

Current note:
- focused provider/shadow regressions are green after the latest Wave 6 slice
- deterministic demo scenario regressions are green
- health endpoint split regressions are green
- the next hard checkpoint is a fresh full backend suite after the latest demo/scheduler slices

### Product Gate

- feature is visible and understandable in UI where relevant
- admin and worker explanations match backend truth
- demo flow remains coherent
- worker messages answer what happened, what the system is doing, and what happens next

### Documentation Gate

- docs updated in the working repo
- docs promoted with the code slice
- no future work described as already shipped

### Promotion Gate

- stable slice isolated
- no unrelated ML artifacts or scratch files mixed in
- deployed repo reverified after promotion
- routing-changing slices include replay evidence with a defined evidence bar
- rule or surface changes are not promoted on low-sample or synthetic-heavy evidence alone
- if governance gates pass but distribution realism fails, the slice still stays in the working repo

## Repo Promotion Workflow

Use this workflow for every Phase 3 slice:

1. Build in the working repo.
2. Validate in the working repo.
3. Update docs in the working repo.
4. Create a clean promotion branch or commit set for that slice only.
5. Rebase or cherry-pick into the deployed repo.
6. Re-run verification in the deployed repo.
7. Push only after the deployed repo is coherent on its own.

Promotion unit rule:
- a promotable slice is all-or-nothing:
  - backend logic change
  - replay report
  - tests
  - UI mapping
  - product copy
  - demo narrative

If one part is missing, the slice stays in the working repo.

Calibration evidence threshold:
- do not promote a new calibration lane on vibes
- minimum suggested baseline:
  - at least `30` `manual_reviewed` examples for the relaxed pattern
  - false-review rate improves under replay
  - false auto-approval risk does not materially spike

Preferred rule:
- rebase if the slice is clean and histories align
- cherry-pick if the slice is narrow but the working repo branch carries unrelated noise

## What To Do First

If Phase 3 starts today, begin with this order:

1. define the decision-memory schema and event logging contract
2. implement the decision-log / training-events table
3. log auto-decisions and manual resolutions with version metadata
4. add export and replay tools
5. build analytics for review drivers, zero-touch rate, false review rate, and queue pressure
6. only then move into risk-wrapper explainability and uncertainty routing

Do not start with:
- real providers
- automatic retraining
- payout polish
- demo-video work

Those are later waves.

## Phase 3 Non-Negotiables

Do not break these while executing the plan:

- event-centric claims
- multi-signal validation before financial action
- audit trail for important decisions
- fail-safe review over unsupported hard rejection
- DB-backed geography as the location truth source
- stable mock-based baseline until each new slice is proven

## Final Note

The roadmap is the scope.

This execution plan is the order of operations.

If the sequence is followed, Phase 3 can grow the system without turning the repo into a pile of half-integrated features.
