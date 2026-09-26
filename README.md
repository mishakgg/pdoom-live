# pdoom.live

**pdoom.live** is a provenance-first observatory for public beliefs, forecasts, and changing views among frontier-AI researchers and leaders.

The memorable entry point is p(doom), but the product is broader: it should make it easy to answer **who said what, when, where, with what definition or horizon, and how that view changed over time**.

## Product thesis

Public discussion about frontier AI is fragmented across social media, papers, podcasts, videos, lab posts, personal blogs, newsletters, conference talks, interviews, repositories, model cards, and testimony. pdoom.live turns those sources into an auditable longitudinal dataset.

Initial topic families:

- AI catastrophe / p(doom) estimates and qualitative risk views
- AGI / ASI timelines
- frontier-model and capability expectations
- agents, coding automation, robotics, and scientific automation
- jobs, labor displacement, productivity, and macroeconomic effects
- scaling, compute, energy, and infrastructure constraints
- alignment, evaluations, governance, and deployment risk
- open-source / open-weight AI and ecosystem expectations

## Core principle

**Observed statements and model-inferred analysis are different data products.**

A person explicitly saying “10%” may be stored as an explicit numerical estimate with its exact definition and source. A qualitative statement may be categorized and summarized, but it must not be converted into a fabricated precise probability.

Every displayed claim should be traceable to source evidence.

## MVP

The first useful version should:

1. maintain a curated registry of frontier-AI people and their verified public identities;
2. ingest selected high-value public sources;
3. normalize content and preserve canonical URLs, timestamps, authorship, and provenance;
4. extract candidate claims and forecasts while retaining source evidence;
5. distinguish explicit numeric forecasts, explicit qualitative views, and model-inferred signals;
6. show people, statements, topics, source timelines, and aggregate trends;
7. support search/filtering and source-first drill-down;
8. provide transparent freshness and coverage information.

Start with a smaller, high-confidence cohort rather than claiming comprehensive coverage prematurely.

## License

The website software is licensed under the [PolyForm Shield License 1.0.0](./LICENSE). You may use, change, and share the code. You may not use it to provide a product that competes with pdoom.live, including a copy of this website. That limit applies even if the copy is free.

The dataset, fixtures, and reports in [`data/`](./data/) are dedicated to the public domain under [CC0 1.0](./data/LICENSE). Reusing that data is allowed. Reusing the data does not include permission to copy the website software and run a competing site.

## Repository guidance

Read [AGENTS.md](./AGENTS.md) before making changes.

Key design documents:

- [Product contract](./docs/PRODUCT.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [Data model](./docs/DATA_MODEL.md)
- [Source and provenance policy](./docs/SOURCE_AND_PROVENANCE_POLICY.md)
- [Initial roadmap](./docs/ROADMAP.md)

## Status

The first testing-ready product slice runs on PostgreSQL with a synthetic fixture cohort. The data-collection side has a separate versioned seed, identity graph, and collectors. That seed is not loaded by `npm run db:seed`.

- [Cohort methodology](./docs/COHORT_METHODOLOGY.md) — cohort `2026.09.0` is a purposive seed, not all AI researchers.
- [Data pipeline](./docs/DATA_PIPELINE.md) — collector envelope, seed files, and the gap to the application import.
- [Ingestion contract](./docs/INGESTION_CONTRACT.md) — canonical document the product imports. The current schema requires `synthetic: true` and is the fixture loader, not the live seed.
- Seed files: `data/seed/cohort/v2026-09/`.
- Quality report: `data/reports/cohort-v2026-09-quality.md`.

## Local development

Requirements: Node.js 22, PostgreSQL 16. Python 3.11+ with `pytest` and `defusedxml` for the collector suite.

```bash
cp .env.example .env
createdb pdoom_live
createdb pdoom_live_test
npm install
npm run db:migrate
npm run db:seed
npm run dev
```

The app listens on `http://localhost:3000`.

| Command | Purpose |
| --- | --- |
| `npm run dev` | Next.js development server |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript |
| `npm test` | Vitest, including database tests against `DATABASE_URL` |
| `npm run db:migrate` | Apply SQL migrations |
| `npm run db:seed` | Idempotently load `data/fixtures/synthetic/dataset.json` |
| `npm run db:reset` | Truncate product tables and seed again |
| `npm run build` | Production build |
| `PYTHONPATH=pipeline python -m pytest` | Collector, identity, and seed tests. No network. |
| `PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.enrich_sources --live` | Confirm pages and ORCID URLs for the existing cohort. Does not add people. |

Database tests refuse to run unless the database name contains `test`. Point `DATABASE_URL` at `pdoom_live_test` before `npm test`, or export it in the shell. Do not point the test runner at the development database.

The fixture people, organizations, and quotations are fictional. The researcher seed under `data/seed/` is a real public-identity registry and is not a synthetic fixture.
