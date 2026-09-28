export type DatasetKind = "live" | "synthetic" | "unknown";

export type FreshnessCounts = {
  current: number;
  aging: number;
  stale: number;
  never_checked: number;
};

export type ReviewCounts = {
  unreviewed: number;
  machine_validated: number;
  human_verified: number;
  rejected: number;
  needs_review: number;
};

export type StatementTypeCounts = {
  explicit_numeric: number;
  explicit_qualitative: number;
  model_inferred_signal: number;
};

export type IntegrityCounts = {
  duplicate_identity_ids: number;
  multiple_current_versions: number;
  human_verified_missing_evidence: number;
  numeric_without_numeric_evidence: number;
  impossible_probability: number;
  public_statement_unavailable_source: number;
};

export type AdapterRunCounts = {
  succeeded: number;
  failed: number;
};

export type CollectionCounts = {
  attempted: number;
  succeeded: number;
  failed: number;
  unchanged: number;
  changed: number;
  new: number;
  rate_limited: number;
  failures_by_class: Record<string, number>;
  runs_by_adapter: Record<string, AdapterRunCounts>;
  failures_by_adapter: Record<string, Record<string, number>>;
  rate_limits_by_adapter: Record<string, number>;
};

export type ExtractionCounts = {
  items_processed: number;
  failures: number;
  candidates: number;
  candidates_by_type: StatementTypeCounts;
  missing_horizon: number;
  missing_definition: number;
  explicit_numeric: number;
};

export type SloInputs = {
  cadence_eligible: number;
  cadence_met: number;
  statement_bearing_sources: number;
  statement_bearing_sources_fresh: number;
};

export type OperationalSnapshot = {
  as_of: string;
  dataset_present: boolean;
  dataset_kind: DatasetKind;
  dataset_generated_at: string | null;
  latest_successful_observation: string | null;
  database_checked: boolean;
  readiness: { database: boolean };
  canonical_valid: boolean;
  import_failure_streak: number;
  collection_window_hours: number;
  cohort_size: number;
  people_with_non_academic_source: number;
  statement_bearing_people: number;
  source_count: number;
  enabled_source_count: number;
  sources_due: number;
  sources_stale: number;
  sources_never_successful: number;
  statements_by_review: ReviewCounts;
  freshness: FreshnessCounts;
  enabled_freshness: FreshnessCounts;
  stale_by_source_type: Record<string, number>;
  never_successful_by_source_type: Record<string, number>;
  collection: CollectionCounts;
  extraction: ExtractionCounts;
  integrity: IntegrityCounts;
  slo: SloInputs;
};

export function emptyFreshness(): FreshnessCounts {
  return { current: 0, aging: 0, stale: 0, never_checked: 0 };
}

export function emptyReviews(): ReviewCounts {
  return { unreviewed: 0, machine_validated: 0, human_verified: 0, rejected: 0, needs_review: 0 };
}

export function emptyStatementTypes(): StatementTypeCounts {
  return { explicit_numeric: 0, explicit_qualitative: 0, model_inferred_signal: 0 };
}

export function emptyIntegrity(): IntegrityCounts {
  return {
    duplicate_identity_ids: 0,
    multiple_current_versions: 0,
    human_verified_missing_evidence: 0,
    numeric_without_numeric_evidence: 0,
    impossible_probability: 0,
    public_statement_unavailable_source: 0,
  };
}

export function emptyCollection(): CollectionCounts {
  return {
    attempted: 0,
    succeeded: 0,
    failed: 0,
    unchanged: 0,
    changed: 0,
    new: 0,
    rate_limited: 0,
    failures_by_class: {},
    runs_by_adapter: {},
    failures_by_adapter: {},
    rate_limits_by_adapter: {},
  };
}

export function defaultSnapshot(asOf = "1970-01-01T00:00:00.000Z"): OperationalSnapshot {
  return {
    as_of: asOf,
    dataset_present: false,
    dataset_kind: "unknown",
    dataset_generated_at: null,
    latest_successful_observation: null,
    database_checked: true,
    readiness: { database: true },
    canonical_valid: true,
    import_failure_streak: 0,
    collection_window_hours: 168,
    cohort_size: 0,
    people_with_non_academic_source: 0,
    statement_bearing_people: 0,
    source_count: 0,
    enabled_source_count: 0,
    sources_due: 0,
    sources_stale: 0,
    sources_never_successful: 0,
    statements_by_review: emptyReviews(),
    freshness: emptyFreshness(),
    enabled_freshness: emptyFreshness(),
    stale_by_source_type: {},
    never_successful_by_source_type: {},
    collection: emptyCollection(),
    extraction: {
      items_processed: 0,
      failures: 0,
      candidates: 0,
      candidates_by_type: emptyStatementTypes(),
      missing_horizon: 0,
      missing_definition: 0,
      explicit_numeric: 0,
    },
    integrity: emptyIntegrity(),
    slo: {
      cadence_eligible: 0,
      cadence_met: 0,
      statement_bearing_sources: 0,
      statement_bearing_sources_fresh: 0,
    },
  };
}

export function completeSnapshot(partial: Partial<OperationalSnapshot> = {}): OperationalSnapshot {
  const base = defaultSnapshot(partial.as_of);
  return {
    ...base,
    ...partial,
    readiness: { ...base.readiness, ...partial.readiness },
    statements_by_review: { ...base.statements_by_review, ...partial.statements_by_review },
    freshness: { ...base.freshness, ...partial.freshness },
    enabled_freshness: { ...base.enabled_freshness, ...partial.enabled_freshness },
    stale_by_source_type: partial.stale_by_source_type ?? base.stale_by_source_type,
    never_successful_by_source_type: partial.never_successful_by_source_type ?? base.never_successful_by_source_type,
    collection: {
      ...base.collection,
      ...partial.collection,
      failures_by_class: { ...base.collection.failures_by_class, ...partial.collection?.failures_by_class },
      runs_by_adapter: partial.collection?.runs_by_adapter ?? base.collection.runs_by_adapter,
      failures_by_adapter: partial.collection?.failures_by_adapter ?? base.collection.failures_by_adapter,
      rate_limits_by_adapter: partial.collection?.rate_limits_by_adapter ?? base.collection.rate_limits_by_adapter,
    },
    extraction: {
      ...base.extraction,
      ...partial.extraction,
      candidates_by_type: { ...base.extraction.candidates_by_type, ...partial.extraction?.candidates_by_type },
    },
    integrity: { ...base.integrity, ...partial.integrity },
    slo: { ...base.slo, ...partial.slo },
  };
}

export function statementTotal(snapshot: OperationalSnapshot): number {
  const reviews = snapshot.statements_by_review;
  return reviews.unreviewed + reviews.machine_validated + reviews.human_verified + reviews.rejected + reviews.needs_review;
}

export function publicStatementCount(snapshot: OperationalSnapshot): number {
  return snapshot.statements_by_review.human_verified + snapshot.statements_by_review.machine_validated;
}
