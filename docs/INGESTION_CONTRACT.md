# Ingestion contract

The product imports one canonical JSON document. The data-collection pipeline should emit this document rather than writing SQL itself.

This document is an internal ingestion contract. It is not the public research API. Public reads and bulk snapshots use a separate export, documented in `docs/PUBLIC_API.md`, which drops operational extraction fields and non-public review states.

Schema: `packages/contracts/schema/canonical-import.schema.json`  
TypeScript source: `packages/contracts/src/schemas.ts`  
Fixture example: `data/fixtures/synthetic/dataset.json`

Schema version `1.0.0` requires `schema_version`, `dataset_id`, `dataset_kind` (`synthetic` or `live`), `generated_at`, and `notice`. `producer` is optional. A live dataset must not set a synthetic flag and must not use `synthetic_fixture` or `collection_method: fixture`.

Identity and affiliation confidence is `high`, `medium`, `low`, or `unknown`. Those words are not probabilities. Numeric `confidence` remains only on statements, forecasts, topics, and relationships, where it is an extraction score.

`content_hash` may be a precomputed SHA-256. `content_hash_input` is optional and is hashed then discarded. A live item does not need its full body.

Operator commands, with `DATABASE_URL` set for the write commands:

- `npm run db:validate -- data/fixtures/synthetic/dataset.json` parses and checks the file. It does not write.
- `npm run db:migrate` applies pending SQL migrations. It does not import a dataset.
- `npm run db:import -- <file>` validates, requires migrations to already be current, then upserts in one transaction. It does not apply migrations. Rows absent from the file are kept.
- `npm run db:status` prints migration state, the current dataset, cohort, counts, and coverage. It does not migrate or import.
- `npm run db:seed` and `npm run db:reset` load the synthetic fixture. Production mode refuses both, and it refuses a synthetic `db:import`.

Canonical values are product semantics. Collector strings such as `openalex_api` map to `api`, and the original string is stored as `collection_adapter` or `verification_detail`. The map is `packages/contracts/vocabulary-map.json`. Unmapped strings fail. `SourceObservation` is still the collector envelope and is not this document.

## Identity

Cross-references use slugs, not database UUIDs. The importer assigns stable UUIDs from those natural keys and upserts:

- organization, person, source, topic, source item, evidence, statement: `slug`
- external identity: `namespace` + `external_id`
- source item version: `source` + `logical_key` + content hash
- forecast: one row per statement
- cohort: `slug` + `version`

Re-importing the same document does not create duplicate statements. A changed content hash is a new source-item version. The previous version keeps its slug. Version 1 slugs remain `item-` plus the SHA-256 prefix of the canonical URL. Later versions use a different slug. Rows absent from a later file are kept.

An ingestion run status may be `running`, `succeeded`, `partial`, or `failed`. `unchanged_count`, `skipped_count`, and `failed_count` are optional on older documents and default to zero in the database. A `partial` or `failed` run is not a full success. `publish-dataset.sh` refuses a document whose latest belief or refresh run is `failed`.

Import keeps existing review decisions and does not rewrite `review_decisions` or `statement_extractions`. A new decision stores a versioned machine-input snapshot and a complete accepted-claim snapshot. Exact unchanged extraction or replay of the accepted claim restores all cumulative corrections, including after later empty-delta decisions. Changes to attribution, extractor, statement/forecast interpretation, source version or evidence require review. Stored `human_verified` may remain while public reads report `needs_review`; approval returns only when the exact covered input is replayed and the full accepted interpretation is restored. A rejection stays rejected. Legacy decisions without complete snapshots require reapproval; matching legacy correction deltas remain preserved. See `docs/CURATION.md` for the representation and migration policy. The canonical JSON schema stays at `1.0.0`.

For statements present in an import, topic membership and forecast presence are authoritative. An omitted forecast removes that statement's previous forecast; statements absent from the document and their forecasts are retained. This prevents an old forecast or topic assignment from silently surviving a changed interpretation.

Forecast review state comes from the incoming extraction until an exactly matching machine/accepted snapshot restores an operator decision. A stored verified forecast does not retain that label after an uncovered interpretation change. Matching legacy corrections can be restored without conferring verification.

The public representation revision tracks accepted-claim semantics, including attribution and extractor references, forecast dates/distributions/resolution, evidence locators/context, and topic membership. In-place semantic changes invalidate a primed representation on its next revision check; the existing cache TTL and bounded hash-collision policy are unchanged.

## Statement classes

`statement_type` is one of:

- `explicit_numeric`
- `explicit_qualitative`
- `model_inferred_signal`

Numeric fields are allowed only on `explicit_numeric` forecasts. `value_text` such as `12%` must match `value_numeric` on the 0–1 scale. Qualitative words do not parse.

`question_key` is the comparability key. A numeric trend includes a forecast when that key, unit, conditionality, value shape, and review state match the method. A horizon is required when the method says so. A matching key is included even if the topic slug differs. Topic slugs explain nearby exclusions. They are not a second comparability key.

Keep separate keys for unconditional extinction, conditional extinction, catastrophic harm, disempowerment, AGI probabilities, AGI years, ASI years, coding automation, unemployment, productivity, and GDP. The rules and the prepared keys are in [Trend methodology](./TREND_METHODOLOGY.md).

## Source text

`content_hash_input` and evidence `text` are untrusted data. The app stores the hash, a content reference, and a short evidence excerpt. It does not execute source text.

Canonical URLs must be `http` or `https`, without embedded credentials, and must not target loopback, private, link-local, or cloud-metadata hosts. Collectors still need to resolve DNS and re-check redirects before any fetch. This repository does not ship a collector.

## Review

Published numeric trends accept `human_verified` only. That covers probability distributions, timeline years, quantities, and historical revisions. Volume counts accept `human_verified` and `machine_validated`. A live import cannot set `human_verified`; that state comes from a review decision. See `docs/CURATION.md`. `needs_review` remains visible on the statement and is not verified, and it is not included in those trends. `unreviewed` candidates and `rejected` statements are not public pages. An approval whose source or evidence no longer matches is treated as `needs_review` and stays out of numeric trends.

`trend_definitions.aggregation` is a tagged object. Besides `explicit_numeric_distribution` and `count_by_topic_and_statement_type`, a document may declare `timeline_forecast`, `quantity_forecast`, or `historical_revision`. Older distribution documents stay valid: `conditionality` is optional on that tag. The product also ships a prepared catalog of those families, so an import with `trend_definitions: []` still has methodology pages. A human-verified explicit numeric question that the catalog does not already own is discovered on its own key, unit, and conditionality.
