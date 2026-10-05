import { z } from "zod";
import { TREND_CONDITIONALITY } from "./trends";
import {
  ATTRIBUTION_METHODS,
  AVAILABILITY_STATUSES,
  COLLECTION_METHODS,
  COLLECTION_STATUSES,
  CONFIDENCE_LEVELS,
  DATASET_KINDS,
  FORECAST_KINDS,
  IDENTITY_NAMESPACES,
  ORGANIZATION_TYPES,
  PARTICIPANT_ROLES,
  PERSON_STATUSES,
  RELATIONSHIP_TYPES,
  REVIEW_STATES,
  SCHEMA_VERSION,
  SEGMENT_KINDS,
  SOURCE_TYPES,
  STATEMENT_TYPES,
  VALUE_TYPES,
  VERIFICATION_METHODS,
} from "./enums";
import { normalizeTimestamp } from "./normalize";
import { assessFetchUrl } from "./urls";

const slug = z
  .string()
  .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)
  .max(80);

const publicUrl = z.string().max(2000).refine((value) => assessFetchUrl(value).ok, {
  message: "URL must be http(s) without credentials or a blocked host",
});

const confidence = z.number().min(0).max(1);
const confidenceLevel = z.enum(CONFIDENCE_LEVELS);
const timestamp = z.string().transform((value, ctx) => {
  try {
    return normalizeTimestamp(value);
  } catch {
    ctx.addIssue({ code: "custom", message: "timestamp must be ISO-8601 with Z or an explicit offset" });
    return z.NEVER;
  }
});
const sha256 = z.string().regex(/^[a-f0-9]{64}$/);
const detail = z.string().min(1).max(160).nullable();
const dateOnly = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

export const organizationSchema = z.object({
  slug,
  name: z.string().min(1).max(200),
  organization_type: z.enum(ORGANIZATION_TYPES),
  canonical_url: publicUrl.nullable(),
}).strict();

export const personSchema = z.object({
  slug,
  display_name: z.string().min(1).max(200),
  given_name: z.string().min(1).max(100).nullable(),
  family_name: z.string().min(1).max(100).nullable(),
  bio_short: z.string().min(1).max(600),
  inclusion_reason: z.string().min(1).max(600),
  cohort_tags: z.array(z.string().min(1).max(80)).max(20),
  status: z.enum(PERSON_STATUSES),
}).strict();

export const affiliationSchema = z.object({
  person_slug: slug,
  organization_slug: slug,
  role: z.string().min(1).max(160).nullable(),
  start_date: dateOnly.nullable(),
  end_date: dateOnly.nullable(),
  source_slug: slug.nullable(),
  confidence_level: confidenceLevel,
  verification_detail: detail,
  review_state: z.enum(REVIEW_STATES),
  is_current: z.boolean(),
}).strict();

export const externalIdentitySchema = z.object({
  person_slug: slug,
  namespace: z.enum(IDENTITY_NAMESPACES),
  external_id: z.string().min(1).max(300),
  canonical_url: publicUrl.nullable(),
  handle: z.string().min(1).max(120).nullable(),
  verification_method: z.enum(VERIFICATION_METHODS),
  verification_detail: detail,
  confidence_level: confidenceLevel,
  review_state: z.enum(REVIEW_STATES),
  verified_at: timestamp.nullable(),
  source_slug: slug.nullable(),
}).strict();

export const sourceSchema = z.object({
  slug,
  source_type: z.enum(SOURCE_TYPES),
  name: z.string().min(1).max(200),
  canonical_url: publicUrl,
  platform: z.string().min(1).max(80).nullable(),
  owner_person_slug: slug.nullable(),
  owner_organization_slug: slug.nullable(),
  collection_method: z.enum(COLLECTION_METHODS),
  collection_adapter: z.string().min(1).max(80).nullable(),
  rights_notes: z.string().max(600).nullable(),
  enabled: z.boolean(),
  review_state: z.enum(REVIEW_STATES),
  last_checked_at: timestamp.nullable(),
  last_success_at: timestamp.nullable(),
}).strict();

export const sourceItemSchema = z.object({
  slug,
  source_slug: slug,
  upstream_id: z.string().min(1).max(300).nullable(),
  logical_key: z.string().min(1).max(300),
  canonical_url: publicUrl,
  title: z.string().min(1).max(300).nullable(),
  published_at: timestamp.nullable(),
  published_timezone: z.string().min(1).max(80).nullable(),
  observed_at: timestamp,
  updated_at_source: timestamp.nullable(),
  language: z.string().min(2).max(16).nullable(),
  content_hash: sha256.nullable(),
  content_hash_input: z.string().min(1).max(200_000).nullable(),
  content_version: z.number().int().positive(),
  content_reference: z.string().min(1).max(300),
  metadata: z.record(z.string(), z.unknown()),
  collection_status: z.enum(COLLECTION_STATUSES),
  availability: z.enum(AVAILABILITY_STATUSES),
  is_current: z.boolean(),
  ingestion_run_slug: slug.nullable(),
}).strict().refine((value) => value.content_hash !== null || value.content_hash_input !== null, {
  message: "source item requires content_hash or content_hash_input",
});

export const participantSchema = z.object({
  source_item_slug: slug,
  person_slug: slug.nullable(),
  organization_slug: slug.nullable(),
  role: z.enum(PARTICIPANT_ROLES),
  attribution_method: z.enum(ATTRIBUTION_METHODS),
  attribution_detail: detail,
  confidence_level: confidenceLevel,
}).strict().refine((value) => value.person_slug || value.organization_slug, {
  message: "participant requires a person or organization",
});

export const evidenceSchema = z.object({
  slug,
  source_item_slug: slug,
  segment_kind: z.enum(SEGMENT_KINDS),
  sequence: z.number().int().positive(),
  start_char: z.number().int().nonnegative().nullable(),
  end_char: z.number().int().nonnegative().nullable(),
  start_ms: z.number().int().nonnegative().nullable(),
  end_ms: z.number().int().nonnegative().nullable(),
  text: z.string().min(1).max(2000),
  context_text: z.string().max(800).nullable(),
}).strict();

export const topicSchema = z.object({
  slug,
  name: z.string().min(1).max(160),
  definition: z.string().min(1).max(1200),
  parent_slug: slug.nullable(),
  version: z.string().min(1).max(40),
}).strict();

export const statementSchema = z.object({
  slug,
  person_slug: slug,
  source_item_slug: slug,
  statement_type: z.enum(STATEMENT_TYPES),
  normalized_text: z.string().min(1).max(600),
  event_time: timestamp.nullable(),
  evidence_slug: slug,
  extractor_version: z.string().min(1).max(80),
  confidence,
  review_state: z.enum(REVIEW_STATES),
  extraction_run_slug: slug.nullable(),
  topic_slugs: z.array(slug).min(1).max(8),
  topic_method: z.string().min(1).max(80),
  topic_confidence: confidence,
}).strict();

export const forecastSchema = z.object({
  statement_slug: slug,
  forecast_kind: z.enum(FORECAST_KINDS),
  question_key: z.string().min(1).max(120),
  question_text: z.string().min(1).max(600),
  definition_text: z.string().min(1).max(800).nullable(),
  condition_text: z.string().max(400).nullable(),
  target_date_start: dateOnly.nullable(),
  target_date_end: dateOnly.nullable(),
  horizon_text: z.string().min(1).max(160).nullable(),
  value_type: z.enum(VALUE_TYPES),
  value_text: z.string().max(40).nullable(),
  value_numeric: z.number().nullable(),
  value_min: z.number().nullable(),
  value_max: z.number().nullable(),
  unit: z.string().min(1).max(40).nullable(),
  distribution: z.record(z.string(), z.unknown()).nullable(),
  resolution_criteria: z.string().max(600).nullable(),
  review_state: z.enum(REVIEW_STATES),
}).strict().superRefine((value, ctx) => {
  const numericFilled =
    value.value_numeric !== null ||
    value.value_min !== null ||
    value.value_max !== null ||
    value.distribution !== null;
  if (value.value_type === "none" && numericFilled) {
    ctx.addIssue({
      code: "custom",
      message: "value_type none cannot carry numeric values",
      path: ["value_type"],
    });
  }
  if (value.value_type === "point" && value.value_numeric === null) {
    ctx.addIssue({ code: "custom", message: "point forecast requires value_numeric", path: ["value_numeric"] });
  }
  if (value.value_type === "range" && (value.value_min === null || value.value_max === null)) {
    ctx.addIssue({ code: "custom", message: "range forecast requires value_min and value_max", path: ["value_min"] });
  }
  if (
    value.value_min !== null &&
    value.value_max !== null &&
    value.value_min > value.value_max
  ) {
    ctx.addIssue({ code: "custom", message: "value_min exceeds value_max", path: ["value_min"] });
  }
  if (value.unit === "probability") {
    for (const [key, numeric] of [
      ["value_numeric", value.value_numeric],
      ["value_min", value.value_min],
      ["value_max", value.value_max],
    ] as const) {
      if (numeric !== null && (numeric < 0 || numeric > 1)) {
        ctx.addIssue({ code: "custom", message: "probability must be between 0 and 1", path: [key] });
      }
    }
  }
});

export const relationshipSchema = z.object({
  from_statement_slug: slug,
  to_statement_slug: slug,
  relationship_type: z.enum(RELATIONSHIP_TYPES),
  method: z.string().min(1).max(80),
  confidence,
  review_state: z.enum(REVIEW_STATES),
}).strict().refine((value) => value.from_statement_slug !== value.to_statement_slug, {
  message: "a statement cannot relate to itself",
});

export const cohortSchema = z.object({
  slug,
  version: z.string().min(1).max(40),
  name: z.string().min(1).max(200),
  definition: z.string().min(1).max(1200),
  member_slugs: z.array(slug).min(1),
}).strict();

export const ingestionRunSchema = z.object({
  slug,
  collector: z.string().min(1).max(120),
  source_slug: slug.nullable(),
  started_at: timestamp,
  completed_at: timestamp.nullable(),
  status: z.enum(["running", "succeeded", "partial", "failed"]),
  cursor_before: z.string().max(200).nullable(),
  cursor_after: z.string().max(200).nullable(),
  observed_count: z.number().int().nonnegative(),
  new_count: z.number().int().nonnegative(),
  changed_count: z.number().int().nonnegative(),
  unchanged_count: z.number().int().nonnegative().optional(),
  skipped_count: z.number().int().nonnegative().optional(),
  failed_count: z.number().int().nonnegative().optional(),
  error_summary: z.string().max(400).nullable(),
}).strict();

export const extractionRunSchema = z.object({
  slug,
  source_item_slug: slug,
  extractor_name: z.string().min(1).max(80),
  extractor_version: z.string().min(1).max(80),
  model_provider: z.string().max(80).nullable(),
  model_name: z.string().max(80).nullable(),
  prompt_contract_version: z.string().min(1).max(40),
  started_at: timestamp,
  completed_at: timestamp.nullable(),
  status: z.enum(["running", "succeeded", "failed"]),
  input_hash: z.string().regex(/^[a-f0-9]{64}$/),
  output_hash: z.string().regex(/^[a-f0-9]{64}$/).nullable(),
}).strict();

export const distributionAggregationSchema = z.object({
  type: z.literal("explicit_numeric_distribution"),
  question_key: z.string().min(1),
  topic_slug: slug,
  sibling_topic_slugs: z.array(slug),
  statement_types: z.array(z.enum(STATEMENT_TYPES)).min(1),
  review_states: z.array(z.enum(REVIEW_STATES)).min(1),
  person_reducer: z.literal("latest_event_time"),
  require_horizon: z.boolean(),
  require_unit: z.string().min(1),
  value_type: z.literal("point"),
  conditionality: z.enum(TREND_CONDITIONALITY).optional(),
}).strict();

export const timelineAggregationSchema = z.object({
  type: z.literal("timeline_forecast"),
  question_key: z.string().min(1).max(120),
  topic_slug: slug,
  sibling_topic_slugs: z.array(slug),
  statement_types: z.array(z.enum(STATEMENT_TYPES)).min(1),
  review_states: z.array(z.enum(REVIEW_STATES)).min(1),
  person_reducer: z.literal("latest_event_time"),
  require_horizon: z.boolean(),
  require_unit: z.literal("year"),
  accept_ranges: z.boolean(),
  conditionality: z.enum(TREND_CONDITIONALITY),
}).strict();

export const quantityAggregationSchema = z.object({
  type: z.literal("quantity_forecast"),
  question_key: z.string().min(1).max(120),
  topic_slug: slug,
  sibling_topic_slugs: z.array(slug),
  statement_types: z.array(z.enum(STATEMENT_TYPES)).min(1),
  review_states: z.array(z.enum(REVIEW_STATES)).min(1),
  person_reducer: z.literal("latest_event_time"),
  require_horizon: z.boolean(),
  require_unit: z.string().min(1).max(40),
  accept_ranges: z.boolean(),
  conditionality: z.enum(TREND_CONDITIONALITY),
}).strict();

export const revisionAggregationSchema = z.object({
  type: z.literal("historical_revision"),
  question_key: z.string().min(1).max(120),
  topic_slug: slug,
  sibling_topic_slugs: z.array(slug),
  statement_types: z.array(z.enum(STATEMENT_TYPES)).min(1),
  review_states: z.array(z.enum(REVIEW_STATES)).min(1),
  relationship_types: z.array(z.enum(["updates", "retracts"])).min(1),
  require_horizon: z.boolean(),
  require_unit: z.string().min(1).max(40),
  conditionality: z.enum(TREND_CONDITIONALITY),
}).strict();

export const volumeAggregationSchema = z.object({
  type: z.literal("count_by_topic_and_statement_type"),
  bucket: z.literal("quarter"),
  review_states: z.array(z.enum(REVIEW_STATES)).min(1),
  cohort_scoped: z.literal(true),
}).strict();

export const aggregationSchema = z.union([
  distributionAggregationSchema,
  volumeAggregationSchema,
  timelineAggregationSchema,
  quantityAggregationSchema,
  revisionAggregationSchema,
]);

export const trendDefinitionSchema = z.object({
  slug,
  name: z.string().min(1).max(200),
  topic_slug: slug.nullable(),
  method_version: z.string().min(1).max(40),
  cohort_slug: slug,
  cohort_version: z.string().min(1).max(40),
  cohort_definition: z.string().min(1).max(1200),
  aggregation: aggregationSchema,
  published: z.boolean(),
}).strict();

export const canonicalImportSchema = z.object({
  schema_version: z.literal(SCHEMA_VERSION),
  dataset_id: z.string().min(1).max(80),
  dataset_kind: z.enum(DATASET_KINDS),
  generated_at: timestamp,
  notice: z.string().min(1).max(1200),
  producer: z.object({
    name: z.string().min(1).max(80),
    version: z.string().min(1).max(40),
  }).strict().nullable(),
  organizations: z.array(organizationSchema).min(1),
  people: z.array(personSchema).min(1),
  affiliations: z.array(affiliationSchema),
  external_identities: z.array(externalIdentitySchema),
  sources: z.array(sourceSchema),
  source_items: z.array(sourceItemSchema),
  participants: z.array(participantSchema),
  evidence_segments: z.array(evidenceSchema),
  topics: z.array(topicSchema),
  statements: z.array(statementSchema),
  forecasts: z.array(forecastSchema),
  relationships: z.array(relationshipSchema),
  cohorts: z.array(cohortSchema).min(1),
  ingestion_runs: z.array(ingestionRunSchema),
  extraction_runs: z.array(extractionRunSchema),
  trend_definitions: z.array(trendDefinitionSchema),
}).strict();

export type CanonicalImport = z.infer<typeof canonicalImportSchema>;
export type ForecastInput = z.infer<typeof forecastSchema>;
export type StatementInput = z.infer<typeof statementSchema>;

const queryDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

export const statementListQuerySchema = z.object({
  cursor: z.string().min(1).max(400).optional(),
  limit: z.coerce.number().int().min(1).max(50).default(20),
  person: slug.optional(),
  organization: slug.optional(),
  source: slug.optional(),
  topic: slug.optional(),
  statement_type: z.enum(STATEMENT_TYPES).optional(),
  review_state: z.enum(REVIEW_STATES).optional(),
  from: queryDate.optional(),
  to: queryDate.optional(),
  q: z.string().trim().min(1).max(200).optional(),
  sort: z.enum(["event_time_desc", "event_time_asc"]).default("event_time_desc"),
}).strict();

export type StatementListQuery = z.infer<typeof statementListQuerySchema>;

export const peopleListQuerySchema = z.object({
  cursor: z.string().min(1).max(400).optional(),
  limit: z.coerce.number().int().min(1).max(50).default(20),
  q: z.string().trim().min(1).max(200).optional(),
  organization: slug.optional(),
  status: z.enum(PERSON_STATUSES).optional(),
}).strict();

export type PeopleListQuery = z.infer<typeof peopleListQuerySchema>;

export const pageSchema = <T extends z.ZodType>(item: T) =>
  z.object({
    data: z.array(item),
    page: z.object({
      limit: z.number().int(),
      total: z.number().int(),
      next_cursor: z.string().nullable(),
      prev_cursor: z.string().nullable(),
    }),
  });

export function parseSearchParams(
  params: URLSearchParams,
): Record<string, string> {
  const record: Record<string, string> = {};
  for (const [key, value] of params.entries()) {
    if (record[key] !== undefined) {
      throw new Error(`duplicate query parameter: ${key}`);
    }
    if (value !== "") record[key] = value;
  }
  return record;
}
