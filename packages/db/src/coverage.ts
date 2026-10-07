import type pg from "pg";

export function staleApprovalSql(statementAlias = "s"): string {
  return `EXISTS (
    SELECT 1
    FROM review_decisions stale_d
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
        OR stale_d.accepted_claim_json IS NULL
        OR stale_d.accepted_claim_json IS DISTINCT FROM statement_claim_v1(${statementAlias}.id)
      )
  )`;
}

/** Approval covers the full accepted interpretation, never merely matching bytes. */
export function coveringDecisionStateSql(statementAlias = "s"): string {
  return `(
    SELECT cover_d.resulting_review_state
    FROM review_decisions cover_d
    WHERE cover_d.statement_id = ${statementAlias}.id
      AND (cover_d.reviewed_at, cover_d.decision_key) = (
        SELECT cover_d2.reviewed_at, cover_d2.decision_key
        FROM review_decisions cover_d2
        WHERE cover_d2.statement_id = ${statementAlias}.id
        ORDER BY cover_d2.reviewed_at DESC, cover_d2.decision_key DESC
        LIMIT 1
      )
      AND (cover_d.resulting_review_state <> 'human_verified'
        OR cover_d.accepted_claim_json = statement_claim_v1(${statementAlias}.id))
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
    SELECT l.statement_id, l.resulting_review_state, l.evidence_hash, l.relationship_json,
      (SELECT COALESCE(jsonb_object_agg(c.key, c.value ORDER BY history.reviewed_at, history.decision_key), '{}'::jsonb)
       FROM review_decisions history
       CROSS JOIN LATERAL jsonb_each(history.corrections_json) c
       WHERE history.statement_id = l.statement_id AND history.candidate_key = l.candidate_key
         AND (history.reviewed_at, history.decision_key) <= (l.reviewed_at, l.decision_key)
      ) AS corrections_json
    FROM latest l
    JOIN statements s ON s.id = l.statement_id
    JOIN source_items si ON si.id = s.source_item_id
    JOIN evidence_segments e ON e.id = s.evidence_segment_id
    LEFT JOIN statement_extractions x ON x.statement_id = s.id
    WHERE l.accepted_claim_json IS NULL
      AND l.source_content_hash = si.content_hash
      AND l.content_version = si.content_version
      AND (
        e.segment_hash = l.evidence_hash
        OR e.segment_hash = x.evidence_hash
      )
  )
`;

/**
 * Reapply operator decisions after an import rewrites machine columns.
 * New decisions replay a full accepted snapshot only onto that decision's exact
 * machine input or accepted claim. Legacy deltas remain replayable on their
 * candidate/provenance but cannot confer human verification. Machine relationships
 * are left untouched unless the operator decision names that same pair and type.
 * Slugs already rewritten by loadReviewPreservation are skipped here so the same
 * statement, forecast, and evidence columns are not corrected twice.
 */
export async function restoreCoveredDecisions(
  client: pg.PoolClient,
  options?: { skipSlugs?: readonly string[] },
): Promise<void> {
  await restoreAcceptedClaims(client);
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
    SET review_state = CASE WHEN c.resulting_review_state = 'human_verified'
          THEN 'needs_review' ELSE c.resulting_review_state END,
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

/** Capture matches before any corrections mutate shared evidence or forecasts. */
async function restoreAcceptedClaims(client: pg.PoolClient): Promise<void> {
  const covered = await client.query<{ id: string }>(`
    SELECT d.id
    FROM statements s
    JOIN LATERAL (
      SELECT id, machine_claim_json, accepted_claim_json
      FROM review_decisions WHERE statement_id = s.id
      ORDER BY reviewed_at DESC, decision_key DESC LIMIT 1
    ) d ON true
    WHERE d.accepted_claim_json IS NOT NULL
      AND statement_claim_v1(s.id) IN (d.machine_claim_json, d.accepted_claim_json)
  `);
  const ids = covered.rows.map((row) => row.id);
  if (!ids.length) return;
  await client.query(`
    UPDATE statements s
    SET normalized_text = d.accepted_claim_json->>'normalized_text',
        statement_type = d.accepted_claim_json->>'statement_type',
        review_state = d.resulting_review_state
    FROM review_decisions d WHERE d.id = ANY($1::uuid[]) AND s.id = d.statement_id
  `, [ids]);
  await client.query(`
    UPDATE evidence_segments e
    SET text = d.accepted_claim_json->'evidence'->>'text',
        segment_hash = d.accepted_claim_json->'evidence'->>'hash',
        start_char = (d.accepted_claim_json->'evidence'->>'start_char')::int,
        end_char = (d.accepted_claim_json->'evidence'->>'end_char')::int,
        start_ms = (d.accepted_claim_json->'evidence'->>'start_ms')::int,
        end_ms = (d.accepted_claim_json->'evidence'->>'end_ms')::int,
        context_text = d.accepted_claim_json->'evidence'->>'context_text'
    FROM review_decisions d JOIN statements s ON s.id = d.statement_id
    WHERE d.id = ANY($1::uuid[]) AND e.id = s.evidence_segment_id
  `, [ids]);
  await client.query(`
    INSERT INTO forecasts (
      id, statement_id, forecast_kind, question_key, question_text, definition_text, condition_text,
      target_date_start, target_date_end, horizon_text, value_type, value_numeric, value_min, value_max,
      unit, distribution_json, resolution_criteria, review_state
    )
    SELECT gen_random_uuid(), d.statement_id, f->>'forecast_kind', f->>'question_key', f->>'question_text',
           f->>'definition_text', f->>'condition_text', (f->>'target_date_start')::date,
           (f->>'target_date_end')::date, f->>'horizon_text', f->>'value_type',
           (f->>'value_numeric')::numeric, (f->>'value_min')::numeric, (f->>'value_max')::numeric,
           f->>'unit', NULLIF(f->'distribution_json', 'null'::jsonb), f->>'resolution_criteria', d.resulting_review_state
    FROM review_decisions d
    CROSS JOIN LATERAL (SELECT d.accepted_claim_json->'forecast' AS f) claim
    WHERE d.id = ANY($1::uuid[]) AND f <> 'null'::jsonb
    ON CONFLICT (statement_id) DO UPDATE SET
      forecast_kind = EXCLUDED.forecast_kind, question_key = EXCLUDED.question_key,
      question_text = EXCLUDED.question_text, definition_text = EXCLUDED.definition_text,
      condition_text = EXCLUDED.condition_text, target_date_start = EXCLUDED.target_date_start,
      target_date_end = EXCLUDED.target_date_end, horizon_text = EXCLUDED.horizon_text,
      value_type = EXCLUDED.value_type, value_numeric = EXCLUDED.value_numeric,
      value_min = EXCLUDED.value_min, value_max = EXCLUDED.value_max, unit = EXCLUDED.unit,
      distribution_json = EXCLUDED.distribution_json, resolution_criteria = EXCLUDED.resolution_criteria,
      review_state = EXCLUDED.review_state
  `, [ids]);
  await client.query(`
    DELETE FROM statement_topics st USING review_decisions d
    WHERE d.id = ANY($1::uuid[]) AND st.statement_id = d.statement_id
  `, [ids]);
  await client.query(`
    INSERT INTO statement_topics (statement_id, topic_id, confidence, method)
    SELECT d.statement_id, t.id, 1, 'curator_review'
    FROM review_decisions d
    CROSS JOIN LATERAL jsonb_array_elements_text(d.accepted_claim_json->'topic_slugs') slug
    JOIN topics t ON t.slug = slug.value
    WHERE d.id = ANY($1::uuid[])
  `, [ids]);
  await client.query(`
    INSERT INTO statement_relationships (
      id, from_statement_id, to_statement_id, relationship_type, method, confidence, review_state
    )
    SELECT gen_random_uuid(), d.statement_id, other.id, d.relationship_json->>'relationship_type',
           'curator_review', 1, d.resulting_review_state
    FROM review_decisions d
    JOIN statements other ON other.slug = d.relationship_json->>'other_statement_slug'
    WHERE d.id = ANY($1::uuid[]) AND other.id <> d.statement_id
    ON CONFLICT (from_statement_id, to_statement_id, relationship_type) DO UPDATE SET
      method = 'curator_review', confidence = EXCLUDED.confidence, review_state = EXCLUDED.review_state
  `, [ids]);
}
