# Coding agent — initial implementation prompt

Work on `mishakgg/pdoom-live` from the current `main`.

Read `README.md`, `AGENTS.md`, and every file under `docs/` before editing. Treat those documents as the current product/data contract. Inspect current branches/PRs first so you do not duplicate or overwrite concurrent work.

## Goal

Build a **testing-ready first product vertical slice** of pdoom.live without depending on live third-party data.

The result should let another developer run the app locally, load deterministic fixture data representing people/sources/statements/forecasts, and exercise the core public experience end to end.

Do not build a crawler in this task. The separate data-collection agent owns live source discovery and ingestion.

## Required implementation

### 1. Application foundation

Create a clean TypeScript web application suitable for a public data product. Prefer a current stable Next.js App Router setup unless the repository already contains another coherent implementation by the time you start.

Keep the stack small. Do not add a large UI framework or unnecessary infrastructure.

Provide:

- reproducible install/run commands;
- linting;
- type checking;
- unit/integration tests;
- environment validation;
- clear local development documentation.

### 2. Canonical PostgreSQL schema

Implement migrations for the core entities in `docs/DATA_MODEL.md`, focusing on the MVP query path:

- Person
- Organization
- Affiliation
- ExternalIdentity
- Source
- SourceItem
- SourceParticipant
- EvidenceSegment
- Topic
- Statement
- Forecast
- StatementTopic
- statement revision/relationship
- ingestion/extraction run metadata sufficient for provenance

Use conservative constraints and indexes. Preserve UTC timestamps and source publication time separately from observation time.

Do not invent numerical values for qualitative statements.

### 3. Stable shared contracts

Create typed contracts/enums for:

- statement type;
- review state;
- source type;
- participant role;
- forecast value type;
- provenance/evidence references;
- paginated API responses.

Structure them so a Python ingestion pipeline can interoperate without copying ambiguous definitions. A small generated JSON Schema/OpenAPI boundary is welcome if it stays simple and testable.

### 4. Deterministic fixture dataset

Add a clearly synthetic fixture dataset with:

- multiple people and organizations;
- multiple source types;
- explicit numeric forecasts;
- qualitative views;
- machine-inferred signals;
- at least one revision/change-over-time example;
- comparable and deliberately non-comparable p(doom)-style questions;
- source evidence with text and/or timestamp references.

Mark fixtures as synthetic. Do not use fabricated quotes attributed to real people.

Provide a repeatable seed/reset command for development and tests.

### 5. Public product surfaces

Build a coherent responsive UI with at least:

- home/activity page;
- people index;
- person detail/timeline;
- topics index;
- topic detail;
- statement/forecast detail page;
- source/evidence display;
- methodology/about page based on repository docs.

The UI must visibly distinguish:

- explicit numeric;
- explicit qualitative;
- model-inferred.

For any aggregate or chart, show sample size and enough methodology/coverage context that it cannot be mistaken for universal consensus.

Do not make the homepage a sensational unsupported “doom meter.”

### 6. Query/API layer

Implement stable read APIs/query helpers supporting:

- cursor pagination;
- person/topic/source filters;
- date ranges;
- statement type;
- review state;
- sort by publication/event time;
- source/evidence drill-down.

Reject invalid cursors/filters cleanly.

Avoid shipping full large source bodies in list responses.

### 7. First transparent trend

Implement one or two simple trends using only deterministic fixtures, such as:

- distribution of genuinely comparable explicit numeric estimates;
- count of new statements by topic/type over time.

The calculation must follow the roadmap:

- versioned methodology;
- declared cohort/topic;
- contributing person/statement counts;
- deterministic tests;
- exclusion of non-comparable definitions.

Do not create an opaque composite “AI sentiment” or inferred p(doom) score.

### 8. Security and robustness

Implement/test relevant safeguards:

- no raw source HTML execution;
- safe external links;
- server-only secrets;
- parameterized DB access;
- input validation;
- pagination bounds;
- hostile text fixture proving source content is rendered as data and cannot become executable instructions.

If you add any URL-fetching helper despite this task not requiring live collection, it must include SSRF protections described in `AGENTS.md`.

### 9. Testing

At minimum cover:

- migrations/schema constraints;
- fixture import idempotency;
- explicit numeric vs qualitative vs inferred boundaries;
- provenance round trip;
- non-comparable forecast exclusion;
- API filtering/pagination;
- basic route/component rendering;
- one hostile-source-content case.

Do not make ordinary tests depend on the network.

## UI direction

The site should feel like a serious live intelligence/forecasting product rather than a blog.

Prioritize:

- dense but readable information;
- excellent typography;
- timestamps/freshness;
- compact source labels;
- clear provenance links;
- timelines;
- restrained charts;
- strong mobile behavior;
- accessible interactions.

The memorable `pdoom.live` name may be playful, but the data presentation should be credible and non-sensational.

## Coordination boundary

Do not implement broad live data collection. The data agent owns seed-research methodology, source discovery, adapters, and collection.

If you need an ingestion interface, define the smallest stable contract and document it. Do not silently change the canonical meaning of shared fields without updating the docs.

## Deliverables

Finish with:

1. working local app;
2. database migrations;
3. deterministic seed data;
4. core routes/UI;
5. read/query API;
6. tests and CI if appropriate;
7. updated setup documentation;
8. a short report stating:
   - base SHA;
   - final SHA;
   - files/areas changed;
   - commands/tests run and results;
   - known gaps;
   - exact contracts the data agent should target.

Open a focused PR rather than merging directly unless repository workflow has been explicitly changed.

Do not stop at an architecture proposal. Implement the vertical slice and leave it runnable.
