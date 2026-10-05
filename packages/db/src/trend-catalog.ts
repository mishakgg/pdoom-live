import type { TrendConditionality } from "@pdoom/contracts";
import type { TrendScope } from "./trend-engine";

export type PreparedTrend = {
  slug: string;
  name: string;
  method_version: string;
  source: "prepared_method";
  kind: "distribution" | "timeline" | "quantity" | "revision";
  question_key: string;
  question_text: string;
  definition_text: string;
  scope: TrendScope;
  accept_ranges: boolean;
  relationship_types: Array<"updates" | "retracts">;
};

const verified = ["human_verified"];
const numeric = ["explicit_numeric"];

function scope(input: {
  question_key: string;
  topic_slug: string;
  sibling_topic_slugs: string[];
  require_unit: string;
  require_horizon: boolean;
  conditionality: TrendConditionality;
}): TrendScope {
  return {
    topic_slug: input.topic_slug,
    sibling_topic_slugs: input.sibling_topic_slugs,
    question_key: input.question_key,
    statement_types: numeric,
    review_states: verified,
    require_horizon: input.require_horizon,
    require_unit: input.require_unit,
    conditionality: input.conditionality,
  };
}

const riskSiblings = ["ai-catastrophic-harm", "permanent-disempowerment", "agi-arrival"];

export const PREPARED_TRENDS: PreparedTrend[] = [
  {
    slug: "extinction-by-2070-distribution",
    name: "Unconditional human-extinction probability by 2070",
    method_version: "explicit-numeric-distribution/1.2.0",
    source: "prepared_method",
    kind: "distribution",
    question_key: "ai_extinction_unconditional_by_2070",
    question_text: "Unconditional probability of literal human extinction caused by advanced AI by the end of 2070.",
    definition_text: "Literal human extinction. Catastrophic harm, disempowerment, and conditional risk stay on their own question keys.",
    scope: scope({
      question_key: "ai_extinction_unconditional_by_2070",
      topic_slug: "ai-extinction",
      sibling_topic_slugs: riskSiblings,
      require_unit: "probability",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: false,
    relationship_types: [],
  },
  {
    slug: "conditional-extinction-given-agi",
    name: "Extinction probability conditional on AGI",
    method_version: "explicit-numeric-distribution/1.2.0",
    source: "prepared_method",
    kind: "distribution",
    question_key: "ai_extinction_conditional_on_agi",
    question_text: "Probability of human extinction from AI, conditional on AGI being built.",
    definition_text: "A conditional probability. It is a different question from unconditional extinction by 2070.",
    scope: scope({
      question_key: "ai_extinction_conditional_on_agi",
      topic_slug: "ai-extinction",
      sibling_topic_slugs: riskSiblings,
      require_unit: "probability",
      require_horizon: true,
      conditionality: "conditional",
    }),
    accept_ranges: false,
    relationship_types: [],
  },
  {
    slug: "catastrophe-not-extinction-by-2070",
    name: "Catastrophic harm short of extinction by 2070",
    method_version: "explicit-numeric-distribution/1.2.0",
    source: "prepared_method",
    kind: "distribution",
    question_key: "ai_catastrophe_not_extinction_by_2070",
    question_text: "Probability of catastrophic harm short of extinction by the end of 2070.",
    definition_text: "Catastrophic harm that is not literal human extinction.",
    scope: scope({
      question_key: "ai_catastrophe_not_extinction_by_2070",
      topic_slug: "ai-catastrophic-harm",
      sibling_topic_slugs: ["ai-extinction", "permanent-disempowerment", "agi-arrival"],
      require_unit: "probability",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: false,
    relationship_types: [],
  },
  {
    slug: "disempowerment-conditional-on-agi",
    name: "Permanent disempowerment conditional on AGI",
    method_version: "explicit-numeric-distribution/1.2.0",
    source: "prepared_method",
    kind: "distribution",
    question_key: "permanent_disempowerment_conditional_on_agi",
    question_text: "Probability of permanent human disempowerment conditional on AGI.",
    definition_text: "Permanent disempowerment. Extinction and catastrophic harm stay on their own question keys.",
    scope: scope({
      question_key: "permanent_disempowerment_conditional_on_agi",
      topic_slug: "permanent-disempowerment",
      sibling_topic_slugs: ["ai-extinction", "ai-catastrophic-harm", "agi-arrival"],
      require_unit: "probability",
      require_horizon: true,
      conditionality: "conditional",
    }),
    accept_ranges: false,
    relationship_types: [],
  },
  {
    slug: "agi-probability-by-2032",
    name: "Probability of AGI by the end of 2032",
    method_version: "explicit-numeric-distribution/1.2.0",
    source: "prepared_method",
    kind: "distribution",
    question_key: "agi_arrival_by_2032",
    question_text: "Probability of AGI arrival by the end of 2032 under the speaker's definition.",
    definition_text: "A probability that AGI arrives by a date. The probability is not an arrival year.",
    scope: scope({
      question_key: "agi_arrival_by_2032",
      topic_slug: "agi-arrival",
      sibling_topic_slugs: ["ai-extinction", "capability-scaling"],
      require_unit: "probability",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: false,
    relationship_types: [],
  },
  {
    slug: "agi-arrival-year",
    name: "AGI arrival year",
    method_version: "timeline-forecast/1.1.0",
    source: "prepared_method",
    kind: "timeline",
    question_key: "agi_arrival_calendar_year",
    question_text: "Calendar year in which the speaker expects AGI, under the speaker's definition.",
    definition_text: "A predicted year. It is not a probability, and it is not an ASI year.",
    scope: scope({
      question_key: "agi_arrival_calendar_year",
      topic_slug: "agi-arrival",
      sibling_topic_slugs: ["ai-extinction", "capability-scaling"],
      require_unit: "year",
      require_horizon: false,
      conditionality: "unspecified",
    }),
    accept_ranges: true,
    relationship_types: [],
  },
  {
    slug: "asi-arrival-year",
    name: "ASI arrival year",
    method_version: "timeline-forecast/1.1.0",
    source: "prepared_method",
    kind: "timeline",
    question_key: "asi_arrival_calendar_year",
    question_text: "Calendar year in which the speaker expects ASI, under the speaker's definition.",
    definition_text: "A predicted ASI year. AGI years and AGI probabilities stay on their own question keys.",
    scope: scope({
      question_key: "asi_arrival_calendar_year",
      topic_slug: "agi-arrival",
      sibling_topic_slugs: ["ai-extinction", "capability-scaling"],
      require_unit: "year",
      require_horizon: false,
      conditionality: "unspecified",
    }),
    accept_ranges: true,
    relationship_types: [],
  },
  {
    slug: "coding-automation-share-by-2028",
    name: "Coding task automation share by 2028",
    method_version: "quantity-forecast/1.1.0",
    source: "prepared_method",
    kind: "quantity",
    question_key: "coding_task_automation_share_by_2028",
    question_text: "Share of coding tasks automated by the end of 2028.",
    definition_text: "A share of coding tasks. Job counts, unemployment changes, and GDP growth are different questions and different units.",
    scope: scope({
      question_key: "coding_task_automation_share_by_2028",
      topic_slug: "coding-automation",
      sibling_topic_slugs: ["labor-displacement"],
      require_unit: "share",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: true,
    relationship_types: [],
  },
  {
    slug: "unemployment-change-by-2030",
    name: "Unemployment change by 2030",
    method_version: "quantity-forecast/1.1.0",
    source: "prepared_method",
    kind: "quantity",
    question_key: "unemployment_plus_2pp_by_2030",
    question_text: "Change in the unemployment rate by 2030, in percentage points.",
    definition_text: "A labor-market quantity in percentage points. It is not a share of automated jobs and it is not a probability.",
    scope: scope({
      question_key: "unemployment_plus_2pp_by_2030",
      topic_slug: "labor-displacement",
      sibling_topic_slugs: ["coding-automation"],
      require_unit: "percentage_points",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: true,
    relationship_types: [],
  },
  {
    slug: "labor-productivity-growth-by-2035",
    name: "Labor productivity growth by 2035",
    method_version: "quantity-forecast/1.1.0",
    source: "prepared_method",
    kind: "quantity",
    question_key: "labor_productivity_growth_pp_by_2035",
    question_text: "Annual labor-productivity growth by 2035, in percentage points.",
    definition_text: "A productivity quantity. GDP growth uses a different question key, even when the unit is also percentage points.",
    scope: scope({
      question_key: "labor_productivity_growth_pp_by_2035",
      topic_slug: "labor-displacement",
      sibling_topic_slugs: ["coding-automation"],
      require_unit: "percentage_points",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: true,
    relationship_types: [],
  },
  {
    slug: "gdp-growth-by-2035",
    name: "GDP growth by 2035",
    method_version: "quantity-forecast/1.1.0",
    source: "prepared_method",
    kind: "quantity",
    question_key: "gdp_growth_pp_by_2035",
    question_text: "Annual GDP growth by 2035, in percentage points.",
    definition_text: "A GDP quantity. Productivity growth and unemployment changes stay on their own question keys.",
    scope: scope({
      question_key: "gdp_growth_pp_by_2035",
      topic_slug: "labor-displacement",
      sibling_topic_slugs: ["coding-automation"],
      require_unit: "percentage_points",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: true,
    relationship_types: [],
  },
  {
    slug: "extinction-by-2070-revisions",
    name: "Revisions of unconditional extinction by 2070",
    method_version: "historical-revision/1.1.0",
    source: "prepared_method",
    kind: "revision",
    question_key: "ai_extinction_unconditional_by_2070",
    question_text: "Unconditional probability of literal human extinction caused by advanced AI by the end of 2070.",
    definition_text: "One person's explicit probability over time, and only where a human-verified update or retraction links the statements.",
    scope: scope({
      question_key: "ai_extinction_unconditional_by_2070",
      topic_slug: "ai-extinction",
      sibling_topic_slugs: riskSiblings,
      require_unit: "probability",
      require_horizon: true,
      conditionality: "unconditional",
    }),
    accept_ranges: false,
    relationship_types: ["updates", "retracts"],
  },
  {
    slug: "agi-arrival-year-revisions",
    name: "Revisions of AGI arrival year",
    method_version: "historical-revision/1.1.0",
    source: "prepared_method",
    kind: "revision",
    question_key: "agi_arrival_calendar_year",
    question_text: "Calendar year in which the speaker expects AGI, under the speaker's definition.",
    definition_text: "A change in one person's predicted AGI year. The link has to be a human-verified update or retraction. A different year from the same person is not enough.",
    scope: scope({
      question_key: "agi_arrival_calendar_year",
      topic_slug: "agi-arrival",
      sibling_topic_slugs: ["ai-extinction"],
      require_unit: "year",
      require_horizon: false,
      conditionality: "unspecified",
    }),
    accept_ranges: false,
    relationship_types: ["updates", "retracts"],
  },
];

export function crossSectionQuestionKeys(trends: Array<{ kind: string; question_key: string }>): Set<string> {
  return new Set(trends.filter((trend) => trend.kind !== "revision").map((trend) => trend.question_key));
}
