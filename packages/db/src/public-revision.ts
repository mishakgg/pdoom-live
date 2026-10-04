import type pg from "pg";
import { getPool } from "./pool";

/**
 * Fingerprint of rows that can change a public payload without a new import:
 * review decisions, statement and forecast text, source versions, evidence
 * hashes, people, cohort membership, and published trend definitions.
 *
 * Large tables contribute a count plus a 64-bit xor of hashes. That detects
 * inserts and ordinary updates, including two reviews that share an HTTP-date
 * second. A xor collision can hide a change until the representation cache
 * TTL expires; counts and review timestamps make that collision insufficient
 * for a new decision or a new row.
 */
const REVISION_SQL = `
SELECT md5(concat_ws(E'\\n',
  coalesce((
    SELECT dataset_id || '|' || imported_at::text || '|' || coalesce(cohort_slug, '') || '|' || coalesce(cohort_version, '')
    FROM dataset_imports
    WHERE is_current
    ORDER BY imported_at DESC
    LIMIT 1
  ), 'none'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(max(reviewed_at)::text, '') || '|' || coalesce(max(created_at)::text, '') || '|' ||
      coalesce(bit_xor(hashtextextended(
        decision_key || '|' || resulting_review_state || '|' || corrections_json::text || '|' ||
        source_content_hash || '|' || evidence_hash || '|' || content_version::text, 0
      ))::text, '0')
    FROM review_decisions
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(
      slug || '|' || review_state || '|' || statement_type || '|' || normalized_text || '|' || coalesce(event_time::text, ''), 0
    ))::text, '0')
    FROM statements
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(
      statement_id::text || '|' || review_state || '|' || question_key || '|' || coalesce(question_text, '') || '|' ||
      coalesce(horizon_text, '') || '|' || coalesce(condition_text, '') || '|' || coalesce(definition_text, '') || '|' ||
      coalesce(unit, '') || '|' || value_type || '|' || coalesce(value_numeric::text, '') || '|' ||
      coalesce(value_min::text, '') || '|' || coalesce(value_max::text, ''), 0
    ))::text, '0')
    FROM forecasts
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(
      slug || '|' || content_hash || '|' || content_version::text || '|' || coalesce(canonical_url, ''), 0
    ))::text, '0')
    FROM source_items
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(slug || '|' || segment_hash, 0))::text, '0')
    FROM evidence_segments
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(max(updated_at)::text, '') || '|' || coalesce(bit_xor(hashtextextended(
      slug || '|' || display_name || '|' || bio_short || '|' || status, 0
    ))::text, '0')
    FROM people
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(cohort_id::text || '|' || person_id::text, 0))::text, '0')
    FROM cohort_memberships
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(max(updated_at)::text, '') || '|' || coalesce(bit_xor(hashtextextended(
      slug || '|' || review_state || '|' || coalesce(last_success_at::text, ''), 0
    ))::text, '0')
    FROM sources
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(max(updated_at)::text, '') || '|' || coalesce(bit_xor(hashtextextended(
      slug || '|' || version || '|' || name, 0
    ))::text, '0')
    FROM topics
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(
      from_statement_id::text || '|' || to_statement_id::text || '|' || relationship_type || '|' || review_state, 0
    ))::text, '0')
    FROM statement_relationships
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(
      person_id::text || '|' || organization_id::text || '|' || review_state || '|' || coalesce(role, ''), 0
    ))::text, '0')
    FROM affiliations
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(bit_xor(hashtextextended(
      person_id::text || '|' || namespace || '|' || external_id || '|' || review_state, 0
    ))::text, '0')
    FROM external_identities
  ), '0'),
  coalesce((
    SELECT count(*)::text || '|' || coalesce(max(created_at)::text, '')
    FROM trend_definitions
    WHERE published
  ), '0')
)) AS revision
`;

export async function publicContentRevision(db: pg.Pool | pg.PoolClient = getPool()): Promise<string> {
  const result = await db.query(REVISION_SQL);
  const revision = result.rows[0]?.revision;
  if (typeof revision !== "string" || revision.length === 0) return "none";
  return revision;
}
