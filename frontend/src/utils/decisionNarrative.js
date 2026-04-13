import { humanizeSlug } from "./formatters";

const FACTOR_LABELS = {
  "movement anomaly": {
    admin: "movement anomaly",
    worker: "route movement pattern",
  },
  "weak pre-event activity": {
    admin: "weak pre-event activity",
    worker: "recent work history",
  },
  "event confidence": {
    admin: "event confidence",
    worker: "incident evidence strength",
  },
  "worker trust score": {
    admin: "worker trust score",
    worker: "account trust history",
  },
  "device risk": {
    admin: "device risk",
    worker: "device consistency",
  },
  "cluster fraud pressure": {
    admin: "cluster pattern pressure",
    worker: "coordinated activity pattern",
  },
  "policy timing risk": {
    admin: "policy timing risk",
    worker: "policy timing check",
  },
  "duplicate claim pressure": {
    admin: "duplicate claim pressure",
    worker: "duplicate activity check",
  },
  "income inflation pressure": {
    admin: "income inflation pressure",
    worker: "income consistency check",
  },
  "elevated fraud pressure": {
    admin: "elevated fraud pressure",
    worker: "risk review pressure",
  },
};

const PATTERN_COPY = {
  weak_overlap_noise: {
    adminLabel: "Weak overlap noise",
    adminSummary: "Common weak signals stacked together, but history shows many of these claims are legitimate at low payouts.",
    workerSummary: "The incident looks real, but the system saw a mild mismatch in route activity and incident evidence before paying.",
  },
  device_micro_noise: {
    adminLabel: "Device-only micro noise",
    adminSummary: "Only device consistency was noisy, and the payout exposure is tiny.",
    workerSummary: "The system paused briefly because the device pattern looked unusual, even though the payout amount is very small.",
  },
  cluster_micro_resolved: {
    adminLabel: "Tiny cluster-device pocket",
    adminSummary: "A small high-confidence cluster/device pocket that replay history often treats as legitimate.",
    workerSummary: "The system found an unusual shared pattern, but similar tiny claims are often still legitimate.",
  },
  cluster_combo_pressure: {
    adminLabel: "Coordinated pattern pressure",
    adminSummary: "Cluster-linked behavior is present with another signal, so this stays in the guarded review bucket.",
    workerSummary: "The system saw a broader shared activity pattern that needs manual checking before payout.",
  },
  mixed_review_pressure: {
    adminLabel: "Mixed review pressure",
    adminSummary: "Signals do not point to one clean explanation, so the claim stays in the general review lane.",
    workerSummary: "The system found mixed signals and needs a manual check before payout can continue.",
  },
};

const RULE_LABELS = {
  gray_band_low_risk_surface_approve: {
    admin: "Borderline low-payout claims are being held too often",
  },
  weak_signal_low_payout_safe_lane: {
    admin: "Weak-signal low-payout claims are creating review friction",
  },
  device_micro_noise_approve: {
    admin: "Tiny device-noise claims are being over-reviewed",
  },
  cluster_micro_resolved_approve: {
    admin: "Small cluster-device cases are behaving safer than expected",
  },
  strong_fraud_reject: {
    admin: "High-risk fraud guardrail remains active",
  },
  fallback_review: {
    admin: "General review fallback is absorbing too many claims",
  },
};

const SURFACE_LABELS = {
  gray_band_surface: {
    admin: "Borderline score surface",
  },
  reduce_false_reviews: {
    admin: "False-review reduction surface",
  },
  guarded_cluster_surface: {
    admin: "Cluster-sensitive surface",
  },
  device_micro_noise: {
    admin: "Tiny device-noise surface",
  },
  weak_overlap_noise: {
    admin: "Weak-signal overlap surface",
  },
  cluster_micro_resolved: {
    admin: "Small cluster-device surface",
  },
};

function uniqueLabels(values = []) {
  const seen = new Set();
  return values.filter((value) => {
    const normalized = String(value || "").trim();
    if (!normalized || seen.has(normalized)) {
      return false;
    }
    seen.add(normalized);
    return true;
  });
}

export function formatAudienceFactor(label, audience = "admin") {
  if (!label) {
    return audience === "worker" ? "system review signal" : "system review signal";
  }
  const mapped = FACTOR_LABELS[label];
  if (mapped) {
    return mapped[audience] || mapped.admin;
  }
  return humanizeSlug(label);
}

export function patternCopy(pattern) {
  return PATTERN_COPY[pattern] || {
    adminLabel: "Standard review pattern",
    adminSummary: "The queue still needs an operator decision because the signal mix is not clean enough for automation.",
    workerSummary: "The system needs a manual check before payout can continue.",
  };
}

export function adminIncidentNarrative(incident) {
  const copy = patternCopy(incident?.pattern_taxonomy);
  const primary = formatAudienceFactor(incident?.primary_factor, "admin");
  const evidence = uniqueLabels([
    ...(incident?.secondary_factors || []).map((factor) => formatAudienceFactor(factor, "admin")),
    ...(incident?.top_factors || []).map((factor) => formatAudienceFactor(factor?.label, "admin")),
  ]).slice(0, 3);
  return {
    patternLabel: copy.adminLabel,
    summary: copy.adminSummary,
    primary,
    evidence,
  };
}

export function workerClaimNarrative(claim) {
  const breakdown = claim?.decision_breakdown || {};
  const components = breakdown?.breakdown || {};
  const pattern = components?.pattern_taxonomy;
  const copy = patternCopy(pattern);
  const decision = claim?.status;

  if (decision === "approved") {
    return "RideShield confirmed the disruption and released the payout automatically.";
  }
  if (decision === "rejected") {
    return "RideShield stopped this payout because the combined disruption and account checks did not support a safe payment.";
  }
  return copy.workerSummary;
}

export function workerFriendlyFactors(claim) {
  const fraudModel = claim?.fraud_model || claim?.decision_breakdown?.fraud_model || {};
  const labels = [
    ...(fraudModel?.top_factors || []).map((factor) => factor?.label),
    ...((claim?.decision_breakdown?.inputs?.fraud_flags || []).map((flag) => humanizeSlug(flag))),
  ];
  return uniqueLabels(labels.map((label) => formatAudienceFactor(label, "worker"))).slice(0, 3);
}

export function formatPolicyRule(ruleId, audience = "admin") {
  if (!ruleId) {
    return audience === "admin" ? "Unclassified rule" : "system rule";
  }
  const mapped = RULE_LABELS[ruleId];
  if (mapped) {
    return mapped[audience] || mapped.admin;
  }
  return humanizeSlug(ruleId);
}

export function formatPolicySurface(surface, audience = "admin") {
  if (!surface) {
    return audience === "admin" ? "Unclassified surface" : "system surface";
  }
  const mapped = SURFACE_LABELS[surface];
  if (mapped) {
    return mapped[audience] || mapped.admin;
  }
  return humanizeSlug(surface);
}
