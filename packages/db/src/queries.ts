import {
  classifyFreshness,
  distributionAggregationSchema,
  isPublicReviewState,
  peopleListQuerySchema,
  REVIEW_STATES,
  statementListQuerySchema,
  volumeAggregationSchema,
  type Freshness,
  type PeopleListQuery,
  type StatementListQuery,
} from "@pdoom/contracts";
import type pg from "pg";
import { effectiveReviewStateSql } from "./coverage";
import { getPool } from "./pool";
import {
  computeExplicitNumericDistribution,
  computeStatementVolume,
  type DistributionAggregation,
  type TrendCandidate,
} from "./trends";

export class InvalidCursorError extends Error {
  constructor() {
    super("invalid_cursor");
    this.name = "InvalidCursorError";
  }
}

export type Page<T> = {
  data: T[];
  page: {
    limit: number;
    total: number;
    next_cursor: string | null;
    prev_cursor: string | null;
  };
};

type CursorPayload = { v: 1; t: string | null; id: string; dir: "next" | "prev" };

function encodeCursor(payload: CursorPayload): string {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function decodeCursor(cursor: string): CursorPayload {
  try {
    const parsed = JSON.parse(Buffer.from(cursor, "base64url").toString("utf8")) as CursorPayload;
    if (parsed.v !== 1 || (parsed.dir !== "next" && parsed.dir !== "prev")) throw new Error("bad");
    if (parsed.t !== null && (typeof parsed.t !== "string" || parsed.t.length > 300)) throw new Error("bad");
    if (!/^[0-9a-f-]{36}$/i.test(parsed.id)) throw new Error("bad");
    return parsed;
  } catch {
    throw new InvalidCursorError();
  }
}

function day(value: Date | string | null): string | null {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  const text = String(value);
  return /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : text;
}

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

const statementSelect = `
  SELECT
    s.id, s.slug, s.statement_type, s.normalized_text, s.event_time, ${effectiveReviewStateSql("s")} AS review_state, s.confidence,
    s.extractor_version,
    p.slug AS person_slug, p.display_name,
    src.slug AS source_slug, src.name AS source_name, src.source_type,
    si.slug AS source_item_slug, si.title AS source_item_title, si.canonical_url, si.published_at, si.observed_at,
    f.question_key, f.question_text, f.value_type, f.value_numeric, f.value_min, f.value_max, f.unit, f.horizon_text,
    COALESCE(topics.topics, '[]'::jsonb) AS topics
  FROM statements s
  JOIN people p ON p.id = s.person_id
  JOIN source_items si ON si.id = s.source_item_id
  JOIN sources src ON src.id = si.source_id
  LEFT JOIN forecasts f ON f.statement_id = s.id
  LEFT JOIN LATERAL (
    SELECT jsonb_agg(jsonb_build_object('slug', t.slug, 'name', t.name) ORDER BY t.name) AS topics
    FROM statement_topics st
    JOIN topics t ON t.id = st.topic_id
    WHERE st.statement_id = s.id
  ) topics ON true
`;

function mapStatement(row: Record<string, unknown>) {
  return {
    id: String(row.id),
    slug: String(row.slug),
    statement_type: String(row.statement_type),
    normalized_text: String(row.normalized_text),
    event_time: iso(row.event_time as Date | null),
    review_state: String(row.review_state),
    confidence: num(row.confidence as string),
    extractor_version: String(row.extractor_version),
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
    },
    forecast: row.question_key
      ? {
          question_key: String(row.question_key),
          question_text: String(row.question_text),
          value_type: String(row.value_type),
          value_numeric: num(row.value_numeric as string | null),
          value_min: num(row.value_min as string | null),
          value_max: num(row.value_max as string | null),
          unit: row.unit ? String(row.unit) : null,
          horizon_text: row.horizon_text ? String(row.horizon_text) : null,
        }
      : null,
    topics: row.topics as Array<{ slug: string; name: string }>,
  };
}

export type StatementSummary = ReturnType<typeof mapStatement>;

function statementFilters(query: StatementListQuery, values: unknown[]): string {
  const clauses: string[] = [];
  if (query.person) {
    values.push(query.person);
    clauses.push(`p.slug = $${values.length}`);
  }
  if (query.organization) {
    values.push(query.organization);
    clauses.push(`EXISTS (
      SELECT 1 FROM affiliations a
      JOIN organizations o ON o.id = a.organization_id
      WHERE a.person_id = p.id AND o.slug = $${values.length}
    )`);
  }
  if (query.source) {
    values.push(query.source);
    clauses.push(`src.slug = $${values.length}`);
  }
  if (query.topic) {
    values.push(query.topic);
    clauses.push(`EXISTS (
      SELECT 1 FROM statement_topics st
      JOIN topics t ON t.id = st.topic_id
      WHERE st.statement_id = s.id AND t.slug = $${values.length}
    )`);
  }
  if (query.statement_type) {
    values.push(query.statement_type);
    clauses.push(`s.statement_type = $${values.length}`);
  }
  if (query.review_state && !isPublicReviewState(query.review_state)) {
    clauses.push("FALSE");
  } else if (query.review_state) {
    values.push(query.review_state);
    clauses.push(`${effectiveReviewStateSql("s")} = $${values.length}`);
  } else {
    values.push(REVIEW_STATES.filter(isPublicReviewState));
    clauses.push(`${effectiveReviewStateSql("s")} = ANY($${values.length}::text[])`);
  }
  if (query.from) {
    values.push(`${query.from}T00:00:00.000Z`);
    clauses.push(`s.event_time >= $${values.length}::timestamptz`);
  }
  if (query.to) {
    values.push(`${query.to}T23:59:59.999Z`);
    clauses.push(`s.event_time <= $${values.length}::timestamptz`);
  }
  if (query.q) {
    values.push(query.q);
    clauses.push(`s.search_vector @@ plainto_tsquery('simple', $${values.length})`);
  }
  return clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
}

export async function listStatements(input: StatementListQuery, pool = getPool()): Promise<Page<StatementSummary>> {
  const query = statementListQuerySchema.parse(input);
  const values: unknown[] = [];
  const where = statementFilters(query, values);
  const cursor = query.cursor ? decodeCursor(query.cursor) : null;
  const direction = cursor?.dir ?? "next";
  const desc = query.sort === "event_time_desc";
  const forward = direction === "next" ? desc : !desc;
  let cursorClause = "";
  if (cursor) {
    values.push(cursor.t);
    const timeParam = values.length;
    values.push(cursor.id);
    const idParam = values.length;
    const op = forward ? "<" : ">";
    cursorClause = `${where ? "AND" : "WHERE"} (
      ($${timeParam}::timestamptz IS NULL AND s.event_time IS NULL AND s.id ${op} $${idParam}::uuid)
      OR ($${timeParam}::timestamptz IS NOT NULL AND (
        s.event_time ${op} $${timeParam}::timestamptz
        OR (s.event_time = $${timeParam}::timestamptz AND s.id ${op} $${idParam}::uuid)
        ${forward && desc ? `OR s.event_time IS NULL` : ""}
        ${!forward && !desc ? `OR ($${timeParam}::timestamptz IS NULL)` : ""}
      ))
    )`;
  }
  const order = forward ? "s.event_time DESC NULLS LAST, s.id DESC" : "s.event_time ASC NULLS FIRST, s.id ASC";
  values.push(query.limit + 1);
  const sql = `${statementSelect} ${where} ${cursorClause} ORDER BY ${order} LIMIT $${values.length}`;
  const result = await pool.query(sql, values);
  const hasExtra = result.rows.length > query.limit;
  let rows = result.rows.slice(0, query.limit);
  if (!forward) rows = rows.reverse();
  const data = rows.map((row) => mapStatement(row));
  const countValues: unknown[] = [];
  const countWhere = statementFilters(query, countValues);
  const total = await pool.query(`SELECT count(*)::int AS count FROM statements s JOIN people p ON p.id = s.person_id JOIN source_items si ON si.id = s.source_item_id JOIN sources src ON src.id = si.source_id ${countWhere}`, countValues);
  const first = data[0];
  const last = data[data.length - 1];
  return {
    data,
    page: {
      limit: query.limit,
      total: total.rows[0].count as number,
      next_cursor:
        last && (hasExtra || direction === "prev")
          ? encodeCursor({ v: 1, t: last.event_time, id: last.id, dir: "next" })
          : null,
      prev_cursor:
        first && cursor
          ? encodeCursor({ v: 1, t: first.event_time, id: first.id, dir: "prev" })
          : null,
    },
  };
}

export async function getStatement(slug: string, pool = getPool()) {
  const result = await pool.query(
    `SELECT
       s.id, s.slug, s.statement_type, s.normalized_text, s.event_time, ${effectiveReviewStateSql("s")} AS review_state, s.confidence,
       s.extractor_version,
       p.slug AS person_slug, p.display_name,
       src.slug AS source_slug, src.name AS source_name, src.source_type,
       si.slug AS source_item_slug, si.title AS source_item_title, si.canonical_url, si.published_at, si.observed_at,
       f.question_key, f.question_text, f.value_type, f.value_numeric, f.value_min, f.value_max, f.unit, f.horizon_text,
       COALESCE(topics.topics, '[]'::jsonb) AS topics,
       e.slug AS evidence_slug, e.segment_kind, e.sequence, e.start_char, e.end_char, e.start_ms, e.end_ms,
       e.text AS evidence_text, e.context_text, e.segment_hash,
       si.content_hash, si.content_reference, si.language, si.published_timezone, si.collection_status, si.availability,
       er.extractor_name, er.prompt_contract_version, er.input_hash, er.model_name
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     JOIN evidence_segments e ON e.id = s.evidence_segment_id
     LEFT JOIN forecasts f ON f.statement_id = s.id
     LEFT JOIN extraction_runs er ON er.id = s.extraction_run_id
     LEFT JOIN LATERAL (
       SELECT jsonb_agg(jsonb_build_object('slug', t.slug, 'name', t.name) ORDER BY t.name) AS topics
       FROM statement_topics st
       JOIN topics t ON t.id = st.topic_id
       WHERE st.statement_id = s.id
     ) topics ON true
     WHERE s.slug = $1`,
    [slug],
  );
  const row = result.rows[0];
  if (!row || !isPublicReviewState(String(row.review_state))) return null;
  const base = mapStatement(row);
  const relations = await pool.query(
    `SELECT r.relationship_type, r.method, r.confidence, r.review_state,
            fs.slug AS from_slug, ts.slug AS to_slug
     FROM statement_relationships r
     JOIN statements fs ON fs.id = r.from_statement_id
     JOIN statements ts ON ts.id = r.to_statement_id
     WHERE fs.slug = $1 OR ts.slug = $1`,
    [slug],
  );
  return {
    ...base,
    evidence: {
      slug: String(row.evidence_slug),
      segment_kind: String(row.segment_kind),
      sequence: Number(row.sequence),
      start_char: row.start_char === null ? null : Number(row.start_char),
      end_char: row.end_char === null ? null : Number(row.end_char),
      start_ms: row.start_ms === null ? null : Number(row.start_ms),
      end_ms: row.end_ms === null ? null : Number(row.end_ms),
      text: String(row.evidence_text),
      context_text: row.context_text ? String(row.context_text) : null,
      segment_hash: String(row.segment_hash),
    },
    provenance: {
      content_hash: String(row.content_hash),
      content_reference: row.content_reference ? String(row.content_reference) : null,
      language: row.language ? String(row.language) : null,
      published_timezone: row.published_timezone ? String(row.published_timezone) : null,
      collection_status: String(row.collection_status),
      availability: String(row.availability),
      extractor_name: row.extractor_name ? String(row.extractor_name) : null,
      prompt_contract_version: row.prompt_contract_version ? String(row.prompt_contract_version) : null,
      input_hash: row.input_hash ? String(row.input_hash) : null,
      model_name: row.model_name ? String(row.model_name) : null,
    },
    relationships: relations.rows.map((relation) => ({
      relationship_type: String(relation.relationship_type),
      method: String(relation.method),
      confidence: num(relation.confidence),
      review_state: String(relation.review_state),
      from_slug: String(relation.from_slug),
      to_slug: String(relation.to_slug),
    })),
  };
}

export async function listPeople(input: PeopleListQuery, pool = getPool()) {
  const query = peopleListQuerySchema.parse(input);
  const values: unknown[] = [];
  const clauses: string[] = [];
  if (query.q) {
    values.push(query.q);
    clauses.push(`p.search_vector @@ plainto_tsquery('simple', $${values.length})`);
  }
  if (query.organization) {
    values.push(query.organization);
    clauses.push(`EXISTS (
      SELECT 1 FROM affiliations a JOIN organizations o ON o.id = a.organization_id
      WHERE a.person_id = p.id AND o.slug = $${values.length}
    )`);
  }
  if (query.status) {
    values.push(query.status);
    clauses.push(`p.status = $${values.length}`);
  }
  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  const cursor = query.cursor ? decodeCursor(query.cursor) : null;
  let cursorClause = "";
  if (cursor?.t) {
    values.push(cursor.t);
    const nameParam = values.length;
    values.push(cursor.id);
    const idParam = values.length;
    const op = cursor.dir === "prev" ? "<" : ">";
    cursorClause = `${where ? "AND" : "WHERE"} (p.display_name ${op} $${nameParam} OR (p.display_name = $${nameParam} AND p.id ${op} $${idParam}::uuid))`;
  }
  values.push(query.limit + 1);
  const sql = `
    SELECT p.id, p.slug, p.display_name, p.bio_short, p.status, p.inclusion_reason, p.cohort_tags,
           o.slug AS organization_slug, o.name AS organization_name, a.role,
           counts.counts
    FROM people p
    LEFT JOIN affiliations a ON a.id = p.current_affiliation_id
    LEFT JOIN organizations o ON o.id = a.organization_id
    LEFT JOIN LATERAL (
      SELECT jsonb_object_agg(statement_type, count) AS counts
      FROM (
        SELECT statement_type, count(*)::int AS count
        FROM statements s WHERE s.person_id = p.id AND s.review_state <> 'rejected'
        GROUP BY statement_type
      ) grouped
    ) counts ON true
    ${where} ${cursorClause}
    ORDER BY p.display_name ASC, p.id ASC
    LIMIT $${values.length}
  `;
  const result = await pool.query(sql, values);
  const hasExtra = result.rows.length > query.limit;
  const rows = result.rows.slice(0, query.limit);
  const countValues: unknown[] = [];
  const countClauses: string[] = [];
  if (query.q) {
    countValues.push(query.q);
    countClauses.push(`p.search_vector @@ plainto_tsquery('simple', $${countValues.length})`);
  }
  if (query.organization) {
    countValues.push(query.organization);
    countClauses.push(`EXISTS (
      SELECT 1 FROM affiliations a JOIN organizations o ON o.id = a.organization_id
      WHERE a.person_id = p.id AND o.slug = $${countValues.length}
    )`);
  }
  if (query.status) {
    countValues.push(query.status);
    countClauses.push(`p.status = $${countValues.length}`);
  }
  const total = await pool.query(
    `SELECT count(*)::int AS count FROM people p ${countClauses.length ? `WHERE ${countClauses.join(" AND ")}` : ""}`,
    countValues,
  );
  const data = rows.map((row) => ({
    id: String(row.id),
    slug: String(row.slug),
    display_name: String(row.display_name),
    bio_short: String(row.bio_short),
    status: String(row.status),
    inclusion_reason: String(row.inclusion_reason),
    cohort_tags: row.cohort_tags as string[],
    organization: row.organization_slug
      ? { slug: String(row.organization_slug), name: String(row.organization_name), role: row.role ? String(row.role) : null }
      : null,
    statement_counts: (row.counts ?? {}) as Record<string, number>,
  }));
  const first = data[0];
  const last = data[data.length - 1];
  return {
    data,
    page: {
      limit: query.limit,
      total: total.rows[0].count as number,
      next_cursor: last && hasExtra ? encodeCursor({ v: 1, t: last.display_name, id: last.id, dir: "next" }) : null,
      prev_cursor: first && cursor ? encodeCursor({ v: 1, t: first.display_name, id: first.id, dir: "prev" }) : null,
    },
  };
}

export async function getPerson(slug: string, pool = getPool()) {
  const people = await listPeople({ limit: 1, q: undefined, status: undefined, organization: undefined }, pool);
  const result = await pool.query(
    `SELECT p.id, p.slug, p.display_name, p.given_name, p.family_name, p.bio_short, p.status,
            p.inclusion_reason, p.cohort_tags, p.updated_at
     FROM people p WHERE p.slug = $1`,
    [slug],
  );
  const person = result.rows[0];
  if (!person) return null;
  void people;
  const affiliations = await pool.query(
    `SELECT a.role, a.start_date, a.end_date, a.confidence_level, a.verification_detail, a.review_state, o.slug, o.name
     FROM affiliations a JOIN organizations o ON o.id = a.organization_id
     WHERE a.person_id = $1
     ORDER BY a.start_date NULLS LAST`,
    [person.id],
  );
  const identities = await pool.query(
    `SELECT namespace, external_id, canonical_url, handle, verification_method, verification_detail,
            confidence_level, review_state, verified_at
     FROM external_identities WHERE person_id = $1 ORDER BY namespace`,
    [person.id],
  );
  const statements = await listStatements({ person: slug, limit: 50, sort: "event_time_desc" }, pool);
  const sources = await pool.query(
    `SELECT slug, name, source_type, canonical_url, collection_method, collection_adapter, review_state,
            last_checked_at, last_success_at, enabled
     FROM sources WHERE owner_person_id = $1 ORDER BY name`,
    [person.id],
  );
  const asOf = new Date().toISOString();
  return {
    slug: String(person.slug),
    display_name: String(person.display_name),
    given_name: person.given_name ? String(person.given_name) : null,
    family_name: person.family_name ? String(person.family_name) : null,
    bio_short: String(person.bio_short),
    status: String(person.status),
    inclusion_reason: String(person.inclusion_reason),
    cohort_tags: person.cohort_tags as string[],
    updated_at: iso(person.updated_at),
    affiliations: affiliations.rows.map((row) => ({
      role: row.role ? String(row.role) : null,
      start_date: day(row.start_date),
      end_date: day(row.end_date),
      confidence_level: String(row.confidence_level),
      verification_detail: row.verification_detail ? String(row.verification_detail) : null,
      review_state: String(row.review_state),
      settled: isPublicReviewState(String(row.review_state)) && String(row.review_state) === "human_verified",
      organization: { slug: String(row.slug), name: String(row.name) },
    })),
    identities: identities.rows.map((row) => ({
      namespace: String(row.namespace),
      external_id: String(row.external_id),
      canonical_url: row.canonical_url ? String(row.canonical_url) : null,
      handle: row.handle ? String(row.handle) : null,
      verification_method: String(row.verification_method),
      verification_detail: row.verification_detail ? String(row.verification_detail) : null,
      confidence_level: String(row.confidence_level),
      review_state: String(row.review_state),
      settled: String(row.review_state) === "human_verified",
      verified_at: iso(row.verified_at),
    })),
    sources: sources.rows.map((row) => ({
      slug: String(row.slug),
      name: String(row.name),
      source_type: String(row.source_type),
      canonical_url: String(row.canonical_url),
      collection_method: String(row.collection_method),
      collection_adapter: row.collection_adapter ? String(row.collection_adapter) : null,
      review_state: String(row.review_state),
      settled: String(row.review_state) === "human_verified",
      enabled: Boolean(row.enabled),
      last_checked_at: iso(row.last_checked_at),
      last_success_at: iso(row.last_success_at),
      freshness: classifyFreshness(iso(row.last_success_at), asOf),
    })),
    statements: statements.data,
  };
}

export async function listTopics(pool = getPool()) {
  const result = await pool.query(`
    SELECT t.slug, t.name, t.definition, t.version, parent.slug AS parent_slug,
           counts.counts, counts.total
    FROM topics t
    LEFT JOIN topics parent ON parent.id = t.parent_topic_id
    LEFT JOIN LATERAL (
      SELECT COALESCE(jsonb_object_agg(statement_type, count), '{}'::jsonb) AS counts,
             COALESCE(sum(count), 0)::int AS total
      FROM (
        SELECT s.statement_type, count(*)::int AS count
        FROM statement_topics st
        JOIN statements s ON s.id = st.statement_id
        WHERE st.topic_id = t.id AND s.review_state <> 'rejected'
        GROUP BY s.statement_type
      ) grouped
    ) counts ON true
    ORDER BY t.name
  `);
  return result.rows.map((row) => ({
    slug: String(row.slug),
    name: String(row.name),
    definition: String(row.definition),
    version: String(row.version),
    parent_slug: row.parent_slug ? String(row.parent_slug) : null,
    statement_counts: (row.counts ?? {}) as Record<string, number>,
    statement_total: Number(row.total),
  }));
}

export async function getTopic(slug: string, pool = getPool()) {
  const topics = await listTopics(pool);
  const topic = topics.find((item) => item.slug === slug);
  if (!topic) return null;
  const statements = await listStatements({ topic: slug, limit: 50, sort: "event_time_desc" }, pool);
  return { ...topic, statements: statements.data };
}

export async function listSources(pool = getPool()) {
  const result = await pool.query(`
    SELECT src.slug, src.name, src.source_type, src.canonical_url, src.platform, src.enabled,
           src.last_checked_at, src.last_success_at, src.collection_method, src.collection_adapter,
           src.review_state, src.rights_notes,
           p.display_name AS owner_name, p.slug AS owner_slug,
           o.name AS organization_name,
           (SELECT count(*)::int FROM source_items si WHERE si.source_id = src.id) AS item_count
    FROM sources src
    LEFT JOIN people p ON p.id = src.owner_person_id
    LEFT JOIN organizations o ON o.id = src.owner_organization_id
    ORDER BY src.name
  `);
  return result.rows.map((row) => ({
    slug: String(row.slug),
    name: String(row.name),
    source_type: String(row.source_type),
    canonical_url: String(row.canonical_url),
    platform: row.platform ? String(row.platform) : null,
    enabled: Boolean(row.enabled),
    last_checked_at: iso(row.last_checked_at),
    last_success_at: iso(row.last_success_at),
    collection_method: String(row.collection_method),
    collection_adapter: row.collection_adapter ? String(row.collection_adapter) : null,
    review_state: String(row.review_state),
    freshness: classifyFreshness(iso(row.last_success_at), new Date().toISOString()),
    rights_notes: row.rights_notes ? String(row.rights_notes) : null,
    owner_name: row.owner_name ? String(row.owner_name) : null,
    owner_slug: row.owner_slug ? String(row.owner_slug) : null,
    organization_name: row.organization_name ? String(row.organization_name) : null,
    item_count: Number(row.item_count),
  }));
}

export async function getSource(slug: string, pool = getPool()) {
  const sources = await listSources(pool);
  const source = sources.find((item) => item.slug === slug);
  if (!source) return null;
  const items = await pool.query(
    `SELECT si.slug, si.title, si.canonical_url, si.published_at, si.observed_at, si.collection_status,
            si.availability, si.content_reference, si.language
     FROM source_items si
     JOIN sources src ON src.id = si.source_id
     WHERE src.slug = $1
     ORDER BY si.published_at DESC NULLS LAST`,
    [slug],
  );
  return {
    ...source,
    items: items.rows.map((row) => ({
      slug: String(row.slug),
      title: row.title ? String(row.title) : null,
      canonical_url: String(row.canonical_url),
      published_at: iso(row.published_at),
      observed_at: iso(row.observed_at),
      collection_status: String(row.collection_status),
      availability: String(row.availability),
      content_reference: row.content_reference ? String(row.content_reference) : null,
      language: row.language ? String(row.language) : null,
    })),
  };
}

export async function getSourceItem(slug: string, pool = getPool()) {
  const result = await pool.query(
    `SELECT si.slug, si.title, si.canonical_url, si.published_at, si.published_timezone, si.observed_at,
            si.language, si.content_hash, si.content_version, si.content_reference, si.metadata_json,
            si.collection_status, si.availability, si.logical_key,
            src.slug AS source_slug, src.name AS source_name, src.source_type
     FROM source_items si
     JOIN sources src ON src.id = si.source_id
     WHERE si.slug = $1`,
    [slug],
  );
  const row = result.rows[0];
  if (!row) return null;
  const participants = await pool.query(
    `SELECT sp.role, sp.attribution_method, sp.attribution_detail, sp.confidence_level, p.slug AS person_slug, p.display_name,
            o.slug AS organization_slug, o.name AS organization_name
     FROM source_participants sp
     JOIN source_items si ON si.id = sp.source_item_id
     LEFT JOIN people p ON p.id = sp.person_id
     LEFT JOIN organizations o ON o.id = sp.organization_id
     WHERE si.slug = $1
     ORDER BY sp.role`,
    [slug],
  );
  const evidence = await pool.query(
    `SELECT e.slug, e.segment_kind, e.sequence, e.start_char, e.end_char, e.start_ms, e.end_ms, e.text, e.context_text, e.segment_hash
     FROM evidence_segments e
     JOIN source_items si ON si.id = e.source_item_id
     WHERE si.slug = $1
     ORDER BY e.sequence`,
    [slug],
  );
  return {
    slug: String(row.slug),
    title: row.title ? String(row.title) : null,
    canonical_url: String(row.canonical_url),
    published_at: iso(row.published_at),
    published_timezone: row.published_timezone ? String(row.published_timezone) : null,
    observed_at: iso(row.observed_at),
    language: row.language ? String(row.language) : null,
    content_hash: String(row.content_hash),
    content_version: Number(row.content_version),
    content_reference: row.content_reference ? String(row.content_reference) : null,
    metadata: row.metadata_json,
    collection_status: String(row.collection_status),
    availability: String(row.availability),
    logical_key: String(row.logical_key),
    source: { slug: String(row.source_slug), name: String(row.source_name), source_type: String(row.source_type) },
    participants: participants.rows.map((participant) => ({
      role: String(participant.role),
      attribution_method: String(participant.attribution_method),
      attribution_detail: participant.attribution_detail ? String(participant.attribution_detail) : null,
      confidence_level: String(participant.confidence_level),
      person_slug: participant.person_slug ? String(participant.person_slug) : null,
      display_name: participant.display_name ? String(participant.display_name) : null,
      organization_slug: participant.organization_slug ? String(participant.organization_slug) : null,
      organization_name: participant.organization_name ? String(participant.organization_name) : null,
    })),
    evidence: evidence.rows.map((segment) => ({
      slug: String(segment.slug),
      segment_kind: String(segment.segment_kind),
      sequence: Number(segment.sequence),
      start_char: segment.start_char === null ? null : Number(segment.start_char),
      end_char: segment.end_char === null ? null : Number(segment.end_char),
      start_ms: segment.start_ms === null ? null : Number(segment.start_ms),
      end_ms: segment.end_ms === null ? null : Number(segment.end_ms),
      text: String(segment.text),
      context_text: segment.context_text ? String(segment.context_text) : null,
      segment_hash: String(segment.segment_hash),
    })),
  };
}

async function loadDistributionCandidates(pool: pg.Pool, cohortSlug: string, cohortVersion: string): Promise<{ size: number; candidates: TrendCandidate[] }> {
  const size = await pool.query(
    `SELECT count(*)::int AS count
     FROM cohort_memberships cm JOIN cohorts c ON c.id = cm.cohort_id
     WHERE c.slug = $1 AND c.version = $2`,
    [cohortSlug, cohortVersion],
  );
  const result = await pool.query(
    `SELECT s.slug AS statement_slug, p.slug AS person_slug, p.display_name, s.statement_type, ${effectiveReviewStateSql("s")} AS review_state,
            s.event_time, f.question_key, f.value_type, f.value_numeric, f.unit, f.horizon_text,
            COALESCE(array_agg(DISTINCT t.slug) FILTER (WHERE t.slug IS NOT NULL), '{}') AS topic_slugs
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN cohort_memberships cm ON cm.person_id = p.id
     JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
     LEFT JOIN forecasts f ON f.statement_id = s.id
     LEFT JOIN statement_topics st ON st.statement_id = s.id
     LEFT JOIN topics t ON t.id = st.topic_id
     GROUP BY s.id, p.slug, p.display_name, f.question_key, f.value_type, f.value_numeric, f.unit, f.horizon_text`,
    [cohortSlug, cohortVersion],
  );
  return {
    size: size.rows[0].count as number,
    candidates: result.rows.map((row) => ({
      statement_slug: String(row.statement_slug),
      person_slug: String(row.person_slug),
      display_name: String(row.display_name),
      statement_type: String(row.statement_type),
      review_state: String(row.review_state),
      topic_slugs: row.topic_slugs as string[],
      question_key: row.question_key ? String(row.question_key) : null,
      value_type: row.value_type ? String(row.value_type) : null,
      value_numeric: num(row.value_numeric),
      unit: row.unit ? String(row.unit) : null,
      horizon_text: row.horizon_text ? String(row.horizon_text) : null,
      event_time: iso(row.event_time),
    })),
  };
}

export async function listTrends(pool = getPool()) {
  const result = await pool.query(
    `SELECT td.slug, td.name, td.method_version, td.published, c.slug AS cohort_slug, c.version AS cohort_version,
            t.slug AS topic_slug
     FROM trend_definitions td
     JOIN cohorts c ON c.id = td.cohort_id
     LEFT JOIN topics t ON t.id = td.topic_id
     WHERE td.published
     ORDER BY td.name`,
  );
  return result.rows.map((row) => ({
    slug: String(row.slug),
    name: String(row.name),
    method_version: String(row.method_version),
    cohort_slug: String(row.cohort_slug),
    cohort_version: String(row.cohort_version),
    topic_slug: row.topic_slug ? String(row.topic_slug) : null,
  }));
}

export async function getTrend(slug: string, pool = getPool()) {
  const result = await pool.query(
    `SELECT td.slug, td.name, td.method_version, td.cohort_definition_json, td.aggregation_definition_json,
            c.slug AS cohort_slug, c.version AS cohort_version, c.definition AS cohort_definition
     FROM trend_definitions td
     JOIN cohorts c ON c.id = td.cohort_id
     WHERE td.slug = $1 AND td.published`,
    [slug],
  );
  const row = result.rows[0];
  if (!row) return null;
  const aggregation = row.aggregation_definition_json;
  const header = {
    slug: String(row.slug),
    name: String(row.name),
    method_version: String(row.method_version),
    cohort_slug: String(row.cohort_slug),
    cohort_version: String(row.cohort_version),
    cohort_definition: String(row.cohort_definition),
    calculated_at: new Date().toISOString(),
  };
  if (aggregation.type === "explicit_numeric_distribution") {
    const parsed = distributionAggregationSchema.parse(aggregation) as DistributionAggregation;
    const loaded = await loadDistributionCandidates(pool, header.cohort_slug, header.cohort_version);
    const distribution = computeExplicitNumericDistribution({
      method_version: header.method_version,
      cohort_slug: header.cohort_slug,
      cohort_version: header.cohort_version,
      cohort_definition: header.cohort_definition,
      cohort_size: loaded.size,
      aggregation: parsed,
      candidates: loaded.candidates,
    });
    return { ...header, kind: "distribution" as const, distribution };
  }
  const parsed = volumeAggregationSchema.parse(aggregation);
  const volumeRows = await pool.query(
    `SELECT s.slug AS statement_slug, p.slug AS person_slug, s.statement_type, ${effectiveReviewStateSql("s")} AS review_state, s.event_time, t.slug AS topic_slug
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN cohort_memberships cm ON cm.person_id = p.id
     JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
     JOIN statement_topics st ON st.statement_id = s.id
     JOIN topics t ON t.id = st.topic_id`,
    [header.cohort_slug, header.cohort_version],
  );
  const volume = computeStatementVolume({
    review_states: parsed.review_states,
    rows: volumeRows.rows.map((item) => ({
      statement_slug: String(item.statement_slug),
      person_slug: String(item.person_slug),
      statement_type: String(item.statement_type),
      review_state: String(item.review_state),
      topic_slug: String(item.topic_slug),
      event_time: iso(item.event_time),
    })),
  });
  return { ...header, kind: "volume" as const, volume };
}

export async function getDatasetRecord(pool = getPool()) {
  const result = await pool.query(
    `SELECT schema_version, dataset_id, dataset_kind, generated_at, imported_at, notice,
            producer_name, producer_version, cohort_slug, cohort_version
     FROM dataset_imports WHERE is_current
     ORDER BY imported_at DESC LIMIT 1`,
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    schema_version: String(row.schema_version),
    dataset_id: String(row.dataset_id),
    dataset_kind: String(row.dataset_kind),
    generated_at: iso(row.generated_at),
    imported_at: iso(row.imported_at),
    notice: String(row.notice),
    producer_name: row.producer_name ? String(row.producer_name) : null,
    producer_version: row.producer_version ? String(row.producer_version) : null,
    cohort_slug: row.cohort_slug ? String(row.cohort_slug) : null,
    cohort_version: row.cohort_version ? String(row.cohort_version) : null,
  };
}

const ACADEMIC_SOURCE_TYPES = ["academic_works", "paper", "preprint"];
const FIRST_PARTY_SOURCE_TYPES = ["personal_site", "blog", "newsletter", "repository", "social_post"];
const FAILING_COLLECTION_STATUSES = [
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

export async function getCoverage(asOf = new Date().toISOString(), pool = getPool()) {
  const dataset = await getDatasetRecord(pool);
  const cohort = dataset?.cohort_slug
    ? await pool.query(
        `SELECT slug, version, name, definition FROM cohorts WHERE slug = $1 AND version = $2`,
        [dataset.cohort_slug, dataset.cohort_version],
      )
    : { rows: [] as Array<Record<string, unknown>> };
  const cohortRow = cohort.rows[0];
  const params = cohortRow ? [cohortRow.slug, cohortRow.version] : [];
  const academicParam = params.length + 1;
  const firstPartyParam = params.length + 2;
  const failingParam = params.length + 1;
  const memberJoin = cohortRow
    ? `JOIN cohort_memberships cm ON cm.person_id = p.id
       JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2`
    : "";
  const sourceScope = cohortRow
    ? `WHERE src.owner_person_id IN (
         SELECT cm.person_id FROM cohort_memberships cm
         JOIN cohorts c ON c.id = cm.cohort_id AND c.slug = $1 AND c.version = $2
       ) OR src.owner_person_id IS NULL`
    : "";
  const [people, typed, latest, failing, statements] = await Promise.all([
    pool.query(
      `SELECT count(DISTINCT p.id)::int AS cohort_size,
              count(DISTINCT p.id) FILTER (WHERE src.id IS NOT NULL)::int AS people_with_sources,
              count(DISTINCT p.id) FILTER (
                WHERE src.source_type IS NOT NULL AND NOT (src.source_type = ANY($${academicParam}::text[]))
              )::int AS people_with_non_academic_sources,
              count(DISTINCT p.id) FILTER (
                WHERE src.source_type = ANY($${firstPartyParam}::text[])
              )::int AS people_with_first_party_sources,
              count(DISTINCT p.id) FILTER (WHERE st.person_id IS NOT NULL)::int AS statement_bearing_people
       FROM people p
       ${memberJoin}
       LEFT JOIN sources src ON src.owner_person_id = p.id
       LEFT JOIN (
         SELECT DISTINCT person_id FROM statements WHERE review_state <> 'rejected'
       ) st ON st.person_id = p.id`,
      [...params, ACADEMIC_SOURCE_TYPES, FIRST_PARTY_SOURCE_TYPES],
    ),
    pool.query(
      `SELECT src.source_type, src.last_success_at
       FROM sources src
       ${sourceScope}`,
      params,
    ),
    pool.query(
      `SELECT max(src.last_success_at) AS last_success_at, max(si.observed_at) AS observed_at
       FROM sources src
       LEFT JOIN source_items si ON si.source_id = src.id
       ${sourceScope}`,
      params,
    ),
    pool.query(
      `SELECT count(DISTINCT src.id)::int AS failing
       FROM sources src
       LEFT JOIN source_items si ON si.source_id = src.id AND si.collection_status = ANY($${failingParam}::text[])
       ${sourceScope ? sourceScope.replace("WHERE", "WHERE (") + ") AND" : "WHERE"} (
         (src.last_checked_at IS NOT NULL AND src.last_success_at IS NULL) OR si.id IS NOT NULL
       )`,
      [...params, FAILING_COLLECTION_STATUSES],
    ),
    pool.query(
      `SELECT count(*)::int AS count FROM statements s WHERE ${effectiveReviewStateSql("s")} = ANY($1::text[])`,
      [REVIEW_STATES.filter(isPublicReviewState)],
    ),
  ]);
  const freshness: Record<Freshness, number> = { current: 0, aging: 0, stale: 0, never_checked: 0 };
  const sourcesByType: Record<string, number> = {};
  let recent = 0;
  let stale = 0;
  for (const row of typed.rows) {
    const type = String(row.source_type);
    sourcesByType[type] = (sourcesByType[type] ?? 0) + 1;
    const state = classifyFreshness(iso(row.last_success_at), asOf);
    freshness[state] += 1;
    if (state === "current") recent += 1;
    if (state === "stale") stale += 1;
  }
  const cohortSize = Number(people.rows[0]?.cohort_size ?? 0);
  return {
    as_of: asOf,
    cohort_slug: cohortRow ? String(cohortRow.slug) : null,
    cohort_version: cohortRow ? String(cohortRow.version) : null,
    cohort_size: cohortSize,
    people_with_sources: Number(people.rows[0]?.people_with_sources ?? 0),
    people_with_non_academic_sources: Number(people.rows[0]?.people_with_non_academic_sources ?? 0),
    people_with_first_party_sources: Number(people.rows[0]?.people_with_first_party_sources ?? 0),
    statement_bearing_people: Number(people.rows[0]?.statement_bearing_people ?? 0),
    public_statement_count: Number(statements.rows[0]?.count ?? 0),
    recent_successfully_checked_sources: recent,
    sources_by_type: sourcesByType,
    source_count: typed.rows.length,
    latest_successful_observation: iso(latest.rows[0]?.last_success_at),
    latest_item_observed_at: iso(latest.rows[0]?.observed_at),
    stale_sources: stale,
    unavailable_or_failing_sources: Number(failing.rows[0]?.failing ?? 0),
    freshness,
  };
}

export async function getOverview(pool = getPool()) {
  const dataset = await getDatasetRecord(pool);
  const coverage = await getCoverage(new Date().toISOString(), pool);
  const [people, statements, items, observed] = await Promise.all([
    pool.query("SELECT count(*)::int AS count FROM people"),
    pool.query("SELECT count(*)::int AS count FROM statements WHERE review_state <> 'rejected'"),
    pool.query("SELECT count(*)::int AS count FROM source_items"),
    pool.query("SELECT max(observed_at) AS observed_at, max(published_at) AS published_at FROM source_items"),
  ]);
  const cohort = dataset?.cohort_slug
    ? await pool.query(`SELECT slug, version, name, definition FROM cohorts WHERE slug = $1 AND version = $2`, [
        dataset.cohort_slug,
        dataset.cohort_version,
      ])
    : { rows: [] as Array<Record<string, unknown>> };
  const trends = (await listTrends(pool)).filter(
    (trend) => !dataset?.cohort_slug || (trend.cohort_slug === dataset.cohort_slug && trend.cohort_version === dataset.cohort_version),
  );
  const verified = await pool.query(
    `SELECT count(*)::int AS count FROM statements s WHERE ${effectiveReviewStateSql("s")} = 'human_verified'`,
  );
  const showTrends = dataset?.dataset_kind !== "live" || Number(verified.rows[0].count) > 0;
  const computed = [];
  if (showTrends) {
    for (const trend of trends) {
      computed.push(await getTrend(trend.slug, pool));
    }
  }
  const recent = await listStatements({ limit: 8, sort: "event_time_desc" }, pool);
  const revisions = await pool.query(
    `SELECT r.relationship_type, fs.slug AS from_slug, ts.slug AS to_slug, p.display_name, p.slug AS person_slug,
            ts.event_time
     FROM statement_relationships r
     JOIN statements fs ON fs.id = r.from_statement_id
     JOIN statements ts ON ts.id = r.to_statement_id
     JOIN people p ON p.id = ts.person_id
     WHERE r.review_state <> 'rejected' AND fs.review_state <> 'rejected' AND ts.review_state <> 'rejected'
     ORDER BY ts.event_time DESC NULLS LAST
     LIMIT 5`,
  );
  return {
    dataset: {
      synthetic: dataset?.dataset_kind === "synthetic",
      dataset_id: dataset?.dataset_id ?? null,
      dataset_kind: dataset?.dataset_kind ?? null,
      schema_version: dataset?.schema_version ?? null,
      generated_at: dataset?.generated_at ?? null,
      imported_at: dataset?.imported_at ?? null,
      producer_name: dataset?.producer_name ?? null,
      producer_version: dataset?.producer_version ?? null,
      notice: dataset?.notice ?? "No dataset is loaded.",
      cohort: cohort.rows[0]
        ? {
            slug: String(cohort.rows[0].slug),
            version: String(cohort.rows[0].version),
            name: String(cohort.rows[0].name),
            definition: String(cohort.rows[0].definition),
          }
        : null,
      coverage,
      person_count: people.rows[0].count as number,
      statement_count: statements.rows[0].count as number,
      source_item_count: items.rows[0].count as number,
      latest_observed_at: iso(observed.rows[0].observed_at),
      latest_published_at: iso(observed.rows[0].published_at),
    },
    trends: computed.filter((trend) => trend !== null),
    recent_statements: recent.data,
    revisions: revisions.rows.map((row) => ({
      relationship_type: String(row.relationship_type),
      from_slug: String(row.from_slug),
      to_slug: String(row.to_slug),
      display_name: String(row.display_name),
      person_slug: String(row.person_slug),
      event_time: iso(row.event_time),
    })),
  };
}

export async function searchAll(q: string, pool = getPool()) {
  const people = await listPeople({ q, limit: 5 }, pool);
  const statements = await listStatements({ q, limit: 8, sort: "event_time_desc" }, pool);
  const topics = await pool.query(
    `SELECT slug, name FROM topics WHERE name ILIKE '%' || $1 || '%' OR definition ILIKE '%' || $1 || '%' ORDER BY name LIMIT 5`,
    [q],
  );
  return {
    people: people.data,
    statements: statements.data,
    topics: topics.rows.map((row) => ({ slug: String(row.slug), name: String(row.name) })),
  };
}
