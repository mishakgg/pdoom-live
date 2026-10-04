# Curation

Human review is a separate record from extraction. An extractor may set `unreviewed`, `needs_review`, or `machine_validated`. Only an operator decision with action `approve` sets `human_verified`.

Local curation is available only when `PDOOM_CURATION_MODE=local`. Otherwise `/curation` and `POST /api/curation/decisions` return 404. The queue and item pages check that flag before reading the database, so a disabled response does not include review records. Production configuration rejects `PDOOM_CURATION_MODE`. The public statement list does not change when the flag is on. Unreviewed and rejected statements stay off public routes. `needs_review` can appear, and it is not labeled verified.

## Decisions

`review_decisions` is append-only. Each row stores the previous and resulting review state, reviewer, time, note, rejection reason, extractor, source item, evidence, source content hash, evidence hash, content version, the original extraction JSON, and any structured corrections.

`statement_extractions` keeps the machine output. Later corrections update the live statement and do not replace that snapshot.

Candidate identity version is `1`. The digest is the unprefixed SHA-256 of person slug, source content hash, evidence hash, extractor name, extractor version, statement type, and the forecast claim: question key, horizon, unit, value type, and numeric values. It does not include normalized text. Empty forecast fields do not change the key. A direct statement and a model signal from the same span are different candidates. Two numeric claims in one passage stay different candidates when the question, horizon, or value differs. The stored key is not rewritten when a reviewer changes the type. Canonical import derives the extractor name from the text before the first `/` in `extractor_version`; a version written as `rule-extract/0.4.0` therefore uses the name `rule-extract`.

`review:stage` keeps the statement `unreviewed`. An extractor recommendation such as `needs_review` is stored on the source item and is not a human verification. The staged source is `unreviewed` as well, so it does not enter public source lists. A missing content hash is rejected rather than invented. Podcast appearances stay podcast sources and are not given a person owner. Participant role `host` is stored for transcript labels. The canonical import enum in schema 1.0.0 does not include `host`; staging writes that role after migration `005_participant_host_role`.

Re-importing a canonical document rewrites machine review columns. When the latest decision's source hash and content version still match, and the evidence is either the accepted span or the original machine span, that decision is applied again, including corrections. Changed evidence matches neither hash, so it does not inherit the old approval. A `human_verified` row whose decision no longer covers the bytes is treated as `needs_review` on public pages. Operator relationships use method `curator_review`. Machine suggestions use their own method and stay `unreviewed` unless an operator decision names that same pair and type.

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
