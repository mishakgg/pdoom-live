# Initial roadmap

The roadmap emphasizes a credible vertical slice before breadth.

## M0 — Foundation

Goal: repository and contracts are clear enough for two agents to work concurrently.

Deliverables:

- project documentation;
- application skeleton;
- database/migration setup;
- shared schemas/enums;
- local development workflow;
- deterministic test fixtures;
- lint/typecheck/test commands;
- basic CI.

Exit condition: a new contributor can run the system locally and understand data ownership/provenance without chat context.

## M1 — Researcher and source registry

Goal: establish a high-confidence seed cohort and verified source identities.

Deliverables:

- Person / Organization / Affiliation schema;
- ExternalIdentity / Source schema;
- importable seed format;
- initial reviewed seed cohort;
- inclusion reasons;
- identity-resolution review states;
- source coverage report.

Exit condition: the system can explain who is tracked, why, which source identities belong to them, and how certain those mappings are.

## M2 — First ingestion vertical slice

Start with a few source types that are accessible, useful, and testable. Good candidates include:

- RSS/Atom and personal/lab sites;
- arXiv/OpenReview-style metadata;
- YouTube metadata plus permitted caption/transcript references;
- GitHub/Hugging Face public activity where relevant.

Deliverables:

- adapter interface;
- fetch safety controls;
- source item/version model;
- normalized segments;
- content hashing/deduplication;
- idempotent jobs;
- deterministic fixtures;
- freshness/error metrics.

Exit condition: repeated collection produces stable source items without duplicates and failures are observable.

## M3 — Statement and forecast extraction

Goal: turn normalized evidence into structured candidate statements without losing provenance.

Deliverables:

- statement/forecast schemas;
- explicit numeric extraction;
- qualitative statement extraction;
- topic assignment;
- evidence span/timestamp linkage;
- model-inferred signals stored separately;
- extraction/version metadata;
- validation/review pipeline;
- adversarial prompt-injection fixtures.

Exit condition: every extracted record is evidence-backed, class boundaries are tested, and re-extraction is replayable.

## M4 — Public product vertical slice

Deliverables:

- home/activity feed;
- people index/detail;
- topic index/detail;
- statement/forecast detail;
- source/evidence links;
- search/filter/pagination;
- freshness and coverage indicators;
- responsive accessible UI.

Exit condition: a user can navigate from an aggregate or list to the exact source evidence and distinguish explicit from inferred content.

## M5 — First defensible trends

Do not begin with one opaque master score.

Start with metrics that are methodologically clear, for example:

- count/rate of new explicit forecasts by topic;
- distribution of comparable explicit numeric estimates;
- median/range only when questions are genuinely comparable;
- newly detected qualitative view changes awaiting/after review;
- coverage/freshness by cohort;
- forecast-horizon distributions.

Deliverables:

- versioned trend definitions;
- deterministic calculation tests;
- methodology pages;
- sample-size/coverage disclosure.

Exit condition: every chart can explain exactly which records contribute and why.

## M6 — Broader source coverage

Add adapters based on measured value and rights/access feasibility:

- podcasts;
- Bluesky;
- Mastodon;
- additional conference/talk sources;
- testimony/public records;
- approved X integration if sustainable;
- reputable press discovery/attribution.

Avoid adding a channel just to increase source count.

## M7 — Research interface

Potential capabilities:

- natural-language exploration grounded only in canonical records;
- compare people over time;
- “what changed this week?”;
- saved queries/feeds;
- data export/API — a read-only `/api/v1` surface and snapshot command are documented in `docs/PUBLIC_API.md`;
- forecast resolution tracking;
- source-coverage diagnostics.

## Near-term division of work

### Coding agent

Start with M0 and the storage/query/product skeleton. Use fixtures, not live scraping, to demonstrate the end-to-end UI.

### Data-collection agent

Start with M1 plus a narrow M2 prototype. Produce reviewed seed data, source registry methodology, adapters/fixtures, and coverage/quality reports.

Coordinate on canonical schemas before either side creates incompatible production tables.
