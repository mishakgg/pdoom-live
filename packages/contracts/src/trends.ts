export const SUMMARY_MIN_POINTS = 3;

export const TREND_CONDITIONALITY = ["unconditional", "conditional", "unspecified"] as const;
export type TrendConditionality = (typeof TREND_CONDITIONALITY)[number];

export const TREND_DENSITIES = ["empty", "sparse", "comparable", "individual", "unlinked"] as const;
export type TrendDensity = (typeof TREND_DENSITIES)[number];

export const EXCLUSION_REASONS = [
  "topic_not_target",
  "statement_type",
  "review_state",
  "missing_forecast",
  "question_key_mismatch",
  "conditionality_mismatch",
  "unit_mismatch",
  "missing_horizon",
  "value_type_not_point",
  "not_latest",
  "superseded",
  "no_verified_revision",
  "relationship_not_a_revision",
  "different_person",
] as const;
export type ExclusionReason = (typeof EXCLUSION_REASONS)[number];

export const EXCLUSION_LABELS: Record<ExclusionReason, string> = {
  topic_not_target: "Filed under a different topic and a different question.",
  statement_type: "This record is not an explicit numerical estimate.",
  review_state: "The review state is outside this method's public review policy.",
  missing_forecast: "No structured forecast is stored for this statement.",
  question_key_mismatch: "Different question key. This forecast answers a different question.",
  conditionality_mismatch: "Conditionality does not match. Conditional and unconditional estimates stay separate.",
  unit_mismatch: "Incompatible unit. This method keeps one declared unit and does not convert.",
  missing_horizon: "The horizon is missing.",
  value_type_not_point: "A range or distribution was supplied where this method requires a point. It is not converted into a midpoint.",
  not_latest: "A later explicit estimate from the same person is kept in this cross-section. Dropping the earlier number is not, by itself, a revision.",
  superseded: "Superseded estimate. A human-verified update or retraction links it to a later estimate on the same question.",
  no_verified_revision: "No human-verified update or retraction connects this estimate to another on the same question.",
  relationship_not_a_revision: "This relationship is a repeat, clarification, or contradiction. It is not drawn as a change of forecast.",
  different_person: "This relationship joins two different people, so it is not one person's revision.",
};

export function exclusionLabel(reason: string): string {
  if (reason in EXCLUSION_LABELS) return EXCLUSION_LABELS[reason as ExclusionReason];
  return "Excluded by this method.";
}

export const TREND_KIND_LABELS = {
  distribution: "Probability distribution",
  timeline: "Timeline forecast",
  quantity: "Quantity forecast",
  revision: "Historical revision",
  volume: "Statement volume",
} as const;

export type TrendKind = keyof typeof TREND_KIND_LABELS;

export function trendKindLabel(kind: string): string {
  if (kind in TREND_KIND_LABELS) return TREND_KIND_LABELS[kind as TrendKind];
  return kind;
}

export function coverageSentence(input: {
  includedPeople: number;
  cohortSize: number;
  density: TrendDensity;
}): string {
  const missing = Math.max(0, input.cohortSize - input.includedPeople);
  const people = `${input.includedPeople} of ${input.cohortSize} cohort members`;
  if (input.density === "empty") {
    return `${people} have a comparable record in this view. ${missing} members are absent. An empty result is an absence of comparable records.`;
  }
  if (input.density === "sparse") {
    return `${people} have a comparable record. ${missing} members are absent. The records below are individual estimates. A median is withheld below ${SUMMARY_MIN_POINTS} comparable point estimates.`;
  }
  if (input.density === "unlinked") {
    return `Comparable estimates are stored for this question. None are joined by a human-verified update or retraction, so no change is drawn. ${missing} cohort members are outside this revision view.`;
  }
  if (input.density === "individual") {
    return `${people} have a human-verified change on this question. ${missing} members have no verified change here. Each person is shown separately.`;
  }
  return `${people} have a comparable record. ${missing} members are absent. The median and the range summarize the included point estimates only.`;
}
