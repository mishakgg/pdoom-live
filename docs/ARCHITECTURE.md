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

MVP:

- exact/person/org/topic filtering;
- PostgreSQL full-text search where useful;
- date and source filtering.

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

At minimum capture:

- collector/source success/failure counts;
- fetch latency;
- duplicate rate;
- new/changed content counts;
- extraction success/failure;
- validation rejection reasons;
- queue/job latency;
- API latency/error rate;
- freshness by source/cohort.

Metrics should help identify silent dataset staleness.

## Deployment

Keep local development one-command where practical.

The initial deployment should be reproducible with:

- environment-variable configuration;
- PostgreSQL;
- web process;
- worker/ingestion process.

Use containers only where they simplify reproducibility; do not make local development depend on unnecessary infrastructure.
