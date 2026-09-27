ALTER TABLE statements ADD COLUMN extractor_name text;
ALTER TABLE statements ADD COLUMN candidate_key text;
ALTER TABLE statements ADD COLUMN proposed_topics text[] NOT NULL DEFAULT '{}';
ALTER TABLE statements ADD COLUMN extraction_confidence_level text;
ALTER TABLE statements ALTER COLUMN confidence DROP NOT NULL;
ALTER TABLE statements ADD CONSTRAINT statements_confidence_present_check
  CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1));
ALTER TABLE statements ADD CONSTRAINT statements_extraction_confidence_level_check
  CHECK (extraction_confidence_level IS NULL OR extraction_confidence_level IN ('high', 'medium', 'low', 'unknown'));

UPDATE statements
SET extractor_name = split_part(extractor_version, '/', 1)
WHERE extractor_name IS NULL;

UPDATE statements AS s
SET candidate_key = encode(digest(
  p.slug || E'\n' || si.content_hash || E'\n' || e.segment_hash || E'\n' || s.extractor_name || E'\n' || s.extractor_version || E'\n' || s.statement_type,
  'sha256'), 'hex')
FROM people AS p, source_items AS si, evidence_segments AS e
WHERE p.id = s.person_id
  AND si.id = s.source_item_id
  AND e.id = s.evidence_segment_id
  AND s.candidate_key IS NULL;

ALTER TABLE statements ALTER COLUMN extractor_name SET NOT NULL;
CREATE UNIQUE INDEX statements_candidate_key_idx ON statements (candidate_key) WHERE candidate_key IS NOT NULL;

CREATE TABLE statement_extractions (
  statement_id uuid PRIMARY KEY REFERENCES statements (id),
  candidate_key text NOT NULL,
  statement_type text NOT NULL,
  normalized_text text NOT NULL,
  confidence numeric(4,3),
  extraction_confidence_level text,
  extractor_name text NOT NULL,
  extractor_version text NOT NULL,
  evidence_text text NOT NULL,
  evidence_hash text NOT NULL,
  source_content_hash text NOT NULL,
  content_version integer NOT NULL,
  forecast_json jsonb,
  topic_slugs text[] NOT NULL,
  captured_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE review_decisions (
  id uuid PRIMARY KEY,
  decision_key text NOT NULL UNIQUE,
  statement_id uuid NOT NULL REFERENCES statements (id),
  candidate_key text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('approve', 'reject', 'needs_changes')),
  rejection_reason text CHECK (rejection_reason IS NULL OR rejection_reason IN (
    'wrong_speaker', 'wrong_source_attribution', 'not_a_forecast', 'extraction_error', 'duplicate',
    'insufficient_evidence', 'definition_ambiguous', 'numerical_interpretation_incorrect',
    'source_unavailable', 'other'
  )),
  previous_review_state text NOT NULL,
  resulting_review_state text NOT NULL,
  reviewed_at timestamptz NOT NULL,
  reviewer text NOT NULL,
  note text,
  extractor_name text,
  extractor_version text,
  source_item_id uuid,
  evidence_segment_id uuid,
  source_content_hash text NOT NULL,
  evidence_hash text NOT NULL,
  content_version integer NOT NULL,
  corrections_json jsonb NOT NULL,
  original_extraction_json jsonb NOT NULL,
  relationship_json jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX review_decisions_statement_idx ON review_decisions (statement_id, reviewed_at);
