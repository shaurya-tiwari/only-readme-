# Risk Model V2 Wrapper: Execution Plan

> **Architectural Objective**: "The system is designed for high-confidence zero-touch automation, with a controlled ambiguity band where human oversight ensures correctness and continuously improves the model. Zero-touch is not about eliminating humans. It’s about eliminating *unnecessary* human intervention."

This finalized blueprint wraps the V2 risk model with deterministic explainability and configurable uncertainty routing. 

---

## Phase 1: Robust Explainability (`backend/ml/risk_model_service.py`)

Instead of throwing a raw float or relying on noisy `RandomForest` internals, we will map explainability using **deterministic feature contribution logic**.

- Use predefined bounds/deltas to assign reasons.
- Ensure the API stably returns the top 1-3 highest-leverage human-readable reasons (e.g., `["Severe Rainfall Surge (+0.12)", "Isolated Platform Outage (+0.05)"]`).
- **Normalization Rule:** Reason contributions will be directionally normalized so their sum never numerically exceeds the actual score impact.
- This guarantees Admin visibility is reproducible, stable, and mathematically coherent.

## Phase 2: Asymmetric Uncertainty Band (`backend/core/decision_engine.py`)

We will build the ambiguity safety-net directly into the core engine to trap the densest gray-area decisions without breaking auto-approval for clear inputs.

- **Hard Override Priority:** If `fraud_score > FRAUD_STRICT_REJECT_THRESHOLD`, the system skips ambiguity entirely and goes straight to `REJECTED`. Ambiguity is for uncertainty, not obvious fraud.
- If `0.24 < risk_score < 0.34` **AND** `confidence < 0.80`, the core engine will gracefully abort Zero-Touch Approval.
- The claim is immediately forced to `DELAYED` and routed to the Admin Queue with the normalized Phase 1 explainability attached.

## Phase 3: Configuration Extraction (`backend/config.py`)

All boundary thresholds will be cleanly extracted into the central environment layer for explicit tunability.

- `RISK_UNCERTAINTY_LOWER = 0.24` (Slightly left-skewed to catch dense borderlines)
- `RISK_UNCERTAINTY_UPPER = 0.34`
- `CONFIDENCE_MIN_THRESHOLD = 0.80`
- `FRAUD_STRICT_REJECT_THRESHOLD = 0.60`
- `MAX_REASONS_RETURNED = 3` (Forcing UX discipline so we don't accidentally bloat dashboards)

## Phase 4: Destructive Edge-Case Testing (`backend/tests/test_edge_cases.py`)

We will enforce confidence and system sanity through 4 brutal edge-case architectures:

1. **The Core Contradiction:** Heavy flood signals + 100% Platform efficiency. (Must trigger ambiguity delay).
2. **"Too Perfect" State:** Extremely low risk + perfect trust score + massive localized disruption anomaly. (Should break blind auto-approval patterns to verify signal).
3. **Noise Overload:** Multiple weak, conflicting signals simultaneously impacting the worker. (Should degrade safely to ambiguity queue, preventing random AI flinches).
4. **"Silent Conflict":** Moderate signals + moderate trust + borderline risk, with no obvious contradiction. (Must still trigger ambiguity queue due to numerical uncertainty rather than dramatic event failure).

---

*(This document represents the locked execution roadmap).*
