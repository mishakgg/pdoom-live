# Ingestion contract

The product imports one canonical JSON document. The data-collection pipeline should emit this document rather than writing SQL itself.

Schema: `packages/contracts/schema/canonical-import.schema.json`  
TypeScript source: `packages/contracts/src/schemas.ts`  
Fixture example: `data/fixtures/synthetic/dataset.json`

`dataset.synthetic` must be `true` for the fixture loader. A future live import can extend the schema version; do not invent probabilities for qualitative text.

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

Published numeric distributions in this slice accept `human_verified` only. Volume counts accept `human_verified` and `machine_validated`. `needs_review` remains visible on the statement, not in those trends.
