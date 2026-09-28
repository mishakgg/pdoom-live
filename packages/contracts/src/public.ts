import { z } from "zod";
import { RESEARCH_REVIEW_STATES, STATEMENT_TYPES, type ResearchReviewState, type ReviewState } from "./enums";
import { reviewPresentation } from "./review";

/** Public export document version. Independent of the canonical import schema version. */
export const PUBLIC_EXPORT_SCHEMA_VERSION = "1.0.0";
export const PUBLIC_API_VERSION = "v1";

export const RESEARCH_EXCLUDED_REVIEW_STATES = ["rejected", "unreviewed", "needs_review"] as const;

export const PUBLIC_API_LIMITS = {
  maxQueryStringLength: 2048,
  maxPageSize: 50,
  defaultPageSize: 20,
  minSearchLength: 2,
  maxSearchLength: 120,
  maxSearchTerms: 8,
  maxCursorLength: 400,
  maxSourceItemsOnDetail: 50,
  searchPeople: 5,
  searchStatements: 8,
  searchTopics: 5,
  rateLimitPerMinute: 600,
  rateWindowMs: 60_000,
  processRateLimitPerMinute: 3000,
} as const;

export const PUBLIC_METHODOLOGY = {
  cohortMethodologyRef: "docs/COHORT_METHODOLOGY.md",
  cohortMethodologyVersion: "2026.09.0",
  provenancePolicyRef: "docs/SOURCE_AND_PROVENANCE_POLICY.md",
  publicApiRef: "docs/PUBLIC_API.md",
  ingestionContractRef: "docs/INGESTION_CONTRACT.md",
} as const;

export const PUBLIC_API_PATHS = [
  "/api/v1/dataset",
  "/api/v1/people",
  "/api/v1/people/{slug}",
  "/api/v1/statements",
  "/api/v1/statements/{slug}",
  "/api/v1/topics",
  "/api/v1/topics/{slug}",
  "/api/v1/sources",
  "/api/v1/sources/{slug}",
  "/api/v1/source-items/{slug}",
  "/api/v1/trends",
  "/api/v1/trends/{slug}",
  "/api/v1/search",
  "/api/v1/openapi.json",
] as const;

const slug = z
  .string()
  .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)
  .max(80);
const queryDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const cursor = z.string().min(1).max(PUBLIC_API_LIMITS.maxCursorLength);
const limit = z.coerce.number().int().min(1).max(PUBLIC_API_LIMITS.maxPageSize).default(PUBLIC_API_LIMITS.defaultPageSize);

export const publicSearchTextSchema = z
  .string()
  .trim()
  .min(PUBLIC_API_LIMITS.minSearchLength)
  .max(PUBLIC_API_LIMITS.maxSearchLength)
  .refine((value) => /[\p{L}\p{N}]/u.test(value), "Search text must include a letter or number.")
  .refine((value) => value.split(/\s+/).length <= PUBLIC_API_LIMITS.maxSearchTerms, "Search text has too many terms.")
  .refine((value) => !/[%_]/.test(value), "Search text cannot include wildcard characters.");

export const publicPeopleQuerySchema = z
  .object({
    cursor: cursor.optional(),
    limit,
    q: publicSearchTextSchema.optional(),
    organization: slug.optional(),
    status: z.enum(["active", "historical"]).optional(),
  })
  .strict();

export const publicStatementQuerySchema = z
  .object({
    cursor: cursor.optional(),
    limit,
    person: slug.optional(),
    organization: slug.optional(),
    source: slug.optional(),
    topic: slug.optional(),
    statement_type: z.enum(STATEMENT_TYPES).optional(),
    review_state: z.enum(RESEARCH_REVIEW_STATES).optional(),
    from: queryDate.optional(),
    to: queryDate.optional(),
    q: publicSearchTextSchema.optional(),
    sort: z.enum(["event_time_desc", "event_time_asc"]).default("event_time_desc"),
  })
  .strict()
  .superRefine((value, ctx) => {
    if (value.from && value.to && value.from > value.to) {
      ctx.addIssue({ code: "custom", message: "from is after to", path: ["from"] });
    }
  });

export const publicPageQuerySchema = z
  .object({
    cursor: cursor.optional(),
    limit,
  })
  .strict();

export const publicSearchQuerySchema = z
  .object({
    q: publicSearchTextSchema,
  })
  .strict();

export type PublicPeopleQuery = z.infer<typeof publicPeopleQuerySchema>;
export type PublicStatementQuery = z.infer<typeof publicStatementQuerySchema>;
export type PublicPageQuery = z.infer<typeof publicPageQuerySchema>;

export type PublicReviewFields = {
  review_state: ResearchReviewState;
  verified: boolean;
  machine_labeled: boolean;
};

export function isResearchPublicReviewState(state: string): state is ResearchReviewState {
  return (RESEARCH_REVIEW_STATES as readonly string[]).includes(state);
}

/** Machine-validated stays unverified. Human-verified is the only verified public state. */
export function publicReviewFields(state: ReviewState | string): PublicReviewFields {
  if (!isResearchPublicReviewState(state)) {
    throw new Error("review state is not in the public research dataset");
  }
  const presentation = reviewPresentation(state);
  return {
    review_state: state,
    verified: presentation.verified,
    machine_labeled: presentation.machine_labeled,
  };
}

export function publicLicense(datasetKind: string | null): { status: "cc0-1.0" | "pending"; note: string } {
  if (datasetKind === "synthetic") {
    return {
      status: "cc0-1.0",
      note: "This snapshot was generated from a synthetic fixture. Records under data/ are dedicated under CC0 1.0 and are not statements by real researchers. Short excerpts are synthetic. The pdoom.live software is separately licensed under PolyForm Shield 1.0.0 and is not part of this data export.",
    };
  }
  return {
    status: "pending",
    note: "A public license for redistribution of the live pdoom.live dataset is pending. This export includes short evidence excerpts for verification. Those excerpts may remain under the copyright of the original source. This export is not permission to republish full articles, transcripts, or books. The pdoom.live software is separately licensed under PolyForm Shield 1.0.0 and is not part of this data export.",
  };
}

export const PUBLIC_PEOPLE_CSV_COLUMNS = [
  "slug",
  "display_name",
  "given_name",
  "family_name",
  "status",
  "in_current_cohort",
  "inclusion_reason",
  "organization_slug",
  "organization_name",
  "organization_role",
] as const;

export const PUBLIC_STATEMENT_CSV_COLUMNS = [
  "slug",
  "person_slug",
  "person_display_name",
  "statement_type",
  "review_state",
  "verified",
  "machine_labeled",
  "event_time",
  "normalized_text",
  "source_slug",
  "source_item_slug",
  "canonical_url",
  "evidence_slug",
  "evidence_segment_hash",
  "topic_slugs",
  "question_key",
  "question_text",
  "definition_text",
  "condition_text",
  "horizon_text",
  "unit",
  "value_type",
  "value_numeric",
  "value_min",
  "value_max",
] as const;

export const PUBLIC_FORECAST_CSV_COLUMNS = [
  "statement_slug",
  "person_slug",
  "person_display_name",
  "statement_type",
  "review_state",
  "verified",
  "machine_labeled",
  "forecast_kind",
  "question_key",
  "question_text",
  "definition_text",
  "condition_text",
  "horizon_text",
  "target_date_start",
  "target_date_end",
  "value_type",
  "value_numeric",
  "value_min",
  "value_max",
  "unit",
  "event_time",
  "canonical_url",
  "source_item_slug",
] as const;
