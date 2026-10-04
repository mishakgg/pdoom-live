import type pg from "pg";

export function staleApprovalSql(statementAlias = "s"): string {
  return `EXISTS (
    SELECT 1
    FROM review_decisions stale_d
    JOIN source_items stale_si ON stale_si.id = ${statementAlias}.source_item_id
    JOIN evidence_segments stale_e ON stale_e.id = ${statementAlias}.evidence_segment_id
    WHERE stale_d.statement_id = ${statementAlias}.id
      AND (stale_d.reviewed_at, stale_d.decision_key) = (
        SELECT d2.reviewed_at, d2.decision_key
        FROM review_decisions d2
        WHERE d2.statement_id = ${statementAlias}.id
        ORDER BY d2.reviewed_at DESC, d2.decision_key DESC
        LIMIT 1
      )
      AND (
        stale_d.resulting_review_state <> 'human_verified'
        OR stale_d.source_content_hash <> stale_si.content_hash
        OR stale_d.evidence_hash <> stale_e.segment_hash
        OR stale_d.content_version <> stale_si.content_version
      )
  )`;
}

/** Latest decision state when the source version matches and the evidence is the approved span or the original machine span. */
export function coveringDecisionStateSql(statementAlias = "s"): string {
  return `(
    SELECT cover_d.resulting_review_state
    FROM review_decisions cover_d
    JOIN source_items cover_si ON cover_si.id = ${statementAlias}.source_item_id
    JOIN evidence_segments cover_e ON cover_e.id = ${statementAlias}.evidence_segment_id
    LEFT JOIN statement_extractions cover_x ON cover_x.statement_id = ${statementAlias}.id
    WHERE cover_d.statement_id = ${statementAlias}.id
      AND (cover_d.reviewed_at, cover_d.decision_key) = (
        SELECT cover_d2.reviewed_at, cover_d2.decision_key
        FROM review_decisions cover_d2
        WHERE cover_d2.statement_id = ${statementAlias}.id
        ORDER BY cover_d2.reviewed_at DESC, cover_d2.decision_key DESC
        LIMIT 1
      )
      AND cover_d.source_content_hash = cover_si.content_hash
      AND cover_d.content_version = cover_si.content_version
      AND (
        cover_e.segment_hash = cover_d.evidence_hash
        OR cover_e.segment_hash = cover_x.evidence_hash
      )
  )`;
}

export function effectiveReviewStateSql(statementAlias = "s"): string {
  return `COALESCE(${coveringDecisionStateSql(statementAlias)}, CASE WHEN ${statementAlias}.review_state = 'human_verified' AND ${staleApprovalSql(statementAlias)} THEN 'needs_review' ELSE ${statementAlias}.review_state END)`;
}

const coveredDecisionsSql = `
  WITH latest AS (
    SELECT DISTINCT ON (d.statement_id) d.*
    FROM review_decisions d
    ORDER BY d.statement_id, d.reviewed_at DESC, d.decision_key DESC
  ),
  covered AS (
    SELECT l.*
    FROM latest l
    JOIN statements s ON s.id = l.statement_id
    JOIN source_items si ON si.id = s.source_item_id
    JOIN evidence_segments e ON e.id = s.evidence_segment_id
    LEFT JOIN statement_extractions x ON x.statement_id = s.id
    WHERE l.source_content_hash = si.content_hash
      AND l.content_version = si.content_version
      AND (
        e.segment_hash = l.evidence_hash
        OR e.segment_hash = x.evidence_hash
      )
  )
`;

/**
 * Reapply operator decisions after an import rewrites machine columns.
 * A decision covers the row only when the source hash and version match and the
 * evidence is either the accepted span or the original machine span. Changed
 * evidence does not inherit an old approval. Machine-suggested relationships
 * are left untouched unless the operator decision names that same pair and type.
 * Slugs already rewritten by loadReviewPreservation are skipped here so the same
 * statement, forecast, and evidence columns are not corrected twice.
 */
export async function restoreCoveredDecisions(
  client: pg.PoolClient,
  options?: { skipSlugs?: readonly string[] },
): Promise<void> {
  const skipSlugs = options?.skipSlugs ?? [];
  await client.query(`
    ${coveredDecisionsSql}
    UPDATE statements s
    SET review_state = c.resulting_review_state,
        normalized_text = CASE
          WHEN c.corrections_json ? 'normalized_text' THEN c.corrections_json->>'normalized_text'
          ELSE s.normalized_text
        END,
        statement_type = CASE
          WHEN c.corrections_json ? 'statement_type' THEN c.corrections_json->>'statement_type'
          ELSE s.statement_type
        END
    FROM covered c
    WHERE s.id = c.statement_id
      AND NOT (s.slug = ANY($1::text[]))
  `, [skipSlugs]);
  await client.query(`
    ${coveredDecisionsSql}
    UPDATE evidence_segments e
    SET text = CASE
          WHEN c.corrections_json ? 'evidence_text' THEN c.corrections_json->>'evidence_text'
          ELSE e.text
        END,
        start_char = CASE
          WHEN c.corrections_json ? 'start_char' THEN (c.corrections_json->>'start_char')::int
          ELSE e.start_char
        END,
        end_char = CASE
          WHEN c.corrections_json ? 'end_char' THEN (c.corrections_json->>'end_char')::int
          ELSE e.end_char
        END,
        segment_hash = CASE
          WHEN c.corrections_json ? 'evidence_text'
            OR c.corrections_json ? 'start_char'
            OR c.corrections_json ? 'end_char'
          THEN c.evidence_hash
          ELSE e.segment_hash
        END
    FROM covered c
    JOIN statements s ON s.id = c.statement_id
    WHERE e.id = s.evidence_segment_id
      AND NOT (s.slug = ANY($1::text[]))
      AND (
        c.corrections_json ? 'evidence_text'
        OR c.corrections_json ? 'start_char'
        OR c.corrections_json ? 'end_char'
      )
  `, [skipSlugs]);
  await client.query(`
    ${coveredDecisionsSql}
    UPDATE forecasts f
    SET review_state = c.resulting_review_state,
        question_key = CASE WHEN c.corrections_json ? 'question_key' THEN c.corrections_json->>'question_key' ELSE f.question_key END,
        question_text = CASE WHEN c.corrections_json ? 'question_text' THEN c.corrections_json->>'question_text' ELSE f.question_text END,
        definition_text = CASE
          WHEN c.corrections_json ? 'definition_text' THEN c.corrections_json->>'definition_text'
          ELSE f.definition_text
        END,
        condition_text = CASE
          WHEN c.corrections_json ? 'condition_text' THEN c.corrections_json->>'condition_text'
          ELSE f.condition_text
        END,
        horizon_text = CASE
          WHEN c.corrections_json ? 'horizon_text' THEN c.corrections_json->>'horizon_text'
          ELSE f.horizon_text
        END,
        value_type = CASE WHEN c.corrections_json ? 'value_type' THEN c.corrections_json->>'value_type' ELSE f.value_type END,
        value_numeric = CASE
          WHEN c.corrections_json ? 'value_numeric' THEN NULLIF(c.corrections_json->>'value_numeric', '')::numeric
          ELSE f.value_numeric
        END,
        value_min = CASE
          WHEN c.corrections_json ? 'value_min' THEN NULLIF(c.corrections_json->>'value_min', '')::numeric
          ELSE f.value_min
        END,
        value_max = CASE
          WHEN c.corrections_json ? 'value_max' THEN NULLIF(c.corrections_json->>'value_max', '')::numeric
          ELSE f.value_max
        END,
        unit = CASE WHEN c.corrections_json ? 'unit' THEN c.corrections_json->>'unit' ELSE f.unit END
    FROM covered c
    WHERE f.statement_id = c.statement_id
      AND c.statement_id NOT IN (SELECT id FROM statements WHERE slug = ANY($1::text[]))
  `, [skipSlugs]);
  await client.query(`
    ${coveredDecisionsSql}
    INSERT INTO statement_relationships (
      id, from_statement_id, to_statement_id, relationship_type, method, confidence, review_state
    )
    SELECT gen_random_uuid(), c.statement_id, other.id, c.relationship_json->>'relationship_type',
           'curator_review', 1, c.resulting_review_state
    FROM covered c
    JOIN statements other ON other.slug = c.relationship_json->>'other_statement_slug'
    WHERE c.relationship_json IS NOT NULL
      AND c.relationship_json->>'relationship_type' IS NOT NULL
      AND other.id <> c.statement_id
    ON CONFLICT (from_statement_id, to_statement_id, relationship_type) DO UPDATE SET
      method = 'curator_review',
      confidence = EXCLUDED.confidence,
      review_state = EXCLUDED.review_state
  `);
}
