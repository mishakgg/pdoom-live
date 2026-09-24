# Product contract

## What pdoom.live is

pdoom.live is a public, source-first observatory for the changing beliefs and forecasts of people working closest to frontier AI.

It is not limited to p(doom). The product should organize and make searchable:

- AI catastrophe-risk estimates and qualitative concern
- AGI/ASI timelines
- future model/capability expectations
- agents, coding, science, robotics, and autonomy
- jobs and labor-market effects
- productivity and macroeconomic effects
- scaling, compute, energy, and infrastructure
- safety, evaluations, alignment, deployment, and governance
- open-source/open-weight expectations

The product's durable asset is the longitudinal dataset: **people + identities + sources + statements + forecasts + revisions over time**.

## Primary users

Initial users may include:

- people following frontier AI closely;
- researchers and forecasters;
- journalists and analysts;
- investors and operators seeking primary-source context;
- policymakers and researchers studying AI expectations.

The interface should remain understandable to a non-specialist.

## Primary user questions

The system should eventually answer questions such as:

- What has this person said about AI extinction risk?
- Has their view changed?
- What definitions and time horizons did they use?
- What are frontier researchers saying about coding automation by 2028?
- Which forecasts about jobs changed most in the last 90 days?
- What evidence supports the current trend?
- Which people in a defined cohort have spoken publicly about a topic?
- What new sourced forecasts appeared this week?
- What do tracked researchers expect about the next capability step, and how uncertain is that evidence?

## Core product surfaces

### Home

A high-signal overview with:

- current topic trends;
- recent material belief changes;
- newly added primary-source statements;
- cohort/sample-size/freshness labels;
- links to underlying evidence.

Avoid a sensational “doom meter” without methodology and provenance.

### People

Each person page should support:

- name and current/relevant affiliation;
- why they are included in the tracked cohort;
- verified public identities and source feeds;
- recent statements;
- topic filters;
- explicit numerical forecasts;
- qualitative positions;
- machine-inferred signals shown separately;
- historical changes;
- source and evidence drill-down.

### Topics

Topic pages should show:

- definitions;
- relevant statements;
- distributions only when the underlying questions are comparable;
- time series;
- cohort filters;
- source mix;
- missing-data / coverage notes.

### Statement / forecast detail

This is the audit surface. It should include:

- speaker/author;
- source;
- date/time;
- direct evidence or timestamp;
- normalized claim;
- type;
- definition/question;
- units;
- horizon;
- conditioning event;
- extraction/review status;
- link to original material.

### Sources / activity

A transparent feed of newly observed source items and processing status.

## Terminology

Use precise language.

- **Statement**: a sourced proposition attributed to a person.
- **Forecast**: a statement about an uncertain future event/outcome.
- **Explicit numeric forecast**: a forecast where the person supplies a number/range/distribution.
- **Explicit qualitative view**: a sourced view without an explicit numerical probability/value.
- **Model-inferred signal**: machine-generated classification or synthesis derived from evidence, clearly labeled as such.
- **Trend**: an aggregate computed over a declared cohort, topic definition, method, and time window.
- **Coverage**: how much of the intended cohort/sources have been observed recently.

## Product principles

1. Source before synthesis.
2. Definitions before aggregation.
3. Change over time is often more informative than a single score.
4. Missingness is data; show it.
5. Do not imply a population consensus from a convenience sample.
6. Keep first-party statements distinguishable from reporting about them.
7. Make methods readable and reproducible.
8. Prefer useful uncertainty over false precision.

## Initial cohort strategy

Start narrow and high-confidence.

Possible seed groups:

- researchers and research leaders at frontier-model organizations;
- significant frontier-model paper authors;
- AI safety/evaluation researchers closely connected to frontier systems;
- selected academics and former frontier researchers with material public forecasting activity.

Every person record should have an inclusion reason. Expansion should come from auditable rules and review, not name-volume targets.

## MVP success criteria

The first release is useful when it can demonstrate, with deterministic fixtures and then live public sources:

1. a verified set of people;
2. multiple source types per person where available;
3. normalized, deduplicated content;
4. sourced claim/forecast extraction;
5. correct separation of explicit and inferred content;
6. reliable filtering and timelines;
7. transparent freshness/coverage;
8. no unsupported “consensus” claims;
9. a clean path for adding new source adapters without redesigning the app.
