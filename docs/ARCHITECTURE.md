# Architecture

## Design goal

Build the simplest architecture that preserves provenance, replayability, source safety, and future scale.

The MVP does not need a large microservice fleet.

## Suggested repository shape

The implementation may evolve, but prefer an understandable layout such as:

```
apps/
  web/                 # TypeScript product UI and application API
packages/
  contracts/           # shared schemas/types/enums
  db/                  # SQL schema/migrations/query helpers
pipeline/
  collectors/          # source-specific discovery/fetch adapters
  normalize/           # canonical source/content normalization
  extract/             # claim/forecast extraction
  quality/             # validation/review/scoring utilities
  jobs/                # idempotent runnable jobs
data/
  fixtures/            # deterministic test fixtures, no secret/private data
docs/
```

Python is appropriate for ingestion/research jobs; TypeScript is preferred for the product/web layer. Do not force a language boundary where it adds no value.

## Logical flow

```
researcher registry
      ↓
verified identities + source registry
      ↓
source discovery / fetch
      ↓
raw observation metadata
      ↓
normalized content
      ↓
deduplication / versioning
      ↓
person attribution
      ↓
candidate statement extraction
      ↓
forecast normalization
      ↓
quality gates / review state
      ↓
canonical database
      ↓
application query API
      ↓
people / topics / trends / search UI
```

## Storage

Use PostgreSQL as the canonical relational store.

Early tables should support the entities in `DATA_MODEL.md`. Keep large source bodies or transcripts out of hot query rows. If full permitted source text is retained, use a separate content/blob abstraction so database queries do not repeatedly move large text.

Do not add a vector database by default. Start with indexed relational search/full-text search and add embeddings only when a demonstrated retrieval use case requires them.

## Raw, normalized, extracted

Keep three concepts distinct.

### Raw observation

What the collector observed from a source at a specific time:

- fetch metadata;
- upstream IDs;
- headers/status where useful;
- content hash;
- raw metadata/body reference when retention is permitted.

### Normalized content

A source-independent representation:

- canonical URL;
- title;
- authors/speakers;
- timestamps;
- text/transcript segments;
- media timestamps;
- language;
- source type.

### Extracted assertions

Structured interpretations:

- statement;
- forecast;
- topic labels;
- numerical value/range;
- units;
- horizon;
- definition;
- evidence span;
- model/extractor version;
- confidence/review state.

This separation allows re-running extraction without re-fetching every source.

## Source adapter contract

Collectors should emit a normalized envelope rather than write arbitrary rows.

Conceptually:

```text
SourceObservation
  source_identity
  upstream_id
  canonical_url
  observed_at
  published_at?
  author_candidates[]
  title?
  content_reference
  segments[]
  metadata
  content_hash
```

Adapters should be independently testable with fixtures.

## Idempotency

Every stage should be safe to retry.

Prefer stable uniqueness using combinations such as:

- platform + upstream ID;
- canonical URL;
- content hash/version;
- person + external identity namespace + external ID.

Re-fetching identical content should not create duplicate public statements.

When content changes, preserve versions instead of silently overwriting evidence already referenced by a published statement.

## Jobs

Start with a small job abstraction that supports:

- job type;
- deterministic/idempotency key;
- bounded retries;
- timeout;
- created/started/completed timestamps;
- error class;
- checkpoint or cursor where needed.

A database-backed job table or similarly simple queue is acceptable for MVP. Do not introduce Kafka or equivalent without demonstrated need.

## Application API

The versioned public read API is `/api/v1`, documented in `docs/PUBLIC_API.md`. It is a separate representation from the canonical import. Unversioned `/api/*` routes are application queries and are not a stability promise.

The query API should support cursor-based pagination and stable filters for:

- people;
- organizations;
- topics;
- statements;
- forecasts;
- sources;
- date range;
- statement type;
- review state.

Do not expose raw internal extraction prompts, secrets, or unreviewed data by accident.

## Trend computation

No trend should exist without a versioned methodology. The public families and exclusion rules are in [Trend methodology](./TREND_METHODOLOGY.md).

A trend response identifies:

- metric/method version;
- source: published definition, prepared method, or discovered question;
- cohort definition and size;
- question key, question text, and definition;
- contributing people and statements;
- missing cohort members;
- density (`empty`, `sparse`, `comparable`, `individual`, or `unlinked`);
- exclusions, each with a human-readable reason;
- calculation inputs that a reader can recompute from canonical rows.

`question_key` is the comparability boundary. Probability distributions, predicted years, quantities, and one-person revisions are separate methods. There is no master score.

Prefer computing these aggregates directly from canonical records. Materialize expensive aggregates only when needed.

## Search

Public discovery stays in PostgreSQL. There is no external search service, vector index, or embedding score.

`/search` and `/api/search` query people, organizations (including public affiliation roles), statements, topics, sources, and source-item titles. They do not read unpublished source bodies, evidence text, metadata JSON, rights notes, verification details, pipeline candidate files, or ambiguity queues.

Statement hits use the same public review rule as statement lists (`isPublicReviewState` in `packages/contracts/src/review.ts`): `rejected` and `unreviewed` are omitted; `needs_review` stays visible and is not verified; `machine_validated` stays labeled. A `human_verified` approval whose source or evidence no longer matches is searched as `needs_review`. Name ties use byte order so similar surnames stay in a stable display-name order. Ranking is a fixed tier, then recency or name:

- exact statement text, then a contiguous phrase, then every query word in the statement;
- exact name, surname, name prefix, word prefix, then every word in the name or short bio;
- affiliation role is a lower tier and never a judgment of the person.

Recency breaks ties. It does not outrank a stronger match. People are not ordered by statement count, employer, or cohort. Token lists are capped, SQL is parameterized, and each search runs under a statement timeout. Expected orders for the synthetic fixture live in `data/fixtures/search/expected-ranking.json`.

Later, semantic retrieval can be added for exploratory question answering, but it must return evidence-backed records rather than free-floating generated claims.

## Security boundaries

Collectors process hostile public input.

Fetcher requirements:

- URL allow/deny validation;
- no loopback/link-local/private/cloud-metadata access;
- bounded redirects;
- bounded body size;
- request timeout;
- content-type checks;
- decompression limits;
- parser resource limits.

Extraction requirements:

- source text is untrusted data;
- source text cannot authorize tools or modify system behavior;
- do not pass credentials to models;
- structured output validation;
- bounded input/output sizes.

UI requirements:

- sanitize rendered rich text;
- safe external-link behavior;
- no arbitrary source HTML execution.

## Observability

A healthy HTTP response is not evidence that the dataset is still being refreshed. The operator guide is [docs/OBSERVABILITY.md](./OBSERVABILITY.md).

`packages/observability` holds the shared metric names, label allowlists, guardrails, and freshness objectives. The web process records bounded API and database counters, writes structured logs for important failures, and assigns request correlation ids. `GET /api/health` is the readiness report, the same check as `GET /api/ready`: the process is live, the database answers, and migrations are current. `GET /api/status` says whether the served dataset is current, aging, or stale. `GET /api/metrics` stays disabled unless a deployment explicitly enables it, and it is not a public debugging feed.

`npm run quality:check` reads the current database, or a canonical file, and reports integrity, collection, extraction, and relative size problems. It does not repair them. The same rules run in `pipeline/pdoom_pipeline/observability` for pipeline snapshots. Synthetic fixtures are not treated as a live collection outage.

There is no tracing vendor and no metric series per person, URL, source item, or statement.

## Deployment

Local development stays a Node process plus PostgreSQL. It does not require Docker.

The production runtime is the Next.js web process and PostgreSQL. Migrations and canonical dataset import are separate operator commands. The web process does not migrate, import, seed, or reset on startup. There is no Redis, queue, crawler scheduler, or vector database in the runtime image.

Run the production image from [`docs/PRODUCTION.md`](./PRODUCTION.md). Ingestion remains an operator job outside the web container.
