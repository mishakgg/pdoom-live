# Trend methodology

Public trends are computed from canonical rows. There is no master score and no conversion of a qualitative view into a probability.

The calculation lives in `packages/db/src/trend-engine.ts`. Prepared questions live in `packages/db/src/trend-catalog.ts`. Exclusion wording lives in `packages/contracts/src/trends.ts`.

## Families

Each family has its own method version. A shared topic is not a reason to put two families on one chart.

| Family | Method version | What the number means |
| --- | --- | --- |
| Probability distribution | `explicit-numeric-distribution/1.1.0` | An explicit probability on one question key |
| Timeline forecast | `timeline-forecast/1.0.0` | A predicted calendar year |
| Quantity forecast | `quantity-forecast/1.0.0` | A quantity in one declared unit |
| Historical revision | `historical-revision/1.0.0` | One person's explicit forecast, linked by a verified update or retraction |
| Statement volume | `count-by-topic-type/1.0.0` | A count of statements, not a forecast |
| Discovered question | `discovered-question/1.0.0` | A stored question key that no prepared or published cross-section already owns |

A predicted year is a date. It is not a probability. A share, a job count, percentage points, and a probability are different units. The engine does not convert units.

## Comparability

`question_key` is the inclusion boundary.

A forecast enters a numeric cross-section when all of these hold:

- the question key matches;
- the statement class is one the method allows (`explicit_numeric` for the prepared numeric methods);
- the review state is one the method allows (public numeric methods: `human_verified`);
- the unit matches the method's declared unit;
- conditionality matches;
- a required horizon is present;
- the value shape matches (a point, or a range when that method accepts ranges).

A matching question key is enough even when the statement's topic slug differs. Topic slugs are used to explain nearby records that were left out, such as a catastrophe statement sitting beside an extinction method. They are not a second comparability key.

Conditionality:

- `unconditional` drops a forecast that carries condition text;
- `conditional` requires condition text;
- `unspecified` does not filter on condition text.

Prepared questions that stay on separate keys:

- `ai_extinction_unconditional_by_2070`
- `ai_extinction_conditional_on_agi`
- `ai_catastrophe_not_extinction_by_2070`
- `permanent_disempowerment_conditional_on_agi`
- `agi_arrival_by_2032` (a probability, not a year)
- `agi_arrival_calendar_year`
- `asi_arrival_calendar_year`
- `coding_task_automation_share_by_2028`
- `unemployment_plus_2pp_by_2030`
- `labor_productivity_growth_pp_by_2035`
- `gdp_growth_pp_by_2035`

Productivity and GDP can share the unit `percentage_points` and still stay apart, because the question keys differ.

## Latest estimate and revisions

A cross-section keeps one estimate per person: the latest `event_time`. When two timestamps tie, the smaller `statement_slug` wins. A dated estimate beats an undated one.

Dropping the earlier number is not a revision. The earlier row is **superseded** only when a human-verified `updates` or `retracts` relationship points from it to another eligible estimate by the same person on the same question. A `machine_validated` link does not count. A `repeats` link is a repeat, not a change.

Historical revisions draw a line only along those verified links, and only between point estimates. Ranges are not points on a revision line. Repeats are listed and are not drawn as change. Eligible estimates with no verified link stay unlinked. There is no cross-person revision median. Each person is a separate series.

## Summaries and sparse data

The median is the midpoint of the two central values when the count is even. It is shown from 3 included point estimates upward (`SUMMARY_MIN_POINTS`). Below that the page lists the individual estimates and withholds the median.

Ranges are not collapsed into midpoints. Probability methods require points, so a range is excluded. Timeline and quantity methods can show a range in the table; that range does not enter the median.

Density:

- `empty` — no comparable record;
- `sparse` — fewer than 3 comparable point estimates;
- `comparable` — 3 or more point estimates in one cross-section;
- `individual` — at least one verified revision chain;
- `unlinked` — comparable estimates exist, and none are joined by a verified revision.

One or two estimates remain inspectable. Zero estimates show the question, the method, the cohort size, and the missing count. An empty result is an absence of comparable records.

## Coverage

Every numeric view names:

- the cohort and its size;
- the method version;
- the question text and definition;
- contributing people and statements;
- cohort members with no comparable record;
- the density.

A small contributing count is shown as that count. The copy does not say that AI researchers, the frontier, or a field believes the figure.

## Where a trend comes from

Three sources can produce a public trend. They do not override each other on the same cross-section.

1. **Published definition.** A `trend_definitions` row in the imported document. It wins when its slug matches a prepared method, or when its question key is already used by a non-revision cross-section.
2. **Prepared method.** The product catalog. These questions are listed for the current cohort even when the count is zero, so a visitor can see the empty state and the exclusion rules.
3. **Discovered question.** A `human_verified` explicit numeric point or range whose question key is not already owned. Discovery groups by question key, unit, and conditionality. The family follows the unit: `probability` is a distribution, `year` is a timeline, anything else is a quantity. `forecast_kind` is not the classifier. Discovered methods require a horizon. The slug is a kebab of question key, unit, and conditionality.

A revision method may share a question key with a distribution or timeline. It does not block that cross-section, and that cross-section does not block the revision.

On a live dataset, the home overview lists only trends with at least one contributing statement. The trends index still lists prepared methods, including empty ones, for the current cohort.

Statement volume still accepts `human_verified` and `machine_validated`. Numeric families accept `human_verified` only.

## Exclusions

Each excluded in-scope record carries a reason code and a sentence. The sentence is what the page shows. The code is stable for tests. The page does not describe SQL.

| Code | Meaning |
| --- | --- |
| `question_key_mismatch` | Different question key |
| `conditionality_mismatch` | Conditional and unconditional estimates were not mixed |
| `unit_mismatch` | The unit is not the method's unit, and no conversion is applied |
| `missing_horizon` | The method requires a horizon and none is stored |
| `value_type_not_point` | A range or distribution was supplied where a point is required |
| `review_state` | Outside this method's public review policy |
| `statement_type` | Not an explicit numerical estimate |
| `not_latest` | A later estimate from the same person is the cross-section row |
| `superseded` | A human-verified update or retraction links this row to a later estimate |
| `no_verified_revision` | No human-verified update or retraction connects this estimate |
| `relationship_not_a_revision` | Repeat, clarification, or contradiction |
| `different_person` | The relationship joins two people |
| `topic_not_target` | Filed under a watched sibling topic and a different question |
| `missing_forecast` | No structured forecast is stored |

## Aggregation JSON

`trend_definitions.aggregation_definition_json` is a tagged object. Schema version stays `1.0.0`. The new tags are optional additions to the existing union:

- `explicit_numeric_distribution` — `conditionality` is optional so older documents still validate;
- `timeline_forecast` — `require_unit` is `year`;
- `quantity_forecast` — `require_unit` is the one unit that may be summarized;
- `historical_revision` — `relationship_types` is `updates` and/or `retracts`;
- `count_by_topic_and_statement_type` — unchanged volume counter.

No database migration is required. The column is already JSON.

## What collectors still have to supply

A live forecast enters one of these views only when the import document carries:

- a stable `question_key` from the list above, or a new key that discovery will keep separate;
- `unit` exactly (`probability`, `year`, `share`, `percentage_points`, `jobs`, or another unconverted unit);
- `human_verified` on the statement and the forecast before it can enter a public numeric trend;
- horizon text on prepared probability and quantity questions that require it;
- `statement_relationships` of type `updates` or `retracts`, reviewed `human_verified`, before a revision line is drawn.

Ranges stay ranges. The product will not invent a midpoint, a revision, or a field-level belief.
