# Curation

Human review is a separate record from extraction. An extractor may set `unreviewed`, `needs_review`, or `machine_validated`. Only an operator decision with action `approve` sets `human_verified`.

Local curation is off unless `PDOOM_CURATION_MODE=local`. `/curation` and `POST /api/curation/decisions` then return 404. The public statement list does not change when the flag is on. Unreviewed and rejected statements stay off public routes. `needs_review` can appear, and it is not labeled verified.

## Decisions

`review_decisions` is append-only. Each row stores the previous and resulting review state, reviewer, time, note, rejection reason, extractor, source item, evidence, source content hash, evidence hash, content version, the original extraction JSON, and any structured corrections.

`statement_extractions` keeps the machine output. Later corrections update the live statement and do not replace that snapshot.

Candidate identity is the SHA-256 of person slug, source content hash, evidence hash, extractor name, extractor version, statement type, and the forecast claim: question key, horizon, unit, value type, and numeric values. It does not include normalized text. A direct statement and a model signal from the same span are different candidates. Two numeric claims in one passage stay different candidates when the horizon or value differs. The stored key is not rewritten when a reviewer changes the type.

A changed source hash, evidence hash, or content version does not match an old approval. Public pages and trends then treat that statement as `needs_review` until a new decision covers the current material. Restoring the reviewed bytes makes the old approval apply again. A new decision that cites the changed hash is a new review.

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
