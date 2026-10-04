/**
 * Baseline for scenario 6 on the recorded main SHA.
 * A human-verified retraction with no replacement number should drop the
 * withdrawn estimate from the public probability distribution.
 * This file measures the current engine. It does not change trend semantics.
 */
import { PREPARED_TRENDS } from "../../packages/db/src/trend-catalog.ts";
import { computeProbabilityDistribution, type TrendCandidate } from "../../packages/db/src/trend-engine.ts";

const method = PREPARED_TRENDS.find((trend) => trend.slug === "extinction-by-2070-distribution");
if (!method) throw new Error("missing extinction distribution");

const withdrawn: TrendCandidate = {
  statement_slug: "coord-withdrawn-estimate",
  person_slug: "coord-person",
  display_name: "Coordination Person",
  statement_type: "explicit_numeric",
  review_state: "human_verified",
  forecast_review_state: "human_verified",
  topic_slugs: ["ai-extinction"],
  question_key: "ai_extinction_unconditional_by_2070",
  question_text: method.question_text,
  definition_text: method.definition_text,
  condition_text: null,
  forecast_kind: "probability",
  value_type: "point",
  value_numeric: 0.2,
  value_min: null,
  value_max: null,
  unit: "probability",
  horizon_text: "by the end of 2070",
  event_time: "2024-01-01T00:00:00.000Z",
};

const withdrawal: TrendCandidate = {
  statement_slug: "coord-withdrawal",
  person_slug: "coord-person",
  display_name: "Coordination Person",
  statement_type: "explicit_qualitative",
  review_state: "human_verified",
  forecast_review_state: "human_verified",
  topic_slugs: ["ai-extinction"],
  question_key: null,
  question_text: null,
  definition_text: null,
  condition_text: null,
  forecast_kind: null,
  value_type: null,
  value_numeric: null,
  value_min: null,
  value_max: null,
  unit: null,
  horizon_text: null,
  event_time: "2025-06-01T00:00:00.000Z",
};

const otherQuestion: TrendCandidate = {
  ...withdrawn,
  statement_slug: "coord-other-question",
  person_slug: "coord-other-person",
  display_name: "Other Person",
  question_key: "ai_extinction_conditional_on_agi",
  value_numeric: 0.9,
  event_time: "2025-01-01T00:00:00.000Z",
};

const result = computeProbabilityDistribution({
  method_version: method.method_version,
  question_text: method.question_text,
  definition_text: method.definition_text,
  cohort_slug: "coordination-baseline",
  cohort_version: "0",
  cohort_definition: "Fixture for the withdrawal baseline. Not a real cohort.",
  cohort_size: 2,
  scope: method.scope,
  candidates: [withdrawn, withdrawal, otherQuestion],
  edges: [
    {
      from_statement_slug: withdrawn.statement_slug,
      to_statement_slug: withdrawal.statement_slug,
      relationship_type: "retracts",
      review_state: "human_verified",
      method: "manual",
    },
  ],
});

const included = result.included.map((item) => item.statement_slug);
const report = {
  base_sha: "d13c8ab9bc2d643e28b7f52daf1a4c15724e77d7",
  scenario_5_other_question_excluded: !included.includes(otherQuestion.statement_slug),
  scenario_6_withdrawn_estimate_excluded: !included.includes(withdrawn.statement_slug),
  included,
  exclusion_reasons: Object.fromEntries(result.exclusions.map((item) => [item.statement_slug, item.reason])),
};

console.log(JSON.stringify(report, null, 2));
if (!report.scenario_5_other_question_excluded || !report.scenario_6_withdrawn_estimate_excluded) {
  process.exitCode = 1;
}
