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

The product imports one JSON document described in `docs/INGESTION_CONTRACT.md` and `packages/contracts/schema/canonical-import.schema.json`. Cross-references are slugs. The importer assigns UUIDs. `dataset_kind` is `synthetic` or `live`. A live export must not claim to be synthetic.

Flow: collector `SourceObservation` → normalized seed registry → `pdoom_pipeline.export.canonical.export_seed` → application `validateDocument` / `importCanonical`. The web app does not read OpenAlex field names. Adapter names survive as `collection_adapter`, `verification_detail`, or `attribution_detail`.

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

The exporter in `pipeline/pdoom_pipeline/export/canonical.py` applies `packages/contracts/vocabulary-map.json`:

- Organization types `research_lab`, `infrastructure`, `safety_org`, and `independent` are canonical. They are not collapsed.
- `openalex_works` becomes `academic_works`. `personal_website` becomes `personal_site`, `research_paper` becomes `paper`, `youtube` becomes `video`, `github` becomes `repository`, `lab_page` becomes `lab_post`. `huggingface`, collector `rss`, and `other` are unmapped and fail.
- `openalex_api`, `arxiv_api`, and `github_api` become `api`. `rss_feed` becomes `rss`. The original method is `collection_adapter`.
- `curator_reviewed` becomes `manual_review`. `openalex_exact_name_and_institution`, `openalex_dominant_profile`, and `openalex_unique_exact_name` become `structured_academic_source`. `openalex_orcid_crosswalk` becomes `cross_link`. The original strategy is `verification_detail`.
- `arxiv_author_metadata`, `feed_author_field`, `github_repo_owner`, `openalex_authorship`, and `name_occurrence_in_body` become `metadata`. `source_author_field` becomes `byline`. The original string is `attribution_detail`.
- Identity and affiliation confidence stays `high` / `medium` / `low`. It is not converted to 0.9 / 0.6 / 0.3. Statement confidence stays numeric.
- `person:{slug}` and `org:{slug}` become the slug only when that prefix is present and matches the slug field. `src:person:{slug}:openalex` becomes `{slug}-openalex`. `cohort_YYYY_MM` becomes `cohort-YYYY-MM`. Other shapes are rejected.
- `Z` and explicit UTC offsets normalize to the same instant before storage.

Identity rows from OpenAlex are `machine_validated` at high confidence and `needs_review` at medium confidence in the seed files. The application trend rules treat those review states differently. Cohort membership on the roster is curator-reviewed. Do not present medium-confidence roles or ids as settled facts.

X, Bluesky, Mastodon, YouTube, Hugging Face, and podcast records were not collected in this version. Do not backfill them by name search.

## Failure classes

`not_found`, `temporarily_unavailable`, `rate_limited`, `unauthorized`, `blocked_by_policy`, `parser_unsupported`, `content_too_large`, `invalid_content`, `collector_bug`, `unsafe_url`.

A collector failure is not evidence that the person has made no public statement.
