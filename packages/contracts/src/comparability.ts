/**
 * Authoritative question and comparability registry.
 *
 * Pipeline keys, curation keys, and catalog keys stay spelled as they are stored.
 * A family key is not rewritten onto a horizon. Records share a comparison only
 * when the structured outcome, condition, deadline, unit, and probability
 * semantics agree.
 *
 * Agent 5 consumes `classifyQuestionKey`, `classifyForecast`, and
 * `comparabilityIdentityMaterial`. Agent 3 consumes `comparabilityRegistryDocument`
 * and must not translate stored keys during import.
 */

export const COMPARABILITY_POLICY_VERSION = "comparability/1.0.0";

export const DATE_ROLES = ["deadline_in_question", "predicted_value", "conditioning_only"] as const;
export type DateRole = (typeof DATE_ROLES)[number];

export const COMPARABILITY_SOURCES = ["pipeline", "curation", "catalog"] as const;
export type ComparabilitySource = (typeof COMPARABILITY_SOURCES)[number];

export type RegistryDeadline = {
  start: string | null;
  end: string | null;
  label: string;
};

export type OutcomeSplit = {
  outcome_id: string;
  label: string;
  pattern: string;
};

export type RegistryQuestion = {
  key: string;
  role: "family" | "exact";
  family_id: string;
  label: string;
  definition: string;
  topic_slug: string;
  value_semantics: "probability" | "year" | "quantity" | "qualitative" | "mixed";
  date_role: DateRole;
  deadline: RegistryDeadline | null;
  unit: string | null;
  conditionality: "unconditional" | "conditional" | "unspecified";
  condition_text: string | null;
  outcome_id: string;
  requires_specific_outcome: boolean;
  outcome_splits: OutcomeSplit[];
  sources: ComparabilitySource[];
};

export type ForecastFacts = {
  question_key?: string | null;
  question_text?: string | null;
  definition_text?: string | null;
  condition_text?: string | null;
  horizon_text?: string | null;
  target_date_start?: string | null;
  target_date_end?: string | null;
  unit?: string | null;
  forecast_kind?: string | null;
  value_type?: string | null;
  value_numeric?: number | null;
  value_min?: number | null;
  value_max?: number | null;
  value_text?: string | null;
  distribution?: Record<string, unknown> | null;
  probability_semantics?: string | null;
};

export type ParsedDeadline = {
  status: "absent" | "structured" | "ambiguous";
  start: string | null;
  end: string | null;
  label: string | null;
};

export type ProbabilitySemantics = "event_probability" | "unspecified";

export type ForecastClassification = {
  policy_version: typeof COMPARABILITY_POLICY_VERSION;
  poolable: boolean;
  reason: ComparabilityExclusion | null;
  exact_question_id: string;
  stored_question_key: string | null;
  /** True only when the stored key is already the exact comparison id. */
  stored_key_is_exact: boolean;
  family_id: string;
  family_key: string | null;
  role: "family" | "exact" | "unknown";
  outcome_id: string;
  outcome_label: string;
  definition: string;
  date_role: DateRole;
  deadline_start: string | null;
  deadline_end: string | null;
  deadline_label: string | null;
  unit: string | null;
  value_semantics: "probability" | "year" | "quantity" | "qualitative";
  conditionality: "unconditional" | "conditional" | "unspecified";
  condition_fingerprint: string;
  condition_label: string | null;
  probability_semantics: ProbabilitySemantics;
  preserved_value: string | null;
};

export type ComparabilityExclusion =
  | "deadline_mismatch"
  | "ambiguous_horizon"
  | "definition_mismatch"
  | "condition_mismatch"
  | "insufficient_agreement"
  | "unit_mismatch";

const OUTCOME_PATTERNS: Record<string, RegExp> = {
  human_extinction: /\bextinction\b/i,
  catastrophe: /\bcatastroph/i,
  disempowerment: /\bdisempower|loss of control\b/i,
  takeover: /\btakeover\b/i,
  mass_death: /most humans die|mass[- ]human death/i,
  agi: /\bagi\b|artificial general intelligence/i,
  asi: /\basi\b|superintelligence/i,
  transformative: /transformative ai/i,
  human_level: /human-level ai|human level ai/i,
  labor_productivity: /labor productivity|productivity growth/i,
  gdp: /\bgdp\b|gross domestic product/i,
  unemployment: /unemployment/i,
  coding: /\bcoding\b|software engineering/i,
  jobs: /\bjobs\b|job displacement|\bworkers\b/i,
  tasks: /\btasks?\b/i,
  wages: /\bwages?\b/i,
  remote_work: /remote work/i,
  compute: /\bcompute\b|\bscaling\b|\benergy\b/i,
};

function family(input: Omit<RegistryQuestion, "role" | "deadline" | "requires_specific_outcome" | "outcome_splits"> & {
  requires_specific_outcome?: boolean;
  outcome_splits?: OutcomeSplit[];
}): RegistryQuestion {
  return {
    ...input,
    role: "family",
    deadline: null,
    requires_specific_outcome: input.requires_specific_outcome ?? false,
    outcome_splits: input.outcome_splits ?? [],
  };
}

function exact(input: Omit<RegistryQuestion, "role" | "requires_specific_outcome" | "outcome_splits">): RegistryQuestion {
  return { ...input, role: "exact", requires_specific_outcome: false, outcome_splits: [] };
}

const PRODUCTIVITY_SPLITS: OutcomeSplit[] = [
  { outcome_id: "labor_productivity", label: "Labor productivity growth", pattern: "labor productivity|productivity growth" },
  { outcome_id: "gdp", label: "GDP growth", pattern: "\\bgdp\\b|gross domestic product" },
];

export const COMPARABILITY_REGISTRY: readonly RegistryQuestion[] = [
  family({
    key: "extinction_unconditional",
    family_id: "human_extinction_unconditional",
    label: "Unconditional AI-caused human extinction",
    definition: "Probability of AI-caused human extinction, not conditioned on AGI or ASI. The horizon is not fixed by this key.",
    topic_slug: "ai-extinction",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "human_extinction",
    sources: ["pipeline"],
  }),
  family({
    key: "ai_extinction_unconditional",
    family_id: "human_extinction_unconditional",
    label: "Unconditional AI-caused human extinction",
    definition: "Literal human extinction. This curation key does not fix a year.",
    topic_slug: "ai-extinction",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "human_extinction",
    sources: ["curation"],
  }),
  exact({
    key: "ai_extinction_unconditional_by_2070",
    family_id: "human_extinction_unconditional",
    label: "Unconditional human extinction from AI by the end of 2070",
    definition: "Literal human extinction by the end of 2070. Catastrophe, disempowerment, and other deadlines stay outside this comparison.",
    topic_slug: "ai-extinction",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2070-12-31", label: "by the end of 2070" },
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "human_extinction",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "extinction_conditional_agi",
    family_id: "human_extinction_conditional_agi",
    label: "Extinction conditional on AGI or ASI",
    definition: "Probability of human extinction conditional on building AGI or ASI. A calendar deadline is not fixed by this key.",
    topic_slug: "ai-extinction",
    value_semantics: "probability",
    date_role: "conditioning_only",
    unit: "probability",
    conditionality: "conditional",
    condition_text: null,
    outcome_id: "human_extinction",
    sources: ["pipeline"],
  }),
  exact({
    key: "ai_extinction_conditional_on_agi",
    family_id: "human_extinction_conditional_agi",
    label: "Extinction conditional on AGI",
    definition: "Probability of human extinction from AI, conditional on AGI being built. A calendar deadline is a different question.",
    topic_slug: "ai-extinction",
    value_semantics: "probability",
    date_role: "conditioning_only",
    deadline: null,
    unit: "probability",
    conditionality: "conditional",
    condition_text: "conditional on AGI being built",
    outcome_id: "human_extinction",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "catastrophe_broad",
    family_id: "ai_catastrophe",
    label: "Catastrophic AI outcome short of a named extinction forecast",
    definition: "A broader catastrophic outcome. Not extinction, disempowerment, or a fixed year.",
    topic_slug: "ai-catastrophe",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "catastrophe",
    sources: ["pipeline"],
  }),
  exact({
    key: "ai_catastrophe_not_extinction_by_2070",
    family_id: "ai_catastrophe",
    label: "Catastrophic harm short of extinction by the end of 2070",
    definition: "Catastrophic harm that is not literal human extinction, by the end of 2070.",
    topic_slug: "ai-catastrophic-harm",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2070-12-31", label: "by the end of 2070" },
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "catastrophe",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "disempowerment",
    family_id: "permanent_disempowerment",
    label: "Permanent disempowerment or loss of control",
    definition: "Permanent human disempowerment or loss of control. Not pooled with extinction.",
    topic_slug: "ai-disempowerment",
    value_semantics: "probability",
    date_role: "conditioning_only",
    unit: "probability",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "disempowerment",
    sources: ["pipeline"],
  }),
  exact({
    key: "permanent_disempowerment_conditional_on_agi",
    family_id: "permanent_disempowerment",
    label: "Permanent disempowerment conditional on AGI",
    definition: "Permanent disempowerment conditional on AGI. Extinction and catastrophe stay outside this comparison.",
    topic_slug: "permanent-disempowerment",
    value_semantics: "probability",
    date_role: "conditioning_only",
    deadline: null,
    unit: "probability",
    conditionality: "conditional",
    condition_text: "conditional on AGI",
    outcome_id: "disempowerment",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "ai_takeover",
    family_id: "ai_takeover",
    label: "AI takeover as the speaker worded it",
    definition: "The speaker's takeover wording. Not pooled with extinction or generic disempowerment.",
    topic_slug: "ai-takeover",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "takeover",
    sources: ["pipeline"],
  }),
  family({
    key: "mass_human_death",
    family_id: "mass_human_death",
    label: "Most humans die",
    definition: "Most humans die. Not pooled with extinction unless the speaker says extinction.",
    topic_slug: "mass-human-death",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "mass_death",
    sources: ["pipeline"],
  }),
  family({
    key: "ambiguous_doom",
    family_id: "ambiguous_doom",
    label: "Ambiguous doom or existential-risk figure",
    definition: "A numeric doom figure whose outcome was not one of the more specific keys. These records are not pooled.",
    topic_slug: "ai-catastrophe",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "ambiguous_doom",
    requires_specific_outcome: true,
    outcome_splits: [],
    sources: ["pipeline"],
  }),
  family({
    key: "agi_timeline",
    family_id: "agi_arrival_year",
    label: "When the speaker expects AGI",
    definition: "A predicted AGI year under the speaker's wording. The year is the forecast value. This key does not name one calendar deadline.",
    topic_slug: "agi-timeline",
    value_semantics: "year",
    date_role: "predicted_value",
    unit: "year",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "agi",
    sources: ["pipeline"],
  }),
  exact({
    key: "agi_arrival_calendar_year",
    family_id: "agi_arrival_year",
    label: "AGI arrival year",
    definition: "Calendar year in which the speaker expects AGI. Different predicted years stay in one comparison. The year is not a probability.",
    topic_slug: "agi-arrival",
    value_semantics: "year",
    date_role: "predicted_value",
    deadline: null,
    unit: "year",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "agi",
    sources: ["catalog"],
  }),
  family({
    key: "asi_timeline",
    family_id: "asi_arrival_year",
    label: "When the speaker expects ASI",
    definition: "A predicted ASI or superintelligence year. Not an AGI year.",
    topic_slug: "asi-timeline",
    value_semantics: "year",
    date_role: "predicted_value",
    unit: "year",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "asi",
    sources: ["pipeline"],
  }),
  family({
    key: "asi_arrival",
    family_id: "asi_arrival_year",
    label: "ASI arrival",
    definition: "Curation key for ASI arrival. It does not fix a year. A probability and a predicted year stay different comparisons.",
    topic_slug: "asi-timeline",
    value_semantics: "mixed",
    date_role: "predicted_value",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "asi",
    sources: ["curation"],
  }),
  exact({
    key: "asi_arrival_calendar_year",
    family_id: "asi_arrival_year",
    label: "ASI arrival year",
    definition: "Calendar year in which the speaker expects ASI. AGI years stay outside this comparison.",
    topic_slug: "agi-arrival",
    value_semantics: "year",
    date_role: "predicted_value",
    deadline: null,
    unit: "year",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "asi",
    sources: ["catalog"],
  }),
  family({
    key: "transformative_ai_timeline",
    family_id: "transformative_ai_year",
    label: "When the speaker expects transformative AI",
    definition: "A predicted transformative-AI year. Not an AGI date.",
    topic_slug: "transformative-ai",
    value_semantics: "year",
    date_role: "predicted_value",
    unit: "year",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "transformative",
    sources: ["pipeline"],
  }),
  family({
    key: "human_level_ai_timeline",
    family_id: "human_level_ai_year",
    label: "When the speaker expects human-level AI",
    definition: "A predicted human-level AI year. Not automatically an AGI year.",
    topic_slug: "human-level-ai",
    value_semantics: "year",
    date_role: "predicted_value",
    unit: "year",
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "human_level",
    sources: ["pipeline"],
  }),
  family({
    key: "agi_by_year_probability",
    family_id: "agi_arrival_probability",
    label: "Probability of AGI by a stated horizon",
    definition: "A probability that AGI arrives by a horizon the speaker states. This key does not choose the horizon.",
    topic_slug: "agi-timeline",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "agi",
    sources: ["pipeline"],
  }),
  exact({
    key: "agi_arrival_by_2032",
    family_id: "agi_arrival_probability",
    label: "Probability of AGI by the end of 2032",
    definition: "Probability that AGI arrives by the end of 2032. The value is a probability, not a year. Other deadlines stay outside this comparison.",
    topic_slug: "agi-arrival",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2032-12-31", label: "by the end of 2032" },
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "agi",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "asi_by_year_probability",
    family_id: "asi_arrival_probability",
    label: "Probability of ASI by a stated horizon",
    definition: "A probability of ASI or superintelligence by a stated horizon. The horizon is not fixed by this key.",
    topic_slug: "asi-timeline",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "asi",
    sources: ["pipeline"],
  }),
  family({
    key: "transformative_ai_by_year_probability",
    family_id: "transformative_ai_probability",
    label: "Probability of transformative AI by a stated horizon",
    definition: "Not an AGI probability. The horizon is not fixed by this key.",
    topic_slug: "transformative-ai",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "transformative",
    sources: ["pipeline"],
  }),
  family({
    key: "human_level_ai_by_year_probability",
    family_id: "human_level_ai_probability",
    label: "Probability of human-level AI by a stated horizon",
    definition: "Not an AGI probability. The horizon is not fixed by this key.",
    topic_slug: "human-level-ai",
    value_semantics: "probability",
    date_role: "deadline_in_question",
    unit: "probability",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "human_level",
    sources: ["pipeline"],
  }),
  family({
    key: "remote_work_automation",
    family_id: "remote_work_automation",
    label: "Full automation of remote work",
    definition: "When the speaker expects full automation of remote work. Not an AGI date or a job-displacement share.",
    topic_slug: "remote-work-automation",
    value_semantics: "mixed",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "remote_work",
    sources: ["pipeline"],
  }),
  family({
    key: "coding_automation",
    family_id: "coding_automation",
    label: "Coding or software-engineering automation",
    definition: "When or to what degree coding work is automated. A year and a share are different comparisons.",
    topic_slug: "coding-automation",
    value_semantics: "mixed",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "coding",
    sources: ["pipeline"],
  }),
  exact({
    key: "coding_task_automation_share_by_2028",
    family_id: "coding_automation",
    label: "Coding task automation share by the end of 2028",
    definition: "Share of coding tasks automated by the end of 2028. Job counts and other deadlines stay outside this comparison.",
    topic_slug: "coding-automation",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2028-12-31", label: "by the end of 2028" },
    unit: "share",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "coding",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "job_displacement",
    family_id: "job_displacement",
    label: "Jobs displaced",
    definition: "Share or timing of jobs displaced. Not a task share and not a wage forecast.",
    topic_slug: "labor",
    value_semantics: "mixed",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "jobs",
    sources: ["pipeline"],
  }),
  family({
    key: "labor_displacement_plausible",
    family_id: "labor_displacement_qualitative",
    label: "Labor displacement, qualitative",
    definition: "A qualitative employment view. Not a probability.",
    topic_slug: "labor",
    value_semantics: "qualitative",
    date_role: "conditioning_only",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "jobs",
    sources: ["curation"],
  }),
  family({
    key: "task_automation",
    family_id: "task_automation",
    label: "Share of tasks automated",
    definition: "Tasks automated or affected. Not a job or unemployment share.",
    topic_slug: "task-automation",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "tasks",
    sources: ["pipeline"],
  }),
  family({
    key: "wage_effect",
    family_id: "wage_effect",
    label: "Wage forecast",
    definition: "A direct forecast about wages. Not a job-displacement share.",
    topic_slug: "wages",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "wages",
    sources: ["pipeline"],
  }),
  family({
    key: "productivity_growth",
    family_id: "economic_output",
    label: "Productivity, GDP, or economic growth",
    definition: "The pipeline family covers more than one quantity. Productivity and GDP are not pooled with each other.",
    topic_slug: "productivity",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "economic_output",
    requires_specific_outcome: true,
    outcome_splits: PRODUCTIVITY_SPLITS,
    sources: ["pipeline"],
  }),
  family({
    key: "economic_growth",
    family_id: "economic_output",
    label: "Economic growth or productivity",
    definition: "Curation family for growth or productivity. It is not one comparison until the quantity is specific.",
    topic_slug: "productivity",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "economic_output",
    requires_specific_outcome: true,
    outcome_splits: PRODUCTIVITY_SPLITS,
    sources: ["curation"],
  }),
  exact({
    key: "labor_productivity_growth_pp_by_2035",
    family_id: "economic_output",
    label: "Labor productivity growth by 2035",
    definition: "Annual labor-productivity growth by 2035, in percentage points. GDP growth is a different question.",
    topic_slug: "labor-displacement",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2035-12-31", label: "by the end of 2035" },
    unit: "percentage_points",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "labor_productivity",
    sources: ["catalog"],
  }),
  exact({
    key: "gdp_growth_pp_by_2035",
    family_id: "economic_output",
    label: "GDP growth by 2035",
    definition: "Annual GDP growth by 2035, in percentage points. Productivity growth is a different question.",
    topic_slug: "labor-displacement",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2035-12-31", label: "by the end of 2035" },
    unit: "percentage_points",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "gdp",
    sources: ["catalog"],
  }),
  exact({
    key: "unemployment_plus_2pp_by_2030",
    family_id: "unemployment_change",
    label: "Unemployment change by 2030",
    definition: "Change in the unemployment rate by 2030, in percentage points.",
    topic_slug: "labor-displacement",
    value_semantics: "quantity",
    date_role: "deadline_in_question",
    deadline: { start: null, end: "2030-12-31", label: "by the end of 2030" },
    unit: "percentage_points",
    conditionality: "unconditional",
    condition_text: null,
    outcome_id: "unemployment",
    sources: ["curation", "catalog"],
  }),
  family({
    key: "capability_milestone",
    family_id: "capability_milestone",
    label: "Capability threshold",
    definition: "A stated capability threshold that is not an AGI, ASI, or coding-automation forecast.",
    topic_slug: "capability",
    value_semantics: "mixed",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "capability",
    sources: ["pipeline"],
  }),
  family({
    key: "compute_scaling",
    family_id: "compute_scaling",
    label: "Compute, scaling, or energy",
    definition: "A compute, scaling, or energy constraint. Not an arrival date by itself.",
    topic_slug: "compute",
    value_semantics: "mixed",
    date_role: "deadline_in_question",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "compute",
    sources: ["pipeline"],
  }),
  family({
    key: "misuse_concern_direction",
    family_id: "misuse_concern",
    label: "Direction of concern about misuse",
    definition: "Qualitative direction only. Not a probability.",
    topic_slug: "ai-risk-qualitative",
    value_semantics: "qualitative",
    date_role: "conditioning_only",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "misuse",
    sources: ["curation"],
  }),
  family({
    key: "scaling_continues",
    family_id: "scaling_capability",
    label: "Whether scaling continues",
    definition: "A qualitative capability claim. Not an arrival date or an extinction probability.",
    topic_slug: "capability",
    value_semantics: "qualitative",
    date_role: "conditioning_only",
    unit: null,
    conditionality: "unspecified",
    condition_text: null,
    outcome_id: "compute",
    sources: ["curation"],
  }),
];

const BY_KEY = new Map(COMPARABILITY_REGISTRY.map((entry) => [entry.key, entry]));

export function classifyQuestionKey(key: string | null | undefined): RegistryQuestion | null {
  if (!key) return null;
  return BY_KEY.get(key) ?? null;
}

export function registryQuestions(): readonly RegistryQuestion[] {
  return COMPARABILITY_REGISTRY;
}

export function comparabilityRegistryDocument(): {
  policy_version: typeof COMPARABILITY_POLICY_VERSION;
  questions: RegistryQuestion[];
} {
  return {
    policy_version: COMPARABILITY_POLICY_VERSION,
    questions: COMPARABILITY_REGISTRY.map((entry) => ({ ...entry, outcome_splits: entry.outcome_splits.map((split) => ({ ...split })), sources: [...entry.sources], deadline: entry.deadline ? { ...entry.deadline } : null })),
  };
}

export function normalizePhrase(value: string | null | undefined): string {
  return (value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function hasText(value: string | null | undefined): boolean {
  return Boolean(value && value.trim());
}

function isoDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value.trim());
  return match?.[1] ?? null;
}

export function parseDeadline(input: Pick<ForecastFacts, "target_date_start" | "target_date_end" | "horizon_text">): ParsedDeadline {
  const start = isoDate(input.target_date_start);
  const end = isoDate(input.target_date_end);
  const years = [...(input.horizon_text ?? "").matchAll(/\b(?:19|20)\d{2}\b/g)].map((match) => Number(match[0]));
  const uniqueYears = [...new Set(years)];
  if (start && end && start > end) return { status: "ambiguous", start, end, label: null };
  if ((start || end) && uniqueYears.length > 0) {
    const endYear = end ? Number(end.slice(0, 4)) : null;
    const startYear = start ? Number(start.slice(0, 4)) : null;
    const conflicts = uniqueYears.some((year) => {
      if (endYear !== null) return year !== endYear;
      return startYear !== null && year !== startYear;
    });
    if (conflicts || uniqueYears.length > 1) return { status: "ambiguous", start, end, label: null };
  }
  if (!end && !start && uniqueYears.length > 1) return { status: "ambiguous", start: null, end: null, label: null };
  if (end || start) {
    const label = end ? `by ${end}` : `from ${start}`;
    return { status: "structured", start, end, label };
  }
  if (uniqueYears.length === 1) {
    const year = uniqueYears[0];
    if (year === undefined) return { status: "ambiguous", start: null, end: null, label: null };
    return { status: "structured", start: null, end: `${year}-12-31`, label: `by the end of ${year}` };
  }
  return { status: "absent", start: null, end: null, label: null };
}

export function readProbabilitySemantics(facts: ForecastFacts): ProbabilitySemantics {
  const nested = facts.distribution && typeof facts.distribution.probability_semantics === "string"
    ? facts.distribution.probability_semantics
    : null;
  const value = facts.probability_semantics ?? nested;
  return value === "event_probability" ? "event_probability" : "unspecified";
}

export function describePreservedValue(facts: ForecastFacts): string | null {
  const text = facts.value_text?.trim() ?? "";
  const bound = /^(at least|at most|more than|less than|greater than|lower bound|upper bound|≥|≤|>|<)/i.test(text);
  if (bound && text) return text;
  if (facts.value_type === "range" && facts.value_min !== null && facts.value_min !== undefined && facts.value_max !== null && facts.value_max !== undefined) {
    return `${facts.value_min}–${facts.value_max}`;
  }
  const distribution = facts.distribution;
  if (!distribution || typeof distribution !== "object") {
    return facts.value_type === "distribution" ? "distribution supplied; not reduced to a point" : null;
  }
  const parts: string[] = [];
  if (Array.isArray(distribution.quantiles)) {
    const quantiles = distribution.quantiles.flatMap((item) => {
      if (!item || typeof item !== "object") return [];
      const record = item as Record<string, unknown>;
      const p = typeof record.p === "number" ? record.p : null;
      const value = typeof record.value === "number" ? record.value : null;
      if (p === null || value === null || p < 0 || p > 1 || !Number.isFinite(value)) return [];
      return [`p${p}=${value}`];
    });
    if (quantiles.length > 0) parts.push(`quantiles ${quantiles.join(", ")}`);
  }
  const bounds = distribution.bounds;
  if (bounds && typeof bounds === "object") {
    const record = bounds as Record<string, unknown>;
    const lower = typeof record.lower === "number" ? record.lower : null;
    const upper = typeof record.upper === "number" ? record.upper : null;
    const kind = typeof record.kind === "string" ? record.kind : "unspecified";
    if (lower !== null || upper !== null) parts.push(`bounds ${lower ?? "…"}–${upper ?? "…"} (${kind})`);
  }
  if (parts.length > 0) return parts.join("; ");
  if (facts.value_type === "distribution") return "distribution supplied; not reduced to a point";
  return null;
}

export function isBoundPhrase(facts: ForecastFacts): boolean {
  const text = facts.value_text?.trim() ?? "";
  return /^(at least|at most|more than|less than|greater than|lower bound|upper bound|≥|≤|>|<)/i.test(text);
}

function combinedText(facts: ForecastFacts): string {
  return `${facts.question_text ?? ""} ${facts.definition_text ?? ""}`.trim();
}

function outcomeConflict(outcomeId: string, facts: ForecastFacts): boolean {
  const text = combinedText(facts);
  if (!text) return false;
  const own = OUTCOME_PATTERNS[outcomeId];
  if (own?.test(text)) return false;
  return Object.entries(OUTCOME_PATTERNS).some(([id, pattern]) => id !== outcomeId && pattern.test(text));
}

function resolveSplit(entry: RegistryQuestion, facts: ForecastFacts): OutcomeSplit | null {
  if (!entry.requires_specific_outcome) return null;
  const text = combinedText(facts);
  const matches = entry.outcome_splits.filter((split) => new RegExp(split.pattern, "i").test(text));
  return matches.length === 1 ? matches[0] ?? null : null;
}

function semanticsFor(entry: RegistryQuestion | null, facts: ForecastFacts): ForecastClassification["value_semantics"] | null {
  if (facts.forecast_kind === "qualitative" || facts.value_type === "none" && facts.forecast_kind === "qualitative") return "qualitative";
  if (facts.unit === "probability") return "probability";
  if (facts.unit === "year") return "year";
  if (facts.unit) return "quantity";
  if (entry?.value_semantics === "qualitative") return "qualitative";
  if (entry?.value_semantics === "probability" || entry?.value_semantics === "year" || entry?.value_semantics === "quantity") return entry.value_semantics;
  return null;
}

function dateRoleFor(entry: RegistryQuestion | null, semantics: ForecastClassification["value_semantics"]): DateRole {
  if (semantics === "year") return "predicted_value";
  if (semantics === "qualitative") return "conditioning_only";
  if (entry?.date_role === "conditioning_only" && semantics === "probability") return entry.date_role;
  if (entry?.date_role === "predicted_value") return "deadline_in_question";
  return entry?.date_role ?? "deadline_in_question";
}

function conditionOf(facts: ForecastFacts, entry: RegistryQuestion | null): { conditionality: ForecastClassification["conditionality"]; fingerprint: string; label: string | null } {
  const label = hasText(facts.condition_text) ? facts.condition_text!.trim() : null;
  const fingerprint = normalizePhrase(label);
  if (fingerprint) return { conditionality: "conditional", fingerprint, label };
  if (entry?.conditionality === "unconditional") return { conditionality: "unconditional", fingerprint: "", label: null };
  return { conditionality: entry?.conditionality ?? "unspecified", fingerprint: "", label: null };
}

function deadlinesAgree(parsed: ParsedDeadline, deadline: RegistryDeadline | null): boolean {
  if (!deadline) return parsed.status !== "structured";
  if (parsed.status === "ambiguous") return false;
  if (parsed.status === "absent") return true;
  if (deadline.end && parsed.end && parsed.end !== deadline.end) return false;
  if (deadline.start && parsed.start && parsed.start !== deadline.start) return false;
  if (deadline.end && !parsed.end && parsed.start) return false;
  return true;
}

function exactMatch(entry: RegistryQuestion, facts: ForecastFacts, parsed: ParsedDeadline, outcomeId: string, semantics: ForecastClassification["value_semantics"], condition: { conditionality: ForecastClassification["conditionality"]; fingerprint: string }, probability: ProbabilitySemantics, allowDeclaredDeadline: boolean): boolean {
  if (entry.role !== "exact") return false;
  if (entry.outcome_id !== outcomeId) return false;
  if (entry.unit && facts.unit && entry.unit !== facts.unit) return false;
  if (entry.unit && !facts.unit) return false;
  if (semantics === "probability" && entry.value_semantics !== "probability") return false;
  if (semantics === "year" && entry.value_semantics !== "year") return false;
  if (semantics === "quantity" && entry.value_semantics !== "quantity") return false;
  if (entry.conditionality === "unconditional" && condition.conditionality === "conditional") return false;
  if (entry.conditionality === "conditional") {
    if (condition.fingerprint !== normalizePhrase(entry.condition_text)) return false;
  }
  if (probability === "event_probability") return false;
  if (entry.date_role === "predicted_value") return semantics === "year" && condition.conditionality !== "conditional";
  if (entry.date_role === "conditioning_only") return parsed.status !== "structured" && parsed.status !== "ambiguous";
  if (parsed.status === "ambiguous") return false;
  if (!deadlinesAgree(parsed, entry.deadline)) return false;
  if (entry.deadline && parsed.status === "absent" && !allowDeclaredDeadline) return false;
  return true;
}

function syntheticId(parts: string[]): string {
  return ["comparability", COMPARABILITY_POLICY_VERSION, ...parts].join("|");
}

function unpooled(partial: Omit<ForecastClassification, "poolable" | "policy_version"> & { reason: ComparabilityExclusion }): ForecastClassification {
  return { ...partial, policy_version: COMPARABILITY_POLICY_VERSION, poolable: false };
}

function pooled(partial: Omit<ForecastClassification, "poolable" | "policy_version" | "reason">): ForecastClassification {
  return { ...partial, policy_version: COMPARABILITY_POLICY_VERSION, poolable: true, reason: null };
}

export function classifyForecast(facts: ForecastFacts): ForecastClassification {
  const storedKey = facts.question_key ?? null;
  const entry = classifyQuestionKey(storedKey);
  const parsed = parseDeadline(facts);
  const probability = readProbabilitySemantics(facts);
  const preserved = describePreservedValue(facts);
  const semantics = semanticsFor(entry, facts);
  const condition = conditionOf(facts, entry);
  const base = {
    stored_question_key: storedKey,
    stored_key_is_exact: entry?.role === "exact",
    family_key: entry?.role === "family" ? entry.key : entry?.family_id ?? storedKey,
    probability_semantics: probability,
    preserved_value: preserved,
    condition_fingerprint: condition.fingerprint,
    condition_label: condition.label,
    conditionality: condition.conditionality,
    deadline_start: parsed.start,
    deadline_end: parsed.end,
    deadline_label: parsed.label,
  };

  if (!storedKey) {
    return unpooled({
      ...base,
      reason: "insufficient_agreement",
      exact_question_id: "missing-question",
      family_id: "missing-question",
      role: "unknown",
      outcome_id: "unknown",
      outcome_label: "Unknown question",
      definition: facts.definition_text?.trim() || "No question key is stored.",
      date_role: "deadline_in_question",
      unit: facts.unit ?? null,
      value_semantics: semantics ?? "quantity",
    });
  }

  if (!semantics || !facts.unit && semantics !== "qualitative") {
    return unpooled({
      ...base,
      reason: "insufficient_agreement",
      exact_question_id: syntheticId([storedKey, "missing-unit"]),
      family_id: entry?.family_id ?? storedKey,
      role: entry?.role ?? "unknown",
      outcome_id: entry?.outcome_id ?? "unknown",
      outcome_label: entry?.label ?? storedKey,
      definition: entry?.definition ?? (facts.definition_text?.trim() || storedKey),
      date_role: entry?.date_role ?? "deadline_in_question",
      unit: facts.unit ?? null,
      value_semantics: semantics ?? "quantity",
    });
  }

  const dateRole = dateRoleFor(entry, semantics);
  let outcomeId = entry?.outcome_id ?? "unspecified_outcome";
  let outcomeLabel = entry?.label ?? storedKey;
  if (entry?.requires_specific_outcome) {
    const split = resolveSplit(entry, facts);
    if (!split) {
      return unpooled({
        ...base,
        reason: "insufficient_agreement",
        exact_question_id: syntheticId([entry.family_id, storedKey, "unspecified-outcome", facts.unit ?? "", parsed.end ?? "no-deadline"]),
        family_id: entry.family_id,
        role: "family",
        outcome_id: entry.outcome_id,
        outcome_label: entry.label,
        definition: facts.definition_text?.trim() || entry.definition,
        date_role: dateRole,
        deadline_label: parsed.label,
        unit: facts.unit ?? null,
        value_semantics: semantics,
      });
    }
    outcomeId = split.outcome_id;
    outcomeLabel = split.label;
  } else if (entry && outcomeConflict(outcomeId, facts)) {
    return unpooled({
      ...base,
      reason: "definition_mismatch",
      exact_question_id: syntheticId([entry.family_id, storedKey, "definition-conflict"]),
      family_id: entry.family_id,
      role: entry.role,
      outcome_id: outcomeId,
      outcome_label: outcomeLabel,
      definition: facts.definition_text?.trim() || entry.definition,
      date_role: dateRole,
      unit: facts.unit ?? null,
      value_semantics: semantics,
    });
  }

  if (entry?.role === "exact") {
    const agrees = exactMatch(entry, facts, parsed, entry.outcome_id, semantics, condition, probability, true);
    if (agrees && (dateRole !== "deadline_in_question" || parsed.status !== "ambiguous")) {
      return pooled({
        ...base,
        exact_question_id: entry.key,
        stored_key_is_exact: true,
        family_id: entry.family_id,
        family_key: entry.family_id,
        role: "exact",
        outcome_id: entry.outcome_id,
        outcome_label: entry.label,
        definition: facts.definition_text?.trim() || entry.definition,
        date_role: entry.date_role,
        deadline_start: parsed.start ?? entry.deadline?.start ?? null,
        deadline_end: parsed.end ?? entry.deadline?.end ?? null,
        deadline_label: entry.deadline?.label ?? parsed.label,
        unit: facts.unit ?? entry.unit,
        value_semantics: semantics,
      });
    }
    const reason: ComparabilityExclusion = parsed.status === "ambiguous"
      ? "ambiguous_horizon"
      : condition.conditionality === "conditional" && entry.conditionality !== "conditional"
        ? "condition_mismatch"
        : condition.fingerprint && entry.condition_text && condition.fingerprint !== normalizePhrase(entry.condition_text)
          ? "condition_mismatch"
          : facts.unit && entry.unit && facts.unit !== entry.unit
            ? "unit_mismatch"
            : parsed.status === "structured" && entry.deadline && parsed.end !== entry.deadline.end
              ? "deadline_mismatch"
              : parsed.status === "structured" && entry.date_role === "conditioning_only"
                ? "deadline_mismatch"
                : "insufficient_agreement";
    return unpooled({
      ...base,
      reason,
      exact_question_id: syntheticId([entry.key, reason, parsed.end ?? "no-deadline", condition.fingerprint || "no-condition", facts.unit ?? "no-unit"]),
      family_id: entry.family_id,
      role: "exact",
      outcome_id: entry.outcome_id,
      outcome_label: entry.label,
      definition: facts.definition_text?.trim() || entry.definition,
      date_role: entry.date_role,
      deadline_label: parsed.label ?? entry.deadline?.label ?? null,
      unit: facts.unit ?? entry.unit,
      value_semantics: semantics,
    });
  }

  if (dateRole === "deadline_in_question" && parsed.status === "ambiguous") {
    return unpooled({
      ...base,
      reason: "ambiguous_horizon",
      exact_question_id: syntheticId([entry?.family_id ?? storedKey, "ambiguous-horizon"]),
      family_id: entry?.family_id ?? storedKey,
      role: entry?.role ?? "unknown",
      outcome_id: outcomeId,
      outcome_label: outcomeLabel,
      definition: facts.definition_text?.trim() || entry?.definition || storedKey,
      date_role: dateRole,
      unit: facts.unit ?? null,
      value_semantics: semantics,
    });
  }

  if (dateRole === "deadline_in_question" && parsed.status === "absent" && entry) {
    return unpooled({
      ...base,
      reason: "ambiguous_horizon",
      exact_question_id: syntheticId([entry.family_id, storedKey, "missing-deadline", facts.unit ?? ""]),
      family_id: entry.family_id,
      role: "family",
      outcome_id: outcomeId,
      outcome_label: outcomeLabel,
      definition: facts.definition_text?.trim() || entry.definition,
      date_role: dateRole,
      unit: facts.unit ?? null,
      value_semantics: semantics,
    });
  }

  const familyId = entry?.family_id ?? storedKey;
  const candidates = COMPARABILITY_REGISTRY.filter((question) => question.role === "exact" && question.family_id === familyId);
  const matched = candidates.filter((question) => exactMatch(question, facts, parsed, outcomeId, semantics, condition, probability, false));
  if (matched.length === 1 && matched[0]) {
    const question = matched[0];
    return pooled({
      ...base,
      exact_question_id: question.key,
      stored_key_is_exact: false,
      family_id: familyId,
      family_key: entry?.key ?? storedKey,
      role: entry?.role ?? "unknown",
      outcome_id: outcomeId,
      outcome_label: question.label,
      definition: facts.definition_text?.trim() || question.definition,
      date_role: question.date_role,
      deadline_start: parsed.start ?? question.deadline?.start ?? null,
      deadline_end: parsed.end ?? question.deadline?.end ?? null,
      deadline_label: question.deadline?.label ?? parsed.label,
      unit: facts.unit ?? question.unit,
      value_semantics: semantics,
    });
  }
  if (matched.length > 1) {
    return unpooled({
      ...base,
      reason: "insufficient_agreement",
      exact_question_id: syntheticId([familyId, "ambiguous-exact", facts.unit ?? "", parsed.end ?? ""]),
      family_id: familyId,
      role: entry?.role ?? "unknown",
      outcome_id: outcomeId,
      outcome_label: outcomeLabel,
      definition: facts.definition_text?.trim() || entry?.definition || storedKey,
      date_role: dateRole,
      unit: facts.unit ?? null,
      value_semantics: semantics,
    });
  }

  if (!entry && dateRole === "deadline_in_question" && parsed.status === "absent") {
    return pooled({
      ...base,
      exact_question_id: storedKey,
      stored_key_is_exact: false,
      family_id: storedKey,
      family_key: storedKey,
      role: "unknown",
      outcome_id: "unspecified_outcome",
      outcome_label: facts.question_text?.trim() || storedKey,
      definition: facts.definition_text?.trim() || "Stored question key with no registered horizon. Records without a structured deadline stay together only under this unknown key.",
      date_role: dateRole,
      deadline_start: null,
      deadline_end: null,
      deadline_label: null,
      unit: facts.unit ?? null,
      value_semantics: semantics,
    });
  }

  const deadlinePart = dateRole === "predicted_value"
    ? "predicted-value"
    : dateRole === "conditioning_only" && parsed.status !== "structured"
      ? "conditioning-only"
      : (parsed.end ?? parsed.start ?? "no-deadline");
  return pooled({
    ...base,
    exact_question_id: syntheticId([
      familyId,
      outcomeId,
      semantics,
      facts.unit ?? "",
      condition.conditionality,
      condition.fingerprint || "none",
      deadlinePart,
      probability,
    ]),
    stored_key_is_exact: false,
    family_id: familyId,
    family_key: entry?.key ?? storedKey,
    role: entry?.role ?? "unknown",
    outcome_id: outcomeId,
    outcome_label: outcomeLabel,
    definition: facts.definition_text?.trim() || entry?.definition || (facts.question_text?.trim() || storedKey),
    date_role: dateRole,
    deadline_start: dateRole === "predicted_value" ? null : parsed.start,
    deadline_end: dateRole === "predicted_value" ? null : parsed.end,
    deadline_label: dateRole === "predicted_value" ? null : parsed.label,
    unit: facts.unit ?? null,
    value_semantics: semantics,
  });
}

export function comparabilityIdentityMaterial(input: ForecastFacts): string {
  const classified = classifyForecast(input);
  return [
    COMPARABILITY_POLICY_VERSION,
    input.question_key ?? "",
    classified.exact_question_id,
    classified.family_id,
    classified.outcome_id,
    normalizePhrase(input.definition_text),
    classified.condition_fingerprint,
    input.target_date_start ?? "",
    input.target_date_end ?? "",
    classified.deadline_end ?? "",
    input.unit ?? "",
    input.value_type ?? "",
    classified.probability_semantics,
  ].join("\n");
}

export function comparisonDecision(facts: ForecastFacts, exactQuestionId: string): {
  match: boolean;
  reason: ComparabilityExclusion | "different_question" | null;
  classification: ForecastClassification;
} {
  const classified = classifyForecast(facts);
  if (classified.poolable && classified.exact_question_id === exactQuestionId) {
    return { match: true, reason: null, classification: classified };
  }
  if (classified.stored_key_is_exact && classified.stored_question_key !== exactQuestionId) {
    return { match: false, reason: "different_question", classification: classified };
  }
  const target = classifyQuestionKey(exactQuestionId);
  if (!target || classified.family_id !== target.family_id) {
    return { match: false, reason: "different_question", classification: classified };
  }
  if (classified.reason) return { match: false, reason: classified.reason, classification: classified };
  if (target.outcome_id !== classified.outcome_id) return { match: false, reason: "definition_mismatch", classification: classified };
  if (target.date_role === "deadline_in_question" && classified.deadline_end && target.deadline?.end && classified.deadline_end !== target.deadline.end) {
    return { match: false, reason: "deadline_mismatch", classification: classified };
  }
  if (classified.conditionality === "conditional" && target.conditionality === "unconditional") {
    return { match: false, reason: "condition_mismatch", classification: classified };
  }
  if (classified.unit && target.unit && classified.unit !== target.unit) {
    return { match: false, reason: "unit_mismatch", classification: classified };
  }
  return { match: false, reason: "insufficient_agreement", classification: classified };
}

export const MEDIAN_INTERPRETATION = {
  probability: "The median summarizes the included statements. It is not automatically the probability of the event.",
  year: "The median year summarizes the included point forecasts. It is a date, not a probability.",
  quantity: "The median summarizes the included point estimates in this unit. It is not a probability.",
} as const;

/**
 * Deduplication key used before comparability/1.0.0. Conditional and unconditional
 * discoveries with the same family key and unit collided on this key.
 */
export function prePolicyMethodKey(input: { kind: string; question_key: string | null; unit: string | null }): string {
  return `${input.kind}\0${input.question_key ?? ""}\0${input.unit ?? ""}`;
}
