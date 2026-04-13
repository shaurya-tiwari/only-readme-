function bucketTimestamp(value, bucketMinutes = 60) {
  if (!value) {
    return "unknown";
  }

  const date = new Date(value);
  const bucketMs = bucketMinutes * 60 * 1000;
  return String(Math.floor(date.getTime() / bucketMs) * bucketMs);
}

function urgencyRank(band) {
  if (band === "critical") {
    return 3;
  }
  if (band === "warning") {
    return 2;
  }
  return 1;
}

export function groupClaimsByIncident(claims = [], options = {}) {
  if (!claims) {
    return [];
  }
  const bucketMinutes = options.bucketMinutes || 60;
  const groups = new Map();

  for (const claim of claims) {
    const incidentTriggers = claim.decision_breakdown?.incident_triggers || [claim.trigger_type];
    const key = [
      claim.worker_id || claim.worker_name || "worker",
      claim.zone || "zone",
      bucketTimestamp(claim.created_at, bucketMinutes),
    ].join("|");

    if (!groups.has(key)) {
      groups.set(key, {
        id: key,
        worker_id: claim.worker_id,
        worker_name: claim.worker_name,
        zone: claim.zone || null,
        status: null,
        created_at: claim.created_at,
        review_deadline: claim.review_deadline || null,
        claim_count: 0,
        trigger_types: [],
        claims: [],
        total_calculated_payout: 0,
        total_final_payout: 0,
        max_fraud_score: null,
        max_fraud_probability: null,
        avg_final_score: 0,
        avg_trust_score: 0,
        max_decision_confidence: 0,
        decision_confidence_band: "low",
        max_urgency_score: 0,
        urgency_band: "steady",
        priority_reason: null,
        payout_risk: 0,
        hours_waiting: 0,
        hours_until_deadline: null,
        primary_factor: null,
        secondary_factors: [],
        pattern_taxonomy: null,
        uncertainty_case: null,
        decision_experience: null,
        overdue_count: 0,
        top_factors: [],
        fraud_model_version: null,
        fraud_fallback_used: null,
        _statuses: new Set(),
      });
    }

    const group = groups.get(key);
    const fraudModel = claim.fraud_model || claim.decision_breakdown?.fraud_model || {};
    group.claim_count += 1;
    if (claim.status) {
      group._statuses.add(claim.status);
    }
    group.claims.push(claim);
    group.trigger_types = Array.from(new Set([...group.trigger_types, ...incidentTriggers].filter(Boolean)));
    group.total_calculated_payout += Number(claim.calculated_payout || 0);
    group.total_final_payout += Number(claim.final_payout || 0);
    group.avg_final_score += Number(claim.final_score || 0);
    group.avg_trust_score += Number(claim.trust_score || 0);
    group.max_fraud_score = group.max_fraud_score === null
      ? Number(claim.fraud_score || 0)
      : Math.max(group.max_fraud_score, Number(claim.fraud_score || 0));
    if (fraudModel.fraud_probability !== null && fraudModel.fraud_probability !== undefined) {
      const fraudProbability = Number(fraudModel.fraud_probability || 0);
      group.max_fraud_probability = group.max_fraud_probability === null
        ? fraudProbability
        : Math.max(group.max_fraud_probability, fraudProbability);
    }
    if ((!group.top_factors || !group.top_factors.length) && Array.isArray(fraudModel.top_factors)) {
      group.top_factors = fraudModel.top_factors.slice(0, 3);
    }
    if (!group.fraud_model_version && fraudModel.model_version) {
      group.fraud_model_version = fraudModel.model_version;
    }
    if (group.fraud_fallback_used === null && fraudModel.fallback_used !== undefined) {
      group.fraud_fallback_used = Boolean(fraudModel.fallback_used);
    }
    const decisionConfidence = Number(claim.decision_confidence || 0);
    if (decisionConfidence >= group.max_decision_confidence) {
      group.max_decision_confidence = decisionConfidence;
      group.decision_confidence_band = claim.decision_confidence_band || group.decision_confidence_band;
    }
    const urgencyScore = Number(claim.urgency_score || 0);
    if (urgencyScore >= group.max_urgency_score) {
      group.max_urgency_score = urgencyScore;
      group.urgency_band = claim.urgency_band || group.urgency_band;
      group.priority_reason = claim.priority_reason || group.priority_reason;
      group.primary_factor = claim.primary_factor || group.primary_factor;
      group.secondary_factors = Array.isArray(claim.secondary_factors) ? claim.secondary_factors.slice(0, 2) : group.secondary_factors;
      group.pattern_taxonomy = claim.pattern_taxonomy || group.pattern_taxonomy;
      group.uncertainty_case = claim.uncertainty_case || group.uncertainty_case;
      group.decision_experience = claim.decision_experience || group.decision_experience;
      group.hours_waiting = Number(claim.hours_waiting || group.hours_waiting || 0);
    }
    group.payout_risk += Number(claim.payout_risk || 0);
    if (claim.hours_until_deadline !== null && claim.hours_until_deadline !== undefined) {
      const deadlineHours = Number(claim.hours_until_deadline);
      group.hours_until_deadline = group.hours_until_deadline === null
        ? deadlineHours
        : Math.min(group.hours_until_deadline, deadlineHours);
    }

    if (claim.review_deadline && (!group.review_deadline || new Date(claim.review_deadline) < new Date(group.review_deadline))) {
      group.review_deadline = claim.review_deadline;
    }
    if (claim.created_at && new Date(claim.created_at) < new Date(group.created_at)) {
      group.created_at = claim.created_at;
    }
    if (claim.is_overdue) {
      group.overdue_count += 1;
    }
  }

  return Array.from(groups.values())
    .map((group) => {
      const statuses = group._statuses;
      let status = "approved";
      if (statuses.has("rejected")) {
        status = "rejected";
      } else if (statuses.has("delayed")) {
        status = "delayed";
      }
      return {
        ...group,
        status,
        avg_final_score: group.claim_count ? group.avg_final_score / group.claim_count : 0,
        avg_trust_score: group.claim_count ? group.avg_trust_score / group.claim_count : 0,
        payout_risk: Number(group.payout_risk.toFixed(2)),
      };
    })
    .sort((a, b) => {
      if ((b.overdue_count || 0) !== (a.overdue_count || 0)) {
        return (b.overdue_count || 0) - (a.overdue_count || 0);
      }
      if ((b.max_urgency_score || 0) !== (a.max_urgency_score || 0)) {
        return (b.max_urgency_score || 0) - (a.max_urgency_score || 0);
      }
      if (urgencyRank(b.urgency_band) !== urgencyRank(a.urgency_band)) {
        return urgencyRank(b.urgency_band) - urgencyRank(a.urgency_band);
      }
      if (a.hours_until_deadline !== null && b.hours_until_deadline !== null && a.hours_until_deadline !== b.hours_until_deadline) {
        return a.hours_until_deadline - b.hours_until_deadline;
      }
      return new Date(b.created_at || 0) - new Date(a.created_at || 0);
    });
}
