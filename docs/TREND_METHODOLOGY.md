# Trend methodology

Public trends are computed from canonical rows. There is no master score and no conversion of a qualitative view into a probability.

The calculation lives in `packages/db/src/trend-engine.ts`. Prepared questions live in `packages/db/src/trend-catalog.ts`. Exclusion wording lives in `packages/contracts/src/trends.ts`.

## Families

Each family has its own method version. A shared topic is not a reason to put two families on one chart.

| Family | Method version | What the number means |
| --- | --- | --- |
| Probability distribution | `explicit-numeric-distribution/1.2.0` | An explicit probability on one exact question |
| Timeline forecast | `timeline-forecast/1.1.0` | A predicted calendar year |
| Quantity forecast | `quantity-forecast/1.1.0` | A quantity in one declared unit and one outcome |
| Historical revision | `historical-revision/1.1.0` | One person's explicit forecast, linked by a verified update, retraction, or withdrawal |
| Qualitative statements | `qualitative-statements/1.0.0` | Wording without a number. No probability is inferred |
| Not pooled | `unpooled-inspection/1.0.0` | A verified numeric record that does not meet one exact question |
| Statement volume | `count-by-topic-type/1.0.0` | A count of statements, not a forecast |
| Discovered question | `discovered-question/1.1.0` | An exact question that no prepared or published cross-section already owns |
| Comparability policy | `comparability/1.0.0` | The pooling rules applied to every numeric result |
| Forecast history | `forecast-history/1.0.0` | Whether a view is the current corpus or a reconstruction |
| Forecast resolution | `forecast-resolution/0.1.0` | Eligibility design only. Public scoring stays off |

A published `trend_definitions` row keeps the `method_version` stored in the import. The synthetic extinction distribution remains `explicit-numeric-distribution/1.1.0` for that reason. The result still carries `comparability_policy_version` `comparability/1.0.0`, which is the pooling policy the engine applied. Prepared catalog methods use the versions in the table above.

A predicted year is a date. It is not a probability. A share, a job count, percentage points, and a probability are different units. The engine does not convert units.

## Comparability

`comparability/1.0.0` distinguishes a question family from an exact question. The registry is `packages/contracts/src/comparability.ts`. Stored keys are not rewritten. `extinction_unconditional` and `ai_extinction_unconditional_by_2070` stay spelled as stored. They share a family id. They share a comparison only when the structured fields agree.

A forecast enters a numeric cross-section when all of these hold:

- the stored key is that exact question, or the record is a family member whose outcome, condition, deadline, unit, and probability semantics match that exact question;
- the statement class is one the method allows (`explicit_numeric` for the prepared numeric methods);
- the review state is one the method allows (public numeric methods: `human_verified`);
- the unit matches the method's declared unit;
- conditionality matches, including an `unspecified` method rejecting condition text;
- a required horizon is present as horizon text or a stored target date;
- the value shape matches (a point, or a range when that method accepts ranges);
- a bound phrase, quantile, or distribution is not reduced to a point.

A family key with no structured deadline is not assigned the catalog horizon. A 2030 probability and a 2050 probability on `extinction_unconditional` stay different exact questions. A predicted AGI year is the value, so 2032 and 2040 can sit in `agi_arrival_calendar_year`. `event_probability` semantics are not pooled with an unspecified probability.

An unknown or ambiguous record stays individually inspectable, with `ambiguous_horizon`, `deadline_mismatch`, `condition_mismatch`, `definition_mismatch`, or `insufficient_agreement`.

A matching exact question is enough even when the statement's topic slug differs. Topic slugs still explain nearby records that answer a different question, such as a catastrophe statement sitting beside an extinction method.

Conditionality:

- `unconditional` drops a forecast that carries condition text;
- `conditional` requires condition text, and the condition fingerprint has to match the exact question when one is declared;
- `unspecified` drops a forecast that carries condition text.

Prepared questions that stay on separate exact keys:

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

Productivity and GDP can share the unit `percentage_points` and the family `productivity_growth`. They stay apart unless the text identifies one outcome and the deadline and unit match that exact question. Vague growth text is not pooled. Exact catalog keys such as `labor_productivity_growth_pp_by_2035` and `gdp_growth_pp_by_2035` are not rewritten onto each other.

## Latest estimate and revisions

A cross-section keeps one estimate per person: the latest `event_time` on that exact question. When two timestamps tie, the smaller `statement_slug` wins. If the tied statements also carry the same value, the extra row is `duplicate_statement` rather than a second contribution. A dated estimate beats an undated one.

Dropping the earlier number is not a revision. The earlier row is **superseded** only when a human-verified `updates` or `retracts` relationship points from it to another eligible point estimate by the same person on the same exact question. A `machine_validated` link does not count. A `repeats` link is a repeat. `clarifies` and `contradicts` are not changes of mind. A later statement on a different deadline is a different question, even when someone links the rows.

A human-verified `retracts` link whose target is not an eligible replacement number is a **withdrawal**. `to_value` is null. No replacement probability is required, and the historical statement stays on the revision record. The withdrawn row leaves the latest cross-section. That does not draw a verified return to an older number unless a separate verified link says so. The stored relationship enum remains `updates`, `clarifies`, `retracts`, `contradicts`, and `repeats`. The engine also accepts `withdraws` if a later schema adds it. This change does not migrate that enum.

Cross-section selection ranks all eligible estimates before applying withdrawals. If the latest estimate is withdrawn, no older estimate automatically takes its place, whether or not an update link joins them. A genuinely later explicit estimate can contribute. Withdrawing only an older estimate does not remove a separate newer estimate.

Relationship direction is older estimate (`from`) to later replacement or withdrawal statement (`to`). Both the relationship and its target statement must be `human_verified`, even if an imported method allows additional review states. Event times must be known and strictly increasing; unknown, invalid, equal, or reversed times remain inspectable but do not apply a withdrawal or establish a revision/repeat. This also excludes self-links and backward edges in a cycle. Timestamps are compared as instants, including UTC offsets. These checks use the current reviewed corpus; they do not assert a historical as-of reconstruction.

Historical revisions draw a line only along those verified links. Ranges are not points on a revision line. There is no cross-person revision median. Each person is a separate series.

## Summaries and sparse data

The median is the midpoint of the two central values when the count is even. It is shown from 3 included point estimates upward (`SUMMARY_MIN_POINTS`). Below that the page lists the individual estimates and withholds the median. A cross-person median summarizes the included statements. It is not automatically the probability of the event, and the count of speakers is not a confidence interval.

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
3. **Discovered question.** A `human_verified` explicit numeric point or range whose exact question is not already owned. Discovery groups by exact question id, so a conditional and an unconditional reading of one family key no longer collapse in method deduplication. The family follows the value: `probability` is a distribution, `year` is a timeline, anything else is a quantity. `forecast_kind` is not the classifier. Discovered probability and quantity methods require a horizon or a stored target date. A predicted-year question does not. The method version is `discovered-question/1.1.0`.

Qualitative statements are a separate discovered group, `qualitative-statements/1.0.0`. Records that fail the comparability rules and are not already owned by a prepared key appear under `unpooled-inspection/1.0.0`.

A revision method may share a question key with a distribution or timeline. It does not block that cross-section, and that cross-section does not block the revision.

On a live dataset, the home overview lists only trends with at least one contributing statement. The trends index still lists prepared methods, including empty ones, for the current cohort.

Statement volume still accepts `human_verified` and `machine_validated`. Numeric families accept `human_verified` only.

## Exclusions

Each excluded in-scope record carries a reason code and a sentence. The sentence is what the page shows. The code is stable for tests. The page does not describe SQL.

| Code | Meaning |
| --- | --- |
| `question_key_mismatch` | Different exact question |
| `conditionality_mismatch` | Conditional and unconditional estimates were not mixed |
| `condition_mismatch` | The stated condition does not match this comparison |
| `unit_mismatch` | The unit is not the method's unit, and no conversion is applied |
| `missing_horizon` | The method requires a horizon and neither horizon text nor a target date is stored |
| `ambiguous_horizon` | The horizon is missing or ambiguous, so the record is not pooled |
| `deadline_mismatch` | A probability's deadline does not match this comparison |
| `definition_mismatch` | The outcome definition does not match this comparison |
| `insufficient_agreement` | The stored fields do not agree closely enough to pool the record |
| `value_type_not_point` | A range, bound, quantile, or distribution was preserved and not reduced to a midpoint |
| `review_state` | Outside this method's public review policy |
| `statement_type` | Not an explicit numerical estimate |
| `not_latest` | A later estimate from the same person is the cross-section row |
| `duplicate_statement` | The same value at the same time is not a second contribution |
| `superseded` | A human-verified update or retraction links this row to a later eligible estimate |
| `withdrawn` | A human-verified withdrawal removes this estimate. No replacement number is required |
| `no_verified_revision` | No human-verified update, retraction, or withdrawal connects this estimate |
| `relationship_not_a_revision` | Repeat, clarification, or contradiction |
| `relationship_time_order` | The target lacks a known, strictly later event time |
| `different_person` | The relationship joins two people |
| `topic_not_target` | Filed under a watched sibling topic and a different question |
| `missing_forecast` | No structured forecast is stored |

## History and resolution

`calculated_at` and a dataset import time are not a historical reconstruction. The current-corpus claim is `forecast-history/1.0.0` with `presented_as_reconstruction: false`. A reconstruction requires `event_time`, source observation time (`known_at`), and human `reviewed_at` all on or before the cutoff. A statement dated before the cutoff can still have been observed or reviewed later. Filtering on `event_time` alone does not make that claim.

`forecast-resolution/0.1.0` describes a future resolved dataset: resolution criteria, an admissible forecast snapshot, outcome evidence, review state, and an evaluation cutoff. `scoreResolvedForecast` returns `disabled` and a null score. An unresolved extinction forecast is not a failure. Speaker count is not a confidence interval. No public scoring columns are added.

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
- horizon text or `target_date_start` / `target_date_end` on prepared probability and quantity questions that require a horizon;
- `statement_relationships` of type `updates` or `retracts`, reviewed `human_verified`, before a revision line is drawn.

Ranges stay ranges. The product will not invent a midpoint, a revision, or a field-level belief.
