# Curation

Human review is a separate record from extraction. An extractor may set `unreviewed`, `needs_review`, or `machine_validated`. Only an operator decision with action `approve` sets `human_verified`.

Local curation is available only when `PDOOM_CURATION_MODE=local`. Otherwise `/curation` and `POST /api/curation/decisions` return 404. The queue and item pages check that flag before reading the database, so a disabled response does not include review records. Production configuration rejects `PDOOM_CURATION_MODE`. The public statement list does not change when the flag is on. Unreviewed and rejected statements stay off public routes. `needs_review` can appear, and it is not labeled verified.

## Decisions

`review_decisions` is append-only. Each row stores the previous and resulting review state, reviewer, time, note, rejection reason, extractor, source item, evidence, source content hash, evidence hash, content version, the original extraction JSON, a structured correction delta, and separate machine-input and accepted-claim snapshots.

`statement_extractions` keeps the machine output. Later corrections update the live statement and do not replace that snapshot.

Candidate identity version is `1`. The digest is the unprefixed SHA-256 of person slug, source content hash, evidence hash, extractor name, extractor version, statement type, and the forecast claim: question key, horizon, unit, value type, and numeric values. It does not include normalized text. Empty forecast fields do not change the key. A direct statement and a model signal from the same span are different candidates. Two numeric claims in one passage stay different candidates when the question, horizon, or value differs. The stored key is not rewritten when a reviewer changes the type. Canonical import derives the extractor name from the text before the first `/` in `extractor_version`; a version written as `rule-extract/0.4.0` therefore uses the name `rule-extract`.

`review:stage` keeps the statement `unreviewed`. An extractor recommendation such as `needs_review` is stored on the source item and is not a human verification. The staged source is `unreviewed` as well, so it does not enter public source lists. A missing content hash is rejected rather than invented. Podcast appearances stay podcast sources and are not given a person owner. Participant role `host` is stored for transcript labels. The canonical import enum in schema 1.0.0 does not include `host`; staging writes that role after migration `005_participant_host_role`.

Website source enumeration, including person source lists and collection coverage, requires the source's own public review state (`needs_review`, `machine_validated`, or `human_verified`). An exact unreviewed source page can become an audit target when one of its statements independently becomes public. It shows only the source locator and items supporting public statements, without staged ownership, collection details, or rights notes. This exception does not promote the source or put it into public lists, indexing, or research exports.

Source items have no separate review state. An item is visible only when it supports a public statement. Its evidence is limited to segments linked to public statements, and person attribution is limited to those statements' speakers. Raw item metadata and attribution notes are not published. Older versions and removed or unavailable originals remain audit targets under this rule. An explicit source rejection overrides statement visibility and hides its content; removal or collection failure does not mean review rejection. Statement relationships require a public relationship state and two public endpoints; attached forecasts require their own public state. Identity and affiliation details and affiliation filters use the website review gate as well.

A public statement's referenced evidence segment must belong to its declared source item. The database's independent foreign keys and canonical import do not establish this invariant. Mismatched rows stay stored for internal review but are excluded from website/API reads, counts, search/discovery, trend inputs, and research exports, even if both items are otherwise public. Public provenance currently has a single item locator/content hash and cannot correctly represent foreign-item evidence. This check does not exclude same-item historical or removed-source evidence.

Public trend inputs exclude unreviewed/rejected statements and omit independently nonpublic forecast fields before computation. This includes ranges, distributions, definitions, horizons, and resolution metadata: excluded-record tables and unpooled inspection views must not become another route to hidden content. Website `needs_review` records remain visible but unsettled. Research computations use the stricter forecast gate; any internal needs-review candidate used to count omissions has no forecast fields and is removed from named public output. Review eligibility and aggregate methods are unchanged. Source-item search person filters require a public statement's speaker attribution, or ownership recorded on a public source container; hidden participants and staged ownership cannot select an item.

Approval coverage uses `statement_claim_v1`, a versioned JSON representation separate from candidate identity. It includes person slug; source item slug, URL, hash and version; extractor name/version; statement type, normalized claim and event time; evidence source, kind, text, hash, context and character/media locators; sorted topic slugs; and the full forecast interpretation (kind, question key/text, definition, condition, target dates, horizon, value shape/numbers/distribution, unit and resolution criteria). It excludes confidence, ingestion/extraction run IDs, evidence ordering and review state. JSON equality normalizes numeric formatting and object-key order; timestamps are UTC and absent fields are explicit nulls.

Each new decision stores `machine_claim_json` and the full resulting `accepted_claim_json`, both version 1. Later decisions on that accepted claim retain the same machine input even when their correction delta is empty. Canonical import reapplies the complete accepted snapshot only when the incoming interpretation equals that machine input or the accepted claim. This permits replay of a corrected evidence span. Changed person, extractor, type, wording or forecast semantics require review even over identical evidence bytes. Public approval requires the live claim to equal the latest accepted snapshot. The stored `human_verified` state may remain for audit while its effective state is `needs_review`.

Migration `006_accepted_claims` adds nullable snapshots without rewriting existing audit or extraction rows. Legacy decisions cannot be safely backfilled from mutable live rows because their audit format omitted some semantics. Their verified labels deliberately become `needs_review` until an explicit new operator approval. Cumulative legacy correction deltas remain replayable for a matching candidate and source/evidence version, but do not confer verification. Reapproval records the interpretation actually reviewed; a legacy machine input that cannot be reconstructed exactly must be reviewed again if subsequently reimported.

Operator relationships use method `curator_review`. Machine suggestions use their own method and stay `unreviewed` unless an operator decision names that same pair and type.

Rejection reasons are `wrong_speaker`, `wrong_source_attribution`, `not_a_forecast`, `extraction_error`, `duplicate`, `insufficient_evidence`, `definition_ambiguous`, `numerical_interpretation_incorrect`, `source_unavailable`, and `other`.

Explicit numeric approval requires the operator to confirm person, evidence, value, units, definition, conditionality, horizon, and question key. The question key must be one of the keys in `QUESTION_TAXONOMY`. The evidence text must contain the number. A qualitative statement cannot receive a probability in this workflow.

## Files

Review manifests use schema `review-decisions/1.0.0`:

```json
{ "schema_version": "review-decisions/1.0.0", "decisions": [] }
```

Store them under `data/reviews/`. They contain operator identifiers and decision text, not credentials.

Commands:

- `npm run review:status`
- `npm run review:validate -- <file>` reads the database and does not write decisions
- `npm run review:import -- <file>`
- `npm run review:export -- <file>`
- `npm run review:stage -- <candidate-jsonl>` inserts `unreviewed` statements for people already in the dataset

Re-importing the same decision key is a no-op. A reused key with different corrections is a conflict. Decisions are exported and applied in `reviewed_at` order, then `decision_key`. Applying that sequence to the extracted statements reconstructs the reviewed dataset.

The queue orders explicit numeric records, then explicit qualitative records, then possible same-question view changes, then other high-confidence records, and model-inferred signals last. That order is not a score of the people.
