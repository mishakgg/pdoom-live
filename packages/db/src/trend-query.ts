import {
  COMPARABILITY_POLICY_VERSION,
  CURRENT_CORPUS_HISTORY,
  RESEARCH_REVIEW_STATES,
  aggregationSchema,
  distributionAggregationSchema,
  quantityAggregationSchema,
  revisionAggregationSchema,
  timelineAggregationSchema,
  volumeAggregationSchema,
  type HistoryClaim,
  type TrendConditionality,
  type TrendDensity,
} from "@pdoom/contracts";
import type pg from "pg";
import { PREPARED_TRENDS, crossSectionQuestionKeys, type PreparedTrend } from "./trend-catalog";
import {
  computeHistoricalRevision,
  computeProbabilityDistribution,
  computeQuantityForecast,
  computeStatementVolume,
  computeTimelineForecast,
  discoverQualitativeGroups,
  discoverQuestionTrends,
  listUnpooledForecasts,
  type DiscoveredTrend,
  type NumericTrendResult,
  type QualitativeGroup,
  type RevisionEdge,
  type RevisionResult,
  type TrendCandidate,
  type TrendScope,
  type UnpooledForecast,
  type VolumeRow,
} from "./trend-engine";
import { effectiveReviewStateSql } from "./coverage";
import { getPool } from "./pool";

export type TrendSource = "published_definition" | "prepared_method" | "discovered_question";

type CohortRef = {
  slug: string;
  version: string;
  definition: string;
  dataset_kind: string | null;
};

type TrendHeader = {
  slug: string;
  name: string;
  method_version: string;
  source: TrendSource;
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  calculated_at: string;
  density: TrendDensity;
  question_key: string | null;
  exact_question_id: string | null;
  comparability_policy_version: typeof COMPARABILITY_POLICY_VERSION;
  history: HistoryClaim;
  contributing_person_count: number;
  contributing_statement_count: number;
  cohort_size: number;
};

export type VolumeTrend = TrendHeader & {
  kind: "volume";
  volume: {
    rows: VolumeRow[];
    exclusions: NumericTrendResult["exclusions"];
    contributing_statement_count: number;
    contributing_person_count: number;
    contributing_people: Array<{ person_slug: string; display_name: string }>;
    coverage: {
      cohort_size: number;
      cohort_members_with_included_estimate: number;
      cohort_members_without_included_estimate: number;
      missingness_note: string;
    };
  };
};

export type QualitativeTrend = TrendHeader & {
  kind: "qualitative";
  qualitative: {
    question_key: string;
    definition_text: string;
    note: string;
    rows: QualitativeGroup["rows"];
  };
};

export type InspectionTrend = TrendHeader & {
  kind: "inspection";
  inspection: {
    note: string;
    rows: UnpooledForecast[];
  };
};

export type PublicTrend =
  | (TrendHeader & { kind: "distribution"; distribution: NumericTrendResult })
  | (TrendHeader & { kind: "timeline"; timeline: NumericTrendResult })
  | (TrendHeader & { kind: "quantity"; quantity: NumericTrendResult })
  | (TrendHeader & { kind: "revision"; revision: RevisionResult })
  | QualitativeTrend
  | InspectionTrend
  | VolumeTrend;

type MethodSpec = {
  slug: string;
  name: string;
  method_version: string;
  source: TrendSource;
  kind: "distribution" | "timeline" | "quantity" | "revision" | "volume" | "qualitative" | "inspection";
  question_key: string | null;
  question_text: string;
  definition_text: string;
  scope: TrendScope | null;
  accept_ranges: boolean;
  relationship_types: string[];
  volume_review_states: string[] | null;
};

type CohortInputs = {
  cohort: CohortRef;
  size: number;
  candidates: TrendCandidate[];
  edges: RevisionEdge[];
};

function iso(value: Date | string | null): string | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function num(value: string | number | null): number | null {
  if (value === null || value === undefined) return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

const EXTINCTION_COPY = {
  question_text: "Unconditional probability of literal human extinction caused by advanced AI by the end of 2070.",
  definition_text: "Literal human extinction. Catastrophic harm, disempowerment, and conditional risk stay on their own question keys.",
};

function copyFor(questionKey: string | null, fallbackText: string | null, fallbackDefinition: string | null): { question_text: string; definition_text: string } {
  const prepared = PREPARED_TRENDS.find((trend) => trend.question_key === questionKey && trend.kind !== "revision");
  if (prepared) return { question_text: prepared.question_text, definition_text: prepared.definition_text };
  if (questionKey === "ai_extinction_unconditional_by_2070") return EXTINCTION_COPY;
  return {
    question_text: fallbackText?.trim() || questionKey || "Stored question",
    definition_text: fallbackDefinition?.trim() || "The question text is taken from the stored forecast.",
  };
}

async function currentCohort(pool: pg.Pool): Promise<CohortRef | null> {
  const result = await pool.query(
    `SELECT d.dataset_kind, d.cohort_slug, d.cohort_version, c.definition
     FROM dataset_imports d
     LEFT JOIN cohorts c ON c.slug = d.cohort_slug AND c.version = d.cohort_version
     WHERE d.is_current
     ORDER BY d.imported_at DESC
     LIMIT 1`,
  );
  const row = result.rows[0];
  if (!row?.cohort_slug || !row.cohort_version) return null;
  return {
    slug: String(row.cohort_slug),
    version: String(row.cohort_version),
    definition: row.definition ? String(row.definition) : "",
    dataset_kind: row.dataset_kind ? String(row.dataset_kind) : null,
  };
}

function trendSourceSql(alias: string, researchSources: boolean): string {
  return researchSources
    ? `${alias}.review_state IN (${RESEARCH_REVIEW_STATES.map((state) => `'${state}'`).join(", ")})`
    : `${alias}.review_state <> 'rejected'`;
}

function forecastInputSql(researchSources = false): string {
  return `SELECT s.slug AS statement_slug, p.slug AS person_slug, p.display_name, s.statement_type, ${effectiveReviewStateSql("s")} AS review_state,
            s.event_time, f.question_key, f.question_text, f.definition_text, f.condition_text, f.forecast_kind,
            f.value_type, f.value_numeric, f.value_min, f.value_max, f.unit, f.horizon_text,
            f.target_date_start, f.target_date_end, f.distribution_json, f.resolution_criteria,
            f.review_state AS forecast_review_state,
            si.observed_at AS known_at,
            (
              SELECT max(rd.reviewed_at)
              FROM review_decisions rd
              WHERE rd.statement_id = s.id AND rd.resulting_review_state = 'human_verified'
            ) AS reviewed_at,
            COALESCE(array_agg(DISTINCT t.slug) FILTER (WHERE t.slug IS NOT NULL), '{}') AS topic_slugs
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN cohort_memberships cm ON cm.person_id = p.id
     JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
     LEFT JOIN forecasts f ON f.statement_id = s.id
     LEFT JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     LEFT JOIN statement_topics st ON st.statement_id = s.id
     LEFT JOIN topics t ON t.id = st.topic_id
     WHERE ${trendSourceSql("src", researchSources)}
     GROUP BY s.id, p.slug, p.display_name, f.question_key, f.question_text, f.definition_text, f.condition_text,
              f.forecast_kind, f.value_type, f.value_numeric, f.value_min, f.value_max, f.unit, f.horizon_text, f.review_state,
              f.target_date_start, f.target_date_end, f.distribution_json, f.resolution_criteria, si.observed_at`;
}

export const FORECAST_INPUT_SQL = forecastInputSql();

function dateOnly(value: unknown): string | null {
  if (!value) return null;
  if (typeof value === "string") {
    const match = /^(\d{4}-\d{2}-\d{2})/.exec(value.trim());
    return match?.[1] ?? null;
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${value.getFullYear()}-${month}-${day}`;
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value) return null;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as Record<string, unknown> : null;
    } catch {
      return null;
    }
  }
  return typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

export function mapForecastRow(row: Record<string, unknown>): TrendCandidate {
  const distribution = asRecord(row.distribution_json);
  const nestedSemantics = distribution && typeof distribution.probability_semantics === "string" ? distribution.probability_semantics : null;
  return {
    statement_slug: String(row.statement_slug),
    person_slug: String(row.person_slug),
    display_name: String(row.display_name),
    statement_type: String(row.statement_type),
    review_state: String(row.review_state),
    forecast_review_state: row.forecast_review_state ? String(row.forecast_review_state) : null,
    topic_slugs: Array.isArray(row.topic_slugs) ? row.topic_slugs.map((topic) => String(topic)) : [],
    question_key: row.question_key ? String(row.question_key) : null,
    question_text: row.question_text ? String(row.question_text) : null,
    definition_text: row.definition_text ? String(row.definition_text) : null,
    condition_text: row.condition_text ? String(row.condition_text) : null,
    forecast_kind: row.forecast_kind ? String(row.forecast_kind) : null,
    value_type: row.value_type ? String(row.value_type) : null,
    value_numeric: num(row.value_numeric as string | number | null),
    value_min: num(row.value_min as string | number | null),
    value_max: num(row.value_max as string | number | null),
    unit: row.unit ? String(row.unit) : null,
    horizon_text: row.horizon_text ? String(row.horizon_text) : null,
    target_date_start: dateOnly(row.target_date_start),
    target_date_end: dateOnly(row.target_date_end),
    distribution,
    probability_semantics: nestedSemantics,
    resolution_criteria: row.resolution_criteria ? String(row.resolution_criteria) : null,
    known_at: iso(row.known_at as Date | string | null),
    reviewed_at: iso(row.reviewed_at as Date | string | null),
    event_time: iso(row.event_time as Date | string | null),
  };
}

async function loadInputs(pool: pg.Pool, cohort: CohortRef, researchSources = false): Promise<CohortInputs> {
  const size = await pool.query(
    `SELECT count(*)::int AS count
     FROM cohort_memberships cm JOIN cohorts c ON c.id = cm.cohort_id
     WHERE c.slug = $1 AND c.version = $2`,
    [cohort.slug, cohort.version],
  );
  const forecasts = await pool.query(forecastInputSql(researchSources), [cohort.slug, cohort.version]);
  const edges = await pool.query(
    `SELECT fs.slug AS from_statement_slug, ts.slug AS to_statement_slug, r.relationship_type, r.review_state, r.method
     FROM statement_relationships r
     JOIN statements fs ON fs.id = r.from_statement_id
     JOIN statements ts ON ts.id = r.to_statement_id
     JOIN source_items fsi ON fsi.id = fs.source_item_id
     JOIN sources fsrc ON fsrc.id = fsi.source_id
     JOIN source_items tsi ON tsi.id = ts.source_item_id
     JOIN sources tsrc ON tsrc.id = tsi.source_id
     JOIN cohort_memberships cm ON cm.person_id = fs.person_id
     JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
     WHERE ${trendSourceSql("fsrc", researchSources)} AND ${trendSourceSql("tsrc", researchSources)}
     ORDER BY fs.slug, ts.slug, r.relationship_type`,
    [cohort.slug, cohort.version],
  );
  return {
    cohort,
    size: Number(size.rows[0]?.count ?? 0),
    candidates: forecasts.rows.map((row) => mapForecastRow(row as Record<string, unknown>)),
    edges: edges.rows.map((row) => ({
      from_statement_slug: String(row.from_statement_slug),
      to_statement_slug: String(row.to_statement_slug),
      relationship_type: String(row.relationship_type),
      review_state: String(row.review_state),
      method: String(row.method),
    })),
  };
}

function conditionalityOf(value: unknown): TrendConditionality {
  if (value === "unconditional" || value === "conditional" || value === "unspecified") return value;
  return "unspecified";
}

function scopeFrom(input: {
  question_key: string;
  topic_slug: string;
  sibling_topic_slugs: string[];
  statement_types: string[];
  review_states: string[];
  require_horizon: boolean;
  require_unit: string;
  conditionality?: TrendConditionality;
}): TrendScope {
  return {
    topic_slug: input.topic_slug,
    sibling_topic_slugs: input.sibling_topic_slugs,
    question_key: input.question_key,
    statement_types: input.statement_types,
    review_states: input.review_states,
    require_horizon: input.require_horizon,
    require_unit: input.require_unit,
    conditionality: input.conditionality ?? "unspecified",
  };
}

async function publishedMethods(pool: pg.Pool, cohort: CohortRef): Promise<MethodSpec[]> {
  const result = await pool.query(
    `SELECT td.slug, td.name, td.method_version, td.aggregation_definition_json
     FROM trend_definitions td
     JOIN cohorts c ON c.id = td.cohort_id
     WHERE td.published AND c.slug = $1 AND c.version = $2
     ORDER BY td.slug`,
    [cohort.slug, cohort.version],
  );
  const methods: MethodSpec[] = [];
  for (const row of result.rows) {
    const parsed = aggregationSchema.parse(row.aggregation_definition_json);
    const slug = String(row.slug);
    const name = String(row.name);
    const methodVersion = String(row.method_version);
    if (parsed.type === "count_by_topic_and_statement_type") {
      methods.push({
        slug,
        name,
        method_version: methodVersion,
        source: "published_definition",
        kind: "volume",
        question_key: null,
        question_text: "Counts of statements by topic and statement class.",
        definition_text: "A count of records. Statement classes stay separate, and the count is not a probability.",
        scope: null,
        accept_ranges: false,
        relationship_types: [],
        volume_review_states: parsed.review_states,
      });
      continue;
    }
    const copy = copyFor(parsed.question_key, null, null);
    if (parsed.type === "explicit_numeric_distribution") {
      const aggregation = distributionAggregationSchema.parse(parsed);
      methods.push({
        slug,
        name,
        method_version: methodVersion,
        source: "published_definition",
        kind: "distribution",
        question_key: aggregation.question_key,
        question_text: copy.question_text,
        definition_text: copy.definition_text,
        scope: scopeFrom({ ...aggregation, conditionality: conditionalityOf(aggregation.conditionality) }),
        accept_ranges: false,
        relationship_types: [],
        volume_review_states: null,
      });
      continue;
    }
    if (parsed.type === "timeline_forecast") {
      const aggregation = timelineAggregationSchema.parse(parsed);
      methods.push({
        slug,
        name,
        method_version: methodVersion,
        source: "published_definition",
        kind: "timeline",
        question_key: aggregation.question_key,
        question_text: copy.question_text,
        definition_text: copy.definition_text,
        scope: scopeFrom(aggregation),
        accept_ranges: aggregation.accept_ranges,
        relationship_types: [],
        volume_review_states: null,
      });
      continue;
    }
    if (parsed.type === "quantity_forecast") {
      const aggregation = quantityAggregationSchema.parse(parsed);
      methods.push({
        slug,
        name,
        method_version: methodVersion,
        source: "published_definition",
        kind: "quantity",
        question_key: aggregation.question_key,
        question_text: copy.question_text,
        definition_text: copy.definition_text,
        scope: scopeFrom(aggregation),
        accept_ranges: aggregation.accept_ranges,
        relationship_types: [],
        volume_review_states: null,
      });
      continue;
    }
    const aggregation = revisionAggregationSchema.parse(parsed);
    const revisionCopy = PREPARED_TRENDS.find((trend) => trend.kind === "revision" && trend.question_key === aggregation.question_key) ?? null;
    methods.push({
      slug,
      name,
      method_version: methodVersion,
      source: "published_definition",
      kind: "revision",
      question_key: aggregation.question_key,
      question_text: revisionCopy?.question_text ?? copy.question_text,
      definition_text: revisionCopy?.definition_text ?? copy.definition_text,
      scope: scopeFrom(aggregation),
      accept_ranges: false,
      relationship_types: aggregation.relationship_types,
      volume_review_states: null,
    });
  }
  return methods;
}

function preparedToMethod(trend: PreparedTrend): MethodSpec {
  return {
    slug: trend.slug,
    name: trend.name,
    method_version: trend.method_version,
    source: "prepared_method",
    kind: trend.kind,
    question_key: trend.question_key,
    question_text: trend.question_text,
    definition_text: trend.definition_text,
    scope: trend.scope,
    accept_ranges: trend.accept_ranges,
    relationship_types: trend.relationship_types,
    volume_review_states: null,
  };
}

function discoveredToMethod(trend: DiscoveredTrend): MethodSpec {
  return {
    slug: trend.slug,
    name: trend.name,
    method_version: trend.method_version,
    source: "discovered_question",
    kind: trend.kind,
    question_key: trend.question_key,
    question_text: trend.question_text,
    definition_text: trend.definition_text,
    scope: trend.scope,
    accept_ranges: trend.accept_ranges,
    relationship_types: [],
    volume_review_states: null,
  };
}

export function trendMethodKey(method: Pick<MethodSpec, "kind" | "question_key" | "scope">): string {
  const exact = method.scope?.exact_question_id ?? method.question_key ?? "";
  const unit = method.scope?.require_unit ?? "";
  const conditionality = method.scope?.conditionality ?? "";
  return `${method.kind}\0${exact}\0${unit}\0${conditionality}`;
}

export function resolveTrendMethods(published: MethodSpec[], candidates: TrendCandidate[]): MethodSpec[] {
  const takenKeys = crossSectionQuestionKeys(
    published.filter((method) => method.question_key).map((method) => ({ kind: method.kind, question_key: method.question_key ?? "" })),
  );
  const prepared = PREPARED_TRENDS.filter((trend) => {
    if (published.some((method) => method.slug === trend.slug)) return false;
    if (trend.kind === "revision") return !published.some((method) => method.kind === "revision" && method.question_key === trend.question_key);
    return !takenKeys.has(trend.question_key);
  }).map(preparedToMethod);
  const crossSection = [...published, ...prepared].filter((method) => method.kind !== "revision" && method.kind !== "volume");
  const discovered = discoverQuestionTrends(
    candidates,
    crossSectionQuestionKeys(crossSection.map((method) => ({ kind: method.kind, question_key: method.question_key ?? "" }))),
    new Set([...published, ...prepared].map((method) => method.slug)),
  ).map(discoveredToMethod);
  const merged = [...published, ...prepared, ...discovered];
  const seen = new Set<string>();
  const unique: MethodSpec[] = [];
  for (const method of merged) {
    const key = method.kind === "volume" ? `volume\0${method.slug}` : trendMethodKey(method);
    if (seen.has(key) || seen.has(method.slug)) continue;
    seen.add(key);
    seen.add(method.slug);
    unique.push(method);
  }
  const order = ["distribution", "timeline", "quantity", "qualitative", "revision", "inspection", "volume"];
  return unique.sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind) || a.name.localeCompare(b.name) || a.slug.localeCompare(b.slug));
}

function contextFor(method: MethodSpec, inputs: CohortInputs) {
  return {
    method_version: method.method_version,
    cohort_slug: inputs.cohort.slug,
    cohort_version: inputs.cohort.version,
    cohort_definition: inputs.cohort.definition,
    cohort_size: inputs.size,
    question_text: method.question_text,
    definition_text: method.definition_text,
  };
}

function headerFor(method: MethodSpec, inputs: CohortInputs, density: TrendDensity, people: number, statements: number): TrendHeader {
  return {
    slug: method.slug,
    name: method.name,
    method_version: method.method_version,
    source: method.source,
    cohort_slug: inputs.cohort.slug,
    cohort_version: inputs.cohort.version,
    cohort_definition: inputs.cohort.definition,
    calculated_at: new Date().toISOString(),
    density,
    question_key: method.question_key,
    exact_question_id: method.scope?.exact_question_id ?? method.question_key,
    comparability_policy_version: COMPARABILITY_POLICY_VERSION,
    history: CURRENT_CORPUS_HISTORY,
    contributing_person_count: people,
    contributing_statement_count: statements,
    cohort_size: inputs.size,
  };
}

async function computeVolume(method: MethodSpec, inputs: CohortInputs, pool: pg.Pool, researchSources = false): Promise<VolumeTrend> {
  const reviewStates = method.volume_review_states ?? ["human_verified", "machine_validated"];
  const parsed = volumeAggregationSchema.parse({
    type: "count_by_topic_and_statement_type",
    bucket: "quarter",
    review_states: reviewStates,
    cohort_scoped: true,
  });
  const volumeRows = await pool.query(
    `SELECT s.slug AS statement_slug, p.slug AS person_slug, p.display_name, s.statement_type, ${effectiveReviewStateSql("s")} AS review_state, s.event_time, t.slug AS topic_slug
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN cohort_memberships cm ON cm.person_id = p.id
     JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
     JOIN statement_topics st ON st.statement_id = s.id
     JOIN topics t ON t.id = st.topic_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     WHERE ${trendSourceSql("src", researchSources)}`,
    [inputs.cohort.slug, inputs.cohort.version],
  );
  const volume = computeStatementVolume({
    review_states: parsed.review_states,
    cohort_size: inputs.size,
    rows: volumeRows.rows.map((item) => ({
      statement_slug: String(item.statement_slug),
      person_slug: String(item.person_slug),
      display_name: String(item.display_name),
      statement_type: String(item.statement_type),
      review_state: String(item.review_state),
      topic_slug: String(item.topic_slug),
      event_time: iso(item.event_time),
    })),
  });
  return {
    ...headerFor(method, inputs, volume.contributing_statement_count > 0 ? "comparable" : "empty", volume.contributing_person_count, volume.contributing_statement_count),
    kind: "volume",
    volume,
  };
}

function computeMethod(method: MethodSpec, inputs: CohortInputs): Exclude<PublicTrend, VolumeTrend> | null {
  if (!method.scope || !method.question_key) return null;
  const context = contextFor(method, inputs);
  if (method.kind === "distribution") {
    const distribution = computeProbabilityDistribution({ ...context, scope: method.scope, candidates: inputs.candidates, edges: inputs.edges });
    return { ...headerFor(method, inputs, distribution.density, distribution.contributing_person_count, distribution.contributing_statement_count), kind: "distribution", distribution };
  }
  if (method.kind === "timeline") {
    const timeline = computeTimelineForecast({
      ...context,
      scope: method.scope,
      candidates: inputs.candidates,
      edges: inputs.edges,
      accept_ranges: method.accept_ranges,
    });
    return { ...headerFor(method, inputs, timeline.density, timeline.contributing_person_count, timeline.contributing_statement_count), kind: "timeline", timeline };
  }
  if (method.kind === "quantity") {
    const quantity = computeQuantityForecast({
      ...context,
      scope: method.scope,
      candidates: inputs.candidates,
      edges: inputs.edges,
      accept_ranges: method.accept_ranges,
    });
    return { ...headerFor(method, inputs, quantity.density, quantity.contributing_person_count, quantity.contributing_statement_count), kind: "quantity", quantity };
  }
  const revision = computeHistoricalRevision({
    ...context,
    scope: method.scope,
    candidates: inputs.candidates,
    edges: inputs.edges,
    relationship_types: method.relationship_types,
  });
  return { ...headerFor(method, inputs, revision.density, revision.contributing_person_count, revision.contributing_statement_count), kind: "revision", revision };
}

const QUALITATIVE_NOTE = "These are qualitative statements. No probability is inferred from this wording.";
const INSPECTION_NOTE = "These records stay individually inspectable. They are not pooled, because the stored outcome, condition, deadline, unit, or definition does not agree closely enough with one exact question.";

function peopleFrom(rows: Array<{ person_slug: string; display_name: string }>): number {
  return new Set(rows.map((row) => row.person_slug)).size;
}

function qualitativeTrends(inputs: CohortInputs): QualitativeTrend[] {
  return discoverQualitativeGroups(inputs.candidates).map((group) => ({
    slug: group.slug,
    name: group.name,
    method_version: "qualitative-statements/1.0.0",
    source: "discovered_question",
    cohort_slug: inputs.cohort.slug,
    cohort_version: inputs.cohort.version,
    cohort_definition: inputs.cohort.definition,
    calculated_at: new Date().toISOString(),
    density: group.rows.length > 0 ? "individual" : "empty",
    question_key: group.question_key,
    exact_question_id: group.question_key,
    comparability_policy_version: COMPARABILITY_POLICY_VERSION,
    history: CURRENT_CORPUS_HISTORY,
    contributing_person_count: peopleFrom(group.rows),
    contributing_statement_count: group.rows.length,
    cohort_size: inputs.size,
    kind: "qualitative",
    qualitative: {
      question_key: group.question_key,
      definition_text: group.definition_text,
      note: QUALITATIVE_NOTE,
      rows: group.rows,
    },
  }));
}

function inspectionTrend(inputs: CohortInputs, takenQuestionKeys: Set<string>): InspectionTrend | null {
  const rows = listUnpooledForecasts(inputs.candidates, takenQuestionKeys);
  if (rows.length === 0) return null;
  return {
    slug: "unpooled-forecasts",
    name: "Forecasts that are not pooled",
    method_version: "unpooled-inspection/1.0.0",
    source: "discovered_question",
    cohort_slug: inputs.cohort.slug,
    cohort_version: inputs.cohort.version,
    cohort_definition: inputs.cohort.definition,
    calculated_at: new Date().toISOString(),
    density: "individual",
    question_key: null,
    exact_question_id: null,
    comparability_policy_version: COMPARABILITY_POLICY_VERSION,
    history: CURRENT_CORPUS_HISTORY,
    contributing_person_count: peopleFrom(rows),
    contributing_statement_count: rows.length,
    cohort_size: inputs.size,
    kind: "inspection",
    inspection: { note: INSPECTION_NOTE, rows },
  };
}

export async function loadTrendInputs(pool = getPool()): Promise<CohortInputs | null> {
  const cohort = await currentCohort(pool);
  if (!cohort) return null;
  return loadInputs(pool, cohort);
}

export async function listComputedTrends(pool = getPool(), researchSources = false): Promise<PublicTrend[]> {
  const cohort = await currentCohort(pool);
  if (!cohort) return [];
  const inputs = await loadInputs(pool, cohort, researchSources);
  const published = await publishedMethods(pool, cohort);
  const methods = resolveTrendMethods(published, inputs.candidates);
  const trends: PublicTrend[] = [];
  for (const method of methods) {
    if (method.kind === "volume") {
      trends.push(await computeVolume(method, inputs, pool, researchSources));
      continue;
    }
    const computed = computeMethod(method, inputs);
    if (computed) trends.push(computed);
  }
  trends.push(...qualitativeTrends(inputs));
  const taken = crossSectionQuestionKeys(
    methods.filter((method) => method.question_key && method.kind !== "revision" && method.kind !== "volume").map((method) => ({
      kind: method.kind,
      question_key: method.question_key ?? "",
    })),
  );
  const inspection = inspectionTrend(inputs, taken);
  if (inspection) trends.push(inspection);
  return trends;
}

export async function getTrend(slug: string, pool = getPool(), researchSources = false): Promise<PublicTrend | null> {
  const trends = await listComputedTrends(pool, researchSources);
  return trends.find((trend) => trend.slug === slug) ?? null;
}

function topicSlugOf(trend: PublicTrend): string | null {
  if (trend.kind === "distribution") return trend.distribution.topic_slug;
  if (trend.kind === "timeline") return trend.timeline.topic_slug;
  if (trend.kind === "quantity") return trend.quantity.topic_slug;
  if (trend.kind === "revision") return trend.revision.topic_slug;
  return null;
}

export async function listTrends(pool = getPool()) {
  const trends = await listComputedTrends(pool);
  return trends.map((trend) => ({
    slug: trend.slug,
    name: trend.name,
    method_version: trend.method_version,
    source: trend.source,
    kind: trend.kind,
    cohort_slug: trend.cohort_slug,
    cohort_version: trend.cohort_version,
    topic_slug: topicSlugOf(trend),
    question_key: trend.question_key,
    exact_question_id: trend.exact_question_id,
    comparability_policy_version: trend.comparability_policy_version,
    presented_as_reconstruction: trend.history.presented_as_reconstruction,
    density: trend.density,
    contributing_person_count: trend.contributing_person_count,
    contributing_statement_count: trend.contributing_statement_count,
    cohort_size: trend.cohort_size,
  }));
}
