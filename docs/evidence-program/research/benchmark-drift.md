# Session 25: Benchmark drift, contamination and comparability

Reviewed 8 October 2026 against repository commit `6cf8c1c89a387a5b26022dd9ea0a216d45b2b629`. See the [separate JSON record](../../../data/evidence-program/research/benchmark-drift.json) and [dated review queue](research-session-review-queue.md).

## Recommendation

Retain all eight collections as qualified research candidates: **five new families and three enrichments**. Prioritize EvalPlus’s small revision boundary, lm-eval’s measurement-change history and LiveBench’s retroactive revisions. None is operationally admitted, and no new adapter, validator or evaluation was run.

The review uses the frozen 64-family inventory and existing historical, algorithmic-efficiency, claim/result, model-identity and negative-replication catalogs. Later PhAIL/MLPerf/RoboArena submissions remain separate enrichment of earlier topics.

The central rule is to preserve **measurement identity**, not merely benchmark and model names. Task membership, prompt content, scorer, environment, scaffold, budget, model identity, denominator, weighting and publication vintage can all change the result.

## 1. EvalPlus: a tractable revision event

The [migration text](https://github.com/evalplus/evalplus/blob/3de226896daa67b54e2683eb6e5f6840ce66018a/tools/mbpp/fix_v010.py) identifies 21 distinct removals and 18 distinct retained-task prompt edits. This corroborates the publisher’s 399→378 task-count notice without independently counting either corpus.

The [before](https://github.com/evalplus/evalplus.github.io/blob/3b9f5b48c92a492a48fde6c0e1bffb9295812caf/results.json) and [after](https://github.com/evalplus/evalplus.github.io/blob/65db7ffdb66ae3fee800bee8d998b412f0a6e648/results.json) files each contain 101 model records:

- CodeGen-16B: MBPP 53.9→54.2%; MBPP+ 44.1→45.5%
- CodeGen-2B: MBPP 44.9→null; MBPP+ 35.1→null
- Their respective HumanEval/HumanEval+ values remain 32.9/28.0 and 24.4/22.6

Annotated tags resolve to the submitted commits. Both tag objects were created on April 17, 2024; the before snapshot is April 21 and the [revision commit](https://github.com/evalplus/evalplus.github.io/commit/65db7ffdb66ae3fee800bee8d998b412f0a6e648) April 22. These are not inference dates. The commit describes dropping results with temporarily unavailable original data; nulls must remain missing.

Framework, release repository and revised leaderboard have separate Apache-2.0 declarations. Linked output bundles remain uninspected. Treat this as a published-score revision, with unknown output/checkpoint linkage, rather than a capability gain or isolated task-removal effect. Retained IDs do not guarantee unchanged prompts.

## 2. lm-eval: distinguish scorer fixes from changed inference

The [v0.4.13 release](https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13), published August 31, 2026, confirms few-shot leakage, extraction, normalization and group-error-bar changes. [PR 3884](https://github.com/EleutherAI/lm-evaluation-harness/pull/3884), merged August 26, documents the BBH choice-prefix failure: “Guilty of Romance” was matched to the shorter “Guilty” choice. The regression example and repair were inspected, not executed.

The [pinned evaluator](https://github.com/EleutherAI/lm-evaluation-harness/blob/v0.4.13/lm_eval/evaluator_utils.py) adds an important qualification: its maximum per-metric count is a lower bound on evaluated documents. It explicitly warns that size-weighted groups can overweight metrics with fewer scored documents. The release therefore does not fully repair all denominator/aggregation problems.

Regrading preserved answers can address scoring-only changes. Leaked or altered demonstrations require new inference. Frozen leaderboard-math scoring and repaired Minerva scoring must remain distinct. Software is MIT; imported tasks and downstream outputs have separate rights.

Link fixes to actual downstream fork/commit paths, including CRP002. A later upstream repair does not establish that every earlier benchmark result was affected.

## 3. LiveBench: one release label can hide a later rerun

The [changelog](https://github.com/LiveBench/LiveBench/blob/main/changelog.md) confirms that on October 3, 2025, agentic coding changed from SWE-Agent to Mini-SWE-Agent and from 50 to 250 steps. The authors report rerunning all models and replacing results under the existing May 30 release label. Paired old/new scores were not acquired.

[PR 524](https://github.com/LiveBench/LiveBench/pull/524), merged August 29, 2026, confirms a pooled-judging collision between two tasks sharing IDs 1–47. It reports 47 erroneous zero scores for one model and adds directory-qualified lookup keys. This is demonstrated-by-source failure plus implemented repair; affected public runs and historical regrading remain unknown.

[Aggregation code](https://github.com/LiveBench/LiveBench/blob/main/livebench/show_livebench_result.py) distinguishes category-weighted scoring, optional question weighting and a missing-judgment policy that changes the common item set. Preserve all three.

The [datasheet](https://github.com/LiveBench/LiveBench/blob/main/docs/DATASHEET.md) explicitly declares the suite Apache-2.0, improving GL005’s evidence. Third-party inputs and judgment rights still need scoped treatment. The [current judgment viewer](https://huggingface.co/datasets/livebench/model_judgment) displays 60.4k rows across seven tasks and three categories, not proof of complete current coverage. History retrieval failed, so the intake’s April 2025 upload boundary remains unreverified.

## 4. LiveCodeBench: selector and population identity

The [README](https://github.com/LiveCodeBench/LiveCodeBench/blob/main/README.md) reports cumulative release sizes 400, 511, 612, 713, 880 and 1,055, through April 2025. These remain publisher counts.

The [loader](https://huggingface.co/datasets/livecodebench/code_generation_lite/blob/main/code_generation_lite.py) distinguishes six-file `release_v6` from one-increment `v6`. The [April 21, 2025 change](https://huggingface.co/datasets/livecodebench/code_generation_lite/commit/819a13a5c0347c1bd2f5600a35bc9ac9695d461b) repairs a duplicated `release_v5` key. Loader revision is therefore necessary to identify earlier requested populations. It downloads files before filtering; it was not executed.

The [errata](https://github.com/LiveCodeBench/LiveCodeBench/blob/main/ERRATA.md) contains 11 multiple-output, two interactive and four erroneous-test IDs, despite prose totals of seven, two and one. `abc337_e` is a verified interactive-task example. Repair and regrading links remain absent. Universally unsolvable tasks still affect absolute-score denominators; their existence cannot be dismissed in comparisons using different subsets or weights.

Software is MIT. The HF card’s unspecified “cc” and loader’s MIT declaration do not settle third-party problem/test redistribution. Temporal freshness is not proof of equal difficulty or no exposure. Earlier LiveBench coding questions create a dependency, not independent evidence.

## 5. METR: suite, scaffold and fitting vintage all matter

The [January 29 report](https://metr.org/blog/2026-1-29-time-horizon-1-1/) confirms 170→228 tasks, 73 additions, 15 removals and 53 modifications; 14 of 33 models were reestimated. GPT-5’s published 50%-horizon changes from 138 to 214 minutes under the revised measurement conditions.

**Additional caveat:** GPT-4-32k-0314 and o1-preview used new tasks with old Vivaria infrastructure before retirement. A TH1.1 label alone does not ensure a uniform harness. Pre-2023 observations were not reestimated, so the stitched trend is explicitly mixed. Human timing also combines measured and estimated baselines.

The [dashboard](https://metr.org/time-horizons/) dates a regularization correction to March 3, 2026. The [March 6 pipeline commit](https://github.com/METR/eval-analysis-public/commit/52cb829c7a2efb2d659285c4b1768d191d97f8d2) changes headline regularization from 0.1 to 0.00001 in both report configurations. It also changes other analysis inputs and adds models; its entire output change cannot be attributed to regularization alone.

Keep January’s comparison separate from March’s correction. Current repository-root inspection still found no LICENSE; code/data rights and raw-run reconstruction remain unresolved. The dashboard’s May 8 update and warning above 16 hours were confirmed. GL004 horizons remain distinct from AP002 productivity trials and SP003 RE-Bench results.

## 6. SWE-bench: reuse the audit, add repair provenance

The [April 15, 2024 repair report](https://github.com/SWE-bench/SWE-bench/blob/169cd7c65d5e0bfa1a96c8a01ef6bf5720d94f70/docs/20240415_eval_bug/README.md) confirms environment/installer problems, the recommendation for version 1.1.0 or later, 126 reported gold validation examples and restored author-reported baselines. It retains three unreproduced instances and architecture limitations.

Only the first [gold-fixture row](https://github.com/SWE-bench/SWE-bench/blob/169cd7c65d5e0bfa1a96c8a01ef6bf5720d94f70/docs/20240415_eval_bug/check-harness.jsonl) was fetched: `astropy__astropy-7858`, model label `gold`. It is a validation fixture, not model performance, and the full 126 rows were not recounted.

The [ChatGPT Agent card](https://deploymentsafety.openai.com/chatgpt-agent/expert-deep-dives) explicitly uses a fixed 477-task subset validated on internal infrastructure. For o3/o4-mini it averages four attempts to estimate pass@1; this is not pass@4. Exact subset membership remains unverified.

Reuse NR008’s [February 2026 audit](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/): 59.4% refers to 138 selected difficult tasks, not all 500 Verified tasks. No duplicate audit was performed. Repair, validity, contamination and later recommendation events remain separate, with GL007/CRP003 result identities and GL014 publisher provenance. Harness licensing does not clear all patches, logs or audit text.

## 7. GSM1K: retain the extraction bridge and membership conflict

[Paper v4, Appendix J](https://arxiv.org/html/2405.00332v4) confirms Claude 3 Opus’s GSM1K accuracy changes from 0.825 under automatic extraction to 0.952 under human extraction. Corresponding GSM8K values are 0.802 and 0.955. The 12.7-point GSM1K difference is an extraction ablation, not temporal improvement.

The paper and [HF card](https://huggingface.co/datasets/ScaleAI/gsm1k/blob/main/README.md) specify 1,205 examples; the [legacy leaderboard](https://labs.scale.com/leaderboard/math) describes 1,000 and says it was deprecated in January 2025. No item manifest establishes a universal 1,000→1,205 transition. Keep the conflict open.

API queries occurred April 16–July 10, 2024; v4 was submitted November 22. HF history dates publication to March 31–April 1, 2025. Later use cannot automatically inherit the original unseen-holdout rationale. The paper is CC BY 4.0; the released dataset lacks a displayed license, despite prospective MIT wording in the paper.

Cross-dataset gaps concern generalization, not direct proof of training exposure. The [GSM8K README](https://github.com/openai/grade-school-math) independently illustrates that fixed calculator code did not regenerate older archived outputs.

## 8. ConStat: diagnostics are reference-dependent

Both pinned [synthetic](https://github.com/eth-sri/ConStat/blob/d6688fe44ff5e40d68931eb7c574dda17694c87f/tables/gsm8k_synthetic.csv) and [rephrase](https://github.com/eth-sri/ConStat/blob/d6688fe44ff5e40d68931eb7c574dda17694c87f/tables/gsm8k_rephrase.csv) tables have 65 rows. Mistral-7B-v0.1 retains the same observed GSM8K score, 0.3904473:

- Synthetic reference: delta 0.0824507; raw p=0.0015
- Rephrased reference: delta −0.0086763; raw p=0.6644

Keep the non-detection. It does not establish no exposure. The [README](https://github.com/eth-sri/ConStat) defines `estimated_contamination` as estimated counterfactual performance, not contamination probability. The [paper](https://arxiv.org/html/2405.16281v1) distinguishes performance-based diagnostics from training-data inclusion and controlled exposure experiments. It applies Benjamini–Hochberg within benchmark/type for reference-model tests; the two CSV p-values remain raw.

The [loader](https://github.com/eth-sri/ConStat/blob/main/src/constat/load_results.py) removes duplicate document IDs and truncates result arrays to the shortest available length. Table-only denominators and exact item alignment remain unknown. The repository’s customized lm-eval v0.4.1 fork must not inherit an assumed 2026 bug exposure.

Repository tables carry Apache-2.0 and the paper CC BY 4.0; external archives were neither acquired nor cleared. Two reference tests and repeated paper/table presentations do not add independent model runs.

## Comparison gate and sole bounded specification

Store comparison status on a pair or defined series:

1. Comparable as recorded
2. Comparable after regrading preserved outputs
3. Requires new inference
4. Different population or protocol
5. Unresolved provenance

Require item-content identity, metric-specific denominators, scoring/aggregation and uncertainty rules, executed model/platform identity, inference dates, prompt/scaffold/budget and publication vintage. Preserve a fixed-panel series separately from fresh-cohort results. Any statistical bridge needs assumptions and uncertainty alongside original scores.

Keep issue report, demonstrated failure, implemented repair, affected-run identification, regrading/rerunning and corrected publication as separate states.

The only proposed specification maps the already-verified EvalPlus boundary: one revision event, 21 removals, 18 prompt edits and 16 metric slots across two models, including two explicit nulls. It must preserve source rights, hashes, date roles and unresolved inference identity; idempotent reimport must not create duplicate runs. Any later fresh read is capped at 12 requests/300 KB of text, excluding archives and outputs. No implementation or acceptance test was executed.

Completed work and eight pending source-specific actions are recorded separately in the JSON, with standalone prompts below. Complete pinned source files were checked against Git blob identities; web-capture hashes are not represented as raw webpage or historical-archive hashes. No source corpus is published.


## Separate next actions and prompts

All eight follow-ups are unstarted. They are bounded documentary research plans; they do not authorize implementation, evaluation execution, source corpus acquisition or canonical admission.

### BD001-A1 / BD001-F1: Map one EvalPlus revision

Source BD001; P0; status `follow_up_not_started`.

Use the already-verified April 2024 MBPP+ metadata, migration text and two-model score extracts. Describe a revision-event mapping only; do not implement an adapter or run benchmarks. If evidence is unavailable, read at most 12 small primary metadata/text artifacts totalling 300 KB, stopping at any access denial. Pins: migration https://github.com/evalplus/evalplus/blob/3de226896daa67b54e2683eb6e5f6840ce66018a/tools/mbpp/fix_v010.py; results before https://github.com/evalplus/evalplus.github.io/blob/3b9f5b48c92a492a48fde6c0e1bffb9295812caf/results.json and after https://github.com/evalplus/evalplus.github.io/blob/65db7ffdb66ae3fee800bee8d998b412f0a6e648/results.json. Scope CodeGen-16B and CodeGen-2B, 21 removals, 18 prompt edits and 16 metric slots. Preserve two nulls, tag-object versus commit identities, artifact rights, and unknown output/checkpoint/inference links. Stop with the specification and unresolved fields; no archives, model outputs or repository edits.

### BD002-A1 / BD002-F1: Qualify one harness result

Source BD002; P0; status `follow_up_not_started`.

For one supplied downstream result, inspect its recorded harness/task revision against https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13 and https://github.com/EleutherAI/lm-evaluation-harness/pull/3884. Use at most six public metadata/text reads and 200 KB. Determine whether the exact scoring, few-shot or group-weighting path matches a documented repair. Require metric-specific counts and actual fork/commit linkage; keep CRP002's unresolved evaluator revision unresolved if no evidence closes it. Classify scoring-only regrade, new inference required, unaffected or unknown, without running source code, fetching outputs, or treating all earlier results as invalid. If no downstream result is supplied, return the missing fields and stop.

### BD003-A1 / BD003-F1: Trace one LiveBench revision

Source BD003; P0; status `follow_up_not_started`.

Read only https://github.com/LiveBench/LiveBench/blob/main/changelog.md, https://github.com/LiveBench/LiveBench/pull/524 and at most four linked metadata pages, at most 200 KB. Find whether any explicit public run IDs and correction artifacts connect the October 3, 2025 agent/budget change or PR524 to published scores. Preserve the 2025-05-30 release label separately from revision and inference dates, task-qualified IDs, category/question weighting and missingness policy. Reuse the suite Apache declaration but do not extend it to third-party inputs or outputs. Return one event-to-run linkage or an explicit unresolved result; no corpus download, code execution, rerun or new collector.

### BD004-A1 / BD004-F1: Resolve one release boundary

Source BD004; P1; status `follow_up_not_started`.

Using https://huggingface.co/datasets/livecodebench/code_generation_lite/commit/819a13a5c0347c1bd2f5600a35bc9ac9695d461b and https://github.com/LiveCodeBench/LiveCodeBench/blob/main/ERRATA.md, inspect at most four small primary metadata/text artifacts, 120 KB total. Document release_v5/release_v6 versus increment v6 selection and one erratum, abc337_e. Preserve exact IDs and source-count conflicts. Seek only explicit repair/regrading metadata and artifact rights; a repair not found stays unknown. Do not download problem/test files, execute the loader, infer contamination-free status from contest dates, or reconstruct scores. Stop after that one documentary chain.

### BD005-A1 / BD005-F1: Separate METR measurement vintages

Source BD005; P0; status `follow_up_not_started`.

Reuse https://metr.org/blog/2026-1-29-time-horizon-1-1/ and https://github.com/METR/eval-analysis-public/commit/52cb829c7a2efb2d659285c4b1768d191d97f8d2. Inspect no more than four small configuration/metadata artifacts, 150 KB, without full commit diffs, DVC fetches or raw runs. Establish the required labels for January TH1 versus TH1.1 estimates and March fitting correction. Keep GPT-4-32k-0314 and o1-preview's old-infrastructure exceptions, human-time provenance and stitched pre-2023 observations explicit. Do not attribute all commit changes to regularization. If common-run/common-scorer evidence or data rights are absent, hold comparability and stop. No source execution or new implementation.

### BD006-A1 / BD006-F1: Link SWE-bench repair provenance

Source BD006; P1; status `follow_up_not_started`.

Reuse GL007/CRP003 and NR008's audited event identities. Inspect the April 15, 2024 report at https://github.com/SWE-bench/SWE-bench/blob/169cd7c65d5e0bfa1a96c8a01ef6bf5720d94f70/docs/20240415_eval_bug/README.md and the N=477 section at https://deploymentsafety.openai.com/chatgpt-agent/expert-deep-dives, plus at most two small public metadata artifacts, 150 KB total. Identify an explicit actual-instance manifest or leave it unresolved. Keep gold fixture validation, restored author-reported baselines, 138-task selected audit, 477-task system-card subset and nominal 500 tasks separate. Do not repeat the validity audit or download predictions/patches/log archives; no harness execution or score reconstruction. Stop with provenance links and missing fields.

### BD007-A1 / BD007-F1: Reconcile GSM1K denominator claims

Source BD007; P1; status `follow_up_not_started`.

Compare https://arxiv.org/html/2405.00332v4 Appendix J, https://labs.scale.com/leaderboard/math and https://huggingface.co/datasets/ScaleAI/gsm1k/blob/main/README.md. Use at most five public metadata/text reads, 150 KB; no question/output corpus. Seek a publisher-authored membership/version explanation for the legacy 1,000-question description versus 1,205 paper/card examples. Keep Claude 3 Opus automatic/human extraction as the same reported ablation, not temporal improvement; preserve April–July 2024 querying and March–April 2025 public release. Return the explanation or unresolved conflict, plus version-local rights. Do not assume a denominator change for every leaderboard row, contact authors, or run models.

### BD008-A1 / BD008-F1: Qualify two ConStat tests

Source BD008; P1; status `follow_up_not_started`.

Reuse the two pinned Mistral-7B-v0.1 rows in https://github.com/eth-sri/ConStat/tree/d6688fe44ff5e40d68931eb7c574dda17694c87f/tables and the paper https://arxiv.org/html/2405.16281v1. Inspect at most four small metadata/text artifacts, 150 KB. Document synthetic versus rephrase reference construction, raw p-values, counterfactual-score field semantics and paper multiple-testing scope; retain the non-detection. Check whether any small manifest supplies exact item sets and executed model/fork identities; otherwise leave them unknown. No external archives, benchmark questions, model outputs, reruns or new adapter. Do not infer training exposure from the statistical diagnostic or transfer a 2026 lm-eval fix onto this customized 2024 fork without linkage.
