ALTER TABLE organizations DROP CONSTRAINT organizations_organization_type_check;
ALTER TABLE organizations ADD CONSTRAINT organizations_organization_type_check CHECK (organization_type IN (
  'frontier_lab', 'research_institute', 'research_lab', 'university', 'company', 'publisher',
  'government', 'nonprofit', 'infrastructure', 'safety_org', 'independent'
));

ALTER TABLE sources DROP CONSTRAINT sources_source_type_check;
ALTER TABLE sources ADD CONSTRAINT sources_source_type_check CHECK (source_type IN (
  'personal_site', 'blog', 'newsletter', 'podcast', 'video', 'paper', 'preprint', 'academic_works',
  'lab_post', 'conference_talk', 'testimony', 'interview', 'repository', 'model_card', 'social_post', 'press'
));

ALTER TABLE sources ADD COLUMN collection_adapter text;
ALTER TABLE sources ADD COLUMN review_state text;
UPDATE sources SET review_state = 'unreviewed';
ALTER TABLE sources ALTER COLUMN review_state SET NOT NULL;
ALTER TABLE sources ADD CONSTRAINT sources_review_state_check
  CHECK (review_state IN ('unreviewed', 'machine_validated', 'human_verified', 'rejected', 'needs_review'));

ALTER TABLE external_identities DROP CONSTRAINT external_identities_verification_method_check;
ALTER TABLE external_identities ADD CONSTRAINT external_identities_verification_method_check CHECK (verification_method IN (
  'self_asserted', 'institutional_profile', 'cross_link', 'platform_verification', 'manual_review',
  'structured_academic_source', 'synthetic_fixture'
));
ALTER TABLE external_identities ADD COLUMN verification_detail text;
ALTER TABLE external_identities ADD COLUMN review_state text;
UPDATE external_identities SET review_state = 'unreviewed';
ALTER TABLE external_identities ALTER COLUMN review_state SET NOT NULL;
ALTER TABLE external_identities ADD CONSTRAINT external_identities_review_state_check
  CHECK (review_state IN ('unreviewed', 'machine_validated', 'human_verified', 'rejected', 'needs_review'));
ALTER TABLE external_identities ADD COLUMN confidence_level text;
UPDATE external_identities SET confidence_level = 'unknown';
ALTER TABLE external_identities ALTER COLUMN confidence_level SET NOT NULL;
ALTER TABLE external_identities ADD CONSTRAINT external_identities_confidence_level_check
  CHECK (confidence_level IN ('high', 'medium', 'low', 'unknown'));
ALTER TABLE external_identities DROP COLUMN confidence;

ALTER TABLE affiliations ADD COLUMN confidence_level text;
ALTER TABLE affiliations ADD COLUMN verification_detail text;
ALTER TABLE affiliations ADD COLUMN review_state text;
UPDATE affiliations SET review_state = 'unreviewed';
ALTER TABLE affiliations ALTER COLUMN review_state SET NOT NULL;
ALTER TABLE affiliations ADD CONSTRAINT affiliations_review_state_check
  CHECK (review_state IN ('unreviewed', 'machine_validated', 'human_verified', 'rejected', 'needs_review'));
UPDATE affiliations SET confidence_level = 'unknown';
ALTER TABLE affiliations ALTER COLUMN confidence_level SET NOT NULL;
ALTER TABLE affiliations ADD CONSTRAINT affiliations_confidence_level_check
  CHECK (confidence_level IN ('high', 'medium', 'low', 'unknown'));
ALTER TABLE affiliations DROP COLUMN confidence;

ALTER TABLE source_participants ADD COLUMN confidence_level text;
ALTER TABLE source_participants ADD COLUMN attribution_detail text;
UPDATE source_participants SET confidence_level = 'unknown';
ALTER TABLE source_participants ALTER COLUMN confidence_level SET NOT NULL;
ALTER TABLE source_participants ADD CONSTRAINT source_participants_confidence_level_check
  CHECK (confidence_level IN ('high', 'medium', 'low', 'unknown'));
ALTER TABLE source_participants DROP COLUMN confidence;

CREATE TABLE dataset_imports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_version text NOT NULL,
  dataset_id text NOT NULL,
  dataset_kind text NOT NULL CHECK (dataset_kind IN ('synthetic', 'live')),
  generated_at timestamptz NOT NULL,
  imported_at timestamptz NOT NULL DEFAULT now(),
  notice text NOT NULL,
  producer_name text,
  producer_version text,
  cohort_slug text,
  cohort_version text,
  is_current boolean NOT NULL DEFAULT true
);

CREATE UNIQUE INDEX dataset_imports_one_current_idx ON dataset_imports (is_current) WHERE is_current;
