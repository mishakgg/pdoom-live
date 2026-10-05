/**
 * Design for a future forecast-resolution dataset.
 * Public scoring stays off until that dataset exists. An unresolved forecast is not a failure.
 */

export const FORECAST_RESOLUTION_POLICY_VERSION = "forecast-resolution/0.1.0";

export type ResolutionReviewState = "human_verified";

export type AdmissibleForecastSnapshot = {
  statement_slug: string;
  exact_question_id: string;
  stored_question_key: string;
  value_type: "point" | "range" | "distribution" | "bound" | "quantile";
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  unit: string;
  event_time: string;
  known_at: string;
  reviewed_at: string;
  review_state: ResolutionReviewState;
  statement_type: "explicit_numeric";
  probability_semantics: "event_probability" | "unspecified";
};

export type OutcomeEvidence = {
  url: string;
  observed_at: string;
  review_state: string;
  description: string;
};

export type ResolutionCase = {
  id: string;
  resolution_criteria: string | null;
  forecast_snapshot: AdmissibleForecastSnapshot | null;
  outcome_evidence: OutcomeEvidence | null;
  evaluation_cutoff: string | null;
  eligible: boolean;
  reasons: string[];
};

export type ResolutionAssessment = {
  policy_version: typeof FORECAST_RESOLUTION_POLICY_VERSION;
  eligible: boolean;
  reasons: string[];
};

export type PublicScore = {
  policy_version: typeof FORECAST_RESOLUTION_POLICY_VERSION;
  status: "disabled";
  score: null;
  reason: string;
};

const DISABLED_REASON = "Public scoring stays off until an adequate resolved dataset exists. An unresolved extinction forecast is not a failure, and speaker count is not a confidence interval.";

export function assessResolutionEligibility(input: {
  resolution_criteria: string | null;
  forecast_snapshot: AdmissibleForecastSnapshot | null;
  outcome_evidence: OutcomeEvidence | null;
  evaluation_cutoff: string | null;
}): ResolutionAssessment {
  const reasons: string[] = [];
  if (!input.resolution_criteria?.trim()) reasons.push("missing_resolution_criteria");
  const snapshot = input.forecast_snapshot;
  if (!snapshot) reasons.push("missing_forecast_snapshot");
  else {
    if (snapshot.statement_type !== "explicit_numeric") reasons.push("snapshot_not_explicit_numeric");
    if (snapshot.review_state !== "human_verified") reasons.push("snapshot_not_human_verified");
    if (!snapshot.event_time || !snapshot.known_at || !snapshot.reviewed_at) reasons.push("snapshot_missing_history");
    if (!snapshot.exact_question_id || !snapshot.unit) reasons.push("snapshot_missing_question");
  }
  const outcome = input.outcome_evidence;
  if (!outcome) reasons.push("missing_outcome_evidence");
  else {
    if (!outcome.url || !outcome.description?.trim()) reasons.push("outcome_evidence_incomplete");
    if (outcome.review_state !== "human_verified") reasons.push("outcome_not_human_verified");
    if (!outcome.observed_at) reasons.push("outcome_missing_observation_time");
  }
  if (!input.evaluation_cutoff) reasons.push("missing_evaluation_cutoff");
  if (snapshot && input.evaluation_cutoff) {
    const cutoff = Date.parse(input.evaluation_cutoff);
    const known = Date.parse(snapshot.known_at);
    const reviewed = Date.parse(snapshot.reviewed_at);
    if (Number.isNaN(cutoff) || Number.isNaN(known) || Number.isNaN(reviewed) || known > cutoff || reviewed > cutoff) {
      reasons.push("snapshot_not_admissible_at_cutoff");
    }
  }
  if (outcome && input.evaluation_cutoff) {
    const cutoff = Date.parse(input.evaluation_cutoff);
    const observed = Date.parse(outcome.observed_at);
    if (Number.isNaN(cutoff) || Number.isNaN(observed) || observed > cutoff) reasons.push("outcome_after_cutoff");
  }
  return {
    policy_version: FORECAST_RESOLUTION_POLICY_VERSION,
    eligible: reasons.length === 0,
    reasons,
  };
}

export function scoreResolvedForecast(_input?: {
  question_key?: string | null;
  resolved?: boolean | null;
  eligible?: boolean | null;
}): PublicScore {
  return {
    policy_version: FORECAST_RESOLUTION_POLICY_VERSION,
    status: "disabled",
    score: null,
    reason: DISABLED_REASON,
  };
}

const admissibleSnapshot: AdmissibleForecastSnapshot = {
  statement_slug: "fixture-resolution-forecast",
  exact_question_id: "ai_extinction_unconditional_by_2070",
  stored_question_key: "ai_extinction_unconditional_by_2070",
  value_type: "point",
  value_numeric: 0.1,
  value_min: null,
  value_max: null,
  unit: "probability",
  event_time: "2024-01-01T00:00:00.000Z",
  known_at: "2024-01-02T00:00:00.000Z",
  reviewed_at: "2024-02-01T00:00:00.000Z",
  review_state: "human_verified",
  statement_type: "explicit_numeric",
  probability_semantics: "unspecified",
};

const admissibleOutcome: OutcomeEvidence = {
  url: "https://example.invalid/resolution/not-a-real-outcome",
  observed_at: "2071-01-15T00:00:00.000Z",
  review_state: "human_verified",
  description: "Fixture outcome evidence for eligibility design. This is not a resolved extinction event.",
};

export const FORECAST_RESOLUTION_FIXTURES: ResolutionCase[] = [
  {
    id: "eligible-design-not-scored",
    resolution_criteria: "Literal human extinction from advanced AI has or has not occurred by the end of 2070, using the question definition stored with the forecast.",
    forecast_snapshot: admissibleSnapshot,
    outcome_evidence: admissibleOutcome,
    evaluation_cutoff: "2071-02-01T00:00:00.000Z",
    eligible: true,
    reasons: [],
  },
  {
    id: "missing-resolution-criteria",
    resolution_criteria: null,
    forecast_snapshot: admissibleSnapshot,
    outcome_evidence: admissibleOutcome,
    evaluation_cutoff: "2071-02-01T00:00:00.000Z",
    eligible: false,
    reasons: ["missing_resolution_criteria"],
  },
  {
    id: "snapshot-not-yet-reviewed",
    resolution_criteria: "Literal human extinction from advanced AI by the end of 2070.",
    forecast_snapshot: { ...admissibleSnapshot, reviewed_at: "2071-03-01T00:00:00.000Z" },
    outcome_evidence: admissibleOutcome,
    evaluation_cutoff: "2071-02-01T00:00:00.000Z",
    eligible: false,
    reasons: ["snapshot_not_admissible_at_cutoff"],
  },
  {
    id: "outcome-not-reviewed",
    resolution_criteria: "Literal human extinction from advanced AI by the end of 2070.",
    forecast_snapshot: admissibleSnapshot,
    outcome_evidence: { ...admissibleOutcome, review_state: "needs_review" },
    evaluation_cutoff: "2071-02-01T00:00:00.000Z",
    eligible: false,
    reasons: ["outcome_not_human_verified"],
  },
  {
    id: "unresolved-extinction-not-a-failure",
    resolution_criteria: "Literal human extinction from advanced AI by the end of 2070.",
    forecast_snapshot: admissibleSnapshot,
    outcome_evidence: null,
    evaluation_cutoff: "2026-01-01T00:00:00.000Z",
    eligible: false,
    reasons: ["missing_outcome_evidence"],
  },
];

export function assertResolutionFixtures(): void {
  for (const fixture of FORECAST_RESOLUTION_FIXTURES) {
    const assessment = assessResolutionEligibility(fixture);
    if (assessment.eligible !== fixture.eligible) {
      throw new Error(`${fixture.id} eligibility drifted`);
    }
    for (const reason of fixture.reasons) {
      if (!assessment.reasons.includes(reason)) throw new Error(`${fixture.id} missing ${reason}`);
    }
  }
}
