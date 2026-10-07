-- Candidate identity v1 remains unchanged. Approval covers this separate,
-- versioned representation of the interpretation, including human corrections.
ALTER TABLE review_decisions ADD COLUMN machine_claim_json jsonb;
ALTER TABLE review_decisions ADD COLUMN accepted_claim_json jsonb;

-- Do not backfill approvals from mutable live rows: older audit records do not
-- contain every semantic field. NULL snapshots require a new operator decision.
CREATE FUNCTION statement_claim_v1(statement_id uuid) RETURNS jsonb
LANGUAGE sql STABLE AS $$
  SELECT jsonb_build_object(
    'version', 1,
    'person_slug', p.slug,
    'source', jsonb_build_object(
      'slug', si.slug, 'canonical_url', si.canonical_url,
      'content_hash', si.content_hash, 'content_version', si.content_version
    ),
    'extractor_name', s.extractor_name, 'extractor_version', s.extractor_version,
    'statement_type', s.statement_type, 'normalized_text', s.normalized_text,
    'event_time', to_char(s.event_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'evidence', jsonb_build_object(
      'source_item_slug', esi.slug, 'segment_kind', e.segment_kind,
      'text', e.text, 'hash', e.segment_hash, 'context_text', e.context_text,
      'start_char', e.start_char, 'end_char', e.end_char,
      'start_ms', e.start_ms, 'end_ms', e.end_ms
    ),
    'forecast', CASE WHEN f.id IS NULL THEN NULL ELSE jsonb_build_object(
      'forecast_kind', f.forecast_kind, 'question_key', f.question_key,
      'question_text', f.question_text, 'definition_text', f.definition_text,
      'condition_text', f.condition_text,
      'target_date_start', f.target_date_start, 'target_date_end', f.target_date_end,
      'horizon_text', f.horizon_text, 'value_type', f.value_type,
      'value_numeric', f.value_numeric, 'value_min', f.value_min, 'value_max', f.value_max,
      'unit', f.unit, 'distribution_json', f.distribution_json,
      'resolution_criteria', f.resolution_criteria
    ) END,
    'topic_slugs', COALESCE((
      SELECT jsonb_agg(t.slug ORDER BY t.slug COLLATE "C")
      FROM statement_topics st JOIN topics t ON t.id = st.topic_id
      WHERE st.statement_id = s.id
    ), '[]'::jsonb)
  )
  FROM statements s
  JOIN people p ON p.id = s.person_id
  JOIN source_items si ON si.id = s.source_item_id
  JOIN evidence_segments e ON e.id = s.evidence_segment_id
  JOIN source_items esi ON esi.id = e.source_item_id
  LEFT JOIN forecasts f ON f.statement_id = s.id
  WHERE s.id = $1
$$;

ALTER TABLE review_decisions ADD CONSTRAINT review_decisions_claim_snapshots_check CHECK (
  (machine_claim_json IS NULL AND accepted_claim_json IS NULL)
  OR (machine_claim_json IS NOT NULL AND accepted_claim_json IS NOT NULL
      AND machine_claim_json @> '{"version":1}'::jsonb
      AND accepted_claim_json @> '{"version":1}'::jsonb)
);
