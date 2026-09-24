CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  organization_type text NOT NULL CHECK (organization_type IN (
    'frontier_lab', 'research_institute', 'university', 'company', 'publisher', 'government', 'nonprofit'
  )),
  canonical_url text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE people (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  display_name text NOT NULL,
  given_name text,
  family_name text,
  bio_short text NOT NULL,
  inclusion_reason text NOT NULL,
  cohort_tags text[] NOT NULL DEFAULT '{}',
  status text NOT NULL CHECK (status IN ('active', 'historical', 'review')),
  current_affiliation_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(display_name, '') || ' ' || coalesce(bio_short, ''))
  ) STORED
);

CREATE INDEX people_search_idx ON people USING gin (search_vector);
CREATE INDEX people_status_idx ON people (status);

CREATE TABLE sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  source_type text NOT NULL CHECK (source_type IN (
    'personal_site', 'blog', 'newsletter', 'podcast', 'video', 'paper', 'lab_post',
    'conference_talk', 'testimony', 'interview', 'repository', 'model_card', 'social_post', 'press'
  )),
  name text NOT NULL,
  canonical_url text NOT NULL,
  platform text,
  owner_person_id uuid REFERENCES people (id) DEFERRABLE INITIALLY DEFERRED,
  owner_organization_id uuid REFERENCES organizations (id),
  collection_method text NOT NULL CHECK (collection_method IN ('fixture', 'rss', 'api', 'manual', 'sitemap')),
  rights_notes text,
  enabled boolean NOT NULL DEFAULT true,
  last_checked_at timestamptz,
  last_success_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE affiliations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id uuid NOT NULL REFERENCES people (id),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  role text,
  start_date date,
  end_date date,
  source_id uuid REFERENCES sources (id) DEFERRABLE INITIALLY DEFERRED,
  confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT affiliations_natural_key UNIQUE NULLS NOT DISTINCT (person_id, organization_id, role, start_date),
  CONSTRAINT affiliations_date_order CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

ALTER TABLE people
  ADD CONSTRAINT people_current_affiliation_fk
  FOREIGN KEY (current_affiliation_id) REFERENCES affiliations (id) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX affiliations_person_idx ON affiliations (person_id);
CREATE INDEX affiliations_org_idx ON affiliations (organization_id);

CREATE TABLE external_identities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id uuid NOT NULL REFERENCES people (id),
  namespace text NOT NULL CHECK (namespace IN (
    'orcid', 'openalex', 'openreview', 'semantic_scholar', 'github', 'huggingface',
    'x', 'bluesky', 'mastodon', 'personal_website', 'lab_profile', 'youtube'
  )),
  external_id text NOT NULL,
  canonical_url text,
  handle text,
  verification_method text NOT NULL CHECK (verification_method IN (
    'self_asserted', 'institutional_profile', 'cross_link', 'platform_verification', 'manual_review', 'synthetic_fixture'
  )),
  confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  verified_at timestamptz,
  source_id uuid REFERENCES sources (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (namespace, external_id)
);

CREATE UNIQUE INDEX external_identities_handle_idx
  ON external_identities (namespace, handle)
  WHERE handle IS NOT NULL;

CREATE TABLE ingestion_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  collector text NOT NULL,
  source_id uuid REFERENCES sources (id),
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
  cursor_before text,
  cursor_after text,
  observed_count integer NOT NULL CHECK (observed_count >= 0),
  new_count integer NOT NULL CHECK (new_count >= 0),
  changed_count integer NOT NULL CHECK (changed_count >= 0),
  error_summary text
);

CREATE TABLE source_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  source_id uuid NOT NULL REFERENCES sources (id),
  upstream_id text,
  logical_key text NOT NULL,
  canonical_url text NOT NULL,
  title text,
  published_at timestamptz,
  published_timezone text,
  observed_at timestamptz NOT NULL,
  updated_at_source timestamptz,
  language text,
  content_hash text NOT NULL CHECK (content_hash ~ '^[a-f0-9]{64}$'),
  content_version integer NOT NULL CHECK (content_version > 0),
  content_reference text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  collection_status text NOT NULL CHECK (collection_status IN (
    'collected', 'partial', 'unavailable', 'not_found', 'rate_limited', 'unauthorized',
    'blocked_by_policy', 'parser_unsupported', 'content_too_large', 'invalid_content', 'collector_bug'
  )),
  availability text NOT NULL CHECK (availability IN ('available', 'removed', 'unknown')),
  is_current boolean NOT NULL DEFAULT true,
  ingestion_run_id uuid REFERENCES ingestion_runs (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, logical_key, content_hash)
);

CREATE UNIQUE INDEX source_items_one_current_idx
  ON source_items (source_id, logical_key)
  WHERE is_current;

CREATE INDEX source_items_published_idx ON source_items (published_at DESC);

CREATE TABLE source_participants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_item_id uuid NOT NULL REFERENCES source_items (id),
  person_id uuid REFERENCES people (id),
  organization_id uuid REFERENCES organizations (id),
  role text NOT NULL CHECK (role IN ('author', 'speaker', 'guest', 'interviewer', 'publisher', 'mentioned')),
  attribution_method text NOT NULL CHECK (attribution_method IN (
    'byline', 'metadata', 'transcript_label', 'manual', 'synthetic_fixture'
  )),
  confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  CHECK (person_id IS NOT NULL OR organization_id IS NOT NULL),
  UNIQUE NULLS NOT DISTINCT (source_item_id, person_id, organization_id, role)
);

CREATE TABLE evidence_segments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  source_item_id uuid NOT NULL REFERENCES source_items (id),
  segment_kind text NOT NULL CHECK (segment_kind IN ('text', 'transcript', 'caption', 'table', 'metadata')),
  sequence integer NOT NULL CHECK (sequence > 0),
  start_char integer,
  end_char integer,
  start_ms integer,
  end_ms integer,
  text text NOT NULL CHECK (char_length(text) BETWEEN 1 AND 2000),
  context_text text CHECK (context_text IS NULL OR char_length(context_text) <= 800),
  segment_hash text NOT NULL CHECK (segment_hash ~ '^[a-f0-9]{64}$'),
  UNIQUE (source_item_id, sequence),
  CHECK (start_char IS NULL OR end_char IS NULL OR end_char >= start_char),
  CHECK (start_ms IS NULL OR end_ms IS NULL OR end_ms >= start_ms)
);

CREATE TABLE topics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  definition text NOT NULL,
  parent_topic_id uuid REFERENCES topics (id),
  version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE extraction_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  source_item_id uuid NOT NULL REFERENCES source_items (id),
  extractor_name text NOT NULL,
  extractor_version text NOT NULL,
  model_provider text,
  model_name text,
  prompt_contract_version text NOT NULL,
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
  input_hash text NOT NULL CHECK (input_hash ~ '^[a-f0-9]{64}$'),
  output_hash text CHECK (output_hash IS NULL OR output_hash ~ '^[a-f0-9]{64}$'),
  UNIQUE (source_item_id, extractor_name, extractor_version, input_hash)
);

CREATE TABLE statements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  person_id uuid NOT NULL REFERENCES people (id),
  source_item_id uuid NOT NULL REFERENCES source_items (id),
  statement_type text NOT NULL CHECK (statement_type IN (
    'explicit_numeric', 'explicit_qualitative', 'model_inferred_signal'
  )),
  normalized_text text NOT NULL CHECK (char_length(normalized_text) BETWEEN 1 AND 600),
  event_time timestamptz,
  evidence_segment_id uuid NOT NULL REFERENCES evidence_segments (id),
  extractor_version text NOT NULL,
  confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  review_state text NOT NULL CHECK (review_state IN (
    'unreviewed', 'machine_validated', 'human_verified', 'rejected', 'needs_review'
  )),
  extraction_run_id uuid REFERENCES extraction_runs (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(normalized_text, ''))
  ) STORED
);

CREATE INDEX statements_search_idx ON statements USING gin (search_vector);
CREATE INDEX statements_person_time_idx ON statements (person_id, event_time DESC);
CREATE INDEX statements_type_review_idx ON statements (statement_type, review_state);
CREATE INDEX statements_event_idx ON statements (event_time DESC, id DESC);

CREATE TABLE forecasts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  statement_id uuid NOT NULL UNIQUE REFERENCES statements (id),
  forecast_kind text NOT NULL CHECK (forecast_kind IN (
    'probability', 'timeline', 'quantity', 'qualitative', 'classification'
  )),
  question_key text NOT NULL,
  question_text text NOT NULL,
  definition_text text,
  condition_text text,
  target_date_start date,
  target_date_end date,
  horizon_text text,
  value_type text NOT NULL CHECK (value_type IN ('point', 'range', 'distribution', 'none')),
  value_numeric numeric(12,5),
  value_min numeric(12,5),
  value_max numeric(12,5),
  unit text,
  distribution_json jsonb,
  resolution_criteria text,
  review_state text NOT NULL CHECK (review_state IN (
    'unreviewed', 'machine_validated', 'human_verified', 'rejected', 'needs_review'
  )),
  CHECK (value_min IS NULL OR value_max IS NULL OR value_min <= value_max),
  CHECK (
    unit IS DISTINCT FROM 'probability' OR (
      (value_numeric IS NULL OR (value_numeric >= 0 AND value_numeric <= 1)) AND
      (value_min IS NULL OR (value_min >= 0 AND value_min <= 1)) AND
      (value_max IS NULL OR (value_max >= 0 AND value_max <= 1))
    )
  )
);

CREATE INDEX forecasts_question_idx ON forecasts (question_key);

CREATE TABLE statement_topics (
  statement_id uuid NOT NULL REFERENCES statements (id),
  topic_id uuid NOT NULL REFERENCES topics (id),
  confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  method text NOT NULL,
  PRIMARY KEY (statement_id, topic_id)
);

CREATE INDEX statement_topics_topic_idx ON statement_topics (topic_id);

CREATE TABLE statement_relationships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  from_statement_id uuid NOT NULL REFERENCES statements (id),
  to_statement_id uuid NOT NULL REFERENCES statements (id),
  relationship_type text NOT NULL CHECK (relationship_type IN (
    'updates', 'clarifies', 'retracts', 'contradicts', 'repeats'
  )),
  method text NOT NULL,
  confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  review_state text NOT NULL CHECK (review_state IN (
    'unreviewed', 'machine_validated', 'human_verified', 'rejected', 'needs_review'
  )),
  CHECK (from_statement_id <> to_statement_id),
  UNIQUE (from_statement_id, to_statement_id, relationship_type)
);

CREATE TABLE cohorts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL,
  version text NOT NULL,
  name text NOT NULL,
  definition text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (slug, version)
);

CREATE TABLE cohort_memberships (
  cohort_id uuid NOT NULL REFERENCES cohorts (id),
  person_id uuid NOT NULL REFERENCES people (id),
  inclusion_reason text NOT NULL,
  PRIMARY KEY (cohort_id, person_id)
);

CREATE TABLE trend_definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  topic_id uuid REFERENCES topics (id),
  method_version text NOT NULL,
  cohort_id uuid NOT NULL REFERENCES cohorts (id),
  cohort_definition_json jsonb NOT NULL,
  aggregation_definition_json jsonb NOT NULL,
  published boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE trend_observations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trend_definition_id uuid NOT NULL REFERENCES trend_definitions (id),
  window_start timestamptz,
  window_end timestamptz,
  calculated_at timestamptz NOT NULL,
  value_json jsonb NOT NULL,
  contributing_statement_count integer NOT NULL CHECK (contributing_statement_count >= 0),
  contributing_person_count integer NOT NULL CHECK (contributing_person_count >= 0),
  coverage_json jsonb NOT NULL
);

CREATE OR REPLACE FUNCTION enforce_forecast_class_boundary()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  st_type text;
BEGIN
  SELECT statement_type INTO st_type FROM statements WHERE id = NEW.statement_id;
  IF st_type IS NULL THEN
    RAISE EXCEPTION 'forecast statement not found';
  END IF;

  IF st_type = 'explicit_numeric' THEN
    IF NEW.value_type NOT IN ('point', 'range', 'distribution') THEN
      RAISE EXCEPTION 'explicit_numeric requires a numeric value_type';
    END IF;
    IF NEW.value_type = 'point' AND NEW.value_numeric IS NULL THEN
      RAISE EXCEPTION 'point forecast requires value_numeric';
    END IF;
    IF NEW.value_type = 'range' AND (NEW.value_min IS NULL OR NEW.value_max IS NULL) THEN
      RAISE EXCEPTION 'range forecast requires bounds';
    END IF;
  ELSIF st_type IN ('explicit_qualitative', 'model_inferred_signal') THEN
    IF NEW.value_numeric IS NOT NULL OR NEW.value_min IS NOT NULL OR NEW.value_max IS NOT NULL OR NEW.distribution_json IS NOT NULL THEN
      RAISE EXCEPTION 'non-numeric statement cannot store numeric forecast values';
    END IF;
    IF NEW.value_type <> 'none' THEN
      RAISE EXCEPTION 'non-numeric statement forecast value_type must be none';
    END IF;
  ELSE
    RAISE EXCEPTION 'unsupported statement type %', st_type;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER forecasts_class_boundary
  BEFORE INSERT OR UPDATE ON forecasts
  FOR EACH ROW
  EXECUTE FUNCTION enforce_forecast_class_boundary();
