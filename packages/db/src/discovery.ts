import {
  INDEXABLE_PERSON_STATUSES,
  PUBLIC_REVIEW_STATES,
  isIndexablePersonStatus,
  isIndexableReviewState,
  isPublicReviewState,
} from "@pdoom/contracts";
import { getPool } from "./pool";

type Queryable = {
  query: (text: string, values?: unknown[]) => Promise<{ rows: Array<Record<string, unknown>> }>;
};

function iso(value: Date | string | null | undefined): string | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

const personStatuses = [...INDEXABLE_PERSON_STATUSES];
const reviewStates = [...PUBLIC_REVIEW_STATES];

const sitemapCte = `
WITH entries AS (
  SELECT '/people/' || p.slug AS path, p.updated_at AS lastmod
  FROM people p
  WHERE p.status = ANY($1::text[])
    AND p.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
  UNION ALL
  SELECT '/topics/' || t.slug, t.updated_at
  FROM topics t
  WHERE t.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
  UNION ALL
  SELECT '/sources/' || src.slug, src.updated_at
  FROM sources src
  WHERE src.review_state = ANY($2::text[])
    AND src.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
  UNION ALL
  SELECT '/source-items/' || si.slug, COALESCE(si.updated_at_source, si.observed_at)
  FROM source_items si
  JOIN sources src ON src.id = si.source_id
  WHERE si.is_current
    AND si.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
    AND src.review_state = ANY($2::text[])
    AND EXISTS (
      SELECT 1
      FROM statements s
      JOIN people p ON p.id = s.person_id
      WHERE s.source_item_id = si.id
        AND s.review_state = ANY($2::text[])
        AND p.status = ANY($1::text[])
    )
  UNION ALL
  SELECT '/statements/' || s.slug, COALESCE(s.event_time, s.created_at)
  FROM statements s
  JOIN people p ON p.id = s.person_id
  WHERE s.review_state = ANY($2::text[])
    AND p.status = ANY($1::text[])
    AND s.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
  UNION ALL
  SELECT '/trends/' || td.slug, td.created_at
  FROM trend_definitions td
  WHERE td.published
    AND td.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
)
`;

export type SitemapRecord = {
  path: string;
  lastModified: string | null;
};

export async function countSitemapRecords(pool: Queryable): Promise<number> {
  const result = await pool.query(`${sitemapCte} SELECT count(*)::int AS count FROM entries`, [
    personStatuses,
    reviewStates,
  ]);
  return Number(result.rows[0]?.count ?? 0);
}

export async function listSitemapRecords(
  pool: Queryable,
  input: { offset: number; limit: number },
): Promise<SitemapRecord[]> {
  const limit = Math.min(Math.max(input.limit, 0), 50_000);
  const offset = Math.max(input.offset, 0);
  const result = await pool.query(
    `${sitemapCte} SELECT path, lastmod FROM entries ORDER BY path LIMIT $3 OFFSET $4`,
    [personStatuses, reviewStates, limit, offset],
  );
  return result.rows.map((row) => ({
    path: String(row.path),
    lastModified: iso(row.lastmod as Date | string | null),
  }));
}

export type FeedEntry = {
  slug: string;
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  created_at: string;
  person_slug: string;
  display_name: string;
  source_name: string;
  source_type: string;
  source_item_slug: string;
  source_item_title: string | null;
  source_canonical_url: string;
  availability: string;
  collection_status: string;
};

export async function listFeedEntries(pool: Queryable, limit: number): Promise<FeedEntry[]> {
  const bounded = Math.min(Math.max(limit, 1), 100);
  const result = await pool.query(
    `SELECT s.slug, s.statement_type, s.normalized_text, s.event_time, s.created_at,
            p.slug AS person_slug, p.display_name,
            src.name AS source_name, src.source_type,
            si.slug AS source_item_slug, si.title AS source_item_title, si.canonical_url AS source_canonical_url,
            si.availability, si.collection_status
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     WHERE s.review_state = ANY($1::text[])
       AND p.status = ANY($2::text[])
       AND s.slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
     ORDER BY s.event_time DESC NULLS LAST, s.created_at DESC, s.id DESC
     LIMIT $3`,
    [reviewStates, personStatuses, bounded],
  );
  return result.rows.map((row) => ({
    slug: String(row.slug),
    statement_type: String(row.statement_type),
    normalized_text: String(row.normalized_text),
    event_time: iso(row.event_time as Date | string | null),
    created_at: iso(row.created_at as Date | string) ?? new Date(0).toISOString(),
    person_slug: String(row.person_slug),
    display_name: String(row.display_name),
    source_name: String(row.source_name),
    source_type: String(row.source_type),
    source_item_slug: String(row.source_item_slug),
    source_item_title: row.source_item_title ? String(row.source_item_title) : null,
    source_canonical_url: String(row.source_canonical_url),
    availability: String(row.availability),
    collection_status: String(row.collection_status),
  }));
}

export type StatementDiscovery = {
  slug: string;
  statement_type: string;
  normalized_text: string;
  review_state: string;
  event_time: string | null;
  person_slug: string;
  display_name: string;
  person_status: string;
  source_name: string;
  source_type: string;
  source_item_slug: string;
  source_item_title: string | null;
  source_canonical_url: string;
  availability: string;
  collection_status: string;
  dataset_kind: string | null;
  indexable: boolean;
};

export async function getStatementDiscovery(slug: string, pool: Queryable = getPool()): Promise<StatementDiscovery | null> {
  const result = await pool.query(
    `SELECT s.slug, s.statement_type, s.normalized_text, s.review_state, s.event_time,
            p.slug AS person_slug, p.display_name, p.status AS person_status,
            src.name AS source_name, src.source_type,
            si.slug AS source_item_slug, si.title AS source_item_title, si.canonical_url AS source_canonical_url,
            si.availability, si.collection_status,
            d.dataset_kind
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     LEFT JOIN dataset_imports d ON d.is_current
     WHERE s.slug = $1`,
    [slug],
  );
  const row = result.rows[0];
  if (!row || !isPublicReviewState(String(row.review_state))) return null;
  const indexable =
    isIndexableReviewState(String(row.review_state)) && isIndexablePersonStatus(String(row.person_status));
  return {
    slug: String(row.slug),
    statement_type: String(row.statement_type),
    normalized_text: indexable ? String(row.normalized_text) : "",
    review_state: String(row.review_state),
    event_time: iso(row.event_time as Date | string | null),
    person_slug: String(row.person_slug),
    display_name: String(row.display_name),
    person_status: String(row.person_status),
    source_name: String(row.source_name),
    source_type: String(row.source_type),
    source_item_slug: String(row.source_item_slug),
    source_item_title: row.source_item_title ? String(row.source_item_title) : null,
    source_canonical_url: String(row.source_canonical_url),
    availability: String(row.availability),
    collection_status: String(row.collection_status),
    dataset_kind: row.dataset_kind ? String(row.dataset_kind) : null,
    indexable,
  };
}

export type SourceItemDiscovery = {
  slug: string;
  title: string | null;
  availability: string;
  collection_status: string;
  is_current: boolean;
  canonical_url: string;
  source_name: string;
  source_type: string;
  source_review_state: string;
  current_slug: string | null;
  indexable: boolean;
  current_indexable: boolean;
  dataset_kind: string | null;
};

export async function getSourceItemDiscovery(slug: string, pool: Queryable = getPool()): Promise<SourceItemDiscovery | null> {
  const result = await pool.query(
    `SELECT si.slug, si.title, si.availability, si.collection_status, si.is_current, si.canonical_url,
            src.name AS source_name, src.source_type, src.review_state AS source_review_state,
            current.slug AS current_slug,
            d.dataset_kind,
            EXISTS (
              SELECT 1
              FROM statements s
              JOIN people p ON p.id = s.person_id
              WHERE s.source_item_id = si.id
                AND s.review_state = ANY($2::text[])
                AND p.status = ANY($3::text[])
            ) AS has_indexable_statement,
            EXISTS (
              SELECT 1
              FROM statements s
              JOIN people p ON p.id = s.person_id
              WHERE current.id IS NOT NULL
                AND s.source_item_id = current.id
                AND s.review_state = ANY($2::text[])
                AND p.status = ANY($3::text[])
            ) AS current_has_indexable_statement
     FROM source_items si
     JOIN sources src ON src.id = si.source_id
     LEFT JOIN source_items current
       ON current.source_id = si.source_id
      AND current.logical_key = si.logical_key
      AND current.is_current
     LEFT JOIN dataset_imports d ON d.is_current
     WHERE si.slug = $1`,
    [slug, reviewStates, personStatuses],
  );
  const row = result.rows[0];
  if (!row) return null;
  const sourceIndexable = isIndexableReviewState(String(row.source_review_state));
  const selfIndexable = sourceIndexable && Boolean(row.has_indexable_statement) && Boolean(row.is_current);
  const currentIndexable = sourceIndexable && Boolean(row.current_has_indexable_statement);
  return {
    slug: String(row.slug),
    title: row.title ? String(row.title) : null,
    availability: String(row.availability),
    collection_status: String(row.collection_status),
    is_current: Boolean(row.is_current),
    canonical_url: String(row.canonical_url),
    source_name: String(row.source_name),
    source_type: String(row.source_type),
    source_review_state: String(row.source_review_state),
    current_slug: row.current_slug ? String(row.current_slug) : null,
    indexable: selfIndexable,
    current_indexable: currentIndexable,
    dataset_kind: row.dataset_kind ? String(row.dataset_kind) : null,
  };
}
