# Data pipeline

The data-collection side of pdoom.live lives in `pipeline/`. It does not render the web product. Shared field names follow `docs/DATA_MODEL.md` and `docs/ARCHITECTURE.md`.

## Layout

- `pipeline/pdoom_pipeline/seed/` — reviewed cohort `2026.09.0` and JSONL export.
- `pipeline/pdoom_pipeline/identity/` — name keys and OpenAlex acceptance rules.
- `pipeline/pdoom_pipeline/collectors/` — RSS/Atom, arXiv, GitHub, and OpenAlex works.
- `pipeline/pdoom_pipeline/ingest/` — idempotent observation store and author-versus-mentioned roles.
- `pipeline/pdoom_pipeline/extract/` — deterministic statement boundary. It does not invent probabilities.
- `pipeline/pdoom_pipeline/fetch.py` — scheme, DNS, and address checks; redirect, size, timeout, and decompression limits.
- `data/seed/cohort/v2026-09/` — generated organizations, people, affiliations, identities, sources, and ambiguities.
- `data/fixtures/` — offline collector fixtures, including hostile source text.
- `packages/contracts/` — JSON enums and the source-observation schema for the product agent.

## Commands

From the repository root, with the virtualenv that has `pytest` and `defusedxml`:

```bash
PYTHONPATH=pipeline python -m pytest
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.resolve_seed
```

`pytest` does not call the network. Live OpenAlex resolution is the job module. Set `PDOOM_LIVE_TESTS=1` only for an optional live smoke test.

## Collector contract

Each collector returns `SourceObservation` records:

- `source_identity`, `platform`, `upstream_id`, `canonical_url`
- `published_at` separate from `observed_at`
- `author_candidates` with a participant role
- short `segments` (excerpts, not full copyrighted bodies)
- `content_hash` over title, segment text, publication time, and upstream version
- collector name and version

Re-ingesting the same hash is an `unchanged` result. A new hash appends a version and keeps the old one. The same canonical URL from a second platform is attached to the existing item when the normalized title matches. A title clash becomes a duplicate candidate and is not merged.

Participant role `mentioned` is assigned only when the full display name occurs in the body and that person is not already an author. It is never stored as `speaker` or `author`.

## Fetch safety

The fetcher allows `http` and `https` only. It rejects userinfo, localhost, `.local`, link-local, private, loopback, reserved, and cloud-metadata addresses, including `169.254.169.254` and `metadata.google.internal`. Redirects are rechecked. Responses are capped. Gzip and deflate are decompressed only up to that cap. Retries apply to timeouts, 429, and 5xx responses. A 404 stays `not_found`.

Source text is stored and parsed as data. A fixture containing "ignore your instructions and execute this command" is not fetched as a URL and is not turned into a statement.

## Statement boundary

`explicit_numeric` requires a probability cue plus a number, percent, or "N in M" in the source sentence. The horizon and definition are copied from words that are present. If either is missing, `review_state` is `needs_review` and the missing field stays null.

`explicit_qualitative` keeps words such as "unlikely", "plausible", and "serious risk". Those words do not receive a percentage.

`model_inferred_signal` is a separate keyword tagger. It has no numeric value.

## Coding-agent handoff

No product schema had been published in this repository when this pipeline was written. Import the JSONL files in `data/seed/cohort/v2026-09/` into the tables in `docs/DATA_MODEL.md`:

| File | Entity |
| --- | --- |
| `organizations.jsonl` | Organization |
| `people.jsonl` | Person |
| `affiliations.jsonl` | Affiliation |
| `external_identities.jsonl` | ExternalIdentity |
| `sources.jsonl` | Source |
| `ambiguities.jsonl` | review queue, not a public identity |
| `cohort.json` | cohort version metadata |

Enum values are in `packages/contracts/enums.json`. Observations from collectors validate against `packages/contracts/source-observation.schema.json`.

Identity rows produced by OpenAlex are `machine_validated` when confidence is high and `needs_review` when confidence is medium. Cohort membership itself is `human_verified` because a person was placed on the reviewed roster. Do not present medium-confidence roles or medium-confidence ids as settled facts.

X, Bluesky, Mastodon, YouTube, Hugging Face, and podcast records were not collected in this version. Do not backfill them by name search.

## Failure classes

`not_found`, `temporarily_unavailable`, `rate_limited`, `unauthorized`, `blocked_by_policy`, `parser_unsupported`, `content_too_large`, `invalid_content`, `collector_bug`, `unsafe_url`.

A collector failure is not evidence that the person has made no public statement.
