# Forecast comparability

Policy version: `comparability/1.0.0`.

This document is the interface for the question registry. Agent 3 owns canonical schemas, persisted-key migrations, export/import integration, and shared barrel exports. Agent 5 owns the curation consumer and candidate identity. This milestone does not change those surfaces.

## Source of truth

`packages/contracts/src/comparability.ts` is the registry. The committed snapshot is `packages/contracts/src/comparability-registry.json`, produced by `comparabilityRegistryDocument()`. Python reads that file through `pdoom_pipeline.belief.comparability.load_comparability_registry`. `pipeline/pdoom_pipeline/belief/taxonomy.py` still exports `QUESTION_KEYS`, `TOPICS`, and `KEY_TOPIC`. Those dicts are families. They are not a second taxonomy.

A test fails if the JSON snapshot drifts from the TypeScript document.

## Stored keys stay spelled as stored

Examples that must not be renamed on import or in curation:

| Stored key | Role | What it is |
| --- | --- | --- |
| `extinction_unconditional` | family | Pipeline key. Deadline is null. It does not become “by 2070”. |
| `ai_extinction_unconditional` | family | Curation key for the same family. Deadline is null. |
| `ai_extinction_unconditional_by_2070` | exact | Catalog question. Deadline end `2070-12-31`. |
| `productivity_growth` | family | Covers more than one quantity. Requires one outcome split. |
| `economic_growth` | family | Curation family for the same split. |
| `labor_productivity_growth_pp_by_2035` | exact | Labor productivity, percentage points, end `2035-12-31`. |
| `gdp_growth_pp_by_2035` | exact | GDP, percentage points, end `2035-12-31`. |
| `agi_timeline` | family | Predicted AGI year. The year is the value. |
| `agi_arrival_calendar_year` | exact | Arrival-year comparison. Predicted years are not split apart. |
| `agi_by_year_probability` | family | A probability. The deadline is part of the question. |
| `agi_arrival_by_2032` | exact | Probability of AGI by `2032-12-31` only. |

`extinction_unconditional` and `ai_extinction_unconditional_by_2070` share `family_id` `human_extinction_unconditional`. A family record joins the exact question only when the outcome, condition, deadline, unit, and probability semantics agree. A missing deadline stays `ambiguous_horizon`. A 2030 deadline and a 2050 deadline get different exact question ids.

## What Agent 5 consumes

Call these from `@pdoom/contracts`. Do not change `candidateKey` in this milestone. `QUESTION_TAXONOMY` remains the approval list.

- `classifyQuestionKey(key)` — registry entry, or null when the key is unknown.
- `classifyForecast(facts)` — poolable flag, exact question id, family id, deadline, condition fingerprint, and exclusion reason.
- `comparabilityIdentityMaterial(facts)` — stable text for a later candidate identity. It includes the policy version, stored key, exact question id, outcome, definition, condition, target dates, unit, value type, and probability semantics.
- `comparisonDecision(facts, exactQuestionId)` — whether a record belongs in one comparison.
- `COMPARABILITY_POLICY_VERSION` — `comparability/1.0.0`.
- `prePolicyMethodKey` — the old deduplication key. It is exported so tests can show that conditional and unconditional discoveries used to collide. New method keys include the exact question id and conditionality.

`stored_key_is_exact` is true only when the stored key is already an exact registry question. A family join sets it false and leaves `stored_question_key` unchanged.

## What Agent 3 consumes

- `comparabilityRegistryDocument()` and the JSON snapshot. Do not translate stored keys during import, export, or a migration. A family key must not be rewritten onto a horizon.
- Schema version stays `1.0.0`. Do not add public scoring columns.
- `calculated_at` and an import `asOf` are not a reconstruction. `CURRENT_CORPUS_HISTORY.presented_as_reconstruction` is false. A reconstruction uses `selectKnownByCutoff`, which requires `event_time`, `known_at` (source observation time), and `reviewed_at` (human verification time) on or before the cutoff. `historyClaimFor({ mode: "event_time_only" })` stays `presented_as_reconstruction: false`.
- The relationship check constraint stays `updates`, `clarifies`, `retracts`, `contradicts`, `repeats`. A verified withdrawal is a `retracts` link whose target is not an eligible replacement number. `to_value` is null. The engine also accepts relationship type `withdraws` if a future enum adds it. Do not add that migration here.
- `scoreResolvedForecast` always returns `{ status: "disabled", score: null }`. `FORECAST_RESOLUTION_FIXTURES` and `assessResolutionEligibility` describe a future dataset: resolution criteria, an admissible forecast snapshot, outcome evidence, review state, and an evaluation cutoff. An eligible fixture is still not scored. An unresolved extinction forecast is not a failure.

## Query boundary

`packages/db/src/trend-query.ts` exports:

- `FORECAST_INPUT_SQL` — selects `target_date_start`, `target_date_end`, `distribution_json`, `resolution_criteria`, `known_at`, and `reviewed_at`.
- `mapForecastRow` — maps those columns onto a trend candidate before the engine runs.
- `resolveTrendMethods` and `trendMethodKey` — method identity includes exact question id, unit, and conditionality.
- `loadTrendInputs` — the cohort load used by `listComputedTrends`.

Prepared method versions are `explicit-numeric-distribution/1.2.0`, `timeline-forecast/1.1.0`, `quantity-forecast/1.1.0`, and `historical-revision/1.1.0`. Discovered numeric questions use `discovered-question/1.1.0`. Qualitative groups use `qualitative-statements/1.0.0`. Unpooled rows use `unpooled-inspection/1.0.0`.

## Deterministic examples

- `extinction_unconditional` with target end `2030-12-31` and the same key with `2050-12-31` produce different exact question ids. One person’s two deadlines are not a revision of each other.
- The same family with condition text `if frontier labs pause scaling` is a different exact question from the unconditional reading. `prePolicyMethodKey` collides; `trendMethodKey` does not.
- `productivity_growth` plus “labor productivity” and percentage points by `2035-12-31` joins `labor_productivity_growth_pp_by_2035`. The same family plus “GDP” joins `gdp_growth_pp_by_2035`. Vague growth text is `insufficient_agreement`.
- `agi_timeline` years 2032 and 2040 join `agi_arrival_calendar_year`. `agi_by_year_probability` by `2032-12-31` joins `agi_arrival_by_2032`. A 2050 deadline does not.
- A stored exact key with horizon text and no target date still uses that key’s declared deadline. A family key does not.
- A human-verified `retracts` link to a qualitative note withdraws the number. The historical value remains on the revision chain with `to_value: null`.
- Same timestamp and same value: the smaller statement slug is kept and the other is `duplicate_statement`. Same timestamp and different values: the smaller slug is kept and the other is `not_latest`.
- `scoreResolvedForecast` on an unresolved extinction question returns a null score.
