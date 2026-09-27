# Ingestion contract

The product imports one canonical JSON document. The data-collection pipeline should emit this document rather than writing SQL itself.

Schema: `packages/contracts/schema/canonical-import.schema.json`  
TypeScript source: `packages/contracts/src/schemas.ts`  
Fixture example: `data/fixtures/synthetic/dataset.json`

Schema version `1.0.0` requires `schema_version`, `dataset_id`, `dataset_kind` (`synthetic` or `live`), `generated_at`, and `notice`. `producer` is optional. A live dataset must not set a synthetic flag and must not use `synthetic_fixture` or `collection_method: fixture`.

Identity and affiliation confidence is `high`, `medium`, `low`, or `unknown`. Those words are not probabilities. Numeric `confidence` remains only on statements, forecasts, topics, and relationships, where it is an extraction score.

`content_hash` may be a precomputed SHA-256. `content_hash_input` is optional and is hashed then discarded. A live item does not need its full body.

Operator commands, with `DATABASE_URL` set for the write commands:

- `npm run db:validate -- data/fixtures/synthetic/dataset.json` parses and checks the file. It does not write.
- `npm run db:import -- <file>` validates, applies pending migrations, then upserts in one transaction. Rows absent from the file are kept.
- `npm run db:status` prints the current dataset, cohort, counts, and coverage.

Canonical values are product semantics. Collector strings such as `openalex_api` map to `api`, and the original string is stored as `collection_adapter` or `verification_detail`. The map is `packages/contracts/vocabulary-map.json`. Unmapped strings fail. `SourceObservation` is still the collector envelope and is not this document.

## Identity

Cross-references use slugs, not database UUIDs. The importer assigns stable UUIDs from those natural keys and upserts:

- organization, person, source, topic, source item, evidence, statement: `slug`
- external identity: `namespace` + `external_id`
- source item version: `source` + `logical_key` + content hash
- forecast: one row per statement
- cohort: `slug` + `version`

Re-importing the same document does not create duplicate statements. A changed `content_hash_input` is a new source-item version; the unpublished body is hashed and discarded.

## Statement classes

`statement_type` is one of:

- `explicit_numeric`
- `explicit_qualitative`
- `model_inferred_signal`

Numeric fields are allowed only on `explicit_numeric` forecasts. `value_text` such as `12%` must match `value_numeric` on the 0–1 scale. Qualitative words do not parse.

`question_key` is the comparability key. Trends include a forecast only when that key, unit, horizon, value type, review state, and topic all match the method. Extinction, catastrophic harm, disempowerment, and AGI arrival must use different keys.

## Source text

`content_hash_input` and evidence `text` are untrusted data. The app stores the hash, a content reference, and a short evidence excerpt. It does not execute source text.

Canonical URLs must be `http` or `https`, without embedded credentials, and must not target loopback, private, link-local, or cloud-metadata hosts. Collectors still need to resolve DNS and re-check redirects before any fetch. This repository does not ship a collector.

## Review

Published numeric distributions accept `human_verified` only. Volume counts accept `human_verified` and `machine_validated`. A live import cannot set `human_verified`; that state comes from a review decision. See `docs/CURATION.md`. `needs_review` can appear on public statement pages and is not verified. `unreviewed` and `rejected` are not public.
