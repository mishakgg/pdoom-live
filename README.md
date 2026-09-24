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

## Repository guidance

Read [AGENTS.md](./AGENTS.md) before making changes.

Key design documents:

- [Product contract](./docs/PRODUCT.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [Data model](./docs/DATA_MODEL.md)
- [Source and provenance policy](./docs/SOURCE_AND_PROVENANCE_POLICY.md)
- [Initial roadmap](./docs/ROADMAP.md)

## Status

Project foundation only. Application implementation and production datasets have not yet been built.
