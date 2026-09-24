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
- `packages/contracts/src/` — application enums and the canonical import schema. That schema is the product contract.
- `packages/contracts/source-observation.schema.json` — collector envelope only. It is not the database import document.

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

## Application contract

The product imports one JSON document described in `docs/INGESTION_CONTRACT.md` and `packages/contracts/schema/canonical-import.schema.json`. Cross-references are slugs. The importer assigns UUIDs. `dataset.synthetic` is fixed to `true` for the fixture loader. The live seed is not that document and must not be marked synthetic to pass the fixture schema.

`SourceObservation` remains the collector output. It is normalized content before a canonical source item exists. A later mapper can turn observations into source items. This repository does not do that mapping yet.

Seed JSONL is the reviewed registry:

| File | Role |
| --- | --- |
| `organizations.jsonl` | organization registry, not yet a canonical import row |
| `people.jsonl` | person registry |
| `affiliations.jsonl` | affiliation registry |
| `external_identities.jsonl` | OpenAlex and ORCID claims with resolver provenance |
| `sources.jsonl` | collectible OpenAlex works feeds |
| `ambiguities.jsonl` | unresolved identity decisions, not public identities |
| `cohort.json` | cohort version metadata |

`packages/contracts/enums.json` records the collector vocabulary used when this pipeline was first written. Application enums live in `packages/contracts/src/enums.ts`. Where they differ, the TypeScript enums win for anything that enters PostgreSQL.

Known gaps, left for a later import rather than forced through the fixture schema:

- Organization types `research_lab`, `infrastructure`, `safety_org`, and `independent` are not in the application enum (`research_institute`, `company`, and the other listed types).
- Source type `openalex_works` is not an application source type. Closest later mapping is `paper` plus `collection_method: api`.
- Collection methods `openalex_api`, `arxiv_api`, `github_api`, and `rss_feed` are finer than `api` and `rss`.
- Verification methods such as `openalex_exact_name_and_institution` and `curator_reviewed` are not in the application enum. Provenance for those strings has to be kept beside a mapped method such as `cross_link` or `manual_review`.
- Attribution methods on observations (`arxiv_author_metadata`, `feed_author_field`, and others) are not the application attribution enum.
- Confidence on identities is `high` / `medium` / `low`. The application field is a number from 0 to 1.
- Seed ids look like `person:{slug}`. The application uses the slug alone.
- Application `externalIdentity.verified_at` is an offset timestamp. Resolver times use a `Z` suffix.
- Participant roles, statement classes, and the current inclusion notes fit the application names and the 600-character bio cap. That does not make the surrounding rows importable.

Identity rows from OpenAlex are `machine_validated` at high confidence and `needs_review` at medium confidence in the seed files. The application trend rules treat those review states differently. Cohort membership on the roster is curator-reviewed. Do not present medium-confidence roles or ids as settled facts.

X, Bluesky, Mastodon, YouTube, Hugging Face, and podcast records were not collected in this version. Do not backfill them by name search.

## Failure classes

`not_found`, `temporarily_unavailable`, `rate_limited`, `unauthorized`, `blocked_by_policy`, `parser_unsupported`, `content_too_large`, `invalid_content`, `collector_bug`, `unsafe_url`.

A collector failure is not evidence that the person has made no public statement.
