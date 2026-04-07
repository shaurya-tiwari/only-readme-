# Frontend Surface Guidance

Date: 2026-04-06

This note applies the frontend-skill lens to RideShield's current product surfaces.

The goal is not "more UI."

The goal is:
- less cognitive noise
- stronger hierarchy
- audience-specific explanations
- fewer raw model terms on-screen

## Visual Thesis

RideShield should feel like a calm operations product for admins and a quiet protection product for workers.

- Admin mood:
  - tactical
  - pressure-aware
  - crisp
  - decision-first
- Worker mood:
  - protective
  - reassuring
  - low-burden
  - payout-first

## Content Plan

### Worker

Primary job:
- answer: "Am I protected, and what happened to my money?"

Show first:
1. protection status
2. latest payout / latest claim outcome
3. one plain-language reason
4. nearby zone pressure

Show second:
1. claim history
2. policy details
3. trust status

Hide or de-emphasize:
- raw factor stacks
- internal model labels
- too many decimal scores
- internal fraud jargon like `cluster` unless translated

### Admin

Primary job:
- answer: "What needs action now, why is it here, and what pattern is driving queue pressure?"

Show first:
1. review queue
2. next decision
3. queue posture

Show second:
1. replay lift / calibration watch
2. top review drivers
3. scheduler/model health

Show third:
1. forecast
2. duplicate/integrity logs
3. map/event context

Hide or de-emphasize:
- duplicated factor lists
- raw repeated `cluster` labels everywhere
- low-signal numbers without interpretation

## What Workers Should See

Workers should not be reading model internals.

Workers should see:
- claim status
- payout amount
- simple explanation
- whether the system is waiting on a manual review
- whether protection is active

Worker-safe language examples:
- "RideShield confirmed the disruption and released the payout automatically."
- "RideShield paused this payout because recent account activity and incident evidence did not line up cleanly enough."
- "RideShield stopped this payout because the combined disruption and account checks did not support a safe payment."

Worker-unsafe language to avoid:
- `cluster fraud pressure`
- `noise overload`
- `core contradiction`
- `device risk`
- raw confidence decimals without translation

If a worker sees a score, it should answer a practical question.

Good:
- payout amount
- protection status
- wait time if delayed

Bad:
- five internal score components in equal visual weight

## What Admins Should See

Admins need pattern language, but still not raw repeated engine output.

Admins should see:
- review pattern
- primary operational driver
- urgency
- payout exposure
- replay/calibration impact

Admin-safe pattern language:
- weak overlap noise
- coordinated pattern pressure
- device-only micro noise
- borderline approval band
- low-trust review pressure

Admin-unsafe clutter:
- primary factor repeated in:
  - title
  - factors
  - top factors
  - priority reason
- long factor-pill soups
- raw flag names without interpretation

## Interaction Thesis

The product should feel like one deliberate decision surface, not a dashboard mosaic.

Recommended interaction rules:

1. Admin queue cards
- one pattern label
- one summary sentence
- up to three evidence chips
- one action row

2. Worker claim detail
- one explanation block
- one payout block
- one compact "how this was weighed" block
- detailed internals only below the fold

3. Intelligence page
- one interpretation per block
- no hero copy that sounds like marketing
- every metric must answer:
  - what changed
  - why it matters
  - what it suggests next

## Current UI Problems

### Worker

- too many raw numbers remain visible
- internal model language still leaks into explanations
- claim-detail score sections still risk feeling like a scoring console

### Admin

- repeated factor labels still appear in multiple places
- `cluster` still dominates visually instead of being grouped into clearer pattern language
- the intelligence surface previously showed fallback-style zeros because backend/frontend fields were out of sync

## Recommended Final Direction

### Worker final direction

Hero:
- protection status
- payout story
- nearby zone pressure

Core:
- one primary claim explanation
- one claim history table
- one policy/trust block

Tone:
- low jargon
- low decimals
- high clarity

### Admin final direction

Top:
- act now
- next decision
- queue posture

Middle:
- calibration watch
- system drivers
- health and scheduler

Bottom:
- forecast
- integrity
- event context

Tone:
- tactical
- compressed
- evidence-first

## Litmus Check

The UI is correct only if:

- a worker can explain their claim outcome without saying "the model"
- an admin can explain a delayed incident without listing raw factor soup
- the intelligence page can be read as an operations briefing, not a feature showcase
