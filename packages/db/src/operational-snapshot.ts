import type { CanonicalImport } from "@pdoom/contracts";
import {
  cadenceDays,
  catalog,
  classifyAge,
  completeSnapshot,
  dbErrorClass,
  failureClass,
  inWindow,
  laterIso,
  logEvent,
  normalizeAdapter,
  setDatabaseReady,
  type CollectionCounts,
  type FreshnessCounts,
  type OperationalSnapshot,
  type ReviewCounts,
} from "@pdoom/observability";
import type pg from "pg";

const ACADEMIC = catalog.academic_source_types;
const FAILING_COLLECTION = [
  "unavailable",
  "not_found",
  "rate_limited",
  "unauthorized",
  "blocked_by_policy",
  "parser_unsupported",
  "content_too_large",
  "invalid_content",
  "collector_bug",
];
const PUBLIC_REVIEW = new Set(["human_verified", "machine_validated"]);
const HEALTHY_COLLECTION = new Set(["collected", "partial"]);

type SourceSignal = {
  source_type: string;
  collection_method: string;
  collection_adapter: string | null;
  enabled: boolean;
  last_checked_at: string | null;
  last_success_at: string | null;
  has_statement: boolean;
};

export async function loadOperationalSnapshot(
  pool: pg.Pool | pg.PoolClient,
  options: { asOf: string; windowHours: number },
): Promise<OperationalSnapshot> {
  try {
    const snapshot = await readSnapshot(pool, options);
    setDatabaseReady(true);
    return snapshot;
  } catch (error) {
    setDatabaseReady(false);
    logEvent({
      level: "error",
      operation: "operational_snapshot",
      outcome: "failed",
      error_class: dbErrorClass(error),
    });
    return completeSnapshot({
      as_of: options.asOf,
      collection_window_hours: options.windowHours,
      database_checked: true,
      readiness: { database: false },
      dataset_present: false,
      dataset_kind: "unknown",
    });
  }
}

export function snapshotFromDocument(
  doc: CanonicalImport,
  options: { asOf: string; windowHours: number },
): OperationalSnapshot {
  const cohort = doc.cohorts[0];
  const members = new Set(cohort?.member_slugs ?? []);
  const academic = new Set<string>(ACADEMIC);
  const evidenceText = new Map(doc.evidence_segments.map((segment) => [segment.slug, segment.text]));
  const forecasts = new Map<string, CanonicalImport["forecasts"]>();
  for (const forecast of doc.forecasts) {
    const list = forecasts.get(forecast.statement_slug) ?? [];
    list.push(forecast);
    forecasts.set(forecast.statement_slug, list);
  }
  const itemBySlug = new Map(doc.source_items.map((item) => [item.slug, item]));
  const reviews = emptyReviews();
  const candidates = { explicit_numeric: 0, explicit_qualitative: 0, model_inferred_signal: 0 };
  let explicitNumeric = 0;
  let missingHorizon = 0;
  let missingDefinition = 0;
  let numericMissing = 0;
  let impossible = 0;
  let publicUnavailable = 0;
  let missingEvidence = 0;
  const bearing = new Set<string>();
  const sourcesWithStatements = new Set<string>();

  for (const forecast of doc.forecasts) {
    if (probabilityViolation(forecast)) impossible += 1;
  }

  for (const statement of doc.statements) {
    const review = reviewKey(statement.review_state);
    reviews[review] += 1;
    if (statement.review_state !== "rejected") {
      const kind = statementTypeKey(statement.statement_type);
      if (kind) candidates[kind] += 1;
      if (members.has(statement.person_slug)) bearing.add(statement.person_slug);
      const sourceSlug = itemBySlug.get(statement.source_item_slug)?.source_slug;
      if (sourceSlug) sourcesWithStatements.add(sourceSlug);
    }
    if (statement.review_state === "human_verified") {
      const text = evidenceText.get(statement.evidence_slug);
      if (!text || text.trim().length === 0) missingEvidence += 1;
    }
    if (PUBLIC_REVIEW.has(statement.review_state)) {
      const item = itemBySlug.get(statement.source_item_slug);
      if (!item || (item.availability === "unknown" && !HEALTHY_COLLECTION.has(item.collection_status))) {
        publicUnavailable += 1;
      }
    }
    if (statement.statement_type === "explicit_numeric" && statement.review_state !== "rejected") {
      explicitNumeric += 1;
      const linked = forecasts.get(statement.slug) ?? [];
      const evidence = evidenceText.get(statement.evidence_slug) ?? "";
      if (!linked.some(hasNumericValue) || !/[0-9]/.test(evidence)) numericMissing += 1;
      if (!linked.some(hasHorizon)) missingHorizon += 1;
      if (!linked.some(hasDefinition)) missingDefinition += 1;
    }
  }

  const nonAcademic = new Set<string>();
  const scoped: SourceSignal[] = [];
  for (const source of doc.sources) {
    if (source.owner_person_slug && members.has(source.owner_person_slug) && !academic.has(source.source_type)) {
      nonAcademic.add(source.owner_person_slug);
    }
    if (source.owner_person_slug !== null && !members.has(source.owner_person_slug)) continue;
    scoped.push({
      source_type: source.source_type,
      collection_method: source.collection_method,
      collection_adapter: source.collection_adapter,
      enabled: source.enabled,
      last_checked_at: source.last_checked_at,
      last_success_at: source.last_success_at,
      has_statement: sourcesWithStatements.has(source.slug),
    });
  }

  const collection = emptyCollection();
  for (const run of doc.ingestion_runs) {
    if (!inWindow(run.started_at, options.asOf, options.windowHours)) continue;
    absorbRun(collection, {
      adapter: run.collector,
      status: run.status,
      observed: run.observed_count,
      created: run.new_count,
      changed: run.changed_count,
      errorClass: run.status === "failed" ? failureClass(run.error_summary) : null,
    });
  }
  for (const item of doc.source_items) {
    if (!item.is_current || HEALTHY_COLLECTION.has(item.collection_status)) continue;
    const source = doc.sources.find((row) => row.slug === item.source_slug);
    absorbFailure(collection, source?.collection_adapter || source?.collection_method || "other", item.collection_status);
  }

  let processed = 0;
  let failures = 0;
  for (const run of doc.extraction_runs) {
    if (!inWindow(run.started_at, options.asOf, options.windowHours)) continue;
    processed += 1;
    if (run.status === "failed") failures += 1;
  }

  let latest = latestSuccess(scoped.map((source) => source.last_success_at));
  for (const run of doc.ingestion_runs) {
    if (run.status === "succeeded") latest = laterIso(latest, run.completed_at);
  }

  const identityCounts = new Map<string, number>();
  for (const identity of doc.external_identities) {
    const key = `${identity.namespace}\u0000${identity.external_id}`;
    identityCounts.set(key, (identityCounts.get(key) ?? 0) + 1);
  }
  const currentVersions = new Map<string, number>();
  for (const item of doc.source_items) {
    if (!item.is_current) continue;
    const key = `${item.source_slug}\u0000${item.logical_key}`;
    currentVersions.set(key, (currentVersions.get(key) ?? 0) + 1);
  }

  return finishSnapshot({
    asOf: options.asOf,
    windowHours: options.windowHours,
    datasetPresent: true,
    datasetKind: doc.dataset_kind,
    generatedAt: doc.generated_at,
    latest,
    databaseChecked: false,
    cohortSize: members.size,
    nonAcademic: nonAcademic.size,
    bearing: bearing.size,
    sources: scoped,
    collection,
    reviews,
    candidates,
    explicitNumeric,
    missingHorizon,
    missingDefinition,
    processed,
    failures,
    integrity: {
      duplicate_identity_ids: [...identityCounts.values()].filter((count) => count > 1).length,
      multiple_current_versions: [...currentVersions.values()].filter((count) => count > 1).length,
      human_verified_missing_evidence: missingEvidence,
      numeric_without_numeric_evidence: numericMissing,
      impossible_probability: impossible,
      public_statement_unavailable_source: publicUnavailable,
    },
  });
}

async function readSnapshot(
  pool: pg.Pool | pg.PoolClient,
  options: { asOf: string; windowHours: number },
): Promise<OperationalSnapshot> {
  const dataset = await pool.query(
    `SELECT dataset_kind, generated_at, cohort_slug, cohort_version
     FROM dataset_imports
     WHERE is_current
     ORDER BY imported_at DESC
     LIMIT 1`,
  );
  const datasetRow = dataset.rows[0] as
    | { dataset_kind: string; generated_at: Date | string; cohort_slug: string | null; cohort_version: string | null }
    | undefined;
  const scoped = Boolean(datasetRow?.cohort_slug && datasetRow.cohort_version);
  const windowStart = new Date(Date.parse(options.asOf) - options.windowHours * 3_600_000).toISOString();
  const [people, sources, statements, numeric, evidence, probability, duplicates, currents, unavailable, runs, latestRun, items, extraction] =
    await Promise.all([
      scoped
        ? pool.query(
            `SELECT count(DISTINCT p.id)::int AS cohort_size,
                    count(DISTINCT p.id) FILTER (
                      WHERE src.source_type IS NOT NULL AND NOT (src.source_type = ANY($3::text[]))
                    )::int AS non_academic,
                    count(DISTINCT p.id) FILTER (WHERE st.person_id IS NOT NULL)::int AS bearing
             FROM people p
             JOIN cohort_memberships cm ON cm.person_id = p.id
             JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
             LEFT JOIN sources src ON src.owner_person_id = p.id
             LEFT JOIN (
               SELECT DISTINCT person_id FROM statements WHERE review_state <> 'rejected'
             ) st ON st.person_id = p.id`,
            [datasetRow?.cohort_slug, datasetRow?.cohort_version, ACADEMIC],
          )
        : Promise.resolve({ rows: [{ cohort_size: 0, non_academic: 0, bearing: 0 }] }),
      pool.query(
        `SELECT src.source_type, src.collection_method, src.collection_adapter, src.enabled,
                src.last_checked_at, src.last_success_at,
                EXISTS (
                  SELECT 1 FROM source_items si
                  JOIN statements s ON s.source_item_id = si.id AND s.review_state <> 'rejected'
                  WHERE si.source_id = src.id
                ) AS has_statement
         FROM sources src
         WHERE $1::boolean AND (
           src.owner_person_id IN (
             SELECT cm.person_id FROM cohort_memberships cm
             JOIN cohorts c ON c.id = cm.cohort_id
             WHERE c.slug = $2 AND c.version = $3
           )
           OR src.owner_person_id IS NULL
         )`,
        [scoped, datasetRow?.cohort_slug ?? "", datasetRow?.cohort_version ?? ""],
      ),
      pool.query(`SELECT review_state, statement_type, count(*)::int AS count FROM statements GROUP BY 1, 2`),
      pool.query(
        `SELECT
           count(*) FILTER (WHERE s.statement_type = 'explicit_numeric' AND s.review_state <> 'rejected')::int AS explicit_numeric,
           count(*) FILTER (
             WHERE s.statement_type = 'explicit_numeric' AND s.review_state <> 'rejected'
               AND (f.id IS NULL OR (f.horizon_text IS NULL AND f.target_date_start IS NULL AND f.target_date_end IS NULL))
           )::int AS missing_horizon,
           count(*) FILTER (
             WHERE s.statement_type = 'explicit_numeric' AND s.review_state <> 'rejected'
               AND (f.id IS NULL OR f.definition_text IS NULL OR btrim(f.definition_text) = '')
           )::int AS missing_definition,
           count(*) FILTER (
             WHERE s.statement_type = 'explicit_numeric' AND s.review_state <> 'rejected'
               AND (
                 f.id IS NULL
                 OR (f.value_numeric IS NULL AND f.value_min IS NULL AND f.value_max IS NULL AND f.distribution_json IS NULL)
                 OR e.id IS NULL
                 OR e.text !~ '[0-9]'
               )
           )::int AS numeric_missing
         FROM statements s
         LEFT JOIN forecasts f ON f.statement_id = s.id
         LEFT JOIN evidence_segments e ON e.id = s.evidence_segment_id`,
      ),
      pool.query(
        `SELECT count(*)::int AS count
         FROM statements s
         LEFT JOIN evidence_segments e ON e.id = s.evidence_segment_id
         WHERE s.review_state = 'human_verified' AND (e.id IS NULL OR btrim(e.text) = '')`,
      ),
      pool.query(
        `SELECT count(*)::int AS count
         FROM forecasts
         WHERE (
           unit = 'probability' OR forecast_kind = 'probability'
         ) AND (
           (value_numeric IS NOT NULL AND (value_numeric < 0 OR value_numeric > 1))
           OR (value_min IS NOT NULL AND (value_min < 0 OR value_min > 1))
           OR (value_max IS NOT NULL AND (value_max < 0 OR value_max > 1))
           OR (value_min IS NOT NULL AND value_max IS NOT NULL AND value_min > value_max)
         )`,
      ),
      pool.query(
        `SELECT count(*)::int AS count FROM (
           SELECT 1 FROM external_identities GROUP BY namespace, external_id HAVING count(*) > 1
         ) duplicates`,
      ),
      pool.query(
        `SELECT count(*)::int AS count FROM (
           SELECT 1 FROM source_items WHERE is_current GROUP BY source_id, logical_key HAVING count(*) > 1
         ) currents`,
      ),
      pool.query(
        `SELECT count(*)::int AS count
         FROM statements s
         JOIN source_items si ON si.id = s.source_item_id
         WHERE s.review_state IN ('human_verified', 'machine_validated')
           AND si.availability = 'unknown'
           AND NOT (si.collection_status = ANY($1::text[]))`,
        [["collected", "partial"]],
      ),
      pool.query(
        `SELECT collector, status, observed_count, new_count, changed_count, error_summary
         FROM ingestion_runs
         WHERE started_at >= $1::timestamptz AND started_at <= $2::timestamptz`,
        [windowStart, options.asOf],
      ),
      pool.query(`SELECT max(completed_at) AS completed_at FROM ingestion_runs WHERE status = 'succeeded'`),
      pool.query(
        `SELECT COALESCE(src.collection_adapter, src.collection_method) AS adapter,
                si.collection_status,
                count(*)::int AS count
         FROM source_items si
         JOIN sources src ON src.id = si.source_id
         WHERE si.is_current AND si.collection_status = ANY($1::text[])
         GROUP BY 1, 2`,
        [FAILING_COLLECTION],
      ),
      pool.query(
        `SELECT status, count(*)::int AS count
         FROM extraction_runs
         WHERE started_at >= $1::timestamptz AND started_at <= $2::timestamptz
         GROUP BY 1`,
        [windowStart, options.asOf],
      ),
    ]);

  const sourceRows: SourceSignal[] = sources.rows.map((row) => ({
    source_type: String(row.source_type),
    collection_method: String(row.collection_method),
    collection_adapter: row.collection_adapter ? String(row.collection_adapter) : null,
    enabled: Boolean(row.enabled),
    last_checked_at: iso(row.last_checked_at),
    last_success_at: iso(row.last_success_at),
    has_statement: Boolean(row.has_statement),
  }));
  const reviews = emptyReviews();
  const candidates = { explicit_numeric: 0, explicit_qualitative: 0, model_inferred_signal: 0 };
  for (const row of statements.rows) {
    const count = number(row.count);
    const review = reviewKey(String(row.review_state));
    reviews[review] += count;
    if (row.review_state === "rejected") continue;
    const kind = statementTypeKey(String(row.statement_type));
    if (kind) candidates[kind] += count;
  }
  const collection = emptyCollection();
  for (const row of runs.rows) {
    absorbRun(collection, {
      adapter: String(row.collector),
      status: String(row.status),
      observed: number(row.observed_count),
      created: number(row.new_count),
      changed: number(row.changed_count),
      errorClass: row.status === "failed" ? failureClass(row.error_summary ? String(row.error_summary) : null) : null,
    });
  }
  for (const row of items.rows) {
    const count = number(row.count);
    for (let index = 0; index < count; index += 1) {
      absorbFailure(collection, String(row.adapter), String(row.collection_status));
    }
  }
  let processed = 0;
  let failures = 0;
  for (const row of extraction.rows) {
    const count = number(row.count);
    processed += count;
    if (row.status === "failed") failures += count;
  }
  const peopleRow = people.rows[0] ?? {};
  const numericRow = numeric.rows[0] ?? {};
  const latest = laterIso(latestSuccess(sourceRows.map((source) => source.last_success_at)), iso(latestRun.rows[0]?.completed_at));
  const kind = datasetRow?.dataset_kind === "live" || datasetRow?.dataset_kind === "synthetic" ? datasetRow.dataset_kind : "unknown";
  return finishSnapshot({
    asOf: options.asOf,
    windowHours: options.windowHours,
    datasetPresent: Boolean(datasetRow),
    datasetKind: kind,
    generatedAt: datasetRow ? iso(datasetRow.generated_at) : null,
    latest,
    databaseChecked: true,
    cohortSize: number(peopleRow.cohort_size),
    nonAcademic: number(peopleRow.non_academic),
    bearing: number(peopleRow.bearing),
    sources: sourceRows,
    collection,
    reviews,
    candidates,
    explicitNumeric: number(numericRow.explicit_numeric),
    missingHorizon: number(numericRow.missing_horizon),
    missingDefinition: number(numericRow.missing_definition),
    processed,
    failures,
    integrity: {
      duplicate_identity_ids: number(duplicates.rows[0]?.count),
      multiple_current_versions: number(currents.rows[0]?.count),
      human_verified_missing_evidence: number(evidence.rows[0]?.count),
      numeric_without_numeric_evidence: number(numericRow.numeric_missing),
      impossible_probability: number(probability.rows[0]?.count),
      public_statement_unavailable_source: number(unavailable.rows[0]?.count),
    },
  });
}

function finishSnapshot(input: {
  asOf: string;
  windowHours: number;
  datasetPresent: boolean;
  datasetKind: OperationalSnapshot["dataset_kind"];
  generatedAt: string | null;
  latest: string | null;
  databaseChecked: boolean;
  cohortSize: number;
  nonAcademic: number;
  bearing: number;
  sources: SourceSignal[];
  collection: CollectionCounts;
  reviews: ReviewCounts;
  candidates: OperationalSnapshot["extraction"]["candidates_by_type"];
  explicitNumeric: number;
  missingHorizon: number;
  missingDefinition: number;
  processed: number;
  failures: number;
  integrity: OperationalSnapshot["integrity"];
}): OperationalSnapshot {
  const freshness = emptyFreshness();
  const enabledFreshness = emptyFreshness();
  const staleByType: Record<string, number> = {};
  const neverByType: Record<string, number> = {};
  let enabled = 0;
  let due = 0;
  let stale = 0;
  let never = 0;
  let eligible = 0;
  let met = 0;
  let statementSources = 0;
  let statementSourcesFresh = 0;
  for (const source of input.sources) {
    const state = classifyAge(source.last_success_at, input.asOf);
    freshness[state] += 1;
    if (source.has_statement) {
      statementSources += 1;
      if (state === "current" || state === "aging") statementSourcesFresh += 1;
    }
    if (!source.enabled) continue;
    enabled += 1;
    enabledFreshness[state] += 1;
    const sourceType = allowedSourceType(source.source_type);
    if (state === "stale") {
      stale += 1;
      staleByType[sourceType] = (staleByType[sourceType] ?? 0) + 1;
    }
    if (!source.last_success_at) {
      never += 1;
      neverByType[sourceType] = (neverByType[sourceType] ?? 0) + 1;
    }
    const cadence = cadenceDays(source.source_type, source.collection_method);
    if (cadence === null) continue;
    eligible += 1;
    const successAge = ageInDays(source.last_success_at, input.asOf);
    if (successAge !== null && successAge <= cadence) met += 1;
    const checkedAge = ageInDays(source.last_checked_at, input.asOf);
    if (checkedAge === null || checkedAge > cadence) due += 1;
  }
  return completeSnapshot({
    as_of: input.asOf,
    collection_window_hours: input.windowHours,
    dataset_present: input.datasetPresent,
    dataset_kind: input.datasetKind,
    dataset_generated_at: input.generatedAt,
    latest_successful_observation: input.latest,
    database_checked: input.databaseChecked,
    readiness: { database: true },
    canonical_valid: true,
    cohort_size: input.cohortSize,
    people_with_non_academic_source: input.nonAcademic,
    statement_bearing_people: input.bearing,
    source_count: input.sources.length,
    enabled_source_count: enabled,
    sources_due: due,
    sources_stale: stale,
    sources_never_successful: never,
    statements_by_review: input.reviews,
    freshness,
    enabled_freshness: enabledFreshness,
    stale_by_source_type: staleByType,
    never_successful_by_source_type: neverByType,
    collection: input.collection,
    extraction: {
      items_processed: input.processed,
      failures: input.failures,
      candidates: input.candidates.explicit_numeric + input.candidates.explicit_qualitative + input.candidates.model_inferred_signal,
      candidates_by_type: input.candidates,
      missing_horizon: input.missingHorizon,
      missing_definition: input.missingDefinition,
      explicit_numeric: input.explicitNumeric,
    },
    integrity: input.integrity,
    slo: {
      cadence_eligible: eligible,
      cadence_met: met,
      statement_bearing_sources: statementSources,
      statement_bearing_sources_fresh: statementSourcesFresh,
    },
  });
}

function absorbRun(
  collection: CollectionCounts,
  run: { adapter: string; status: string; observed: number; created: number; changed: number; errorClass: string | null },
): void {
  const adapter = normalizeAdapter(run.adapter);
  collection.attempted += 1;
  const slot = collection.runs_by_adapter[adapter] ?? { succeeded: 0, failed: 0 };
  if (run.status === "succeeded") {
    collection.succeeded += 1;
    collection.unchanged += Math.max(0, run.observed - run.created - run.changed);
    collection.changed += run.changed;
    collection.new += run.created;
    slot.succeeded += 1;
  } else if (run.status === "failed") {
    collection.failed += 1;
    slot.failed += 1;
    absorbFailure(collection, adapter, run.errorClass ?? "unclassified");
  }
  collection.runs_by_adapter[adapter] = slot;
}

function absorbFailure(collection: CollectionCounts, adapterValue: string, classValue: string): void {
  const adapter = normalizeAdapter(adapterValue);
  const klass = failureClass(classValue);
  collection.failures_by_class[klass] = (collection.failures_by_class[klass] ?? 0) + 1;
  const byAdapter = collection.failures_by_adapter[adapter] ?? {};
  byAdapter[klass] = (byAdapter[klass] ?? 0) + 1;
  collection.failures_by_adapter[adapter] = byAdapter;
  if (klass === "rate_limited") {
    collection.rate_limited += 1;
    collection.rate_limits_by_adapter[adapter] = (collection.rate_limits_by_adapter[adapter] ?? 0) + 1;
  }
}

function emptyReviews(): ReviewCounts {
  return { unreviewed: 0, machine_validated: 0, human_verified: 0, rejected: 0, needs_review: 0 };
}

function emptyFreshness(): FreshnessCounts {
  return { current: 0, aging: 0, stale: 0, never_checked: 0 };
}

function emptyCollection(): CollectionCounts {
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

function reviewKey(value: string): keyof ReviewCounts {
  if (value in emptyReviews()) return value as keyof ReviewCounts;
  return "unreviewed";
}

function statementTypeKey(value: string): keyof OperationalSnapshot["extraction"]["candidates_by_type"] | null {
  if (value === "explicit_numeric" || value === "explicit_qualitative" || value === "model_inferred_signal") return value;
  return null;
}

function allowedSourceType(value: string): string {
  return (catalog.labels.source_type as readonly string[]).includes(value) ? value : "other";
}

function ageInDays(timestamp: string | null, asOf: string): number | null {
  if (!timestamp) return null;
  const at = Date.parse(timestamp);
  const end = Date.parse(asOf);
  if (Number.isNaN(at) || Number.isNaN(end)) return null;
  return (end - at) / 86_400_000;
}

function latestSuccess(values: Array<string | null>): string | null {
  return values.reduce<string | null>((latest, value) => laterIso(latest, value), null);
}

function hasNumericValue(forecast: CanonicalImport["forecasts"][number]): boolean {
  return forecast.value_numeric !== null || forecast.value_min !== null || forecast.value_max !== null || forecast.distribution !== null;
}

function hasHorizon(forecast: CanonicalImport["forecasts"][number]): boolean {
  return Boolean(forecast.horizon_text || forecast.target_date_start || forecast.target_date_end);
}

function hasDefinition(forecast: CanonicalImport["forecasts"][number]): boolean {
  return Boolean(forecast.definition_text && forecast.definition_text.trim());
}

function probabilityViolation(forecast: CanonicalImport["forecasts"][number]): boolean {
  const probability = forecast.unit === "probability" || forecast.forecast_kind === "probability";
  if (!probability) return false;
  if (forecast.value_min !== null && forecast.value_max !== null && forecast.value_min > forecast.value_max) return true;
  return [forecast.value_numeric, forecast.value_min, forecast.value_max].some((value) => value !== null && (value < 0 || value > 1));
}

function iso(value: Date | string | null | undefined): string | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function number(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}
