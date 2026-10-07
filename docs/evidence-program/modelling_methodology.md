# AI evidence modelling methodology

Proposed analytical methodology • 7 October 2026

## Purpose and current readiness

Integrate and verify established datasets first, then collect evidence for demonstrated gaps. Build separate, reproducible analyses of capabilities, resources, safety, adoption and attributed forecasts. Each analysis must state its estimand: the precise quantity, population, conditions and time window it describes. A benchmark gain is not automatically a change in catastrophe probability, and a descriptive association is not a causal model.

This methodology follows the completed [64-family source inventory](source_priorities.md), the [coverage audit](coverage_findings.md) at repository commit `f5274396885dbb654fc2861a78fa5be8f42fad38`, the [proposed v0.1 dataset contract](dataset_spec.md) with 13 record types, and the [Chinese-language preparation guide](chinese_guide.md). None establishes that the candidate datasets have been acquired. The audit found much broader catalogs and adapter support than saved quantitative evidence. Its 333 saved observation rows and 41 candidate rows are not independent documents or verified forecasts; no saved candidate was `human_verified`. These are checked-in findings, not current production measurements.

Supported now are the bounded coverage audit, source-level evidence assessment, contract validation and synthetic methodological checks. Real benchmark-growth estimates, cross-country comparisons, causal effects, calibrated catastrophe probabilities and public forecast scoring are not ready. The recipes below become usable only when their stated input and review gates pass. This document fits no real model, computes no actual p(doom), changes no frozen contract and authorizes no collection or publication.

## Integrate evidence without manufacturing independence

For every reused dataset, pin its release, native row identifier, schema and method documentation. Verify rights, version stability, units, missingness and meaning before joining. Preserve `upstream_refs` and ordered, versioned transformations; retain the upstream authority rather than copying a secondary table and losing its origin. New collection should fill a specific missing period, model, question, language or primary evidence link that existing releases cannot supply.

Use the contract's distinctions. `benchmark_run`, `resource_observation`, `safety_evaluation` and `incident` describe observations with different meanings. `forecast_question`, `forecast` and `resolution` support attributed predictions and adjudication. `model_version` and `release_event` distinguish a system from an announcement. `source_artifact`, `actor`, `statement` and `snapshot` preserve attribution and provenance. A publisher is not an anonymous survey collective, and a measurement is not a developer's personal forecast.

Join exact revisions and count the intended observational unit. Three reports reproducing one vendor table remain one reported result with three citations. An original Chinese statement and its translation remain one belief lineage. An upstream estimate incorporated into AI Index or a system card is not independent corroboration. Preserve these relationships even when records remain separate for audit.

Define each analysis in a short preregistered specification: target quantity; included population; unit of analysis; eligible versions and dates; comparison protocol; transformations; weighting; missingness and duplicate rules; uncertainty; sensitivity checks; and stopping/exclusion criteria. Freeze these before examining the held-out results. Separate exploratory findings from confirmatory tests. Repeatedly selecting the best method on evaluation data can bias reported performance. [Cawley and Talbot](https://www.jmlr.org/papers/v11/cawley10a.html).

## Coverage is part of every result

The 64 candidate families, 40 global and 24 Chinese-focused, are a planning frame, not all global AI evidence. Publish the frame version, search/discovery routes and inclusion rules. Keep discovered sources, admitted sources, successful checks, observed records, usable evidence and reviewed records distinct. Operational success can be reported as successful checks divided by due admitted checks in a specified window, alongside the numerator and denominator. With no due checks the rate is undefined, not zero or 100%.

Analytical completeness needs another denominator: a declared model panel, benchmark task set, survey population, forecast question set or incident exposure frame. If that universe cannot be enumerated, say that completeness is unknown. Multiple language or domain memberships can overlap. Do not add overlapping categories as if they partitioned the dataset.

The Chinese preparation package supplies review aids and 25 invented cases, not demonstrated extractor accuracy. The audit's zero usable belief evidence among 15 people affiliated with China-headquartered organizations is a coverage gap, not an estimate of their beliefs or nationality. Missing language fields prevent a language census. Preserve original-script evidence, exact speaker, translation lineage, qualifiers, bounds and temporal precision. Conflicting Chinese and English outcome wording blocks pooling until reviewed; official translation status alone does not settle semantics.

## Recipe 1 Compare benchmark performance

The estimand is performance change for specified model versions on a specified task distribution under a fixed evaluation protocol. Require exact model identity, benchmark release and split, metric direction and scale, evaluator, run date, harness, prompt/scaffold, tools, sampling and inference budget. If an immutable model revision is unavailable, narrow the claim to the provider-labelled system observed at that time. Provider reports and independent reproductions remain separate strata.

Construct a matched panel from comparable runs. Choose model release date or evaluation date as the time axis and state which; show both in the underlying data. Report per-task-family results before any composite. HELM's scenario, adaptation and multi-metric framing supports keeping the evaluation conditions explicit. [HELM paper](https://arxiv.org/abs/2211.09110). Benchmarks measuring coding, multilingual reasoning, vision, robotics and agentic task completion do not share a natural universal unit of progress.

For bounded accuracy, show an absolute percentage-point change and, when meaningful, relative change or error reduction as separately labelled quantities. Dividing an absolute change by a defined elapsed duration gives percentage points per year, not exponential growth; declare the duration convention and preserve date uncertainty. Do not annualize an arbitrary leaderboard score. For a genuinely positive ratio-scale measure, endpoint annualized change can be `(x_end / x_start)^(1 / elapsed_years) − 1`. It describes that interval; it neither tests exponential growth nor predicts its continuation. Nonpositive values, changing units and incomparable endpoints are excluded from this calculation.

Worked example A is wholly synthetic. Three invented, identically defined task-duration thresholds are 2, 4 and 8 hours at elapsed years 0, 1 and 2. The endpoint ratio is 4; annualized change is `4^(1/2) − 1 = 1`, or 100%; the equivalent doubling time over this interval is 12 months. These fabricated points supply no uncertainty interval or evidence of a real trend. A task-duration threshold refers to human task duration at a specified model success criterion, not how long an AI runs. METR defines such task-completion measures for its task suite. [METR paper](https://arxiv.org/abs/2503.14499).

Worked example B is also synthetic. On the same 100 tasks, two versions score 40% and 60%. The change is 20 percentage points, the relative score increase is 50%, and error falls from 60% to 40%, a one-third relative reduction. These are different summaries of the same observations. Counts alone do not reveal paired task outcomes, so they do not justify a paired confidence interval. The frozen unit registry has no `percentage_point` enum: this is an analysis label, not a schema extension.

If enough comparable observations become available, report interval-specific rates or fit a prespecified descriptive model such as log metric against elapsed time. Inspect residuals, influential points and structural breaks; compare alternative shapes on held-out time periods. Do not choose exponential extrapolation because a short graph looks straight. Report a fixed panel and a frontier envelope separately: selecting each period's best model produces a selected-best trajectory, not typical-model improvement.

## Benchmark versions contamination and breaks

A changed dataset, grader, scaffold, judge model, pass-at-k setting or inference budget can change the measurement. A new benchmark release should begin a new series unless matched overlap runs establish a defensible bridge. A bridge needs a documented transformation, uncertainty and validation on runs not used to estimate it. A few shared model names are insufficient. Preserve unbridged series when assumptions fail.

Record test release dates, model training-cutoff claims, known benchmark exposure, contamination checks and their limits. A newer task release can reduce some exposure risks; it cannot prove absence of training, tuning or repeated-test adaptation. LiveBench's changing question sets make release pinning especially important. [LiveBench paper](https://arxiv.org/abs/2406.19314). Report cleanly documented, suspected and unknown contamination strata without pretending that an unknown score can be corrected by an invented discount.

Prefer a matched-task sensitivity analysis when task composition changes. Otherwise display the break and retain both regimes. Missing or retired model results are not zero. Saturated tests may cease to distinguish improvements, and a null change on them is not evidence that all capabilities stopped improving. Benchmark-language changes are also protocol changes; national or linguistic coverage cannot be inferred from a model developer's location.

## Recipe 2 Measure resources and efficiency

Choose a resource estimand before calculating growth: training FLOP for a defined phase, hardware capacity, energy, nominal expenditure, real expenditure or inference price under a particular billing unit. Require the source's measurement boundary and reported/measured/estimated classification. Preserve hardware, numerical precision, utilization, currency, price date, included stages and estimator dependencies. Epoch documents architecture-based and hardware-based compute estimation, including assumptions that distinguish estimates from reported inputs. [Epoch estimation methods](https://epoch.ai/data/ai-models-documentation/estimation).

Build separate series for comparable definitions. Positive ratio-scale quantities can use log changes or the endpoint formula above; costs denominated in different currencies or years need a declared conversion before comparison. Keep native values and conversion inputs. Do not fit nominal expenditure and physical compute as if they measured the same resource. An API token price is not a provider's production cost or a cost per successful task.

For efficiency, fix a performance target and evaluation protocol, then compare the resources needed to achieve it. Show the observed performance-resource frontier and uncovered ranges; interpolation requires stated assumptions, and extrapolated target attainment is not a measurement. Include unsuccessful attempts and tool/retry costs in cost per successful task under a declared accounting rule. A benchmark-imputed compute estimate cannot independently validate the same compute-performance relationship used to create it. Keep such circular evidence out of the principal association analysis.

## Recipe 3 Compare safety evidence and observed harms

A safety-evaluation estimand might be attack success under a fixed threat model, evaluator effort, system configuration and mitigation state. Compare only matched protocols and report capability elicitation separately from deployed-system behavior. Keep thresholds tied to the original rubric; passing a threshold is not a universal certificate of safety. Zero observed failures in a finite test does not establish zero failure probability.

For incidents, deduplicate at the event level while retaining all reports and disagreements. Distinguish alleged involvement, verified involvement and causal attribution; use a versioned severity rubric. AIID's editorial guidance explicitly addresses when reports refer to the same incident. [AI Incident Database editorial guide](https://incidentdatabase.ai/editors-guide/). Do not count a translation or syndicated story as another harm.

A count trend describes recorded incidents in that collection process. An incident rate additionally requires relevant exposure and a stable ascertainment process, such as reviewed incidents per defined deployment-hours. Show reporting lag, unresolved cases and revisions. More reporting, more deployment and greater underlying hazard can all raise recorded counts; these data alone do not identify their separate effects. Near misses, laboratory demonstrations and deployed harms remain separate groups. No empirical incident count becomes an extinction probability through rescaling.

## Recipe 4 Compare adoption and economic observations

Define the population, question, sampling design, reference period, weighting and denominator before joining statistical releases. Enterprise adoption among firms of a given size is not individual use, and intention to adopt is not current deployment. Use supplied design weights and uncertainty where supported; preserve changes in questionnaire wording, sector coverage and response modes.

The inventory documents a Census AI-use wording change in November 2025. Treat the pre/post series as different regimes unless a validated bridge exists, rather than assigning the entire jump to behavioral change. [Census explanation](https://www.census.gov/library/stories/2026/05/ai-use-businesses.html). Likewise, distinguish Chinese model announcements, actual releases and administrative filings; these counts do not measure equivalent events or capability.

Report within-series changes first. Cross-country comparison requires aligned concepts, populations and reference periods; otherwise offer a labelled side-by-side description. A correlation between AI adoption and productivity is observational and may reflect selection, sector composition, timing or other changes. Causal attribution requires a separate identification design and evidence, not more decimal places in a regression.

## Recipe 5 Describe beliefs and forecast revisions

A descriptive belief estimand concerns an explicitly selected group answering the same question at a specified time. Exact outcome definition, population, conditioning, horizon, units and answer semantics must agree. Extinction, catastrophe, permanent disempowerment and loss of control are separate outcomes. Conditional-on-AGI probabilities cannot be pooled with unconditional ones. An arrival-year prediction is not a probability of arrival by that year.

Use one active eligible estimate per person and exact question under a declared as-of rule. Resolve withdrawals before selecting the contribution; an obsolete estimate must not reappear when its replacement is withdrawn. Preserve genuine ranges, bounds, quantiles and qualitative language rather than forcing point values. Compare matched people separately from contributor entry and exit. Report the selected group, eligible and contributing counts, exclusions and age of estimates alongside any median or distribution.

For surveys, retain the instrument, wave, field dates, sampling frame, recruitment, response counts, weights and overlap across waves. The original AI Impacts author survey documents methods and question forms that matter for interpretation. [Survey paper](https://aiimpacts.org/wp-content/uploads/2023/04/Thousands_of_AI_authors_on_the_future_of_AI.pdf). A source-published median belongs to the wave's collective, with the aggregator recorded separately. A percentage endorsing a statement is not the probability that statement is true. Anonymous records must not be deanonymized for dependence adjustment; document unknown overlap instead.

Differences between convenience samples need composition and wording caveats. The corpus cannot represent a global expert consensus merely through breadth. Speaker counts do not establish an uncertainty interval on the underlying event probability. Forecast markets also require their own participation, incentive, liquidity and aggregation context, and usable access rights; a market snapshot is not interchangeable with an individual survey answer.

## Uncertainty and dependence

Distinguish three sources of uncertainty in every output. Sampling uncertainty arises when sampled tasks, people or events stand for a declared larger population. Measurement uncertainty includes stochastic runs, scoring errors, translation ambiguity, uncertain model identity and estimated compute inputs. Epistemic uncertainty concerns unsupported definitions, model structure, causal mechanisms and transfer beyond the observed setting. These categories can interact; do not add their variances or combine their ranges without a joint model and dependence assumptions.

For a fixed task set evaluated exhaustively, there is no task-sampling uncertainty about that exact finite set, although stochastic-run and measurement uncertainty remain. Inference to a broader task population needs a justified sampling or generalization model. A narrow interval over observed tasks cannot repair a biased task selection. A vendor's interval, an analyst's bootstrap interval, a measurement range and an assumption-driven scenario range must carry distinct labels and methods.

Use paired comparisons when runs share tasks, and preserve task-family clusters. Repeated estimates from one author, repeated waves of a panel, one event's forecast updates and related model releases are not independent rows. Report both raw records and unique analysis units. Resampling or hierarchical analysis must respect the relevant clusters and target population; uncertainty methods should be specified before comparing results. With too few informative clusters, show the observations and limitations rather than a deceptively precise interval. Unknown respondent overlap warrants sensitivity analysis, not assumed independence.

Missingness must carry reasons: never evaluated, inaccessible, failed collection, undisclosed, ineligible, or unresolved. Do not replace these with zero or carry a last value forward silently. Report analysis under defensible alternative inclusion rules, such as independently evaluated versus all reported runs, fixed versus changing panels, or unknown-contamination exclusions. Weighting can address documented selection probabilities; it cannot conjure representativeness when inclusion is unknown.

## Recipe 6 Reconstruct historical information honestly

Separate three products: today's corpus sorted by event date; an as-known historical snapshot; and a retrospective reconstruction of historically published evidence. Only the second claims what this dataset had available at a cutoff. The proposed contract's `known_at` records when a revision first became available to the dataset, not its source publication date. The existing repository also has history/comparability helpers to preserve, rather than replace. [History contract](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/history.ts).

For an as-known analysis, freeze exact record revisions and their dependencies, enforce knowledge and represented-review cutoffs, and use conservative bounds for uncertain forecast times. A closed snapshot includes previous revisions for audit; select the eligible active revision explicitly rather than count every revision. A late-discovered 2020 claim remains known in 2026. Do not backdate it or silently import a later correction into an earlier view.

A retrospective corpus may retain an authenticated forecast demonstrably published before its outcome even if collected later. Label this separately from an as-known backtest and document how timestamp authenticity, later edits, missing deleted forecasts and discovery selection were checked. Such evidence can support a limited historical scoring exercise; it cannot prove that a prospective system would have found it. Survivorship favors available archives and memorable predictions.

Freeze forecast origins, question definitions, transforms and model-selection rules before evaluating held-out periods. Prevent translations, duplicated reports, the same event and revisions from crossing split boundaries in ways that leak outcomes. Current language models may know later events when interpreting old texts; use outcome-blind adjudication where practical, dated evidence and sensitivity checks. No date filter can undo leakage already encoded in a target, feature or hand-selected dataset.

## Recipe 7 Evaluate resolved forecasts

Scoring requires an exact question revision, admissible numerical forecast, forecast-origin rule, resolvable answer domain, prespecified resolution criteria and human-reviewed outcome evidence. Keep origin cutoff, event deadline, resolution time and evaluation cutoff separate. Compare forecasters or methods on the same eligible event set, origins or lead times, weights and missing-forecast rule. A method evaluated only on its easiest questions cannot fairly outrank one covering all questions.

For resolved binary events, let `p_i` be a probability and `y_i` the adjudicated zero-or-one outcome. Mean Brier loss is `sum((p_i − y_i)^2) / n`, with lower values better. Proper scoring rules provide a principled evaluation framework, but the choice of cases and comparisons still matters. [Gneiting and Raftery](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf). Dates, quantities, bounds and incomplete quantile sets require suitable separately defined evaluation; do not invent a full distribution to make a score possible.

Worked example C is wholly synthetic arithmetic. Four invented forecasts are 0.2, 0.6, 0.7 and 0.9; their resolved outcomes are 0, 1, 0 and 1. Squared errors are 0.04, 0.16, 0.49 and 0.01, totaling 0.70. The mean loss is 0.175. An explicitly illustrative constant-0.5 baseline has loss 0.25 on the same cases. Relative skill is `1 − 0.175 / 0.25 = 0.30`, a 30% loss reduction against that particular baseline. This relative skill is undefined when baseline loss is zero. These four invented cases establish neither calibration nor real forecasting skill. A real baseline must be chosen prospectively and suit the question set, rather than defaulting to 0.5 because it is convenient.

Report proper score, baseline-relative skill, reliability and discrimination separately. Reliability bins require enough informative cases and cluster-aware uncertainty; a good average score does not prove good calibration. Freeze binning and snapshot rules, and show event counts as well as forecast counts. Do not select each person's best-timed forecast after resolution. Preserve the frozen resolution statuses `open`, `resolved`, `ambiguous` and `void`. Document an unmet condition in the rationale or analysis-exclusion context according to the original question rules; it is not a new schema status or automatically a false outcome.

An event-time record is right-censored only when it is known not to have occurred through an observed cutoff while its later time remains unknown. Missing follow-up, unresolved adjudication and ambiguous events are not automatically right-censored. A binary forecast whose deadline is still future is not scored as false. Survival analysis needs its own estimand, observation model and defensible censoring assumptions. Scoring only resolved cases can itself select a biased subset, so report exclusions and unresolved durations.

Humanity's survival does not turn unresolved extinction forecasts into failures or create repeated independent extinction trials. Historical analogies can test procedures on bounded resolvable questions, but cannot validate a universal catastrophe probability. Existing public scoring remains disabled until a reviewed, adequate resolution corpus and explicit release decision justify changing that behavior. [Resolution contract](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/forecast-resolution.ts).

## Scenario reasoning has a separate boundary

Scenario diagrams may organize assumptions and reveal missing evidence. For fixed scenario assumptions S, the chain rule gives `P(D and L and H | S) = P(D | S) × P(L | D,S) × P(H | L,D,S)`, where D, L and H are precisely defined deployment, control-failure and harm events. This expression describes one joint pathway. It is not total harm probability unless the event structure actually makes it equivalent; other paths remain outside it.

No probabilities are assigned here. Benchmarks, selected incidents and expert opinions generally do not identify these conditional terms. Substituting marginal probabilities, assuming independence or multiplying unrelated survey medians is invalid. Any later scenario exercise must label elicited assumptions, dependencies, alternative pathways and sensitivity ranges. It should not present those assumptions as measured likelihoods or claim a data-identified p(doom).

## Admission validation and outputs

Before running a recipe, pass six gates: lawful and versioned source reuse; faithful identity and evidence lineage; contract-valid records and exact units; analysis-specific semantic comparability; temporal and dependence eligibility; and a reviewed analysis specification. Statistical adequacy is recipe-specific. Define acceptable precision and validation against the intended claim before seeing results; a universal row-count threshold would obscure dependence and bias.

Validate transformations against the native release, recompute supplied examples, inspect unexpected missingness and double-check a reviewed sample of source-to-record mappings. The proposed schemas preserve decimal strings and distinguish interval types, but passing them cannot prove translation quality, evaluator independence or comparability. Rights, human review and publication are separate gates. Derived analysis metadata belongs in an analysis report or companion artifact; do not insert unsupported fields into the frozen v0.1 records.

Each analytical output should identify its snapshot, native releases, method version, units, population, dates, numerator/denominator, exclusions, uncertainty method, sensitivity results and reproducible inputs/code. Display protocol breaks, corrections and as-published versus revised values. Save failed analyses and reasons when prerequisites are absent; an honest unready result is preferable to a fabricated continuous series.

Operational dependencies remain brief: permitted source access, genuine review, F:-only bounded collection storage, and verified private Drive handoff before local cleanup. These are not completed by this methodology. Private acquisition is separate from public release. Implementation tickets remain outside this step; none of the recipes schedules collection, activates scoring or changes the repository.

## Repository companions

- [Analysis recipes](../../data/evidence-program/analysis_recipes.json) are a proposed planning checklist, not executable production configuration.
- [Synthetic arithmetic checker](../../tools/evidence_program/check_methodology_examples.py) reproduces the [19-check result](../../data/evidence-program/methodology_example_checks.json).
- [Repository checks](../../tools/evidence_program/README.md) run this checker alongside the frozen contract and preparation checks.
