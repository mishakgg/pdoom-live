# Canonical data model

This document defines conceptual entities. The implementation may normalize further, but should preserve these distinctions.

## Person

Represents a tracked human.

Suggested fields:

- `id`
- `slug`
- `display_name`
- `given_name`
- `family_name`
- `bio_short`
- `current_affiliation_id?`
- `inclusion_reason`
- `cohort_tags[]`
- `status` — active / historical / review
- `created_at`
- `updated_at`

Do not put source-platform usernames directly on the person row.

## Organization

- `id`
- `slug`
- `name`
- `organization_type`
- `canonical_url?`
- `created_at`
- `updated_at`

Affiliation history should be modeled separately when dates matter.

## Affiliation

- `person_id`
- `organization_id`
- `role?`
- `start_date?`
- `end_date?`
- `source_id?`
- `confidence_level` — `high` / `medium` / `low` / `unknown`. Not a probability.
- `verification_detail?`
- `review_state`

## External identity

Maps a person to a public identity namespace.

Examples:

- ORCID
- OpenAlex
- OpenReview
- Semantic Scholar
- GitHub
- Hugging Face
- X
- Bluesky
- Mastodon
- personal website
- lab profile

Fields:

- `id`
- `person_id`
- `namespace`
- `external_id`
- `canonical_url?`
- `handle?`
- `verification_method`
- `verification_detail?` — pipeline strategy, such as `openalex_exact_name_and_institution`
- `confidence_level` — categorical, not a probability
- `review_state`
- `verified_at?`
- `source_id?`

Unique constraints should prevent accidental duplicate mappings.

## Source

A logical publisher/feed/channel.

Examples: a personal blog, YouTube channel, podcast, lab news page, GitHub account.

- `id`
- `source_type`
- `name`
- `canonical_url`
- `platform?`
- `owner_person_id?`
- `owner_organization_id?`
- `collection_method`
- `collection_adapter?` — collector method such as `openalex_api` when the canonical method is `api`
- `review_state`
- `rights_notes?`
- `enabled`
- `last_checked_at?`
- `last_success_at?`

## Source item

An observed public content item.

Examples: post, video, podcast episode, paper, interview, blog entry, model card, testimony transcript.

- `id`
- `source_id`
- `upstream_id?`
- `canonical_url`
- `title?`
- `published_at?`
- `observed_at`
- `updated_at_source?`
- `language?`
- `content_hash`
- `content_version`
- `content_reference?`
- `metadata_json`
- `collection_status`

Canonical URL and platform upstream IDs should be used for deduplication where reliable.

## Source participant

Links a source item to people or organizations.

- `source_item_id`
- `person_id?`
- `organization_id?`
- `role` — author / speaker / guest / interviewer / publisher / mentioned
- `attribution_method`
- `attribution_detail?`
- `confidence_level`

“Mentioned” must never be confused with “speaker.”

## Evidence segment

A verifiable slice of a source item.

- `id`
- `source_item_id`
- `segment_kind` — text / transcript / caption / table / metadata
- `sequence`
- `start_char?`
- `end_char?`
- `start_ms?`
- `end_ms?`
- `text`
- `segment_hash`

Evidence retention must comply with the source policy.

## Topic

Use stable topic identifiers with definitions.

- `id`
- `slug`
- `name`
- `definition`
- `parent_topic_id?`
- `version`

Do not allow extractor-generated arbitrary labels to silently become canonical topics.

## Statement

A sourced proposition attributable to a person.

- `id`
- `person_id`
- `source_item_id`
- `statement_type`
- `normalized_text`
- `event_time?`
- `evidence_segment_id`
- `extractor_version`
- `confidence`
- `review_state`
- `created_at`

Initial `statement_type` values:

- `explicit_numeric`
- `explicit_qualitative`
- `model_inferred_signal`

Consider additional non-forecast statement classes separately rather than overloading these values.

## Forecast

A structured future-facing statement. A forecast should point back to a Statement.

- `id`
- `statement_id`
- `forecast_kind`
- `question_text`
- `definition_text?`
- `condition_text?`
- `target_date_start?`
- `target_date_end?`
- `horizon_text?`
- `value_type`
- `value_numeric?`
- `value_min?`
- `value_max?`
- `unit?`
- `distribution_json?`
- `resolution_criteria?`
- `review_state`

Never populate numerical values from qualitative language merely to simplify charts.

## Statement topic

Many-to-many:

- `statement_id`
- `topic_id`
- `confidence`
- `method`

## Relationship / revision

To represent changing views without destroying history:

- `id`
- `from_statement_id`
- `to_statement_id`
- `relationship_type` — updates / clarifies / retracts / contradicts / repeats
- `method`
- `confidence`
- `review_state`

## Ingestion run

- `id`
- `collector`
- `source_id?`
- `started_at`
- `completed_at?`
- `status`
- `cursor_before?`
- `cursor_after?`
- `observed_count`
- `new_count`
- `changed_count`
- `error_summary?`

## Extraction run

- `id`
- `source_item_id`
- `extractor_name`
- `extractor_version`
- `model_provider?`
- `model_name?`
- `prompt_contract_version`
- `started_at`
- `completed_at?`
- `status`
- `input_hash`
- `output_hash?`

Store enough metadata to reproduce or compare extraction behavior without exposing secrets.

## Trend definition

- `id`
- `slug`
- `name`
- `topic_id`
- `method_version`
- `cohort_definition_json`
- `aggregation_definition_json`
- `published`

## Trend observation

- `trend_definition_id`
- `window_start`
- `window_end`
- `calculated_at`
- `value_json`
- `contributing_statement_count`
- `contributing_person_count`
- `coverage_json`

Every aggregate response should be reconstructible from canonical contributing records and a versioned method.

## Review states

Suggested shared states:

- `unreviewed`
- `machine_validated`
- `human_verified`
- `rejected`
- `needs_review`

The public product may expose different states differently. High-impact statements should not quietly bypass review/quality gates. `human_verified` is written only by an operator review decision. The machine extraction stays in `statement_extractions`. `review_decisions` appends each approve, reject, or needs-changes action. See `docs/CURATION.md`.

## Deletion and correction

Sources can disappear, authors can correct themselves, and extraction can be wrong.

Prefer:

- tombstoning or status changes over destructive erasure where lawful/appropriate;
- versioned corrections;
- preserving which public aggregates used which statement/version;
- clear correction timestamps.

Never silently rewrite historical evidence.

## Implementation additions

The first product slice adds these fields without collapsing the entities above:

- Slugs on people, organizations, sources, source items, evidence, statements, topics, cohorts, and runs, used as natural keys in the import document.
- `source_items.logical_key`, `content_hash`, `content_version`, and `is_current`. The unpublished body is not a column.
- `forecasts.question_key`, the comparability key a trend must match.
- `cohorts` and `cohort_memberships`, so a trend can name a cohort version.
- `trend_definitions.method_version` plus the aggregation JSON. Observations are computed from canonical rows.
- `dataset_imports` stores `schema_version`, `dataset_id`, `dataset_kind` (`synthetic` or `live`), `generated_at`, `imported_at`, `notice`, producer, and the current cohort. One row is current.
- Identity, affiliation, and participant confidence is categorical. Statement, forecast, topic, and relationship confidence stays numeric.
- Freshness of a source is `current` within 14 days of `last_success_at`, `aging` within 90 days, `stale` after that, and `never_checked` when `last_success_at` is null. That is collection state.

The import document is specified in `docs/INGESTION_CONTRACT.md`. Public review rules live in `packages/contracts/src/review.ts`: `rejected` and `unreviewed` are never public, `needs_review` is visible but not verified, `human_verified` may support verified trends, and `machine_validated` stays labeled as machine output. An approval whose source or evidence hash no longer matches the current item is treated as `needs_review` until a new decision covers that material.
