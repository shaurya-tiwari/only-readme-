# RideShield Two-Repo Audit

Date: 2026-04-06

## Scope

This audit compares:

- Deployed repo:
  - `RideShield-AI-Powered-Parametric-Income-Protection`
  - GitHub: `https://github.com/Gupta-Sarthak-358/Ride-Shield-InsurTech-System`
- Working repo:
  - `RideShield_work`

This revision reflects the current state after:
- local auth/test reliability fixes
- separate local test DBs
- Phase 3 Wave 0-5 work in the working repo
- post-Wave-5 policy enforcement passes
- first Wave 5.5 traffic-source implementation
- policy-health analytics and admin-safe translation follow-up
- pressure-profile and source-comparison follow-up
- reannotation, governed experiment, and safe backfill tooling follow-up
- gray-band district split and cluster-routing-only follow-up
- guided distribution shaping, source-alignment gating, and executable promotion-contract follow-up
- micro-world realism follow-up
- refreshed intelligence and review surfaces in the working repo

## Docs Reviewed

### Deployed repo

- `README.md`
- `docs/DevNotes.md`
- `docs/Phase3_Roadmap.md`

### Working repo

- `docs/PHASE2_CURRENT_STATE.md`
- `docs/DevNotes.md`
- `docs/architecture.md`
- `docs/Phase3_Roadmap.md`
- `docs/Phase3_Execution_Plan.md`
- `docs/Phase3_Waves_0_5_Report.md`
- `docs/Phase3_Review_Compendium.md`

## Executive Summary

- The deployed repo remains the correct public-facing repo.
- The working repo is now materially more advanced than the deployed repo because it contains:
  - decision memory
  - replay analytics
  - calibration logic
  - Wave 5 UI/product-surface updates
  - policy-layer execution contracts
  - per-layer policy registries
  - cluster classification and routing metadata
  - rule/surface introspection in analytics
- The primary risk is no longer auth integrity.
- The primary risk is now promotion discipline:
  - the working repo is learning quickly
  - the deployed repo must only receive curated stable slices
- The next technical risk after promotion discipline is stimulus starvation:
  - realistic thresholds produce too little event traffic
  - the policy engine can become under-exercised even when it is architecturally strong

## Validation Snapshot

### Deployed repo

- local auth/test reliability patch exists, not pushed
- backend tests: `64/64`
- frontend tests: `73/73`
- frontend build: passed
- live deployed auth: verified on Vercel + Render

### Working repo

- backend tests: `114/114`
- decision memory and replay live locally
- delayed queue locally cleared for calibration analysis
- policy rule metadata and layer ownership now emitted in decisions
- policy surface and rule analytics now available in admin payloads
- traffic-source labels now flow through decisions, decision memory, and analytics
- policy-health summary now available in analytics payloads
- source-comparison and contamination analytics now available in admin payloads
- baseline-truth mode sources now configurable in runtime config
- controlled pressure profiles now exist for local traffic generation
- historical reannotation export now exists for old decision-memory rows
- governed experiment runner now exists for large synthetic policy evaluation
- guided distribution shaping now exists in the experiment runner:
  - underfilled buckets are favored during generation
  - oversampled buckets are penalized
- difficulty-profile control now exists for synthetic experiments:
  - `clean_legit`
  - `noisy_legit`
  - `borderline`
  - `adversarial`
- source-alignment measurement now exists:
  - baseline vs synthetic outcome divergence
  - baseline vs synthetic rule divergence
  - baseline vs synthetic surface divergence
  - baseline vs synthetic difficulty divergence
- micro-world realism work now exists:
  - worker archetypes
  - time-window style behavioral overlap
  - conflict-pattern generation
- executable promotion-contract evaluation now exists in experiment reports:
  - distribution validity
  - baseline improvement
  - fraud-risk limit
  - sufficient sample size
  - multi-source consistency
- replay-gated policy-upgrade backfill tooling now exists for delayed claims
- gray-band district routing now exists in code
- cluster raw-penalty activity is now retired from the decision engine path
- admin/intelligence UI now surfaces translated rule/surface friction and evidence mix
- frontend tests: `73/73`
- frontend lint: passed
- frontend build: passed

## What Changed Since The Earlier Audit

The earlier audit is no longer an accurate picture.

The following are now true:

- cookie/session tests are fixed locally in both repos
- separate local test DBs exist for both repos
- Wave 0-5 work exists in the working repo
- current local Phase 3 evidence base includes:
  - `299` claim-created rows
  - `380` decision logs
  - `81` resolved labels
- current false-review analysis and policy replay are available
- the local working-repo queue has been cleaned so analysis is no longer distorted by stale backlog
- policy execution now emits:
  - `policy_layer`
  - `rule_id`
  - rule metadata
- gray-band routing is now an explicit policy surface
- uncertainty routing now has exclusivity enforcement
- policy analytics can now answer which surfaces and rules create friction
- Wave 5.5 traffic-source segmentation now exists:
  - `baseline`
  - `simulation_pressure`
  - `scenario`
  - `replay_amplified`
- source-aware policy governance now exists:
  - per-source comparison metrics
  - contamination summary
  - baseline-truth mode source filtering contract
- pressure profiles now exist for local growth:
  - `balanced_pressure`
  - `gray_band_heavy`
  - `fraud_pressure`
  - `clean_baseline`
- historical reannotation now exists:
  - `original_decision`
  - `replayed_decision`
  - `policy_version_delta`
- governed policy experiments now exist:
  - anchor layer from stored decision memory
  - bounded replay amplification
  - scenario injection tier
- safe backfill tooling now exists:
  - current decision must replay to approve
  - confidence must remain high
  - strong flags still block auto-resolution
- gray-band policy districts now exist:
  - `low_payout_legit_surface`
  - `mid_trust_ambiguity_surface`
  - `early_fraud_signal_surface`
  - `cluster_sensitive_surface`
- policy health is now measurable through:
  - friction score
  - automation efficiency
  - review load
  - rule concentration
  - surface imbalance
- the next governance problem is now visible:
  - good-looking rules may still do bad operational work
  - surface definitions may need iteration once real distributions appear
- the next stimulus-quality problem is now also visible:
  - payout and trust shaping can be guided well enough
  - but cluster and uncertainty realism still lag behind the target profile
  - and source behavior still diverges too far from baseline rule and surface patterns
- the next realism insight is now clear:
  - cluster is materially improved
  - uncertainty emergence is now the main remaining realism bottleneck

## Deployed Repo Audit

### Strengths

- Best-scoped repo for external judging and presentation.
- Stronger documentation honesty than the working repo.
- Good Phase 2 product story:
  - onboarding
  - worker dashboard
  - admin review
  - explainability
  - demo runner
- Auth/session flow was verified live against the deployed system.

### Findings

#### MEDIUM

- The localhost bearer fallback still creates a second auth path in frontend behavior.
- Decision policy is still concentrated in one backend module.
- Public demo credentials still need explicit disposable-environment framing.
- Admin UX is improved, but still dense for real operations.

#### LOW

- Minor polish and copy cleanup still remain.
- Some documentation is presentation-strong but still relies on the reader understanding the mock-vs-future boundary.

### Verdict

- Strong deploy-facing Phase 2 repo.
- Good enough to show.
- Should stay frozen until grading is fully done.

### Score

- Engineering: `8.5/10`
- Product clarity: `8.5/10`
- Deployment readiness: `8/10`

## Working Repo Audit

### Strengths

- Now clearly the real build surface for Phase 3.
- Contains the strongest architecture evolution already:
  - decision memory
  - replay
  - false-review analytics
  - uncertainty routing
  - outcome-based calibration
  - first Wave 5 product-surface cleanup
  - policy-layer contract enforcement
  - per-layer policy registries
  - cluster context classification
  - policy introspection by rule and surface
  - traffic-source-aware decision memory and analytics
  - policy-health analytics
  - source-comparison analytics and truth-mode support
  - controlled pressure profiles for local simulation
  - historical reannotation and governed experiment tooling
  - guided distribution shaping in the experiment runner
  - difficulty-profile shaping for synthetic pressure
  - source-alignment divergence reporting
  - micro-world behavioral simulation
  - executable promotion-contract evaluation for experiments
  - replay-gated safe backfill tooling
  - explicit gray-band districts
  - cluster routing-only metadata behavior
  - translated admin/intelligence rule-surface visibility
- Backend verification is strong:
  - `114/114` passing

### Findings

#### HIGH

- Promotion risk is now the main concern.
  - The working repo has moved beyond the deployed repo in multiple slices.
  - If stable and experimental changes are not promoted carefully, the deployed repo can quickly become inconsistent.

#### MEDIUM

- The working repo still mixes:
  - current stable behavior
  - Phase 3 experimentation
  - local data-growth scripts
  - calibration tooling
  - docs/reporting artifacts
- Some Phase 3 evidence still comes from synthetic/local growth, not only true human-reviewed production-like outcomes.
- The policy engine is now structured enough that low-stimulus simulation becomes its own risk.
  - with realistic thresholds, little traffic flows
  - memory, replay, and calibration then starve
- Wave 5.5 stimulus labeling exists, but calibration safety now depends on stimulus quality:
  - bad pressure distributions can still poison analytics if they are unrealistic
- Pressure generation is now more controlled, but weighting discipline still matters:
  - simulation can dominate baseline if run carelessly
  - replay amplification can create false confidence if treated as truth
- Large experiment tooling now exists, but synthetic volume still does not equal trustworthy evidence.
- The first governed experiments already showed two subtle risks:
  - simple policy gates can pass while distribution realism still fails
  - guided shaping can fix payout/trust realism faster than cluster/uncertainty realism
- The latest governed experiment exposed the next realism layer:
  - synthetic outcome, rule, and surface behavior can still diverge sharply from baseline even after variable shaping improves
- The micro-world pass improved the system again:
  - outcome divergence is now low enough to be directionally believable
  - rule and surface divergence dropped materially
  - uncertainty emergence remains the main realism gap
- Policy introspection is now partially wired into the UI, but still lacks deeper trend views and explicit rule-impact ranking.

#### LOW

- Documentation volume is high.
- Without consolidation it was drifting; this has improved, but docs still need active maintenance.

### Verdict

- Strong engineering repo.
- Correct place for all further Phase 3 work.
- Not appropriate to present as the clean public artifact.

### Score

- Engineering: `8.8/10`
- Product clarity: `8.2/10`
- Repo hygiene: `6.5/10`

## Product Audit

### What Is Strong

- The core thesis still works:
  - event-first parametric protection
  - zero-touch claims
  - explainable fraud-aware routing
- Worker and admin surfaces now tell a more connected story.
- The Phase 3 system is starting to feel evidence-based instead of threshold-only.

### What Still Feels Weak

- Admin surfaces still risk over-explaining raw internal factors.
- Worker surfaces still carry more numerical internals than a real worker needs.
- Pattern names like `cluster` are useful for builders, but should be translated more consistently for product users.

## Engineering Audit

### What Is Strong

- Good use of append-only decision memory.
- Replay-first calibration is the right approach.
- Tests are not fake-light.
- The system now has a measurable feedback substrate instead of policy-only tuning.
- The policy engine now records:
  - layer ownership
  - rule IDs
  - policy surface metadata
- The system can now measure false reviews by surface and rule, not only by raw flags.
- The system can now compute policy-health summaries instead of only raw decision counts.
- The system can now compare baseline vs simulated behavior instead of only counting mixed traffic.
- The system can now reannotate yesterday's decisions against today's policy without overwriting history.
- The system can now reject a seemingly healthy experiment as insufficiently representative.
- The system can now block a policy change even when a run looks operationally strong, if the promotion contract or realism gates fail.
- The system can now measure when synthetic traffic is drifting too far from baseline behavior at the rule and surface level.
- The system can now distinguish between:
  - structural correctness
  - relational realism
  instead of treating both as one problem.

### What Still Needs Care

- Calibration changes must not be overfit to synthetic/local growth history.
- Taxonomy and threshold changes need replay checks before promotion.
- Stable-vs-experimental boundaries must remain explicit.
- The simulation currently risks being too quiet to generate enough diverse decision traffic under realistic thresholds.
- The opposite risk now also exists:
  - poorly designed simulation pressure can produce confident but misleading policy analytics
- Now that policy is measurable, the team risks overreacting to low-sample early findings.
- Surface definitions may still be too coarse and will likely need iteration once more evidence accumulates.
- Policy health should be managed through impact and evidence quality, not only raw frequency.

## Current Evidence From The Working Repo

- delayed queue: `0` after local cleanup
- approved claims: `232`
- rejected claims: `67`
- false reviews: `44`
- replay match rate: `84.3%`
- delayed -> approved under current replay: `29`
- approved -> delayed under current replay: `10`

Current dominant false-review patterns:
1. `movement + pre_activity`
2. `cluster + device`
3. `device`

Current biggest waste:
- `0.60-0.65` score band

Current architectural upgrades:
- policy registries now exist physically by layer
- cluster is moving from penalty-first logic toward classification-first routing
- analytics can now surface policy friction by rule and surface
- admin/intelligence UI now shows translated friction summaries and traffic-source evidence mix
- source contamination and baseline-truth mode are now first-class analytics concepts
- local simulation can now run named pressure profiles instead of only raw pressure volume
- historical rows can now be replay-reannotated into versioned exports instead of being blindly reused
- large experiments can now be run as governed anchor + amplified + scenario mixes
- large experiments can now distinguish:
  - operationally interesting runs
  - promotable runs
- the gray band is now decomposed into explicit policy districts instead of one pooled surface
- cluster no longer claims raw penalty ownership in the decision engine path

## Main Problems Right Now

### Deployed repo

1. Must remain frozen until grading is complete.
2. Still lacks the stronger Phase 3 evidence infrastructure.
3. Still carries dense admin experience and policy concentration.

### Working repo

1. Promotion discipline is the biggest risk.
2. Calibration evidence is improving, but not all of it is real-world/human-final yet.
3. The simulation needs controlled stimulus modes so the policy engine sees enough event/claim diversity.
4. Stimulus quality is now a governance problem of its own:
   - traffic must be labeled
   - pressure traffic must stay realistic enough
   - scenario traffic must remain intentional
5. Source-aware weighting is still not enforced strongly enough for calibration decisions.
6. Experiment distributions still need stronger cluster and uncertainty shaping before very large runs like `100000` rows are treated as meaningful.
7. Source alignment is improved, but not yet sufficient:
   - rule and surface divergence are much lower
   - difficulty and uncertainty realism still lag
8. Promotion governance now has an executable contract in the experiment runner, but the same contract still needs to be enforced consistently in wider calibration and promotion workflows.
9. Frontend still needs richer trend views for policy health and rule impact over time.
10. Some user-facing explanations still need stronger translation from internal model language to product language.
11. The next risk is policy-health drift:
   - micro-rules can accumulate faster than they are governed
   - early analytics can trigger premature pruning if evidence quality is ignored

## Recommendation

- Keep building in the working repo.
- Promote only reviewed stable slices into the deployed repo.
- Use replay and false-review evidence as the promotion gate for decision-policy changes.
- Add controlled simulation traffic instead of waiting for realistic thresholds to generate enough claims.
- Keep policy analytics segmented by `traffic_source` so simulated behavior does not masquerade as baseline truth.
- Use baseline-truth mode for promotion and calibration validation whenever source mixing becomes heavy.
- Track policy health explicitly:
  - friction score
  - automation efficiency
  - rule concentration
  - surface imbalance
- Reannotate historical decision memory before treating older rows as structurally current evidence.
- Rank rules by impact before pruning:
  - frequency
  - false-review contribution
  - replay consequence
- Treat pressure profiles as governed inputs, not convenience scripts.
- Treat large synthetic experiments as hypothesis tools, not truth generators.
- Do not run the `100000` experiment as a decision input until realism gates, especially cluster and uncertainty shaping, are materially closer to tolerance.
- Do not run the `100000` experiment as a decision input until source-alignment divergence is materially closer to baseline behavior as well.
- Do not let realism research consume demo work once the system becomes directionally trustworthy for judges.
- Do not delete or relax rules on first analytics contact; validate impact against evidence quality first.
- Do not push deploy-facing changes until grading is complete.

## Bottom Line

- Deployed repo: showable, coherent, Phase-2-safe.
- Working repo: richer, smarter, and now the true Phase 3 engine room.
- The challenge is no longer “can the system work?”
- The challenge is “can the team promote the right parts cleanly?”
