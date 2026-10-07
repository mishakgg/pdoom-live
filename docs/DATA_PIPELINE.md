# Data pipeline

The data-collection side of pdoom.live lives in `pipeline/`. It does not render the web product. Shared field names follow `docs/DATA_MODEL.md` and `docs/ARCHITECTURE.md`.

## Layout

- `pipeline/pdoom_pipeline/seed/` — reviewed cohort `2026.09.0`, the `2026.10.0` copy-forward, and JSONL export.
- `pipeline/pdoom_pipeline/enrich/` — name-confirmed pages, ORCID researcher URLs, and rel=me profiles.
- `pipeline/pdoom_pipeline/identity/` — name keys and OpenAlex acceptance rules.
- `pipeline/pdoom_pipeline/collectors/` — RSS/Atom, arXiv, GitHub, OpenAlex works, plus callable ForumMagnum and Bluesky adapters that are not on the recurring runner.
- `pipeline/pdoom_pipeline/ingest/` — idempotent observation store and author-versus-mentioned roles.
- `pipeline/pdoom_pipeline/belief/` — collection priority, question keys, owned essays, podcast guest rules, and view-change candidates.
- `pipeline/pdoom_pipeline/extract/` — deterministic statement boundary. It does not invent probabilities.
- `pipeline/pdoom_pipeline/export/` — seed registry and belief-corpus canonical documents.
- `pipeline/pdoom_pipeline/fetch.py` — scheme, DNS, and address checks; redirect, size, timeout, and decompression limits.
- `data/seed/cohort/v2026-09/` — generated organizations, people, affiliations, identities, sources, and ambiguities for cohort `2026.09.0`.
- `data/seed/cohort/v2026-10/` — cohort `2026.10.0`. It does not replace the historical directory.
- `data/fixtures/` — offline collector fixtures, including hostile source text.
- `packages/contracts/src/` — application enums and the canonical import schema. That schema is the product contract.
- `packages/contracts/source-observation.schema.json` — collector envelope only. It is not the database import document.

## Commands

From the repository root, with the virtualenv that has `pytest` and `defusedxml`:

```bash
PYTHONPATH=pipeline python -m pytest
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.resolve_seed
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.enrich_sources --live
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.collect_beliefs --live
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.refresh --once
```

`refresh --once` is the bounded recurring path. It is documented in `docs/REFRESH.md`. The command refuses to run without `--once`, and no timer is enabled. `collect_beliefs --live` calls the same refresh.

Each selected source in that run ends as new, changed, unchanged, skipped, or failed. The belief ingestion run records `unchanged_count`, `skipped_count`, and `failed_count` beside the new and changed counts. A run that retains progress and also records a failure has status `partial`. A run whose selected sources all fail, with nothing retained, has status `failed`. A partial run and a failed run stay out of the full-success count. The same rule is in `docs/REFRESH.md` and `docs/INGESTION_CONTRACT.md`.

`pytest` does not call the network. `resolve_seed --resolve` queries OpenAlex. `enrich_sources --live` reads ORCID records that are already linked and fetches claimed or ORCID URLs. It does not add people and it does not search social accounts by name. Set `PDOOM_LIVE_TESTS=1` only for an optional live smoke test.

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

The fetcher allows `http` and `https` only. It rejects userinfo, localhost, `.local`, link-local, private, loopback, reserved, and cloud-metadata addresses, including `169.254.169.254` and `metadata.google.internal`. Redirects are rechecked. Responses are capped. Gzip and deflate are decompressed only up to that cap. Retries apply to timeouts, 429, and 5xx responses. The production fetcher sleeps, honors Retry-After up to 60 seconds, and stops at the refresh deadline. A 404 stays `not_found`. HTTP 304 with a cached body is a successful unchanged check.

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
| `sources.jsonl` | OpenAlex works feeds plus verified pages, feeds, and reference-only channels |
| `ambiguities.jsonl` | unresolved identity decisions, not public identities |
| `enrichment.json` | page decisions and collector runs for the latest enrichment |
| `cohort.json` | cohort version metadata |

`data/collections/cohort-v2026-09/source_observations.jsonl` holds `SourceObservation` rows from the RSS and GitHub collectors. `candidate_statements.jsonl` holds unreviewed extractor output. Those files are not a canonical import document.

`packages/contracts/enums.json` records the collector vocabulary used when this pipeline was first written. Application enums live in `packages/contracts/src/enums.ts`. Where they differ, the TypeScript enums win for anything that enters PostgreSQL.

The exporter in `pipeline/pdoom_pipeline/export/canonical.py` applies `packages/contracts/vocabulary-map.json`:

- Organization types `research_lab`, `infrastructure`, `safety_org`, and `independent` are canonical. They are not collapsed.
- `openalex_works` becomes `academic_works`. `personal_website` becomes `personal_site`, `research_paper` becomes `paper`, `youtube` becomes `video`, `github` becomes `repository`, `lab_page` becomes `lab_post`, `x` becomes `social_post`, and an `rss` feed source becomes `blog`. `newsletter` and `podcast` already use the application names. `huggingface` and `other` are unmapped and fail.
- `openalex_api`, `arxiv_api`, and `github_api` become `api`. `rss_feed` becomes `rss`. `reference_only` becomes `manual`. The original method is `collection_adapter`.
- `curator_reviewed` becomes `manual_review`. `openalex_exact_name_and_institution`, `openalex_dominant_profile`, and `openalex_unique_exact_name` become `structured_academic_source`. `openalex_orcid_crosswalk`, `orcid_researcher_url`, `claimed_url_page_name`, and `rel_me` become `cross_link`. The original strategy is `verification_detail`.
- `arxiv_author_metadata`, `feed_author_field`, `github_repo_owner`, `openalex_authorship`, and `name_occurrence_in_body` become `metadata`. `source_author_field` becomes `byline`. The original string is `attribution_detail`.
- Identity and affiliation confidence stays `high` / `medium` / `low`. It is not converted to 0.9 / 0.6 / 0.3. Statement confidence stays numeric.
- `person:{slug}` and `org:{slug}` become the slug only when that prefix is present and matches the slug field. `src:person:{slug}:openalex` becomes `{slug}-openalex`. A fifth id segment, used when one person has two sources of the same kind, is appended after the adapter. Underscores in the adapter become hyphens. `cohort_YYYY_MM` becomes `cohort-YYYY-MM`. Other shapes are rejected.
- `Z` and explicit UTC offsets normalize to the same instant before storage.

Identity rows from OpenAlex are `machine_validated` at high confidence and `needs_review` at medium confidence in the seed files. The application trend rules treat those review states differently. Cohort membership on the roster is curator-reviewed. Do not present medium-confidence roles or ids as settled facts.

Enrichment adds a personal or lab profile only when the fetched page contains the person's full display name. `rel=me` links on that page can add GitHub, Hugging Face, Bluesky, Mastodon, X, or YouTube. An X URL listed on the linked ORCID record is kept only when that page also contains the full name. LinkedIn, Wikipedia, and sitewide feeds such as recent-changes or oEmbed are not registered. Name search is not used. Profiles that fail the name check stay unconfirmed. GitHub metadata and RSS/Atom, including a YouTube channel Atom feed when a channel id is linked, are the collectors used for these new sources. Bluesky, Mastodon, and X rows created by enrichment stay identities with collection disabled.

Cohort `2026.10.0` adds a separate, unwired Bluesky author-feed collector and a ForumMagnum collector. They run only for accounts confirmed from a page or post already linked to the person. The recurring belief job does not call them. Integration steps are in [channel integration](./CHANNEL_INTEGRATION_2026_10.md). `bluesky` maps to canonical source type `social_post`. `forum_magnum_api` and `bluesky_api` map to collection method `api`.

## Failure classes

`not_found`, `temporarily_unavailable`, `rate_limited`, `unauthorized`, `blocked_by_policy`, `parser_unsupported`, `content_too_large`, `invalid_content`, `collector_bug`, `unsafe_url`.

A collector failure is not evidence that the person has made no public statement.

## Operational checks

The cohort quality report under `data/reports/` describes coverage. It is not the freshness check. [Operator observability](./OBSERVABILITY.md) defines collection and extraction signals, service objectives, and alert conditions. Pipeline snapshots can be checked with:

```bash
PYTHONPATH=pipeline python -m pdoom_pipeline.observability check --snapshot snapshot.json
```

That command reports failures. It does not rewrite the observation store.

### Observation identity and provenance revisions

The retained observation store scopes RSS upstream GUIDs by the admitted source
identity. A feed-local GUID such as `1` cannot merge unrelated feeds. Platform-wide
arXiv, GitHub and OpenAlex identifiers keep their existing namespace. Clean legacy
store files are read without changing their content hashes, content versions or
public source-item slugs; recoverable RSS aliases acquire their source scope from
retained observations. Source URL aliases survive save/reload.

A content version may have several independently retained source observations.
Their internal `provenance_observations` history preserves source identity, author
candidates, collector metadata and evidence locators, including start/end
milliseconds. An author or locator correction appends a provenance revision even
when the content digest is unchanged. Exact replay reuses its revision. The
content digest and public `content_version` retain their existing meaning; these
internal provenance revisions do not manufacture a new content hash, author
identity, confidence level or public historical source-item row.

The top-level fields of a retained version project its selected provenance
observation for the existing exporter. Admission revocation removes observations
for that source while keeping independently admitted co-observations. Evidence
permission changes scrub every retained provenance revision for that source, not
only the selected projection. Previously published database records still need
the separate reviewed revocation workflow described in `REFRESH.md`.

Public approval is separate: changing a projected author, participant or evidence
locator must be evaluated by the accepted-claim coverage gate, with unmatched
provenance downgraded for review. A byte hash match alone is not approval. This
store change preserves an internal provenance history; it does not implement
immutable public provenance-revision history or repair already published records.

A legacy RSS record containing different-source observations under different
canonical URLs may already have been merged by an unscoped GUID. Loading such a
record fails with `legacy RSS identity reconciliation required`, its logical-key
SHA-256 prefix and safe source identifiers. The saved file is not rewritten.
Keep that file and any matching database/export backup for operator review; do
not delete state and reingest as version 1. Reconcile the source items and any
published references explicitly before retrying. Legitimate co-observations with
the same canonical URL still load normally. No automatic public repair is made.

Successful migration writes internal observation-store schema `1.1.0`, marking
that RSS upstream identity is scoped. The legacy connectivity check runs only
while loading schema `1.0.0` (or its historical missing-version equivalent).
After a validated URL move, revoking the original source can legitimately remove
the only retained observation of the original logical URL; a scoped store keeps
that stable logical/public identity on subsequent reloads. Unknown future store
schemas require explicit migration rather than being silently interpreted.
