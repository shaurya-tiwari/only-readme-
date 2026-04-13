# Current Difficulties And Open Questions

Date: 2026-04-06

This document is written for guides, mentors, and senior developers who need the current state without pitch language.

It explains where the system is strong, where it is still weak, and where external guidance would actually help.

## Current Context

The working repo has now completed meaningful early Phase 3 work:
- decision memory
- replay analytics
- uncertainty routing
- outcome-based calibration
- first Wave 5 product-surface cleanup

This means the system is no longer purely threshold-based.

However, the current evidence and calibration are still local-first and partially synthetic.

Another important reality:
- the design is now ahead of its own enforcement
- the architecture is getting clearer, but code-level guarantees are still catching up

## Main Difficulties

### 1. Calibration Quality vs Data Quality

Problem:
- the system now has decision memory and replay
- but much of the recent enlarged dataset was generated locally through seeded workers, accelerated scheduler runs, and synthetic resolution passes

Why this matters:
- this is useful for iteration
- but it is not the same as a large set of real human-reviewed final labels

Open question:
- how much calibration confidence is acceptable before stronger real-world labels exist?

Where mentor input would help:
- defining what minimum evidence bar should exist before promoting calibration changes

### 2. False Reviews Still Concentrate In One Band

Current observation:
- the `0.60-0.65` band still contains the largest false-review concentration

Problem:
- broad threshold drops are unsafe
- but keeping that entire band in review also wastes operator effort
- current uncertainty behavior still leans too hard toward:
  - "if unsure -> review"
- some of the intended graded-uncertainty behavior is still more documented than enforced

Open question:
- what is the right structure for splitting this band further?
  - payout
  - trust
  - signal type
  - uncertainty case
  - historical pattern

Where senior guidance would help:
- shaping a more principled decision surface instead of stacking more special-case lanes
- defining graded uncertainty behavior so low-value ambiguity does not get treated like high-exposure ambiguity
- validating the first explicit guardrails for:
  - low payout
  - high payout
  - high trust
  - low confidence

### 3. `cluster` Is Still Hard To Handle Cleanly

Current observation:
- `cluster + device` appears in false-review-heavy pockets
- broader `cluster` combinations still deserve caution

Problem:
- `cluster` is not one thing
- treating it as always strong is too conservative
- treating it as weak is too dangerous
- the current system still risks using `cluster` as a penalty bucket instead of a scenario type
- some of the better cluster semantics are clearer in docs than they are in fully enforced routing

Open question:
- how should `cluster` be decomposed?
  - cluster size
  - cluster density
  - average trust in cluster
  - pre-activity density
  - activity variance
  - payout size
  - event confidence
  - worker novelty
  - policy timing

Where mentor input would help:
- defining a more defensible cluster taxonomy or feature set
- deciding whether the right abstraction is:
  - `fraud_ring`
  - `shelter_cluster`
  - `coincidence_cluster`
  - `mixed_cluster`
- deciding how aggressively raw direct cluster penalty logic should be retired from the engine

### 4. Product Translation Is Still Behind Engine Progress

Problem:
- the backend is now more nuanced than the UI
- admin and worker surfaces still leak too much internal language

Examples:
- raw `cluster` language
- repeated factor pills
- internal uncertainty cases not yet fully translated for product users
- some screens still expose state instead of a clear story

Open question:
- what is the right boundary between:
  - operational explainability
  - internal engine diagnostics
  - user-facing simplicity

Where guide input would help:
- deciding what should be visible to:
  - worker
  - admin
  - mentor/judge/demo audience

Specific product-copy rule now needed:
- worker messages should always answer:
  1. what happened
  2. what the system is doing
  3. what happens next
- admin messages should compress meaning into:
  - pattern
  - recommendation
  - historical tendency
  - exposure

### 5. Promotion Risk Between Working And Deployed Repos

Problem:
- the working repo is now meaningfully ahead of the deployed repo
- many useful slices exist only locally

Risk:
- pushing everything would be reckless
- promoting too slowly means the deployed repo lags far behind the real system

Open question:
- what should count as a promotable slice?

Where senior engineering input would help:
- defining the promotion standard for:
  - tests
  - replay evidence
  - docs
  - UI readiness
  - product copy
  - demo narrative

Current recommended direction:
- treat one promotion unit as:
  - backend logic change
  - replay report
  - test coverage
  - UI mapping
  - product copy
  - demo narrative
- if one part is missing, the slice should stay local

Additional evidence-bar rule needed:
- a calibration lane should not be promoted unless:
  - there are enough `manual_reviewed` rows for that pattern
  - replay improves false-review behavior
  - fraud leakage does not materially worsen

### 6. Policy Structure Is Still Growing Organically

Problem:
- the system is smarter now, but the policy logic is still at risk of becoming a pile of special cases
- repeated local fixes can quietly create overlapping rules and hidden contradictions
- the docs now define policy layers, but the code still needs a stronger execution contract

Open question:
- should the next structural step be a formal policy-rule layer or a documented decision-policy map first?

Where senior guidance would help:
- deciding how aggressively to move from hardcoded branch logic toward a policy-driven rule structure
- defining the right policy layers, such as:
  - Fraud Layer
  - Strong Approve Layer
  - Micro Payout Safe Lane
  - Ambiguity Resolver
  - Review Fallback

Concrete missing enforcement:
- each decision should eventually log:
  - `policy_layer`
  - `rule_id`
  - `decision_policy_version`

If the team cannot answer:
- "which layer decided this claim?"

then the architecture is still only partially enforced.

### 7. Real Providers Are Still Future Work

Problem:
- Phase 3 roadmap intentionally does not start with real providers
- but any meaningful production-style calibration later will depend on real signal quality and staleness behavior

Open question:
- when should the team switch from local/synthetic-heavy learning work into provider integration work?

Where mentor input would help:
- validating whether the current order remains correct:
  - memory
  - analytics
  - calibration
  - then providers

## What Is Strong Right Now

- append-only decision memory exists
- replay exists
- false-review patterns are measurable
- uncertainty routing is explicit
- queue cleanup and calibration are evidence-based, not random
- backend verification is strong in the working repo

## What Is Still Weak Right Now

- calibration evidence is still not sufficiently real-world
- admin and worker product translation still needs refinement
- some lanes are narrow and useful, but the overall decision surface is still growing organically
- the deployed repo has not received these Phase 3 slices yet

## Specific Questions Worth Asking Mentors Or Senior Developers

1. What evidence threshold should be required before promoting new calibration lanes?
2. How should `cluster` be represented so it is not always over-penalized but still treated cautiously?
3. Should the `0.60-0.65` band be split by rule layers or by a learned wrapper over stored outcomes?
4. How much UI explainability is too much for workers vs admins?
5. What is the cleanest promotion strategy from the working repo to the deployed repo once the system becomes more adaptive?
6. How should uncertainty types map to different actions instead of one default review path?
7. When should the codebase move from layered branch logic toward a formal policy-rule system?
8. What should the first explicit payout, trust, and confidence guardrails be before further calibration?

## Bottom Line

The system is no longer blocked by basic plumbing.

The current challenge is judgment:
- how to calibrate safely
- how to behave intelligently inside uncertainty
- how to translate intelligence into product surfaces
- how to prevent policy growth from turning into patchwork
- how to force code to obey the new architecture instead of only describing it in docs
- and how to promote only the right slices into the deployed repo
