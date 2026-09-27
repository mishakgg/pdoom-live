import { createHash } from "node:crypto";
import { z } from "zod";
import { RELATIONSHIP_TYPES, STATEMENT_TYPES, VALUE_TYPES, type ReviewState, type StatementType } from "./enums";
import { normalizeTimestamp } from "./normalize";

export const REVIEW_DECISION_SCHEMA = "review-decisions/1.0.0";

export const REVIEW_ACTIONS = ["approve", "reject", "needs_changes"] as const;
export type ReviewAction = (typeof REVIEW_ACTIONS)[number];

export const REJECTION_REASONS = [
  "wrong_speaker",
  "wrong_source_attribution",
  "not_a_forecast",
  "extraction_error",
  "duplicate",
  "insufficient_evidence",
  "definition_ambiguous",
  "numerical_interpretation_incorrect",
  "source_unavailable",
  "other",
] as const;
export type RejectionReason = (typeof REJECTION_REASONS)[number];

export const QUESTION_TAXONOMY = [
  {
    key: "ai_extinction_unconditional",
    label: "Unconditional AI-caused human extinction",
    note: "Literal human extinction. Not catastrophe, disempowerment, or a conditional probability.",
  },
  {
    key: "ai_extinction_unconditional_by_2070",
    label: "Unconditional human extinction from AI by the end of 2070",
    note: "Same outcome as unconditional extinction, with this horizon fixed. Not interchangeable with other dates.",
  },
  {
    key: "ai_extinction_conditional_on_agi",
    label: "Extinction conditional on AGI",
    note: "Conditioned on AGI being built. Not an unconditional extinction probability.",
  },
  {
    key: "ai_catastrophe_not_extinction_by_2070",
    label: "Broader AI catastrophe",
    note: "Catastrophic harm short of extinction. Not an extinction probability.",
  },
  {
    key: "permanent_disempowerment_conditional_on_agi",
    label: "Permanent disempowerment",
    note: "Permanent loss of human control. Conditional and unconditional forms stay distinct.",
  },
  {
    key: "agi_arrival_by_2032",
    label: "AGI by a stated year",
    note: "Arrival of AGI under the speaker's definition. Not ASI and not extinction.",
  },
  {
    key: "asi_arrival",
    label: "ASI by a stated year",
    note: "Artificial superintelligence arrival. Not AGI arrival.",
  },
  {
    key: "coding_task_automation_share_by_2028",
    label: "Coding or task automation",
    note: "Share or timing of automated tasks. Not a risk probability.",
  },
  {
    key: "labor_displacement_plausible",
    label: "Labor displacement",
    note: "Employment effects. Not extinction or catastrophe.",
  },
  {
    key: "unemployment_plus_2pp_by_2030",
    label: "Unemployment change",
    note: "A labor-market quantity. Not a p(doom) estimate.",
  },
  {
    key: "economic_growth",
    label: "Economic growth or productivity",
    note: "Growth or productivity. Not a risk probability and not labor displacement.",
  },
  {
    key: "misuse_concern_direction",
    label: "Direction of concern about misuse",
    note: "Qualitative direction only. Not a probability.",
  },
  {
    key: "scaling_continues",
    label: "Whether scaling continues to produce capability gains",
    note: "A capability claim. Not an arrival date or an extinction probability.",
  },
] as const;

export type QuestionKey = (typeof QUESTION_TAXONOMY)[number]["key"];

const QUESTION_KEYS = new Set<string>(QUESTION_TAXONOMY.map((item) => item.key));

export function isKnownQuestionKey(value: string): boolean {
  return QUESTION_KEYS.has(value);
}

export function candidateIdentityMaterial(input: {
  person_slug: string;
  source_content_hash: string;
  evidence_hash: string;
  extractor_name: string;
  extractor_version: string;
  statement_type: string;
}): string {
  return [
    input.person_slug,
    input.source_content_hash,
    input.evidence_hash,
    input.extractor_name,
    input.extractor_version,
    input.statement_type,
  ].join("\n");
}

export function candidateKey(input: {
  person_slug: string;
  source_content_hash: string;
  evidence_hash: string;
  extractor_name: string;
  extractor_version: string;
  statement_type: string;
}): string {
  return createHash("sha256").update(candidateIdentityMaterial(input), "utf8").digest("hex");
}

export type NumericConfirmations = {
  person: boolean;
  evidence: boolean;
  value: boolean;
  units: boolean;
  definition: boolean;
  conditionality: boolean;
  horizon: boolean;
  question_key: boolean;
};

export function resultingReviewState(action: ReviewAction): ReviewState {
  if (action === "approve") return "human_verified";
  if (action === "reject") return "rejected";
  return "needs_review";
}

export function assertReviewTransition(previous: ReviewState, action: ReviewAction): void {
  const allowed: Record<ReviewState, ReviewAction[]> = {
    unreviewed: ["approve", "reject", "needs_changes"],
    needs_review: ["approve", "reject", "needs_changes"],
    machine_validated: ["approve", "reject", "needs_changes"],
    human_verified: ["reject", "needs_changes"],
    rejected: ["needs_changes"],
  };
  if (!allowed[previous].includes(action)) {
    throw new Error(`invalid review transition: ${previous} via ${action}`);
  }
}

const PERCENT = /\b(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)\b/gi;
const PROBABILITY_DECIMAL = /\b(?:0?\.\d+|1(?:\.0+)?)\b/g;

function close(left: number, right: number): boolean {
  return Math.abs(left - right) < 1e-9;
}

export function numbersInEvidence(evidence: string, unit: string | null): number[] {
  const found: number[] = [];
  if (unit === "probability" || unit === null) {
    for (const match of evidence.matchAll(PERCENT)) {
      const value = Number(match[1]) / 100;
      if (value >= 0 && value <= 1) found.push(value);
    }
    for (const match of evidence.matchAll(PROBABILITY_DECIMAL)) {
      const value = Number(match[0]);
      if (value >= 0 && value <= 1) found.push(value);
    }
  }
  const plain = evidence.matchAll(/\b\d+(?:\.\d+)?\b/g);
  for (const match of plain) found.push(Number(match[0]));
  return found;
}

export function evidenceSupportsNumbers(
  evidence: string,
  input: {
    unit: string | null;
    value_type: string;
    value_numeric: number | null;
    value_min: number | null;
    value_max: number | null;
  },
): boolean {
  const needed = [input.value_numeric, input.value_min, input.value_max].filter((value): value is number => value !== null);
  if (input.value_type === "none" || needed.length === 0) return true;
  const found = numbersInEvidence(evidence, input.unit);
  return needed.every((value) => found.some((item) => close(item, value) || (input.unit === "probability" && close(item, value * 100))));
}

export type ReviewWarning = { code: string; message: string };

export function reviewWarnings(input: {
  statement_type: StatementType;
  horizon_text: string | null;
  definition_text: string | null;
  condition_text: string | null;
  question_key: string | null;
  value_type: string | null;
  unit: string | null;
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  source_type: string | null;
  evidence_text: string;
}): ReviewWarning[] {
  const warnings: ReviewWarning[] = [];
  if (!input.horizon_text) warnings.push({ code: "missing_horizon", message: "No horizon is recorded." });
  if (!input.definition_text) warnings.push({ code: "missing_definition", message: "No forecast definition is recorded." });
  if (input.statement_type === "explicit_numeric" && !input.condition_text && !/unconditional|conditional/i.test(`${input.question_key ?? ""} ${input.definition_text ?? ""}`)) {
    warnings.push({ code: "unclear_condition", message: "Conditionality is not explicit." });
  }
  if (input.source_type === "press") {
    warnings.push({ code: "secondary_source", message: "This source type is secondary reporting." });
  }
  if (input.value_type === "range") {
    warnings.push({ code: "range_value", message: "The value is a range, not a point estimate." });
  }
  if (
    input.statement_type === "explicit_numeric" &&
    !evidenceSupportsNumbers(input.evidence_text, {
      unit: input.unit,
      value_type: input.value_type ?? "none",
      value_numeric: input.value_numeric,
      value_min: input.value_min,
      value_max: input.value_max,
    })
  ) {
    warnings.push({ code: "value_disagrees", message: "The evidence text does not contain this numeric value." });
  }
  return warnings;
}

export function suggestQuestionKeys(input: { normalized_text: string; topics: string[] }): string[] {
  const haystack = `${input.normalized_text} ${input.topics.join(" ")}`.toLowerCase();
  const conditional = /\bconditional\b/.test(haystack);
  const scored = QUESTION_TAXONOMY.filter((item) => {
    if (haystack.includes("extinction") && item.key.startsWith("ai_extinction_unconditional") && !conditional) {
      return item.key === "ai_extinction_unconditional_by_2070" ? haystack.includes("2070") : true;
    }
    if (conditional && haystack.includes("extinction")) return item.key === "ai_extinction_conditional_on_agi";
    if (haystack.includes("catastroph")) return item.key === "ai_catastrophe_not_extinction_by_2070";
    if (haystack.includes("disempower")) return item.key === "permanent_disempowerment_conditional_on_agi";
    if (/\basi\b|superintelligence/.test(haystack) && !haystack.includes("extinction")) return item.key === "asi_arrival";
    if (haystack.includes("agi") && !haystack.includes("extinction") && !haystack.includes("disempower") && !haystack.includes("catastroph")) {
      return item.key === "agi_arrival_by_2032";
    }
    if (haystack.includes("coding") || haystack.includes("automat")) return item.key === "coding_task_automation_share_by_2028";
    if (haystack.includes("unemployment")) return item.key === "unemployment_plus_2pp_by_2030";
    if (haystack.includes("labor")) return item.key === "labor_displacement_plausible";
    if (haystack.includes("growth") || haystack.includes("productivity")) return item.key === "economic_growth";
    return false;
  });
  return [...new Set(scored.map((item) => item.key))];
}

export function reviewPriority(input: {
  statement_type: StatementType;
  has_related: boolean;
  confidence: number | null;
  confidence_level: string | null;
}): number {
  if (input.statement_type === "explicit_numeric") return 1;
  if (input.statement_type === "explicit_qualitative") return 2;
  if (input.has_related) return 3;
  const high = (input.confidence !== null && input.confidence >= 0.8) || input.confidence_level === "high";
  if (high && input.statement_type !== "model_inferred_signal") return 4;
  return 5;
}

export function curationEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  return env.PDOOM_CURATION_MODE === "local";
}

const slug = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).max(80);
const timestamp = z.string().transform((value, ctx) => {
  try {
    return normalizeTimestamp(value);
  } catch {
    ctx.addIssue({ code: "custom", message: "timestamp must be ISO-8601 with Z or an explicit offset" });
    return z.NEVER;
  }
});

export const reviewCorrectionsSchema = z.object({
  statement_type: z.enum(STATEMENT_TYPES).optional(),
  normalized_text: z.string().min(1).max(600).optional(),
  topic_slugs: z.array(slug).max(8).optional(),
  question_key: z.string().min(1).max(120).optional(),
  question_text: z.string().min(1).max(600).optional(),
  horizon_text: z.string().max(160).nullable().optional(),
  definition_text: z.string().max(800).nullable().optional(),
  condition_text: z.string().max(400).nullable().optional(),
  value_type: z.enum(VALUE_TYPES).optional(),
  value_numeric: z.number().nullable().optional(),
  value_min: z.number().nullable().optional(),
  value_max: z.number().nullable().optional(),
  unit: z.string().max(40).nullable().optional(),
  evidence_text: z.string().min(1).max(2000).optional(),
  start_char: z.number().int().nonnegative().nullable().optional(),
  end_char: z.number().int().nonnegative().nullable().optional(),
}).strict();

export const reviewConfirmationsSchema = z.object({
  person: z.boolean(),
  evidence: z.boolean(),
  value: z.boolean(),
  units: z.boolean(),
  definition: z.boolean(),
  conditionality: z.boolean(),
  horizon: z.boolean(),
  question_key: z.boolean(),
}).strict();

export const reviewCommandSchema = z.object({
  decision_key: z.string().regex(/^[a-f0-9]{64}$/).nullable().default(null),
  statement_slug: slug,
  decision: z.enum(REVIEW_ACTIONS),
  reviewer: z.string().trim().min(1).max(80),
  reviewed_at: timestamp,
  note: z.string().max(2000).nullable(),
  rejection_reason: z.enum(REJECTION_REASONS).nullable(),
  confirmations: reviewConfirmationsSchema,
  corrections: reviewCorrectionsSchema,
  relationship: z.object({
    other_statement_slug: slug,
    relationship_type: z.enum(RELATIONSHIP_TYPES),
  }).strict().nullable(),
  source_content_hash: z.string().regex(/^[a-f0-9]{64}$/).nullable(),
  evidence_hash: z.string().regex(/^[a-f0-9]{64}$/).nullable(),
  content_version: z.number().int().positive().nullable(),
}).strict();

export type ReviewCommand = z.infer<typeof reviewCommandSchema>;

export function decisionKey(command: ReviewCommand): string {
  return createHash("sha256").update(JSON.stringify({ ...command, decision_key: null }), "utf8").digest("hex");
}

export const reviewManifestSchema = z.object({
  schema_version: z.literal(REVIEW_DECISION_SCHEMA),
  decisions: z.array(reviewCommandSchema),
}).strict();

export type ReviewManifest = z.infer<typeof reviewManifestSchema>;
