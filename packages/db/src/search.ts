import { createHash } from "node:crypto";
import {
  SEARCH_PAGE_LIMIT_DEFAULT,
  SEARCH_RANK,
  SEARCH_SUGGEST_LIMITS,
  prepareSearchText,
  publicReviewStates,
  searchQuerySchema,
  searchTypesForFilters,
  type SearchEntityType,
  type SearchGroup,
  type SearchHit,
  type SearchMatch,
  type SearchOrganizationHit,
  type SearchPersonHit,
  type SearchQuery,
  type SearchResponse,
  type SearchSourceHit,
  type SearchSourceItemHit,
  type SearchStatementHit,
  type SearchTopicHit,
} from "@pdoom/contracts";
import type pg from "pg";
import { effectiveReviewStateSql } from "./coverage";
import { getPool } from "./pool";
import { InvalidCursorError } from "./queries";
import { isPool, isStatementTimeout, withConsistentRead } from "./read-snapshot";

export class SearchTimeoutError extends Error {
  constructor() {
    super("search_timeout");
    this.name = "SearchTimeoutError";
  }
}

type SortMode = "name" | "time";

type CursorPayload = {
  v: 2;
  fp: string;
  rank: number;
  tie: string;
  id: string;
  sort: SortMode;
};

type BoundQuery = {
  text: string;
  values: unknown[];
};

class Params {
  values: unknown[] = [];

  add(value: unknown): string {
    this.values.push(value);
    return `$${this.values.length}`;
  }
}

const QUERY_CTE = `
  q AS (
    SELECT
      $1::text AS norm,
      $2::text AS like_norm,
      $3::text[] AS tokens,
      $4::text[] AS public_states,
      (
        SELECT string_agg((plainto_tsquery('simple', token)::text || ':*'), ' & ')::tsquery
        FROM unnest($3::text[]) AS token
      ) AS tsq
  )
`;

function collapse(expr: string): string {
  return `lower(regexp_replace(btrim(${expr}), '[[:space:]]+', ' ', 'g'))`;
}

function tokenPrefix(expr: string): string {
  return `cardinality(q.tokens) > 0 AND NOT EXISTS (
    SELECT 1 FROM unnest(q.tokens) AS token
    WHERE NOT EXISTS (
      SELECT 1
      FROM unnest(string_to_array(regexp_replace(lower(${expr}), '[[:space:][:punct:]]+', ' ', 'g'), ' ')) AS word
      WHERE word <> '' AND word LIKE token || '%'
    )
  )`;
}

function nameRank(expr: string, family: string | null, vectorSql: string, roleSql: string | null): string {
  const collapsed = collapse(expr);
  return `CASE
    WHEN ${collapsed} = q.norm THEN ${SEARCH_RANK.exact_name}
    ${family ? `WHEN cardinality(q.tokens) = 1 AND lower(btrim(${family})) = q.tokens[1] THEN ${SEARCH_RANK.family_name}` : ""}
    WHEN ${collapsed} LIKE q.like_norm || ' %' ESCAPE '!' THEN ${SEARCH_RANK.name_prefix}
    WHEN ${tokenPrefix(expr)} THEN ${SEARCH_RANK.token_prefix}
    WHEN ${vectorSql} THEN ${SEARCH_RANK.all_tokens}
    ${roleSql ? `WHEN ${roleSql} THEN ${SEARCH_RANK.affiliation_role}` : ""}
    ELSE 0
  END`;
}

function matchFromRank(rankExpr: string): string {
  return `CASE ${rankExpr}
    WHEN ${SEARCH_RANK.exact_text} THEN 'exact_text'
    WHEN ${SEARCH_RANK.exact_name} THEN 'exact_name'
    WHEN ${SEARCH_RANK.family_name} THEN 'family_name'
    WHEN ${SEARCH_RANK.name_prefix} THEN 'name_prefix'
    WHEN ${SEARCH_RANK.token_prefix} THEN 'token_prefix'
    WHEN ${SEARCH_RANK.phrase} THEN 'phrase'
    WHEN ${SEARCH_RANK.all_tokens} THEN 'all_tokens'
    WHEN ${SEARCH_RANK.affiliation_role} THEN 'affiliation_role'
    ELSE 'none'
  END`;
}

function sortFor(kind: SearchEntityType): SortMode {
  return kind === "statement" || kind === "source_item" ? "time" : "name";
}

function fingerprint(parsed: SearchQuery, normalized: string, tokens: string[]): string {
  const body = JSON.stringify({
    q: normalized,
    tokens,
    type: parsed.type ?? null,
    topic: parsed.topic ?? null,
    person: parsed.person ?? null,
    statement_type: parsed.statement_type ?? null,
    from: parsed.from ?? null,
    to: parsed.to ?? null,
  });
  return createHash("sha256").update(body).digest("hex").slice(0, 16);
}

function encodeCursor(payload: CursorPayload): string {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function decodeCursor(cursor: string, fp: string, sort: SortMode): CursorPayload {
  try {
    const parsed = JSON.parse(Buffer.from(cursor, "base64url").toString("utf8")) as CursorPayload;
    if (parsed.v !== 2 || parsed.fp !== fp || parsed.sort !== sort) throw new Error("bad");
    if (!Number.isInteger(parsed.rank) || parsed.rank < 0 || parsed.rank > 1000) throw new Error("bad");
    if (typeof parsed.tie !== "string" || parsed.tie.length > 80) throw new Error("bad");
    if (!/^[0-9a-f-]{36}$/i.test(parsed.id)) throw new Error("bad");
    if (!Object.values(SEARCH_RANK).includes(parsed.rank) && parsed.rank !== 0) throw new Error("bad");
    return parsed;
  } catch (error) {
    if (error instanceof InvalidCursorError) throw error;
    throw new InvalidCursorError();
  }
}

function cursorPredicate(sort: SortMode, rank: string, tie: string, id: string): string {
  if (sort === "name") {
    return `(
      ${rank}::int IS NULL
      OR hit_rank < ${rank}::int
      OR (hit_rank = ${rank}::int AND tie COLLATE "C" > ${tie} COLLATE "C")
      OR (hit_rank = ${rank}::int AND tie COLLATE "C" = ${tie} COLLATE "C" AND id > ${id}::uuid)
    )`;
  }
  return `(
    ${rank}::int IS NULL
    OR hit_rank < ${rank}::int
    OR (
      hit_rank = ${rank}::int AND (
        (${tie} <> '' AND (
          (tie <> '' AND (tie COLLATE "C" < ${tie} COLLATE "C" OR (tie COLLATE "C" = ${tie} COLLATE "C" AND id > ${id}::uuid)))
          OR tie = ''
        ))
        OR (${tie} = '' AND tie = '' AND id > ${id}::uuid)
      )
    )
  )`;
}

function emptyGroup<T>(limit: number): SearchGroup<T> {
  return { data: [], page: { limit, total: 0, next_cursor: null } };
}

function emptyResponse(parsed: SearchQuery, prepared: ReturnType<typeof prepareSearchText>, types: SearchEntityType[]): SearchResponse {
  const limit = parsed.limit ?? SEARCH_PAGE_LIMIT_DEFAULT;
  return {
    query: {
      text: parsed.q,
      normalized: prepared.normalized,
      tokens: prepared.tokens,
      truncated: prepared.truncated,
      reason: prepared.reason,
      types,
    },
    groups: {
      person: emptyGroup(limit),
      organization: emptyGroup(limit),
      statement: emptyGroup(limit),
      topic: emptyGroup(limit),
      source: emptyGroup(limit),
      source_item: emptyGroup(limit),
    },
  };
}

function num(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function iso(value: unknown): string | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(String(value));
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function asMatch(value: unknown): SearchMatch {
  const text = String(value);
  if (text in SEARCH_RANK) return text as SearchMatch;
  return "all_tokens";
}

type ScoredRow = Record<string, unknown> & {
  id: string;
  hit_rank: number;
  tie: string;
  hit_match: string;
};

function pageOf<T extends SearchHit>(
  rows: ScoredRow[],
  limit: number,
  total: number,
  map: (row: ScoredRow) => T,
  cursorMeta: { fp: string; sort: SortMode },
): SearchGroup<T> {
  const hasMore = rows.length > limit;
  const visible = rows.slice(0, limit);
  const last = visible[visible.length - 1];
  return {
    data: visible.map(map),
    page: {
      limit,
      total,
      next_cursor:
        hasMore && last
          ? encodeCursor({
              v: 2,
              fp: cursorMeta.fp,
              rank: Number(last.hit_rank),
              tie: String(last.tie ?? ""),
              id: String(last.id),
              sort: cursorMeta.sort,
            })
          : null,
    },
  };
}

function sharedParams(prepared: ReturnType<typeof prepareSearchText>): Params {
  const params = new Params();
  params.add(prepared.normalized);
  params.add(prepared.likeNorm);
  params.add(prepared.tokens);
  params.add(publicReviewStates());
  return params;
}

function bindFilters(params: Params, parsed: SearchQuery): {
  person: string;
  topic: string;
  statementType: string;
  from: string;
  to: string;
} {
  return {
    person: params.add(parsed.person ?? null),
    topic: params.add(parsed.topic ?? null),
    statementType: params.add(parsed.statement_type ?? null),
    from: params.add(parsed.from ? `${parsed.from}T00:00:00.000Z` : null),
    to: params.add(parsed.to ? `${parsed.to}T23:59:59.999Z` : null),
  };
}

function bindCursor(params: Params, cursor: CursorPayload | null, limit: number): { rank: string; tie: string; id: string; limit: string } {
  return {
    rank: params.add(cursor ? cursor.rank : null),
    tie: params.add(cursor ? cursor.tie : ""),
    id: params.add(cursor ? cursor.id : "00000000-0000-0000-0000-000000000000"),
    limit: params.add(limit + 1),
  };
}

const ROLE_MATCH = `EXISTS (
  SELECT 1 FROM affiliations a
  WHERE a.organization_id = o.id
    AND a.review_state = ANY(q.public_states)
    AND to_tsvector('simple', coalesce(a.role, '')) @@ q.tsq
)`;

function peopleSql(prepared: ReturnType<typeof prepareSearchText>, parsed: SearchQuery, cursor: CursorPayload | null, limit: number, mode: "count" | "page"): BoundQuery {
  const params = sharedParams(prepared);
  const person = params.add(parsed.person ?? null);
  const page = mode === "page" ? bindCursor(params, cursor, limit) : null;
  const rank = nameRank("p.display_name", "p.family_name", "p.search_vector @@ q.tsq", null);
  const text = `
    WITH ${QUERY_CTE},
    scored AS (
      SELECT
        p.id,
        p.slug,
        p.display_name,
        p.status,
        o.slug AS organization_slug,
        o.name AS organization_name,
        a.role AS organization_role,
        lower(p.display_name) AS tie,
        ${rank} AS hit_rank
      FROM people p
      CROSS JOIN q
      LEFT JOIN affiliations a ON a.id = p.current_affiliation_id
      LEFT JOIN organizations o ON o.id = a.organization_id
      WHERE (${person}::text IS NULL OR p.slug = ${person})
    ),
    matched AS (
      SELECT scored.*, ${matchFromRank("scored.hit_rank")} AS hit_match
      FROM scored
      WHERE scored.hit_rank > 0
    )
    ${mode === "count"
      ? "SELECT count(*)::int AS total_count FROM matched"
      : `SELECT * FROM matched
         WHERE ${cursorPredicate("name", page!.rank, page!.tie, page!.id)}
         ORDER BY hit_rank DESC, tie COLLATE "C" ASC, id ASC
         LIMIT ${page!.limit}`}
  `;
  return { text, values: params.values };
}

function organizationsSql(_prepared: ReturnType<typeof prepareSearchText>, _parsed: SearchQuery, cursor: CursorPayload | null, limit: number, mode: "count" | "page"): BoundQuery {
  const params = sharedParams(_prepared);
  const page = mode === "page" ? bindCursor(params, cursor, limit) : null;
  const rank = nameRank("o.name", null, "to_tsvector('simple', coalesce(o.name, '')) @@ q.tsq", ROLE_MATCH);
  const text = `
    WITH ${QUERY_CTE},
    scored AS (
      SELECT
        o.id,
        o.slug,
        o.name,
        o.organization_type,
        role_hit.person_slug,
        role_hit.display_name AS person_name,
        role_hit.role,
        lower(o.name) AS tie,
        ${rank} AS hit_rank
      FROM organizations o
      CROSS JOIN q
      LEFT JOIN LATERAL (
        SELECT p.slug AS person_slug, p.display_name, a.role
        FROM affiliations a
        JOIN people p ON p.id = a.person_id
        WHERE a.organization_id = o.id
          AND a.review_state = ANY(q.public_states)
          AND to_tsvector('simple', coalesce(a.role, '')) @@ q.tsq
        ORDER BY p.display_name ASC, p.id ASC
        LIMIT 1
      ) role_hit ON true
    ),
    matched AS (
      SELECT scored.*, ${matchFromRank("scored.hit_rank")} AS hit_match
      FROM scored
      WHERE scored.hit_rank > 0
    )
    ${mode === "count"
      ? "SELECT count(*)::int AS total_count FROM matched"
      : `SELECT * FROM matched
         WHERE ${cursorPredicate("name", page!.rank, page!.tie, page!.id)}
         ORDER BY hit_rank DESC, tie COLLATE "C" ASC, id ASC
         LIMIT ${page!.limit}`}
  `;
  return { text, values: params.values };
}

function topicsSql(prepared: ReturnType<typeof prepareSearchText>, parsed: SearchQuery, cursor: CursorPayload | null, limit: number, mode: "count" | "page"): BoundQuery {
  const params = sharedParams(prepared);
  const topic = params.add(parsed.topic ?? null);
  const page = mode === "page" ? bindCursor(params, cursor, limit) : null;
  const rank = nameRank(
    "t.name",
    null,
    "to_tsvector('simple', coalesce(t.name, '') || ' ' || coalesce(t.definition, '')) @@ q.tsq",
    null,
  );
  const text = `
    WITH ${QUERY_CTE},
    scored AS (
      SELECT t.id, t.slug, t.name, t.definition, lower(t.name) AS tie, ${rank} AS hit_rank
      FROM topics t
      CROSS JOIN q
      WHERE (${topic}::text IS NULL OR t.slug = ${topic})
    ),
    matched AS (
      SELECT scored.*, ${matchFromRank("scored.hit_rank")} AS hit_match
      FROM scored
      WHERE scored.hit_rank > 0
    )
    ${mode === "count"
      ? "SELECT count(*)::int AS total_count FROM matched"
      : `SELECT * FROM matched
         WHERE ${cursorPredicate("name", page!.rank, page!.tie, page!.id)}
         ORDER BY hit_rank DESC, tie COLLATE "C" ASC, id ASC
         LIMIT ${page!.limit}`}
  `;
  return { text, values: params.values };
}

function sourcesSql(prepared: ReturnType<typeof prepareSearchText>, parsed: SearchQuery, cursor: CursorPayload | null, limit: number, mode: "count" | "page"): BoundQuery {
  const params = sharedParams(prepared);
  const person = params.add(parsed.person ?? null);
  const page = mode === "page" ? bindCursor(params, cursor, limit) : null;
  const rank = nameRank("src.name", null, "to_tsvector('simple', coalesce(src.name, '')) @@ q.tsq", null);
  const text = `
    WITH ${QUERY_CTE},
    scored AS (
      SELECT
        src.id,
        src.slug,
        src.name,
        src.source_type,
        src.review_state,
        p.slug AS owner_slug,
        p.display_name AS owner_name,
        lower(src.name) AS tie,
        ${rank} AS hit_rank
      FROM sources src
      CROSS JOIN q
      LEFT JOIN people p ON p.id = src.owner_person_id
      WHERE src.review_state = ANY(q.public_states)
        AND (${person}::text IS NULL OR p.slug = ${person})
    ),
    matched AS (
      SELECT scored.*, ${matchFromRank("scored.hit_rank")} AS hit_match
      FROM scored
      WHERE scored.hit_rank > 0
    )
    ${mode === "count"
      ? "SELECT count(*)::int AS total_count FROM matched"
      : `SELECT * FROM matched
         WHERE ${cursorPredicate("name", page!.rank, page!.tie, page!.id)}
         ORDER BY hit_rank DESC, tie COLLATE "C" ASC, id ASC
         LIMIT ${page!.limit}`}
  `;
  return { text, values: params.values };
}

const TIME_TIE = `coalesce(to_char(%s AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.US'), '')`;

function statementsSql(prepared: ReturnType<typeof prepareSearchText>, parsed: SearchQuery, cursor: CursorPayload | null, limit: number, mode: "count" | "page"): BoundQuery {
  const params = sharedParams(prepared);
  const filters = bindFilters(params, parsed);
  const page = mode === "page" ? bindCursor(params, cursor, limit) : null;
  const rank = `CASE
    WHEN ${collapse("s.normalized_text")} = q.norm THEN ${SEARCH_RANK.exact_text}
    WHEN strpos(lower(s.normalized_text), q.norm) > 0 THEN ${SEARCH_RANK.phrase}
    ELSE ${SEARCH_RANK.all_tokens}
  END`;
  const text = `
    WITH ${QUERY_CTE},
    scored AS (
      SELECT
        s.id,
        s.slug,
        s.statement_type,
        s.normalized_text,
        s.event_time,
        ${effectiveReviewStateSql("s")} AS review_state,
        p.slug AS person_slug,
        p.display_name,
        src.slug AS source_slug,
        src.name AS source_name,
        src.source_type,
        si.slug AS source_item_slug,
        si.title AS source_item_title,
        si.published_at,
        f.value_type,
        f.value_numeric,
        f.value_min,
        f.value_max,
        f.unit,
        f.horizon_text,
        COALESCE(topics.topics, '[]'::jsonb) AS topics,
        ${TIME_TIE.replace("%s", "s.event_time")} AS tie,
        ${rank} AS hit_rank
      FROM statements s
      CROSS JOIN q
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
      WHERE ${effectiveReviewStateSql("s")} = ANY(q.public_states)
        AND s.search_vector @@ q.tsq
        AND (${filters.person}::text IS NULL OR p.slug = ${filters.person})
        AND (${filters.statementType}::text IS NULL OR s.statement_type = ${filters.statementType})
        AND (${filters.from}::timestamptz IS NULL OR s.event_time >= ${filters.from}::timestamptz)
        AND (${filters.to}::timestamptz IS NULL OR s.event_time <= ${filters.to}::timestamptz)
        AND (${filters.topic}::text IS NULL OR EXISTS (
          SELECT 1 FROM statement_topics st
          JOIN topics t ON t.id = st.topic_id
          WHERE st.statement_id = s.id AND t.slug = ${filters.topic}
        ))
    ),
    matched AS (
      SELECT scored.*, ${matchFromRank("scored.hit_rank")} AS hit_match
      FROM scored
    )
    ${mode === "count"
      ? "SELECT count(*)::int AS total_count FROM matched"
      : `SELECT * FROM matched
         WHERE ${cursorPredicate("time", page!.rank, page!.tie, page!.id)}
         ORDER BY hit_rank DESC, (tie = '') ASC, tie COLLATE "C" DESC, id ASC
         LIMIT ${page!.limit}`}
  `;
  return { text, values: params.values };
}

function sourceItemsSql(prepared: ReturnType<typeof prepareSearchText>, parsed: SearchQuery, cursor: CursorPayload | null, limit: number, mode: "count" | "page"): BoundQuery {
  const params = sharedParams(prepared);
  const person = params.add(parsed.person ?? null);
  const from = params.add(parsed.from ? `${parsed.from}T00:00:00.000Z` : null);
  const to = params.add(parsed.to ? `${parsed.to}T23:59:59.999Z` : null);
  const page = mode === "page" ? bindCursor(params, cursor, limit) : null;
  const rank = nameRank("si.title", null, "to_tsvector('simple', coalesce(si.title, '')) @@ q.tsq", null);
  const text = `
    WITH ${QUERY_CTE},
    scored AS (
      SELECT
        si.id,
        si.slug,
        si.title,
        si.published_at,
        src.slug AS source_slug,
        src.name AS source_name,
        src.source_type,
        ${TIME_TIE.replace("%s", "si.published_at")} AS tie,
        ${rank} AS hit_rank
      FROM source_items si
      CROSS JOIN q
      JOIN sources src ON src.id = si.source_id
      WHERE si.is_current
        AND (${from}::timestamptz IS NULL OR si.published_at >= ${from}::timestamptz)
        AND (${to}::timestamptz IS NULL OR si.published_at <= ${to}::timestamptz)
        AND (${person}::text IS NULL OR EXISTS (
          SELECT 1 FROM source_participants sp
          JOIN people p ON p.id = sp.person_id
          WHERE sp.source_item_id = si.id AND p.slug = ${person}
        ) OR EXISTS (
          SELECT 1 FROM people owner
          WHERE owner.id = src.owner_person_id AND owner.slug = ${person}
        ))
    ),
    matched AS (
      SELECT scored.*, ${matchFromRank("scored.hit_rank")} AS hit_match
      FROM scored
      WHERE scored.hit_rank > 0
    )
    ${mode === "count"
      ? "SELECT count(*)::int AS total_count FROM matched"
      : `SELECT * FROM matched
         WHERE ${cursorPredicate("time", page!.rank, page!.tie, page!.id)}
         ORDER BY hit_rank DESC, (tie = '') ASC, tie COLLATE "C" DESC, id ASC
         LIMIT ${page!.limit}`}
  `;
  return { text, values: params.values };
}

const BUILDERS = {
  person: peopleSql,
  organization: organizationsSql,
  statement: statementsSql,
  topic: topicsSql,
  source: sourcesSql,
  source_item: sourceItemsSql,
} as const;

function mapPerson(row: ScoredRow): SearchPersonHit {
  return {
    kind: "person",
    id: String(row.id),
    slug: String(row.slug),
    display_name: String(row.display_name),
    status: String(row.status),
    organization: row.organization_slug
      ? {
          slug: String(row.organization_slug),
          name: String(row.organization_name),
          role: row.organization_role ? String(row.organization_role) : null,
        }
      : null,
    match: asMatch(row.hit_match),
  };
}

function mapOrganization(row: ScoredRow): SearchOrganizationHit {
  const affiliation =
    row.hit_match === "affiliation_role" && row.person_slug
      ? {
          person_slug: String(row.person_slug),
          display_name: String(row.person_name),
          role: row.role ? String(row.role) : null,
        }
      : null;
  return {
    kind: "organization",
    id: String(row.id),
    slug: String(row.slug),
    name: String(row.name),
    organization_type: String(row.organization_type),
    affiliation,
    match: asMatch(row.hit_match),
  };
}

function mapStatement(row: ScoredRow): SearchStatementHit {
  const topics = Array.isArray(row.topics) ? (row.topics as Array<{ slug: string; name: string }>) : [];
  return {
    kind: "statement",
    id: String(row.id),
    slug: String(row.slug),
    statement_type: String(row.statement_type),
    normalized_text: String(row.normalized_text),
    event_time: iso(row.event_time),
    review_state: String(row.review_state),
    person: { slug: String(row.person_slug), display_name: String(row.display_name) },
    source: {
      slug: String(row.source_slug),
      name: String(row.source_name),
      source_type: String(row.source_type),
    },
    source_item: {
      slug: String(row.source_item_slug),
      title: row.source_item_title ? String(row.source_item_title) : null,
      published_at: iso(row.published_at),
    },
    topics,
    forecast: row.value_type
      ? {
          horizon_text: row.horizon_text ? String(row.horizon_text) : null,
          value_type: String(row.value_type),
          value_numeric: num(row.value_numeric),
          value_min: num(row.value_min),
          value_max: num(row.value_max),
          unit: row.unit ? String(row.unit) : null,
        }
      : null,
    match: asMatch(row.hit_match),
  };
}

function mapTopic(row: ScoredRow): SearchTopicHit {
  return {
    kind: "topic",
    id: String(row.id),
    slug: String(row.slug),
    name: String(row.name),
    definition: String(row.definition),
    match: asMatch(row.hit_match),
  };
}

function mapSource(row: ScoredRow): SearchSourceHit {
  return {
    kind: "source",
    id: String(row.id),
    slug: String(row.slug),
    name: String(row.name),
    source_type: String(row.source_type),
    review_state: String(row.review_state),
    owner: row.owner_slug ? { slug: String(row.owner_slug), display_name: String(row.owner_name) } : null,
    match: asMatch(row.hit_match),
  };
}

function mapSourceItem(row: ScoredRow): SearchSourceItemHit {
  return {
    kind: "source_item",
    id: String(row.id),
    slug: String(row.slug),
    title: row.title ? String(row.title) : null,
    published_at: iso(row.published_at),
    source: {
      slug: String(row.source_slug),
      name: String(row.source_name),
      source_type: String(row.source_type),
    },
    match: asMatch(row.hit_match),
  };
}

const MAPPERS = {
  person: mapPerson,
  organization: mapOrganization,
  statement: mapStatement,
  topic: mapTopic,
  source: mapSource,
  source_item: mapSourceItem,
} as const;

async function searchKind(
  client: pg.Pool | pg.PoolClient,
  kind: SearchEntityType,
  prepared: ReturnType<typeof prepareSearchText>,
  parsed: SearchQuery,
  cursor: CursorPayload | null,
  limit: number,
  fp: string,
): Promise<SearchGroup<SearchHit>> {
  const sort = sortFor(kind);
  const build = BUILDERS[kind];
  const map = MAPPERS[kind] as (row: ScoredRow) => SearchHit;
  const countQuery = build(prepared, parsed, cursor, limit, "count");
  const count = await client.query(countQuery.text, countQuery.values);
  const page = build(prepared, parsed, cursor, limit, "page");
  const rows = await client.query(page.text, page.values);
  const total = Number(count.rows[0]?.total_count ?? 0);
  return pageOf(rows.rows as ScoredRow[], limit, total, map, { fp, sort });
}

async function searchGroups(
  client: pg.Pool | pg.PoolClient,
  parsed: SearchQuery,
  prepared: ReturnType<typeof prepareSearchText>,
  types: SearchEntityType[],
  fp: string,
  cursor: CursorPayload | null,
  response: SearchResponse,
): Promise<SearchResponse> {
  for (const kind of types) {
    const limit = parsed.mode === "suggest" ? SEARCH_SUGGEST_LIMITS[kind] : (parsed.limit ?? SEARCH_PAGE_LIMIT_DEFAULT);
    const kindCursor = parsed.type === kind ? cursor : null;
    const group = await searchKind(client, kind, prepared, parsed, kindCursor, limit, fp);
    (response.groups as Record<SearchEntityType, SearchGroup<SearchHit>>)[kind] = group;
  }
  return response;
}

export async function searchPublic(input: SearchQuery, pool: pg.Pool | pg.PoolClient = getPool()): Promise<SearchResponse> {
  const parsed = searchQuerySchema.parse(input);
  const prepared = prepareSearchText(parsed.q);
  const types = searchTypesForFilters(parsed);
  const fp = fingerprint(parsed, prepared.normalized, prepared.tokens);
  const cursor = parsed.cursor && parsed.type ? decodeCursor(parsed.cursor, fp, sortFor(parsed.type)) : null;
  const response = emptyResponse(parsed, prepared, types);
  if (prepared.reason !== "ok") return response;
  try {
    if (!isPool(pool)) return await searchGroups(pool, parsed, prepared, types, fp, cursor, response);
    return await withConsistentRead(pool, async (client) => {
      await client.query("SET LOCAL statement_timeout = '2s'");
      return searchGroups(client, parsed, prepared, types, fp, cursor, response);
    });
  } catch (error) {
    if (isStatementTimeout(error)) throw new SearchTimeoutError();
    throw error;
  }
}
