export const STATEMENT_TYPES = [
  "explicit_numeric",
  "explicit_qualitative",
  "model_inferred_signal",
] as const;
export type StatementType = (typeof STATEMENT_TYPES)[number];

export const REVIEW_STATES = [
  "unreviewed",
  "machine_validated",
  "human_verified",
  "rejected",
  "needs_review",
] as const;
export type ReviewState = (typeof REVIEW_STATES)[number];

export const PERSON_STATUSES = ["active", "historical", "review"] as const;
export type PersonStatus = (typeof PERSON_STATUSES)[number];

export const ORGANIZATION_TYPES = [
  "frontier_lab",
  "research_institute",
  "research_lab",
  "university",
  "company",
  "publisher",
  "government",
  "nonprofit",
  "infrastructure",
  "safety_org",
  "independent",
] as const;
export type OrganizationType = (typeof ORGANIZATION_TYPES)[number];

export const SOURCE_TYPES = [
  "personal_site",
  "blog",
  "newsletter",
  "podcast",
  "video",
  "paper",
  "preprint",
  "academic_works",
  "lab_post",
  "conference_talk",
  "testimony",
  "interview",
  "repository",
  "model_card",
  "social_post",
  "press",
] as const;
export type SourceType = (typeof SOURCE_TYPES)[number];

export const COLLECTION_METHODS = ["fixture", "rss", "api", "manual", "sitemap"] as const;
export type CollectionMethod = (typeof COLLECTION_METHODS)[number];

export const COLLECTION_STATUSES = [
  "collected",
  "partial",
  "unavailable",
  "not_found",
  "rate_limited",
  "unauthorized",
  "blocked_by_policy",
  "parser_unsupported",
  "content_too_large",
  "invalid_content",
  "collector_bug",
] as const;
export type CollectionStatus = (typeof COLLECTION_STATUSES)[number];

export const AVAILABILITY_STATUSES = ["available", "removed", "unknown"] as const;
export type AvailabilityStatus = (typeof AVAILABILITY_STATUSES)[number];

export const PARTICIPANT_ROLES = [
  "author",
  "speaker",
  "guest",
  "interviewer",
  "publisher",
  "mentioned",
] as const;
export type ParticipantRole = (typeof PARTICIPANT_ROLES)[number];

export const ATTRIBUTION_METHODS = [
  "byline",
  "metadata",
  "transcript_label",
  "manual",
  "synthetic_fixture",
] as const;
export type AttributionMethod = (typeof ATTRIBUTION_METHODS)[number];

export const VERIFICATION_METHODS = [
  "self_asserted",
  "institutional_profile",
  "cross_link",
  "platform_verification",
  "manual_review",
  "structured_academic_source",
  "synthetic_fixture",
] as const;
export type VerificationMethod = (typeof VERIFICATION_METHODS)[number];

export const SEGMENT_KINDS = ["text", "transcript", "caption", "table", "metadata"] as const;
export type SegmentKind = (typeof SEGMENT_KINDS)[number];

export const FORECAST_KINDS = [
  "probability",
  "timeline",
  "quantity",
  "qualitative",
  "classification",
] as const;
export type ForecastKind = (typeof FORECAST_KINDS)[number];

export const VALUE_TYPES = ["point", "range", "distribution", "none"] as const;
export type ValueType = (typeof VALUE_TYPES)[number];

export const RELATIONSHIP_TYPES = [
  "updates",
  "clarifies",
  "retracts",
  "contradicts",
  "repeats",
] as const;
export type RelationshipType = (typeof RELATIONSHIP_TYPES)[number];

export const IDENTITY_NAMESPACES = [
  "orcid",
  "openalex",
  "openreview",
  "semantic_scholar",
  "github",
  "huggingface",
  "x",
  "bluesky",
  "mastodon",
  "personal_website",
  "lab_profile",
  "youtube",
] as const;
export type IdentityNamespace = (typeof IDENTITY_NAMESPACES)[number];

export const STATEMENT_TYPE_LABELS: Record<StatementType, string> = {
  explicit_numeric: "Explicit numerical estimate",
  explicit_qualitative: "Explicit qualitative view",
  model_inferred_signal: "Model-inferred signal",
};

export const CONFIDENCE_LEVELS = ["high", "medium", "low", "unknown"] as const;
export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];

export const DATASET_KINDS = ["synthetic", "live"] as const;
export type DatasetKind = (typeof DATASET_KINDS)[number];

export const SCHEMA_VERSION = "1.0.0";

export const PUBLIC_REVIEW_STATES = ["human_verified", "machine_validated"] as const satisfies readonly ReviewState[];
export type PublicReviewState = (typeof PUBLIC_REVIEW_STATES)[number];
