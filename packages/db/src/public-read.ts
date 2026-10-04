import {
  PUBLIC_API_LIMITS,
  PUBLIC_EXPORT_SCHEMA_VERSION,
  PUBLIC_API_VERSION,
  PUBLIC_METHODOLOGY,
  RESEARCH_EXCLUDED_REVIEW_STATES,
  RESEARCH_REVIEW_STATES,
  isResearchPublicReviewState,
  publicLicense,
  publicReviewFields,
  type PublicPageQuery,
  type PublicPeopleQuery,
  type PublicReviewFields,
  type PublicStatementQuery,
  classifyFreshness,
  type Freshness,
} from "@pdoom/contracts";
import type pg from "pg";
import { effectiveReviewStateSql } from "./coverage";
import { getPool } from "./pool";
import { InvalidCursorError } from "./queries";
import { isPool, isStatementTimeout, queryOnClient, withConsistentRead } from "./read-snapshot";
import { SearchTimeoutError } from "./search";
import type { Exclusion, RevisionResult } from "./trend-engine";
import { getTrend, listComputedTrends, type PublicTrend } from "./trend-query";

type Db = pg.Pool | pg.PoolClient;

const PUBLIC_STATES = [...RESEARCH_REVIEW_STATES];

export type PublicPage<T> = {
  data: T[];
  page: {
    limit: number;
    total: number;
    next_cursor: string | null;
    prev_cursor: string | null;
  };
};

export type PublicForecast = PublicReviewFields & {
  statement_slug: string;
  forecast_kind: string;
  question_key: string;
  question_text: string;
  definition_text: string | null;
  condition_text: string | null;
  horizon_text: string | null;
  target_date_start: string | null;
  target_date_end: string | null;
  value_type: string;
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  distribution: Record<string, unknown> | null;
  resolution_criteria: string | null;
};

export type PublicEvidence = {
  slug: string;
  segment_kind: string;
  sequence: number;
  start_char: number | null;
  end_char: number | null;
  start_ms: number | null;
  end_ms: number | null;
  segment_hash: string;
  text: string;
  text_truncated: boolean;
  context_text: string | null;
  context_truncated: boolean;
};

export type PublicRelationship = PublicReviewFields & {
  from_statement_slug: string;
  to_statement_slug: string;
  relationship_type: string;
};

export type PublicStatement = PublicReviewFields & {
  slug: string;
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  person: { slug: string; display_name: string };
  source: { slug: string; name: string; source_type: string };
  source_item: {
    slug: string;
    title: string | null;
    canonical_url: string;
    published_at: string | null;
    observed_at: string | null;
    published_timezone: string | null;
    language: string | null;
    content_hash: string;
    content_reference: string | null;
    availability: string;
    collection_status: string;
  };
  evidence: PublicEvidence;
  forecast: PublicForecast | null;
  topics: Array<{ slug: string; name: string }>;
  relationships: PublicRelationship[];
};

export type PublicStatementSummary = PublicReviewFields & {
  slug: string;
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  person: { slug: string; display_name: string };
  source: { slug: string; name: string; source_type: string };
  source_item: {
    slug: string;
    title: string | null;
    canonical_url: string;
    published_at: string | null;
    observed_at: string | null;
  };
  evidence_ref: {
    slug: string;
    segment_kind: string;
    sequence: number;
    start_char: number | null;
    end_char: number | null;
    start_ms: number | null;
    end_ms: number | null;
    segment_hash: string;
  };
  forecast: PublicForecast | null;
  topics: Array<{ slug: string; name: string }>;
};

export type PublicAffiliation = PublicReviewFields & {
  organization_slug: string;
  organization_name: string;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  confidence_level: string;
  is_current: boolean;
};

export type PublicIdentity = PublicReviewFields & {
  person_slug: string;
  namespace: string;
  external_id: string;
  canonical_url: string | null;
  handle: string | null;
  verification_method: string;
  confidence_level: string;
  verified_at: string | null;
};

export type PublicPerson = {
  slug: string;
  display_name: string;
  given_name: string | null;
  family_name: string | null;
  bio_short: string;
  status: string;
  in_current_cohort: boolean;
  inclusion_reason: string;
  cohort_tags: string[];
  updated_at: string | null;
  organization: { slug: string; name: string; role: string | null } | null;
  public_statement_counts: Record<string, number>;
  affiliations: PublicAffiliation[];
  identities: PublicIdentity[];
};

export type PublicPersonSummary = Omit<PublicPerson, "affiliations" | "identities" | "given_name" | "family_name" | "updated_at">;

export type PublicOrganization = {
  slug: string;
  name: string;
  organization_type: string;
  canonical_url: string | null;
};

export type PublicSource = PublicReviewFields & {
  slug: string;
  name: string;
  source_type: string;
  canonical_url: string;
  platform: string | null;
  owner_person_slug: string | null;
  owner_organization_slug: string | null;
  collection_method: string;
  last_success_at: string | null;
  freshness: Freshness;
  public_item_count: number;
};

export type PublicSourceItem = {
  slug: string;
  source_slug: string;
  upstream_id: string | null;
  canonical_url: string;
  title: string | null;
  published_at: string | null;
  published_timezone: string | null;
  observed_at: string | null;
  language: string | null;
  content_hash: string;
  content_version: number;
  content_reference: string | null;
  availability: string;
  collection_status: string;
  participants: Array<{
    role: string;
    attribution_method: string;
    confidence_level: string;
    person_slug: string | null;
    display_name: string | null;
    organization_slug: string | null;
  }>;
};

export type PublicTopic = {
  slug: string;
  name: string;
  definition: string;
  version: string;
  parent_slug: string | null;
  public_statement_counts: Record<string, number>;
  public_statement_total: number;
};

export type PublicDatasetStamp = {
  dataset_id: string | null;
  dataset_kind: string | null;
  imported_at: string | null;
};

type CursorPayload = { v: 1; t: string | null; id: string; dir: "next" | "prev" };

function bind(values: unknown[], value: unknown): string {
  values.push(value);
  return `$${values.length}`;
}

function encodeCursor(payload: CursorPayload): string {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function decodeCursor(cursor: string): CursorPayload {
  try {
    const parsed = JSON.parse(Buffer.from(cursor, "base64url").toString("utf8")) as CursorPayload;
    if (parsed.v !== 1 || (parsed.dir !== "next" && parsed.dir !== "prev")) throw new Error("bad");
    if (parsed.t !== null && (typeof parsed.t !== "string" || parsed.t.length > 300)) throw new Error("bad");
    if (typeof parsed.id !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(parsed.id) || parsed.id.length > 80) {
      throw new Error("bad");
    }
    return parsed;
  } catch (error) {
    if (error instanceof InvalidCursorError) throw error;
    throw new InvalidCursorError();
  }
}

function iso(value: Date | string | null): string | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function day(value: Date | string | null): string | null {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  const text = String(value);
  return /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : text;
}

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function int(value: string | number | null | undefined): number | null {
  const parsed = num(value);
  return parsed === null ? null : Math.trunc(parsed);
}

function excerpt(value: string | null, max: number): { text: string | null; truncated: boolean } {
  if (value === null) return { text: null, truncated: false };
  if (value.length <= max) return { text: value, truncated: false };
  return { text: value.slice(0, max), truncated: true };
}

function asObject(value: unknown): Record<string, unknown> | null {
  if (value === null || value === undefined) return null;
  const parsed = typeof value === "string" ? JSON.parse(value) as unknown : value;
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed as Record<string, unknown>;
  return null;
}

function asTopics(value: unknown): Array<{ slug: string; name: string }> {
  const parsed = typeof value === "string" ? JSON.parse(value) as unknown : value;
  if (!Array.isArray(parsed)) return [];
  return parsed.map((item) => {
    const topic = item as { slug?: string; name?: string };
    return { slug: String(topic.slug), name: String(topic.name) };
  });
}

function asCounts(value: unknown): Record<string, number> {
  const parsed = asObject(value) ?? {};
  const counts: Record<string, number> = {};
  for (const [key, count] of Object.entries(parsed)) counts[key] = Number(count);
  return counts;
}

function publicPersonPredicate(alias: string, publicParam: string): string {
  return `(
    ${alias}.status IN ('active', 'historical')
    OR EXISTS (
      SELECT 1 FROM statements s
      WHERE s.person_id = ${alias}.id AND ${effectiveReviewStateSql("s")} = ANY(${publicParam}::text[])
    )
  )`;
}

function pageResult<T>(input: {
  rows: T[];
  limit: number;
  total: number;
  cursor: CursorPayload | null;
  forward: boolean;
  hasExtra: boolean;
  cursorOf: (row: T) => { t: string | null; id: string };
}): PublicPage<T> {
  let data = input.rows.slice(0, input.limit);
  if (!input.forward) data = data.reverse();
  const first = data[0];
  const last = data[data.length - 1];
  const hasNext = input.forward ? input.hasExtra : Boolean(input.cursor);
  const hasPrev = input.forward ? Boolean(input.cursor) : input.hasExtra;
  return {
    data,
    page: {
      limit: input.limit,
      total: input.total,
      next_cursor: last && hasNext ? encodeCursor({ v: 1, ...input.cursorOf(last), dir: "next" }) : null,
      prev_cursor: first && hasPrev ? encodeCursor({ v: 1, ...input.cursorOf(first), dir: "prev" }) : null,
    },
  };
}

const statementSelect = `
  SELECT
    s.slug, s.statement_type, s.normalized_text, s.event_time, ${effectiveReviewStateSql("s")} AS review_state,
    p.slug AS person_slug, p.display_name,
    src.slug AS source_slug, src.name AS source_name, src.source_type,
    si.slug AS source_item_slug, si.title AS source_item_title, si.canonical_url,
    si.published_at, si.observed_at, si.published_timezone, si.language,
    si.content_hash, si.content_reference, si.availability, si.collection_status,
    e.slug AS evidence_slug, e.segment_kind, e.sequence, e.start_char, e.end_char,
    e.start_ms, e.end_ms, e.text AS evidence_text, e.context_text, e.segment_hash,
    f.forecast_kind, f.question_key, f.question_text, f.definition_text, f.condition_text,
    f.horizon_text, f.target_date_start, f.target_date_end, f.value_type, f.value_numeric,
    f.value_min, f.value_max, f.unit, f.distribution_json, f.resolution_criteria,
    f.review_state AS forecast_review_state,
    COALESCE(topics.topics, '[]'::jsonb) AS topics
  FROM statements s
  JOIN people p ON p.id = s.person_id
  JOIN source_items si ON si.id = s.source_item_id
  JOIN sources src ON src.id = si.source_id
  JOIN evidence_segments e ON e.id = s.evidence_segment_id
  LEFT JOIN forecasts f ON f.statement_id = s.id
  LEFT JOIN LATERAL (
    SELECT jsonb_agg(jsonb_build_object('slug', t.slug, 'name', t.name) ORDER BY t.slug) AS topics
    FROM statement_topics st
    JOIN topics t ON t.id = st.topic_id
    WHERE st.statement_id = s.id
  ) topics ON true
`;

function mapForecast(row: Record<string, unknown>, statementType: string, statementSlug: string): PublicForecast | null {
  if (!row.question_key || !row.forecast_review_state || !isResearchPublicReviewState(String(row.forecast_review_state))) {
    return null;
  }
  const statementState = String(row.review_state);
  const forecastState = String(row.forecast_review_state);
  const reviewState = forecastState === "human_verified" && statementState !== "human_verified" ? statementState : forecastState;
  if (!isResearchPublicReviewState(reviewState)) return null;
  const numeric = statementType === "explicit_numeric";
  return {
    ...publicReviewFields(reviewState),
    statement_slug: statementSlug,
    forecast_kind: String(row.forecast_kind),
    question_key: String(row.question_key),
    question_text: String(row.question_text),
    definition_text: row.definition_text ? String(row.definition_text) : null,
    condition_text: row.condition_text ? String(row.condition_text) : null,
    horizon_text: row.horizon_text ? String(row.horizon_text) : null,
    target_date_start: day(row.target_date_start as Date | null),
    target_date_end: day(row.target_date_end as Date | null),
    value_type: numeric ? String(row.value_type) : "none",
    value_numeric: numeric ? num(row.value_numeric as string | null) : null,
    value_min: numeric ? num(row.value_min as string | null) : null,
    value_max: numeric ? num(row.value_max as string | null) : null,
    unit: row.unit ? String(row.unit) : null,
    distribution: numeric ? asObject(row.distribution_json) : null,
    resolution_criteria: row.resolution_criteria ? String(row.resolution_criteria) : null,
  };
}

function mapStatement(row: Record<string, unknown>): PublicStatement {
  const review = publicReviewFields(String(row.review_state));
  const statementType = String(row.statement_type);
  const slug = String(row.slug);
  const text = excerpt(String(row.evidence_text), 2000);
  const context = excerpt(row.context_text ? String(row.context_text) : null, 800);
  return {
    ...review,
    slug,
    statement_type: statementType,
    normalized_text: String(row.normalized_text),
    event_time: iso(row.event_time as Date | null),
    person: { slug: String(row.person_slug), display_name: String(row.display_name) },
    source: {
      slug: String(row.source_slug),
      name: String(row.source_name),
      source_type: String(row.source_type),
    },
    source_item: {
      slug: String(row.source_item_slug),
      title: row.source_item_title ? String(row.source_item_title) : null,
      canonical_url: String(row.canonical_url),
      published_at: iso(row.published_at as Date | null),
      observed_at: iso(row.observed_at as Date | null),
      published_timezone: row.published_timezone ? String(row.published_timezone) : null,
      language: row.language ? String(row.language) : null,
      content_hash: String(row.content_hash),
      content_reference: row.content_reference ? String(row.content_reference) : null,
      availability: String(row.availability),
      collection_status: String(row.collection_status),
    },
    evidence: {
      slug: String(row.evidence_slug),
      segment_kind: String(row.segment_kind),
      sequence: Number(row.sequence),
      start_char: int(row.start_char as string | null),
      end_char: int(row.end_char as string | null),
      start_ms: int(row.start_ms as string | null),
      end_ms: int(row.end_ms as string | null),
      segment_hash: String(row.segment_hash),
      text: text.text ?? "",
      text_truncated: text.truncated,
      context_text: context.text,
      context_truncated: context.truncated,
    },
    forecast: mapForecast(row, statementType, slug),
    topics: asTopics(row.topics),
    relationships: [],
  };
}

export function summarizeStatement(statement: PublicStatement): PublicStatementSummary {
  return {
    review_state: statement.review_state,
    verified: statement.verified,
    machine_labeled: statement.machine_labeled,
    slug: statement.slug,
    statement_type: statement.statement_type,
    normalized_text: statement.normalized_text,
    event_time: statement.event_time,
    person: statement.person,
    source: statement.source,
    source_item: {
      slug: statement.source_item.slug,
      title: statement.source_item.title,
      canonical_url: statement.source_item.canonical_url,
      published_at: statement.source_item.published_at,
      observed_at: statement.source_item.observed_at,
    },
    evidence_ref: {
      slug: statement.evidence.slug,
      segment_kind: statement.evidence.segment_kind,
      sequence: statement.evidence.sequence,
      start_char: statement.evidence.start_char,
      end_char: statement.evidence.end_char,
      start_ms: statement.evidence.start_ms,
      end_ms: statement.evidence.end_ms,
      segment_hash: statement.evidence.segment_hash,
    },
    forecast: statement.forecast,
    topics: statement.topics,
  };
}

function statementWhere(query: PublicStatementQuery, values: unknown[]): { where: string; publicParam: string } {
  const publicParam = bind(values, PUBLIC_STATES);
  const clauses = [
    query.review_state
      ? `${effectiveReviewStateSql("s")} = ${bind(values, query.review_state)}`
      : `${effectiveReviewStateSql("s")} = ANY(${publicParam}::text[])`,
  ];
  if (query.person) clauses.push(`p.slug = ${bind(values, query.person)}`);
  if (query.organization) {
    clauses.push(`EXISTS (
      SELECT 1 FROM affiliations a
      JOIN organizations o ON o.id = a.organization_id
      WHERE a.person_id = p.id AND o.slug = ${bind(values, query.organization)}
        AND a.review_state = ANY(${publicParam}::text[])
    )`);
  }
  if (query.source) clauses.push(`src.slug = ${bind(values, query.source)}`);
  if (query.topic) {
    clauses.push(`EXISTS (
      SELECT 1 FROM statement_topics st
      JOIN topics t ON t.id = st.topic_id
      WHERE st.statement_id = s.id AND t.slug = ${bind(values, query.topic)}
    )`);
  }
  if (query.statement_type) clauses.push(`s.statement_type = ${bind(values, query.statement_type)}`);
  if (query.from) clauses.push(`s.event_time >= ${bind(values, `${query.from}T00:00:00.000Z`)}::timestamptz`);
  if (query.to) clauses.push(`s.event_time <= ${bind(values, `${query.to}T23:59:59.999Z`)}::timestamptz`);
  if (query.q) clauses.push(`s.search_vector @@ plainto_tsquery('simple', ${bind(values, query.q)})`);
  return { where: `WHERE ${clauses.join(" AND ")}`, publicParam };
}

function statementOrder(sort: PublicStatementQuery["sort"], cursor: CursorPayload | null, values: unknown[]) {
  const desc = sort === "event_time_desc";
  const forward = !cursor || cursor.dir === "next";
  const queryDescending = desc ? forward : !forward;
  let clause = "";
  if (cursor) {
    const timeParam = bind(values, cursor.t);
    const idParam = bind(values, cursor.id);
    if (desc) {
      clause = cursor.dir === "next"
        ? `AND (
            (${timeParam}::timestamptz IS NOT NULL AND (
              s.event_time < ${timeParam}::timestamptz
              OR (s.event_time = ${timeParam}::timestamptz AND s.slug < ${idParam})
              OR s.event_time IS NULL
            ))
            OR (${timeParam}::timestamptz IS NULL AND s.event_time IS NULL AND s.slug < ${idParam})
          )`
        : `AND (
            (${timeParam}::timestamptz IS NOT NULL AND (
              s.event_time > ${timeParam}::timestamptz
              OR (s.event_time = ${timeParam}::timestamptz AND s.slug > ${idParam})
            ))
            OR (${timeParam}::timestamptz IS NULL AND s.event_time IS NOT NULL)
            OR (${timeParam}::timestamptz IS NULL AND s.event_time IS NULL AND s.slug > ${idParam})
          )`;
    } else {
      clause = cursor.dir === "next"
        ? `AND (
            (${timeParam}::timestamptz IS NULL AND s.event_time IS NULL AND s.slug > ${idParam})
            OR (${timeParam}::timestamptz IS NULL AND s.event_time IS NOT NULL)
            OR (${timeParam}::timestamptz IS NOT NULL AND (
              s.event_time > ${timeParam}::timestamptz
              OR (s.event_time = ${timeParam}::timestamptz AND s.slug > ${idParam})
            ))
          )`
        : `AND (
            (${timeParam}::timestamptz IS NOT NULL AND (
              s.event_time < ${timeParam}::timestamptz
              OR (s.event_time = ${timeParam}::timestamptz AND s.slug < ${idParam})
              OR s.event_time IS NULL
            ))
            OR (${timeParam}::timestamptz IS NULL AND s.event_time IS NULL AND s.slug < ${idParam})
          )`;
    }
  }
  const ordering = queryDescending
    ? "s.event_time DESC NULLS LAST, s.slug DESC"
    : "s.event_time ASC NULLS FIRST, s.slug ASC";
  return { clause, ordering, forward };
}

async function fetchStatements(
  query: PublicStatementQuery,
  pool: Db,
  mode: "page" | "all",
): Promise<{ rows: PublicStatement[]; page: PublicPage<PublicStatement>["page"] | null }> {
  const values: unknown[] = [];
  const { where } = statementWhere(query, values);
  if (mode === "all") {
    const result = await pool.query(`${statementSelect} ${where} ORDER BY s.slug ASC`, values);
    return { rows: result.rows.map((row) => mapStatement(row)), page: null };
  }
  const cursor = query.cursor ? decodeCursor(query.cursor) : null;
  const order = statementOrder(query.sort, cursor, values);
  const limitParam = bind(values, query.limit + 1);
  const result = await pool.query(
    `${statementSelect} ${where} ${order.clause} ORDER BY ${order.ordering} LIMIT ${limitParam}`,
    values,
  );
  const countValues: unknown[] = [];
  const countWhere = statementWhere(query, countValues).where;
  const total = await pool.query(
    `SELECT count(*)::int AS count
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     ${countWhere}`,
    countValues,
  );
  const hasExtra = result.rows.length > query.limit;
  const mapped = result.rows.map((row) => mapStatement(row));
  const page = pageResult({
    rows: mapped,
    limit: query.limit,
    total: Number(total.rows[0]?.count ?? 0),
    cursor,
    forward: order.forward,
    hasExtra,
    cursorOf: (row) => ({ t: row.event_time, id: row.slug }),
  });
  return { rows: page.data, page: page.page };
}

async function fetchRelationships(pool: Db, statementSlug?: string): Promise<PublicRelationship[]> {
  const values: unknown[] = [PUBLIC_STATES];
  const slugClause = statementSlug ? `AND (fs.slug = $2 OR ts.slug = $2)` : "";
  if (statementSlug) values.push(statementSlug);
  const result = await pool.query(
    `SELECT r.relationship_type, r.review_state, fs.slug AS from_slug, ts.slug AS to_slug
     FROM statement_relationships r
     JOIN statements fs ON fs.id = r.from_statement_id
     JOIN statements ts ON ts.id = r.to_statement_id
     WHERE r.review_state = ANY($1::text[])
       AND ${effectiveReviewStateSql("fs")} = ANY($1::text[])
       AND ${effectiveReviewStateSql("ts")} = ANY($1::text[])
       ${slugClause}
     ORDER BY fs.slug, ts.slug, r.relationship_type`,
    values,
  );
  return result.rows.map((row) => ({
    ...publicReviewFields(String(row.review_state)),
    from_statement_slug: String(row.from_slug),
    to_statement_slug: String(row.to_slug),
    relationship_type: String(row.relationship_type),
  }));
}

function attachRelationships(statements: PublicStatement[], relationships: PublicRelationship[]) {
  const bySlug = new Map<string, PublicRelationship[]>();
  for (const relationship of relationships) {
    for (const slug of [relationship.from_statement_slug, relationship.to_statement_slug]) {
      const list = bySlug.get(slug) ?? [];
      list.push(relationship);
      bySlug.set(slug, list);
    }
  }
  for (const statement of statements) {
    statement.relationships = (bySlug.get(statement.slug) ?? []).sort((left, right) =>
      `${left.relationship_type}|${left.from_statement_slug}|${left.to_statement_slug}`.localeCompare(
        `${right.relationship_type}|${right.from_statement_slug}|${right.to_statement_slug}`,
      ),
    );
  }
}

export async function listPublicStatements(query: PublicStatementQuery, pool: Db = getPool()): Promise<PublicPage<PublicStatementSummary>> {
  if (isPool(pool)) return withConsistentRead(pool, (db) => listPublicStatements(query, db));
  const fetched = await fetchStatements(query, pool, "page");
  return {
    data: fetched.rows.map(summarizeStatement),
    page: fetched.page ?? { limit: query.limit, total: fetched.rows.length, next_cursor: null, prev_cursor: null },
  };
}

export async function getPublicStatement(slug: string, pool: Db = getPool()): Promise<PublicStatement | null> {
  if (isPool(pool)) return withConsistentRead(pool, (db) => getPublicStatement(slug, db));
  const values: unknown[] = [PUBLIC_STATES, slug];
  const result = await pool.query(
    `${statementSelect} WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[]) AND s.slug = $2`,
    values,
  );
  const row = result.rows[0];
  if (!row) return null;
  const statement = mapStatement(row);
  attachRelationships([statement], await fetchRelationships(pool, slug));
  return statement;
}

function mapPerson(row: Record<string, unknown>): PublicPersonSummary {
  return {
    slug: String(row.slug),
    display_name: String(row.display_name),
    bio_short: String(row.bio_short),
    status: String(row.status),
    in_current_cohort: Boolean(row.in_current_cohort),
    inclusion_reason: String(row.inclusion_reason),
    cohort_tags: (row.cohort_tags as string[]) ?? [],
    organization: row.organization_slug
      ? {
          slug: String(row.organization_slug),
          name: String(row.organization_name),
          role: row.organization_role ? String(row.organization_role) : null,
        }
      : null,
    public_statement_counts: asCounts(row.counts),
  };
}

const personSelect = (publicParam: string) => `
  SELECT p.slug, p.display_name, p.given_name, p.family_name, p.bio_short, p.status,
         p.inclusion_reason, p.cohort_tags, p.updated_at,
         EXISTS (
           SELECT 1 FROM cohort_memberships cm
           JOIN cohorts c ON c.id = cm.cohort_id
           JOIN dataset_imports d ON d.is_current
             AND d.cohort_slug = c.slug AND d.cohort_version = c.version
           WHERE cm.person_id = p.id
         ) AS in_current_cohort,
         o.slug AS organization_slug, o.name AS organization_name, a.role AS organization_role,
         counts.counts
  FROM people p
  LEFT JOIN affiliations a ON a.id = p.current_affiliation_id AND a.review_state = ANY(${publicParam}::text[])
  LEFT JOIN organizations o ON o.id = a.organization_id
  LEFT JOIN LATERAL (
    SELECT COALESCE(jsonb_object_agg(statement_type, count), '{}'::jsonb) AS counts
    FROM (
      SELECT statement_type, count(*)::int AS count
      FROM statements s
      WHERE s.person_id = p.id AND ${effectiveReviewStateSql("s")} = ANY(${publicParam}::text[])
      GROUP BY statement_type
    ) grouped
  ) counts ON true
`;

function peopleWhere(query: PublicPeopleQuery, values: unknown[]): { where: string; publicParam: string } {
  const publicParam = bind(values, PUBLIC_STATES);
  const clauses = [publicPersonPredicate("p", publicParam)];
  if (query.q) clauses.push(`p.search_vector @@ plainto_tsquery('simple', ${bind(values, query.q)})`);
  if (query.organization) {
    clauses.push(`EXISTS (
      SELECT 1 FROM affiliations a
      JOIN organizations o ON o.id = a.organization_id
      WHERE a.person_id = p.id AND o.slug = ${bind(values, query.organization)}
        AND a.review_state = ANY(${publicParam}::text[])
    )`);
  }
  if (query.status) clauses.push(`p.status = ${bind(values, query.status)}`);
  return { where: `WHERE ${clauses.join(" AND ")}`, publicParam };
}

export async function listPublicPeople(query: PublicPeopleQuery, pool: Db = getPool()): Promise<PublicPage<PublicPersonSummary>> {
  if (isPool(pool)) return withConsistentRead(pool, (db) => listPublicPeople(query, db));
  const values: unknown[] = [];
  const { where, publicParam } = peopleWhere(query, values);
  const cursor = query.cursor ? decodeCursor(query.cursor) : null;
  if (cursor && cursor.t === null) throw new InvalidCursorError();
  const forward = !cursor || cursor.dir === "next";
  let cursorClause = "";
  if (cursor?.t) {
    const nameParam = bind(values, cursor.t);
    const idParam = bind(values, cursor.id);
    const op = forward ? ">" : "<";
    cursorClause = `AND (p.display_name ${op} ${nameParam} OR (p.display_name = ${nameParam} AND p.slug ${op} ${idParam}))`;
  }
  const limitParam = bind(values, query.limit + 1);
  const order = forward ? "p.display_name ASC, p.slug ASC" : "p.display_name DESC, p.slug DESC";
  const result = await pool.query(
    `${personSelect(publicParam)} ${where} ${cursorClause} ORDER BY ${order} LIMIT ${limitParam}`,
    values,
  );
  const countValues: unknown[] = [];
  const countWhere = peopleWhere(query, countValues).where;
  const total = await pool.query(`SELECT count(*)::int AS count FROM people p ${countWhere}`, countValues);
  const mapped = result.rows.map((row) => mapPerson(row));
  return pageResult({
    rows: mapped,
    limit: query.limit,
    total: Number(total.rows[0]?.count ?? 0),
    cursor,
    forward,
    hasExtra: result.rows.length > query.limit,
    cursorOf: (row) => ({ t: row.display_name, id: row.slug }),
  });
}

async function loadAffiliations(pool: Db, personSlug?: string): Promise<Map<string, PublicAffiliation[]>> {
  const values: unknown[] = [PUBLIC_STATES];
  const clause = personSlug ? "AND p.slug = $2" : "";
  if (personSlug) values.push(personSlug);
  const result = await pool.query(
    `SELECT p.slug AS person_slug, o.slug AS organization_slug, o.name AS organization_name,
            a.role, a.start_date, a.end_date, a.confidence_level, a.review_state,
            (p.current_affiliation_id = a.id) AS is_current
     FROM affiliations a
     JOIN people p ON p.id = a.person_id
     JOIN organizations o ON o.id = a.organization_id
     WHERE a.review_state = ANY($1::text[]) ${clause}
     ORDER BY p.slug, a.start_date NULLS LAST, o.slug`,
    values,
  );
  const grouped = new Map<string, PublicAffiliation[]>();
  for (const row of result.rows) {
    const slug = String(row.person_slug);
    const list = grouped.get(slug) ?? [];
    list.push({
      ...publicReviewFields(String(row.review_state)),
      organization_slug: String(row.organization_slug),
      organization_name: String(row.organization_name),
      role: row.role ? String(row.role) : null,
      start_date: day(row.start_date),
      end_date: day(row.end_date),
      confidence_level: String(row.confidence_level),
      is_current: Boolean(row.is_current),
    });
    grouped.set(slug, list);
  }
  return grouped;
}

async function loadIdentities(pool: Db, personSlug?: string): Promise<Map<string, PublicIdentity[]>> {
  const values: unknown[] = [PUBLIC_STATES];
  const clause = personSlug ? "AND p.slug = $2" : "";
  if (personSlug) values.push(personSlug);
  const result = await pool.query(
    `SELECT p.slug AS person_slug, e.namespace, e.external_id, e.canonical_url, e.handle,
            e.verification_method, e.confidence_level, e.review_state, e.verified_at
     FROM external_identities e
     JOIN people p ON p.id = e.person_id
     WHERE e.review_state = ANY($1::text[])
       AND ${publicPersonPredicate("p", "$1")}
       ${clause}
     ORDER BY p.slug, e.namespace, e.external_id`,
    values,
  );
  const grouped = new Map<string, PublicIdentity[]>();
  for (const row of result.rows) {
    const slug = String(row.person_slug);
    const list = grouped.get(slug) ?? [];
    list.push({
      ...publicReviewFields(String(row.review_state)),
      person_slug: slug,
      namespace: String(row.namespace),
      external_id: String(row.external_id),
      canonical_url: row.canonical_url ? String(row.canonical_url) : null,
      handle: row.handle ? String(row.handle) : null,
      verification_method: String(row.verification_method),
      confidence_level: String(row.confidence_level),
      verified_at: iso(row.verified_at),
    });
    grouped.set(slug, list);
  }
  return grouped;
}

export async function getPublicPerson(slug: string, pool: Db = getPool()): Promise<PublicPerson | null> {
  if (isPool(pool)) return withConsistentRead(pool, (db) => getPublicPerson(slug, db));
  const values: unknown[] = [PUBLIC_STATES, slug];
  const result = await pool.query(
    `${personSelect("$1")} WHERE ${publicPersonPredicate("p", "$1")} AND p.slug = $2`,
    values,
  );
  const row = result.rows[0];
  if (!row) return null;
  const summary = mapPerson(row);
  return {
    ...summary,
    given_name: row.given_name ? String(row.given_name) : null,
    family_name: row.family_name ? String(row.family_name) : null,
    updated_at: iso(row.updated_at),
    affiliations: (await loadAffiliations(pool, slug)).get(slug) ?? [],
    identities: (await loadIdentities(pool, slug)).get(slug) ?? [],
  };
}

export async function listPublicTopics(pool: Db = getPool()): Promise<{ data: PublicTopic[]; truncated: boolean }> {
  const result = await pool.query(
    `SELECT t.slug, t.name, t.definition, t.version, parent.slug AS parent_slug, counts.counts, counts.total
     FROM topics t
     LEFT JOIN topics parent ON parent.id = t.parent_topic_id
     LEFT JOIN LATERAL (
       SELECT COALESCE(jsonb_object_agg(statement_type, count), '{}'::jsonb) AS counts,
              COALESCE(sum(count), 0)::int AS total
       FROM (
         SELECT s.statement_type, count(*)::int AS count
         FROM statement_topics st
         JOIN statements s ON s.id = st.statement_id
         WHERE st.topic_id = t.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[])
         GROUP BY s.statement_type
       ) grouped
     ) counts ON true
     ORDER BY t.slug`,
    [PUBLIC_STATES],
  );
  const data = result.rows.map((row) => ({
    slug: String(row.slug),
    name: String(row.name),
    definition: String(row.definition),
    version: String(row.version),
    parent_slug: row.parent_slug ? String(row.parent_slug) : null,
    public_statement_counts: asCounts(row.counts),
    public_statement_total: Number(row.total ?? 0),
  }));
  return { data: data.slice(0, 500), truncated: data.length > 500 };
}

export async function getPublicTopic(slug: string, pool: Db = getPool()): Promise<PublicTopic | null> {
  const result = await pool.query(
    `SELECT t.slug, t.name, t.definition, t.version, parent.slug AS parent_slug, counts.counts, counts.total
     FROM topics t
     LEFT JOIN topics parent ON parent.id = t.parent_topic_id
     LEFT JOIN LATERAL (
       SELECT COALESCE(jsonb_object_agg(statement_type, count), '{}'::jsonb) AS counts,
              COALESCE(sum(count), 0)::int AS total
       FROM (
         SELECT s.statement_type, count(*)::int AS count
         FROM statement_topics st
         JOIN statements s ON s.id = st.statement_id
         WHERE st.topic_id = t.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[])
         GROUP BY s.statement_type
       ) grouped
     ) counts ON true
     WHERE t.slug = $2`,
    [PUBLIC_STATES, slug],
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    slug: String(row.slug),
    name: String(row.name),
    definition: String(row.definition),
    version: String(row.version),
    parent_slug: row.parent_slug ? String(row.parent_slug) : null,
    public_statement_counts: asCounts(row.counts),
    public_statement_total: Number(row.total ?? 0),
  };
}

function mapSource(row: Record<string, unknown>, asOf: string): PublicSource {
  const lastSuccess = iso(row.last_success_at as Date | null);
  return {
    ...publicReviewFields(String(row.review_state)),
    slug: String(row.slug),
    name: String(row.name),
    source_type: String(row.source_type),
    canonical_url: String(row.canonical_url),
    platform: row.platform ? String(row.platform) : null,
    owner_person_slug: row.owner_person_slug ? String(row.owner_person_slug) : null,
    owner_organization_slug: row.owner_organization_slug ? String(row.owner_organization_slug) : null,
    collection_method: String(row.collection_method),
    last_success_at: lastSuccess,
    freshness: classifyFreshness(lastSuccess, asOf),
    public_item_count: Number(row.public_item_count ?? 0),
  };
}

const sourceSelect = `
  SELECT src.slug, src.name, src.source_type, src.canonical_url, src.platform, src.collection_method,
         src.review_state, src.last_success_at,
         p.slug AS owner_person_slug, o.slug AS owner_organization_slug,
         (
           SELECT count(DISTINCT si.id)::int
           FROM source_items si
           JOIN statements s ON s.source_item_id = si.id
           WHERE si.source_id = src.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[])
         ) AS public_item_count
  FROM sources src
  LEFT JOIN people p ON p.id = src.owner_person_id
  LEFT JOIN organizations o ON o.id = src.owner_organization_id
`;

export async function listPublicSources(query: PublicPageQuery, asOf: string, pool: Db = getPool()): Promise<PublicPage<PublicSource>> {
  if (isPool(pool)) return withConsistentRead(pool, (db) => listPublicSources(query, asOf, db));
  const values: unknown[] = [PUBLIC_STATES];
  const where = "WHERE src.review_state = ANY($1::text[])";
  const cursor = query.cursor ? decodeCursor(query.cursor) : null;
  if (cursor && cursor.t === null) throw new InvalidCursorError();
  const forward = !cursor || cursor.dir === "next";
  let cursorClause = "";
  if (cursor?.t) {
    const nameParam = bind(values, cursor.t);
    const idParam = bind(values, cursor.id);
    const op = forward ? ">" : "<";
    cursorClause = `AND (src.name ${op} ${nameParam} OR (src.name = ${nameParam} AND src.slug ${op} ${idParam}))`;
  }
  const limitParam = bind(values, query.limit + 1);
  const order = forward ? "src.name ASC, src.slug ASC" : "src.name DESC, src.slug DESC";
  const result = await pool.query(`${sourceSelect} ${where} ${cursorClause} ORDER BY ${order} LIMIT ${limitParam}`, values);
  const total = await pool.query(`SELECT count(*)::int AS count FROM sources src ${where}`, [PUBLIC_STATES]);
  return pageResult({
    rows: result.rows.map((row) => mapSource(row, asOf)),
    limit: query.limit,
    total: Number(total.rows[0]?.count ?? 0),
    cursor,
    forward,
    hasExtra: result.rows.length > query.limit,
    cursorOf: (row) => ({ t: row.name, id: row.slug }),
  });
}

export function getPublicSource(slug: string, asOf: string, pool: Db = getPool()) {
  return queryOnClient(pool, async (pool) => {
  const result = await pool.query(`${sourceSelect} WHERE src.review_state = ANY($1::text[]) AND src.slug = $2`, [
    PUBLIC_STATES,
    slug,
  ]);
  const row = result.rows[0];
  if (!row) return null;
  const items = await pool.query(
    `SELECT si.slug, si.title, si.canonical_url, si.published_at, si.observed_at
     FROM source_items si
     JOIN sources src ON src.id = si.source_id
     WHERE src.slug = $2
       AND EXISTS (
         SELECT 1 FROM statements s
         WHERE s.source_item_id = si.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[])
       )
     ORDER BY si.published_at DESC NULLS LAST, si.slug
     LIMIT $3`,
    [PUBLIC_STATES, slug, PUBLIC_API_LIMITS.maxSourceItemsOnDetail + 1],
  );
  const truncated = items.rows.length > PUBLIC_API_LIMITS.maxSourceItemsOnDetail;
  return {
    ...mapSource(row, asOf),
    items: items.rows.slice(0, PUBLIC_API_LIMITS.maxSourceItemsOnDetail).map((item) => ({
      slug: String(item.slug),
      title: item.title ? String(item.title) : null,
      canonical_url: String(item.canonical_url),
      published_at: iso(item.published_at),
      observed_at: iso(item.observed_at),
    })),
    items_truncated: truncated,
  };
  });
}

async function loadParticipants(pool: Db, sourceItemSlug?: string) {
  const values: unknown[] = [PUBLIC_STATES];
  const clause = sourceItemSlug ? "AND si.slug = $2" : "";
  if (sourceItemSlug) values.push(sourceItemSlug);
  const result = await pool.query(
    `SELECT si.slug AS source_item_slug, sp.role, sp.attribution_method, sp.confidence_level,
            CASE WHEN p.id IS NOT NULL AND ${publicPersonPredicate("p", "$1")} THEN p.slug ELSE NULL END AS person_slug,
            CASE WHEN p.id IS NOT NULL AND ${publicPersonPredicate("p", "$1")} THEN p.display_name ELSE NULL END AS display_name,
            o.slug AS organization_slug
     FROM source_participants sp
     JOIN source_items si ON si.id = sp.source_item_id
     LEFT JOIN people p ON p.id = sp.person_id
     LEFT JOIN organizations o ON o.id = sp.organization_id
     WHERE EXISTS (
       SELECT 1 FROM statements s
       WHERE s.source_item_id = si.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[])
     )
     ${clause}
     ORDER BY si.slug, sp.role, p.slug NULLS LAST, o.slug NULLS LAST`,
    values,
  );
  const grouped = new Map<string, PublicSourceItem["participants"]>();
  for (const row of result.rows) {
    if (!row.person_slug && !row.organization_slug) continue;
    const slug = String(row.source_item_slug);
    const list = grouped.get(slug) ?? [];
    list.push({
      role: String(row.role),
      attribution_method: String(row.attribution_method),
      confidence_level: String(row.confidence_level),
      person_slug: row.person_slug ? String(row.person_slug) : null,
      display_name: row.display_name ? String(row.display_name) : null,
      organization_slug: row.organization_slug ? String(row.organization_slug) : null,
    });
    grouped.set(slug, list);
  }
  return grouped;
}

function mapSourceItem(row: Record<string, unknown>, participants: PublicSourceItem["participants"]): PublicSourceItem {
  return {
    slug: String(row.slug),
    source_slug: String(row.source_slug),
    upstream_id: row.upstream_id ? String(row.upstream_id) : null,
    canonical_url: String(row.canonical_url),
    title: row.title ? String(row.title) : null,
    published_at: iso(row.published_at as Date | null),
    published_timezone: row.published_timezone ? String(row.published_timezone) : null,
    observed_at: iso(row.observed_at as Date | null),
    language: row.language ? String(row.language) : null,
    content_hash: String(row.content_hash),
    content_version: Number(row.content_version),
    content_reference: row.content_reference ? String(row.content_reference) : null,
    availability: String(row.availability),
    collection_status: String(row.collection_status),
    participants,
  };
}

const sourceItemSelect = `
  SELECT si.slug, src.slug AS source_slug, si.upstream_id, si.canonical_url, si.title,
         si.published_at, si.published_timezone, si.observed_at, si.language, si.content_hash,
         si.content_version, si.content_reference, si.availability, si.collection_status
  FROM source_items si
  JOIN sources src ON src.id = si.source_id
  WHERE src.review_state = ANY($1::text[])
    AND EXISTS (
      SELECT 1 FROM statements s
      WHERE s.source_item_id = si.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[])
    )
`;

export async function getPublicSourceItem(slug: string, pool: Db = getPool()): Promise<PublicSourceItem | null> {
  if (isPool(pool)) return withConsistentRead(pool, (db) => getPublicSourceItem(slug, db));
  const result = await pool.query(`${sourceItemSelect} AND si.slug = $2`, [PUBLIC_STATES, slug]);
  const row = result.rows[0];
  if (!row) return null;
  const participants = await loadParticipants(pool, slug);
  return mapSourceItem(row, participants.get(slug) ?? []);
}

export async function listPublicOrganizations(pool: Db = getPool()): Promise<PublicOrganization[]> {
  const result = await pool.query(
    `SELECT DISTINCT o.slug, o.name, o.organization_type, o.canonical_url
     FROM organizations o
     WHERE o.id IN (
       SELECT a.organization_id
       FROM affiliations a
       JOIN people p ON p.id = a.person_id
       WHERE a.review_state = ANY($1::text[]) AND ${publicPersonPredicate("p", "$1")}
       UNION
       SELECT src.owner_organization_id
       FROM sources src
       WHERE src.review_state = ANY($1::text[]) AND src.owner_organization_id IS NOT NULL
       UNION
       SELECT sp.organization_id
       FROM source_participants sp
       JOIN source_items si ON si.id = sp.source_item_id
       JOIN statements s ON s.source_item_id = si.id
       WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[]) AND sp.organization_id IS NOT NULL
     )
     ORDER BY o.slug`,
    [PUBLIC_STATES],
  );
  return result.rows.map((row) => ({
    slug: String(row.slug),
    name: String(row.name),
    organization_type: String(row.organization_type),
    canonical_url: row.canonical_url ? String(row.canonical_url) : null,
  }));
}

async function researchStatementSlugs(pool: Db): Promise<Set<string>> {
  const result = await pool.query(
    `SELECT s.slug FROM statements s WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[])`,
    [PUBLIC_STATES],
  );
  return new Set(result.rows.map((row) => String(row.slug)));
}

function partitionExclusions(exclusions: Exclusion[], allowed: Set<string>): { exclusions: Exclusion[]; omitted_non_research_count: number } {
  const visible = exclusions.filter((item) => allowed.has(item.statement_slug));
  return { exclusions: visible, omitted_non_research_count: exclusions.length - visible.length };
}

function presentRevision(revision: RevisionResult, allowed: Set<string>): { revision: RevisionResult; omitted_non_research_count: number } {
  const separated = partitionExclusions(revision.exclusions, allowed);
  const chains = revision.chains.filter((chain) =>
    chain.points.every((point) => allowed.has(point.statement_slug))
    && chain.links.every((link) => allowed.has(link.from_statement_slug) && allowed.has(link.to_statement_slug)),
  );
  const repeats = revision.repeats.filter((repeat) => allowed.has(repeat.from_statement_slug) && allowed.has(repeat.to_statement_slug));
  const omitted = separated.omitted_non_research_count + (revision.chains.length - chains.length) + (revision.repeats.length - repeats.length);
  return {
    revision: { ...revision, exclusions: separated.exclusions, chains, repeats },
    omitted_non_research_count: omitted,
  };
}

function presentTrend(trend: PublicTrend, allowed: Set<string>, asOf: string) {
  const stamped = { ...trend, calculated_at: asOf };
  if (trend.kind === "volume") {
    const separated = partitionExclusions(trend.volume.exclusions, allowed);
    return { ...stamped, volume: { ...trend.volume, exclusions: separated.exclusions }, omitted_non_research_count: separated.omitted_non_research_count };
  }
  if (trend.kind === "distribution") {
    const separated = partitionExclusions(trend.distribution.exclusions, allowed);
    return { ...stamped, distribution: { ...trend.distribution, exclusions: separated.exclusions }, omitted_non_research_count: separated.omitted_non_research_count };
  }
  if (trend.kind === "timeline") {
    const separated = partitionExclusions(trend.timeline.exclusions, allowed);
    return { ...stamped, timeline: { ...trend.timeline, exclusions: separated.exclusions }, omitted_non_research_count: separated.omitted_non_research_count };
  }
  if (trend.kind === "quantity") {
    const separated = partitionExclusions(trend.quantity.exclusions, allowed);
    return { ...stamped, quantity: { ...trend.quantity, exclusions: separated.exclusions }, omitted_non_research_count: separated.omitted_non_research_count };
  }
  if (trend.kind === "qualitative") {
    const rows = trend.qualitative.rows.filter((row) => allowed.has(row.statement_slug));
    return {
      ...stamped,
      qualitative: { ...trend.qualitative, rows },
      omitted_non_research_count: trend.qualitative.rows.length - rows.length,
    };
  }
  if (trend.kind === "inspection") {
    const rows = trend.inspection.rows.filter((row) => allowed.has(row.statement_slug));
    return {
      ...stamped,
      inspection: { ...trend.inspection, rows },
      omitted_non_research_count: trend.inspection.rows.length - rows.length,
    };
  }
  const revision = presentRevision(trend.revision, allowed);
  return { ...stamped, revision: revision.revision, omitted_non_research_count: revision.omitted_non_research_count };
}

async function loadResearchTrends(asOf: string, pool: Db) {
  const trends = await listComputedTrends(pool as unknown as pg.Pool);
  const allowed = await researchStatementSlugs(pool);
  return trends.map((trend) => presentTrend(trend, allowed, asOf)).sort((left, right) => left.slug.localeCompare(right.slug));
}

export function listPublicTrends(pool: Db = getPool()) {
  return queryOnClient(pool, async (pool) => {
  const trends = await loadResearchTrends("1970-01-01T00:00:00.000Z", pool);
  return {
    data: trends.map((trend) => ({
      slug: trend.slug,
      name: trend.name,
      method_version: trend.method_version,
      source: trend.source,
      kind: trend.kind,
      cohort_slug: trend.cohort_slug,
      cohort_version: trend.cohort_version,
      question_key: trend.question_key,
      density: trend.density,
      contributing_person_count: trend.contributing_person_count,
      contributing_statement_count: trend.contributing_statement_count,
      cohort_size: trend.cohort_size,
      published: true,
    })),
    truncated: false,
  };
  });
}

export function getPublicTrend(slug: string, asOf: string, pool: Db = getPool()) {
  return queryOnClient(pool, async (pool) => {
  const trend = await getTrend(slug, pool as unknown as pg.Pool);
  if (!trend) return null;
  return presentTrend(trend, await researchStatementSlugs(pool), asOf);
  });
}

export function searchResearch(q: string, pool: Db = getPool()) {
  return queryOnClient(pool, async (client) => {
    await client.query("SET LOCAL statement_timeout = '2s'");
    try {
      return await searchResearchBody(q, client);
    } catch (error) {
      if (isStatementTimeout(error)) throw new SearchTimeoutError();
      throw error;
    }
  });
}

async function searchResearchBody(q: string, pool: Db) {
  const people = await listPublicPeople({ q, limit: PUBLIC_API_LIMITS.searchPeople }, pool);
  const statements = await listPublicStatements({ q, limit: PUBLIC_API_LIMITS.searchStatements, sort: "event_time_desc" }, pool);
  const topics = await pool.query(
    `SELECT slug, name
     FROM topics
     WHERE name ILIKE $1 ESCAPE '\\' OR definition ILIKE $1 ESCAPE '\\' OR slug = $2
     ORDER BY name, slug
     LIMIT $3`,
    [likeContains(q), q, PUBLIC_API_LIMITS.searchTopics],
  );
  return {
    people: people.data,
    statements: statements.data,
    topics: topics.rows.map((row) => ({ slug: String(row.slug), name: String(row.name) })),
  };
}

function likeContains(value: string): string {
  return `%${value.replace(/[\\%_]/g, (char) => `\\${char}`)}%`;
}

export async function getDatasetStamp(pool: Db = getPool()): Promise<PublicDatasetStamp> {
  const result = await pool.query(
    `SELECT dataset_id, dataset_kind, imported_at
     FROM dataset_imports WHERE is_current
     ORDER BY imported_at DESC LIMIT 1`,
  );
  const row = result.rows[0];
  if (!row) return { dataset_id: null, dataset_kind: null, imported_at: null };
  return {
    dataset_id: String(row.dataset_id),
    dataset_kind: String(row.dataset_kind),
    imported_at: iso(row.imported_at),
  };
}

export function getPublicCatalog(asOf: string | null, pool: Db = getPool()) {
  return queryOnClient(pool, async (pool) => {
  const datasetResult = await pool.query(
    `SELECT schema_version, dataset_id, dataset_kind, generated_at, imported_at, notice,
            producer_name, producer_version, cohort_slug, cohort_version
     FROM dataset_imports WHERE is_current
     ORDER BY imported_at DESC LIMIT 1`,
  );
  const datasetRow = datasetResult.rows[0];
  const cohort = datasetRow?.cohort_slug
    ? await pool.query(`SELECT slug, version, name, definition FROM cohorts WHERE slug = $1 AND version = $2`, [
        datasetRow.cohort_slug,
        datasetRow.cohort_version,
      ])
    : { rows: [] as Array<Record<string, unknown>> };
  const cohortRow = cohort.rows[0];
  const stampTime = asOf ?? (datasetRow ? iso(datasetRow.imported_at) : null);
  // Sequential: snapshot export runs these on one transaction client.
  const counts = await pool.query(
      `SELECT
         (SELECT count(*)::int FROM people p WHERE ${publicPersonPredicate("p", "$1")}) AS people,
         (SELECT count(*)::int FROM external_identities e JOIN people p ON p.id = e.person_id
            WHERE e.review_state = ANY($1::text[]) AND ${publicPersonPredicate("p", "$1")}) AS identities,
         (SELECT count(*)::int FROM sources src WHERE src.review_state = ANY($1::text[])) AS sources,
         (SELECT count(DISTINCT si.id)::int FROM source_items si
            JOIN sources src ON src.id = si.source_id
            WHERE src.review_state = ANY($1::text[])
              AND EXISTS (SELECT 1 FROM statements s WHERE s.source_item_id = si.id AND ${effectiveReviewStateSql("s")} = ANY($1::text[]))) AS source_items,
         (SELECT count(*)::int FROM statements s WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[])) AS statements,
         (SELECT count(*)::int FROM forecasts f
            JOIN statements s ON s.id = f.statement_id
            WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[]) AND f.review_state = ANY($1::text[])) AS forecasts,
         (SELECT count(*)::int FROM topics) AS topics,
         (SELECT count(*)::int FROM statement_relationships r
            JOIN statements fs ON fs.id = r.from_statement_id
            JOIN statements ts ON ts.id = r.to_statement_id
            WHERE r.review_state = ANY($1::text[])
              AND ${effectiveReviewStateSql("fs")} = ANY($1::text[])
              AND ${effectiveReviewStateSql("ts")} = ANY($1::text[])) AS relationships,
         (SELECT count(*)::int FROM trend_definitions WHERE published) AS trends`,
      [PUBLIC_STATES],
    );
  const observed = await pool.query(
      `SELECT max(si.observed_at) AS observed_at, max(si.published_at) AS published_at
       FROM source_items si
       JOIN statements s ON s.source_item_id = si.id
       WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[])`,
      [PUBLIC_STATES],
    );
  const researchTrends = await loadResearchTrends(stampTime ?? "1970-01-01T00:00:00.000Z", pool);
  const methods = [...new Set(researchTrends.map((trend) => trend.method_version))].sort();
  const topics = await pool.query(`SELECT slug, version FROM topics ORDER BY slug`);
  const organizations = await listPublicOrganizations(pool);
  const countRow = counts.rows[0] ?? {};
  return {
    api_version: PUBLIC_API_VERSION,
    export_schema_version: PUBLIC_EXPORT_SCHEMA_VERSION,
    as_of: stampTime,
    dataset: datasetRow
      ? {
          dataset_id: String(datasetRow.dataset_id),
          dataset_kind: String(datasetRow.dataset_kind),
          import_schema_version: String(datasetRow.schema_version),
          source_generated_at: iso(datasetRow.generated_at),
          imported_at: iso(datasetRow.imported_at),
          notice: String(datasetRow.notice),
          producer_name: datasetRow.producer_name ? String(datasetRow.producer_name) : null,
          producer_version: datasetRow.producer_version ? String(datasetRow.producer_version) : null,
        }
      : null,
    cohort: cohortRow
      ? {
          slug: String(cohortRow.slug),
          version: String(cohortRow.version),
          name: String(cohortRow.name),
          definition: String(cohortRow.definition),
        }
      : null,
    methodology: {
      cohort_methodology_ref: PUBLIC_METHODOLOGY.cohortMethodologyRef,
      cohort_methodology_version: PUBLIC_METHODOLOGY.cohortMethodologyVersion,
      cohort_methodology_note:
        "cohort_methodology_version is the written methodology document. cohort.slug and cohort.version identify the cohort loaded in this dataset, which may be a synthetic fixture cohort.",
      provenance_policy_ref: PUBLIC_METHODOLOGY.provenancePolicyRef,
      public_api_ref: PUBLIC_METHODOLOGY.publicApiRef,
      trend_method_versions: methods,
      topic_versions: topics.rows.map((row) => ({ slug: String(row.slug), version: String(row.version) })),
    },
    publication: {
      included_review_states: RESEARCH_REVIEW_STATES,
      excluded_review_states: RESEARCH_EXCLUDED_REVIEW_STATES,
      machine_validated:
        "machine_validated records are included and labeled machine_labeled=true, verified=false. They are not human-verified.",
      site_difference:
        "The website can show needs_review statements as unsettled. It does not show unreviewed or rejected records. This research export and /api/v1 omit rejected, unreviewed, and needs_review records, including a human_verified approval whose source or evidence no longer matches.",
    },
    license: publicLicense(datasetRow ? String(datasetRow.dataset_kind) : null),
    counts: {
      people: Number(countRow.people ?? 0),
      organizations: organizations.length,
      identities: Number(countRow.identities ?? 0),
      sources: Number(countRow.sources ?? 0),
      source_items: Number(countRow.source_items ?? 0),
      statements: Number(countRow.statements ?? 0),
      forecasts: Number(countRow.forecasts ?? 0),
      topics: Number(countRow.topics ?? 0),
      relationships: Number(countRow.relationships ?? 0),
      trends: researchTrends.length,
    },
    latest_observed_at: iso(observed.rows[0]?.observed_at ?? null),
    latest_published_at: iso(observed.rows[0]?.published_at ?? null),
  };
  });
}

export type PublicCatalog = Awaited<ReturnType<typeof getPublicCatalog>>;

export async function loadPublicExport(generatedAt: string, pool: Db = getPool()) {
  const catalog = await getPublicCatalog(generatedAt, pool);
  const peopleRows = await pool.query(
    `${personSelect("$1")} WHERE ${publicPersonPredicate("p", "$1")} ORDER BY p.slug`,
    [PUBLIC_STATES],
  );
  const affiliations = await loadAffiliations(pool);
  const identities = await loadIdentities(pool);
  const people: PublicPerson[] = peopleRows.rows.map((row) => {
    const summary = mapPerson(row);
    return {
      ...summary,
      given_name: row.given_name ? String(row.given_name) : null,
      family_name: row.family_name ? String(row.family_name) : null,
      updated_at: iso(row.updated_at),
      affiliations: affiliations.get(summary.slug) ?? [],
      identities: identities.get(summary.slug) ?? [],
    };
  });
  const statements = (await fetchStatements({ limit: PUBLIC_API_LIMITS.defaultPageSize, sort: "event_time_desc" }, pool, "all")).rows;
  const relationships = await fetchRelationships(pool);
  attachRelationships(statements, relationships);
  const sources = (
    await pool.query(`${sourceSelect} WHERE src.review_state = ANY($1::text[]) ORDER BY src.slug`, [PUBLIC_STATES])
  ).rows.map((row) => mapSource(row, generatedAt));
  const participants = await loadParticipants(pool);
  const sourceItems = (
    await pool.query(`${sourceItemSelect} ORDER BY si.slug`, [PUBLIC_STATES])
  ).rows.map((row) => mapSourceItem(row, participants.get(String(row.slug)) ?? []));
  const organizations = await listPublicOrganizations(pool);
  const topics = (await listPublicTopics(pool)).data;
  const identityRows = [...identities.values()].flat().sort((left, right) =>
    `${left.person_slug}|${left.namespace}|${left.external_id}`.localeCompare(
      `${right.person_slug}|${right.namespace}|${right.external_id}`,
    ),
  );
  const forecasts = statements.flatMap((statement) => (statement.forecast ? [statement.forecast] : []));
  const trends = await loadResearchTrends(generatedAt, pool);
  return {
    catalog,
    people,
    organizations,
    identities: identityRows,
    sources,
    source_items: sourceItems,
    statements,
    forecasts,
    topics,
    relationships,
    trends,
  };
}

export type PublicExportBundle = Awaited<ReturnType<typeof loadPublicExport>>;
