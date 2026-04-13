# Phase 3 Progress Report: Waves 0-5 Plus Realism Passes

Date: 2026-04-07

This report replaces the fragmented wave notes for Waves 0 through 5 and now includes the post-Wave-5 enforcement passes, the first Wave 5.5 implementation slice, the policy-health/admin-translation follow-up, the pressure-profile/source-comparison follow-up, the large-experiment governance tooling, the explicit gray-band district split, and the first micro-world realism passes.

It captures:
- what was completed in the working repo
- what changed in the system
- what evidence now exists for later calibration
- what still remains open before promotion to the deployed repo

## Scope

This report covers the working repo only.

Nothing in this report implies promotion into the deployed repo unless stated separately.

## System Overview

RideShield is now beyond threshold-only claim routing.

The working repo currently contains:
- a policy-layered decision engine
- decision memory and replay
- policy analytics and promotion governance
- controlled synthetic traffic and source segmentation
- a lightweight behavioral micro-world for realism work

The system is structurally sound.

The main remaining problem is no longer policy architecture.

It is realism:
- making synthetic cluster behavior believable
- making uncertainty emerge from conflict instead of direct injection
- keeping synthetic rule and surface behavior close enough to baseline to trust experiments directionally

## Current Architecture

### Decision System

- policy is structured into:
  - fraud rules
  - strong approve rules
  - micro-lane rules
  - uncertainty rules
  - fallback rules
- each decision records:
  - `policy_layer`
  - `rule_id`
  - `surface`
  - `risk_expectation`
- the `0.60-0.65` gray band is split into:
  - `low_payout_legit_surface`
  - `mid_trust_ambiguity_surface`
  - `early_fraud_signal_surface`
  - `cluster_sensitive_surface`
- cluster influence is routing-only, not score-owned

### Decision Memory And Analytics

- decisions persist:
  - policy metadata
  - surface metadata
  - `traffic_source`
  - `pressure_profile`
- analytics can measure:
  - rule frequency
  - surface distribution
  - false-review attribution
  - replay transitions
  - source comparison
  - policy-health metrics
- promotion governance now checks:
  - `distribution_valid`
  - `baseline_improves`
  - `fraud_risk_within_limit`
  - `sufficient_sample_size`
  - `multi_source_consistency`
  - `source_alignment_valid`

### Simulation Foundation

- simulation evolved through:
  - random generation
  - distribution shaping
  - relational shaping
  - micro-world simulation
- current behavioral generator uses worker archetypes:
  - `LEGIT_STABLE`
  - `LEGIT_NOISY`
  - `FRAUD_OPPORTUNISTIC`
  - `FRAUD_RING_MEMBER`
  - `MIXED_BEHAVIOR`
- current behavioral difficulty categories:
  - `clean_legit`
  - `noisy_legit`
  - `borderline`
  - `adversarial`
- current conflict patterns:
  - `trust_vs_cluster`
  - `score_vs_behavior`
  - `deceptive_semi_fraud`
  - `too_perfect_signal`

## Simulation Evolution

- Wave 5.5 started with synthetic pressure and traffic-source labeling.
- It then added governed experiments, baseline comparison, and promotion gates.
- It then moved from variable shaping to relational shaping.
- It now uses a small behavioral micro-world so cluster and uncertainty can emerge from worker behavior instead of being assigned directly.

## Current Experiment Snapshot

Latest `1000`-row run:
- payout distribution is effectively on target
- trust distribution is effectively on target
- cluster mix is materially more believable than earlier passes
- outcome divergence: `0.064`
- rule divergence: `0.134`
- surface divergence: `0.134`
- `max_gap`: `0.268`
- difficulty divergence: `0.364`
- promotion contract: `allow_policy_change = false`

What improved:
- rule and surface alignment improved materially
- cluster realism improved materially
- baseline vs synthetic outcome behavior is now directionally believable

What still fails:
- uncertainty is still dominated by `none`
- `noise_overload` and `silent_conflict` still under-emerge
- replay is still too easy relative to baseline on fraud risk
- scenario traffic is still harsher than baseline in the wrong way

## Current Limitations

- remaining realism gaps are now relational, not structural
- uncertainty is not emerging often enough from real signal tension
- behavioral difficulty still diverges too much from baseline
- large synthetic runs like `100000` are still not trustworthy as calibration evidence
- this is research-level tuning, not required for demo viability

## Next Steps

Short-term engineering focus:
1. strengthen emergence of:
   - `noise_overload`
   - `silent_conflict`
2. rebalance replay and scenario difficulty so synthetic fraud risk is less distorted
3. tighten rule and surface alignment further against baseline

Hackathon-facing focus after that:
1. integrate at least one semi-real or real provider path cleanly
2. polish frontend language so internal engine terms stay hidden
3. package clear demo flows for:
   - zero-touch claim
   - replay-based policy improvement
   - fraud-vs-legit separation under cluster context
4. keep the judge narrative centered on:
   - automated claims
   - explainable decisions
   - evidence-backed improvement over time

## Wave 0: Guardrails

Completed:
- separate local test DBs per repo
- explicit decision-policy versioning
- explicit session cookie security config
- Phase 3 working-vs-deployed repo workflow

Why it mattered:
- prevented local auth/test drift
- made Phase 3 work safe to continue without destabilizing the deploy-facing repo

## Wave 1: Decision Memory

Completed:
- append-only `decision_logs`
- claim-created memory rows
- manual-resolution memory rows
- backfill-resolution memory rows
- replay/export tooling
- local backfill of the current DB

What the system remembers now:
- frozen decision inputs
- feature snapshot at decision time
- system decision
- final human/system resolution
- payout and wait context
- fraud model version
- decision policy version

Current evidence base:
- claims total: `299`
- decision logs total: `380`
- resolved labels: `81`

Why it mattered:
- Phase 3 no longer depends on guessing from mutable live rows
- false reviews and replay effects can be measured directly

## Wave 2: Observability And Analytics

Completed:
- review-driver summary
- false-review pattern summary
- replay summary
- decision-memory summary
- fallback from empty recent windows to active queue
- long-window decision-memory analytics in admin payloads

What analytics now answers:
- which delayed claims were later legitimate
- which score bands waste review effort
- which driver labels dominate false reviews
- how current policy replay differs from stored decisions

Key current findings:
- false reviews: `44`
- replay rows: `299`
- replay match rate: `84.3%`
- delayed -> approved under current replay: `29`
- approved -> delayed under current replay: `10`

## Wave 3: Uncertainty Routing

Completed:
- deterministic reason labels
- explicit uncertainty cases
- explicit uncertainty route/band payload
- config-extracted thresholds and confidence bands
- edge-case tests

Uncertainty cases now supported:
- `core_contradiction`
- `too_perfect_state`
- `noise_overload`
- `silent_conflict`

Why it mattered:
- the engine can now explain *why* a borderline claim stayed in review
- later calibration can target ambiguous patterns instead of broad threshold drops

## Wave 4: Outcome-Based Calibration

Completed:
- false-review safe lane for weak-signal low-payout claims
- explicit pattern taxonomy in the decision engine
- isolated `device` micro-payout lane
- guarded `cluster + device` micro-payout lane
- stronger protection for broader `cluster` combinations
- post-cleanup replay and calibration report generation

Current dominant false-review patterns:
1. `movement + pre_activity`: `18`
2. `cluster + device`: `9`
3. `device`: `8`

Current false-review concentration:
- `0.60-0.65`: `31`
- `0.45-0.55`: `8`
- `>= 0.65`: `5`

Current payout concentration:
- `< 75`: `27`
- `75-125`: `17`

Important interpretation:
- the main waste is still the `0.60-0.65` band
- weak-signal overlap remains the biggest false-review source
- broad `cluster` relaxation is still not justified
- only a tiny `cluster + device` pocket is safe enough for a guarded lane

## Queue Cleanup Result

The working repo local delayed queue was analyzed and cleared using the current policy plus cautious cleanup rules.

Post-cleanup state:
- delayed queue: `0`
- approved: `232`
- rejected: `67`

Why this mattered:
- old backlog was distorting Phase 3 analysis
- the cleaned dataset now reflects calibration work more honestly

## Wave 5: Product-Surface Completion

Completed:
- admin review queue now shows pattern-oriented narratives instead of duplicated raw labels
- next-decision panel now surfaces review pattern + evidence instead of raw repeated factors
- worker decision and claim-detail surfaces use plain-language explanations
- intelligence page now reads from the correct analytics payload and shows:
  - fraud rate
  - false-review drivers
  - replay tradeoff
  - memory health

What changed in the product surface:
- admins see operational pattern labels and evidence
- workers see payout/review explanations in plain language
- raw internal factor clutter is reduced

Follow-up completed after Wave 5:
- intelligence and admin surfaces now include translated policy-health summaries instead of only raw memory analytics
- rule and surface friction are exposed with admin-safe labels, not raw engine IDs
- evidence mix now shows `traffic_source` distribution so baseline and simulated behavior are not visually collapsed together

## Post-Wave-5 Enforcement Passes

Completed:
- explicit policy execution contract in the decision engine:
  - `policy_layer`
  - `rule_id`
  - `decision_policy_version`
- first hard guardrails extracted and emitted:
  - low payout
  - high payout
  - high trust
  - low confidence
  - gray-band bounds
- physical per-layer policy registries:
  - fraud
  - strong approve
  - micro lane
  - ambiguity resolver
  - fallback
- explicit gray-band routing surface
- uncertainty-rule exclusivity enforcement
- rule metadata:
  - purpose
  - surface
  - risk expectation
- cluster classification and routing context:
  - `not_clustered`
  - `coincidence_cluster`
  - `fraud_ring`
  - `mixed_cluster`
- policy introspection analytics:
  - top policy rules
  - policy layer counts
  - false reviews by surface
  - replay transitions by surface

Why it mattered:
- the architecture is no longer only documented
- code can now answer which policy layer and rule decided a claim
- replay and analytics can measure policy friction by surface, not only by raw flag patterns
- the `0.60-0.65` gray band is now an explicit routing surface instead of just a threshold accident

What is still not finished:
- cluster still has some legacy coupling and is not fully routing-only yet
- the gray band still needs multiple dedicated micro-policies instead of only a first surface rule
- the new introspection metrics are now partially surfaced in the frontend, but still need richer trend and time-window views

## Wave 5.5: Controlled Simulation Traffic

Completed:
- strict `traffic_source` propagation through cycle execution, claim decisions, and decision memory
- event metadata now records:
  - `traffic_source`
  - `traffic_sources_seen`
  - `scenario_name`
- decision memory now stores `traffic_source` in `context_snapshot`
- analytics now segment by `traffic_source` for:
  - decision-memory summary
  - false-review pattern summary
  - replay summary
- local history-growth tooling now labels generated traffic explicitly
- bounded replay amplification tool added:
  - `scripts/amplify_decision_logs.py`

Traffic sources now supported:
- `baseline`
- `simulation_pressure`
- `scenario`
- `replay_amplified`

Why it mattered:
- Phase 3 can now answer whether a pattern came from calm baseline traffic, pressure traffic, scenario traffic, or replay amplification
- this prevents the system from evolving on unlabeled synthetic pressure
- Wave 5.5 is now part of the engine path, not a loose dev hack

Important caution:
- controlled stimulus is now possible, but bad stimulus design can still poison calibration
- the next discipline problem is not only generating more traffic
- it is generating labeled, bounded, realistic-enough traffic that does not distort policy evolution

## Policy Health And Admin Translation Follow-up

Completed:
- backend policy-health summary added to analytics payloads
- policy health now computes:
  - friction score
  - automation efficiency
  - review load
  - rule concentration
  - surface imbalance
- top friction rules and top friction surfaces are now exposed separately
- frontend admin/intelligence surfaces now translate:
  - `rule_id` -> operational pattern wording
  - `surface` -> admin-safe surface wording
- traffic-source mix is now shown in the intelligence/admin surface so simulation traffic does not masquerade as baseline truth

Why it mattered:
- Phase 3 is no longer only about measuring decisions
- it is now about governing policy change without overreacting to raw internals
- the UI now exposes enough policy-health signal for admin decision-making without leaking engine language directly

Validation:
- backend analytics suite: `7/7`
- full backend suite: `95/95`
- frontend tests: `73/73`
- frontend lint: passed
- frontend build: passed

Environment note:
- frontend verification required running Node tasks outside the default sandbox because the sandboxed run hit an `EPERM` on `C:\Users\satvi`
- this was an execution-environment issue, not an app-code regression

## Source Comparison And Pressure-Profile Follow-up

Completed:
- analytics now compares behavior by `traffic_source` instead of only segmenting counts
- source comparison now exposes, per source:
  - claim-created rows
  - share of window
  - automation efficiency
  - review load
  - false-review rate
  - top rule
  - top surface
- analytics now computes source contamination:
  - trusted rows
  - simulated rows
  - trusted share
  - simulated share
- baseline-truth mode contract added through runtime config:
  - trusted traffic sources
  - synthetic traffic sources
- local history growth now supports named pressure profiles:
  - `balanced_pressure`
  - `gray_band_heavy`
  - `fraud_pressure`
  - `clean_baseline`
- pressure profile identity now flows through event metadata and decision memory context

Why it mattered:
- segmentation alone was not enough
- Phase 3 now needs source-aware comparison and contamination reading before policy changes are trusted
- this is the first real control-system slice for Wave 5.5, not just stimulus generation

Smoke result:
- one local `gray_band_heavy` run across Delhi produced:
  - `46` claims
  - `28` approved
  - `18` delayed
  - `0` rejected
  - `5` events created
- this confirmed that pressure-profile identity is flowing through execution rather than only existing in config

## Reannotation And Governed Experiment Tooling

Completed:
- historical decision reannotation export added:
  - `scripts/reannotate_decision_history.py`
- governed policy experiment runner added:
  - `scripts/run_policy_experiment.py`
- replay-gated safe backfill tool added:
  - `scripts/backfill_policy_upgrade.py`

What these tools do:
- reannotation:
  - replays old `claim_created` rows through the current engine
  - writes:
    - `original_decision`
    - `replayed_decision`
    - `policy_version_delta`
  - does not overwrite the original decision memory
- experiment runner:
  - generates experiments from three tiers:
    - anchor memory
    - bounded replay amplification
    - scenario injection
  - computes:
    - friction score
    - automation efficiency
    - false auto-approval risk
    - rule concentration
    - surface imbalance
    - metrics by `traffic_source`
- safe backfill:
  - reviews delayed claims under the current engine
  - only qualifies candidates when:
    - decision replays to `approved`
    - confidence remains `high`
    - uncertainty is absent
    - strong or non-weak flags are absent

Smoke results:
- reannotation:
  - wrote `5` rows to `logs/decision_memory/reannotated_history.jsonl`
- governed experiment:
  - wrote `1000` synthetic evaluation rows into `logs/decision_memory/policy_experiment_report.json`
  - summary:
    - friction score: `20.5`
    - automation efficiency: `61.8`
    - false auto-approval risk: `3.7`
  - traffic-source split:
    - baseline: `50%`
    - replay_amplified: `35%`
    - scenario: `15%`
- safe backfill dry run:
  - scanned `18` delayed claims
  - found `0` safe auto-resolution candidates
  - all current delayed rows were blocked by non-weak flags

Why it mattered:
- Phase 3 now has a safer path to large synthetic experimentation
- old decision memory can be compared against current policy before reuse
- delayed-claim correction can now be replay-gated instead of using broad cleanup rules

What the first governed experiment proved:
- the experiment runner can now report:
  - target vs actual distributions
  - baseline vs non-baseline deltas
  - promotion-style governance gates
- a `1000` row sample run passed simple policy-change gates but still failed distribution realism:
  - `max_gap = 0.522`
  - `within_tolerance = false`
- this is the correct outcome:
  - the system can now say "this experiment is not representative enough yet" instead of just returning pretty metrics

## Guided Distribution Shaping And Executable Promotion Contract

Completed:
- the experiment runner now uses guided candidate selection instead of only random generation plus post-hoc judging
- generation now biases toward underfilled buckets across:
  - payout bands
  - trust bands
  - cluster types
  - uncertainty cases
- a difficulty profile now shapes synthetic traffic pressure:
  - easy
  - borderline
  - adversarial
- source-alignment reporting now compares baseline vs synthetic behavior across:
  - outcomes
  - rules
  - surfaces
  - difficulty mix
- the experiment report now includes an explicit promotion contract result:
  - `allow_policy_change`
  - source-consistency details
  - gate checks instead of only raw metrics

What improved:
- payout shaping materially improved in the latest `1000`-row run:
  - target realism gaps for payout bands dropped into the `0.004-0.013` range
- trust shaping improved enough to stay near target tolerance
- the runner can now fail itself for the right reasons instead of leaving that judgment manual

What is still failing honestly:
- overall realism still fails:
  - `max_gap = 0.292`
  - `within_tolerance = false`
- the remaining realism miss is concentrated in:
  - cluster-type mix
  - uncertainty-case mix
- source alignment also fails clearly:
  - `max_divergence = 0.652`
- the executable promotion contract now blocks policy change because:
  - realism still fails
  - fraud-risk delta is too high
  - source consistency fails under synthetic tiers

Why it mattered:
- Wave 5.5 is no longer just "run bigger experiments"
- the system can now distinguish:
  - experiments that are operationally interesting
  - experiments that are trustworthy enough to influence policy
- this is the first step from experiment tooling toward actual experiment governance

## Gray-Band Surface Split And Cluster Purge Follow-up

Completed:
- the `0.60-0.65` zone is no longer treated as one generic gray-band surface
- explicit gray-band surfaces now exist in code:
  - `low_payout_legit_surface`
  - `mid_trust_ambiguity_surface`
  - `early_fraud_signal_surface`
  - `cluster_sensitive_surface`
- the low-payout legitimate gray-band pocket now routes through its own approval rule
- cluster behavior is now routing-only in the decision engine metadata path:
  - `cluster_raw_penalty_active` is now always `false`

Why it mattered:
- gray-band experiments can now target distinct policy surfaces instead of one pooled dead zone
- cluster no longer claims hidden score pressure while also influencing routing
- policy analytics can now measure friction by the new gray-band districts instead of one overcrowded bucket

## What Has Not Been Promoted

Still working-repo only:
- decision-memory infrastructure
- replay analytics and calibration logic
- queue cleanup scripts
- Wave 5 UI changes
- local data-growth scripts and seeded DB expansion

## Current Remaining Risks

1. Calibration is still partly based on synthetic/generated history, not only real human-reviewed outcomes.
2. The strongest remaining false-review concentration is still the `0.60-0.65` band.
3. Broader `cluster` behavior still needs caution.
4. Under realistic trigger thresholds, the system can starve for events and claims, which weakens learning/calibration velocity.
5. Policy-health summaries now exist, but rule-impact ranking and time-window trend views are still not built.
6. Source-aware weighting for calibration decisions still needs stronger enforcement.
7. Large synthetic experiments still need tighter cluster and uncertainty shaping before they become trustworthy inputs.
8. Source alignment is now measurable, but synthetic rule/surface firing is still too far from baseline behavior.
9. Promotion governance is now executable, but the promotion contract still needs to be enforced outside the experiment runner as well.
10. The deployed repo has not yet received these Phase 3 slices.

## Recommended Next Steps

1. Use the new traffic-source contract to keep baseline, pressure, scenario, and replay-amplified evidence separated.
2. Continue splitting the gray band into multiple surfaces:
   - low payout legit
   - medium trust ambiguity
   - emerging fraud pressure
   - cluster-aware gray routing
3. Rank rules by operational impact:
   - frequency
   - false-review contribution
   - replay transitions
4. Use source-comparison summaries to prevent simulated traffic from silently dominating policy interpretation.
5. Reannotate historical rows before treating older memory as current-policy evidence.
6. Keep collecting local decision memory and resolved labels.
7. Improve cluster-type and uncertainty-case generation until distribution realism reaches the actual tolerance bar.
8. Use source-alignment distance to keep synthetic rule and surface behavior from drifting too far from baseline.
9. Promote only stable slices into the deployed repo after validation and docs update.

## Validation Snapshot

Current working-repo verification after the latest enforcement pass:
- backend tests: `114/114`
- frontend tests: `73/73`
- frontend lint: passed
- frontend build: passed

Frontend verification required an escalated run because sandboxed Node execution hit a filesystem `EPERM` before the app code executed.
Backend verification requires the local Docker/Postgres test DB on host port `5433`; if Docker is not running, the suite fails at connection setup rather than on app logic.
