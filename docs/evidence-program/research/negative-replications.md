# Negative results and replications

Session 22, reviewed 8 October 2026 against repository commit `6cf8c1c89a387a5b26022dd9ea0a216d45b2b629`. See the [separate JSON record](../../../data/evidence-program/research/negative-replications.json) and [dated review queue](research-session-review-queue.md).

## Follow-up qualification: 8 October 2026

The [experimental effects follow-up](followups/experimental-effects-review.md) ([JSON](../../../data/evidence-program/research/followups/experimental-effects-review.json)) adds an independently reviewed research delta for deep prompt 2 / bundle B. For NR007-A1 / NR007 and AP002 / AP-A03, the bounded overlap and estimand review is complete with residual holds. AP002 and NR007 cover the same early and later METR study waves, not new independent experiments. Separately rechecked producer-update intervals and methods enrich prior verified catalog evidence; they do not identify the historical executed covariance or turn a contextually different later wave into an exact replication or comparable causal trend. An interval spanning zero does not establish equivalence. The I4R historical/current-edition and Costello correction/editorial branches remain separately qualified in the same follow-up. The fingerprinted original catalog and all historical text below remain unchanged; a failed reread does not invalidate prior verified evidence. Source admission and lossless canonical mapping remain held.

## Recommendation

Retain eight collections as research evidence: **three new families and five enrichments** against the current catalogs. The initial five-new/three-enrichment split predates the ReScience/MLRC and Crossref additions. The strongest scientific starting points remain MLRC reports, StrongREJECT and Crossref editorial links. The smallest structured step is a **specification-only mapping of one already-verified Crossref chain into CRP006**, without another collector or validator.

An attempted experiment, its outcome and an editorial action are separate records. A selected failed example does not invalidate an entire benchmark; an interval spanning zero does not prove zero effect; a missing replication is not a failed replication. Mirrors, notices, metadata assertions and syntheses do not add independent experiments.

## 1. MLRC / LICO: new study, existing family

Enrich CRP001 rather than create another MLRC/ReScience family. The [original LICO paper](https://proceedings.neurips.cc/paper_files/paper/2023/file/c2eac51b6353a4441e8b7426f8e8db78-Paper-Conference.pdf), Table 3, reports full-label CIFAR-100 accuracy of 80.9 ± 0.18 for WRN and 82.2 ± 0.02 with LICO. The [replication v1](https://arxiv.org/html/2410.13989v1), Table 2, instead gives its own baseline 78.1 ± 0.66 and LICO 77.3 ± 0.90 across three seeds. Those latter numbers are a within-replication comparison, not an original-versus-replication pair.

The report partially reproduces subsidiary findings but not consistent central improvements. Missing implementation details and reduced ImageNet data constrain interpretation. Its architecture labels disagree between sections 3.3–3.4 and Table 2; the ± statistic is unnamed. Preserve both uncertainties. [Official proceedings](https://reproml.org/proceedings/) label the cohort 2023, while the [arXiv record](https://arxiv.org/abs/2410.13989) says MLRC 2024 and lists submission on 17 October 2024. These are not execution dates.

Coverage is cohort-oriented, with linked iterations from 2018 through 2025, not a verified completed cohort in every calendar year. The replication manuscript declares CC0. Code, data, original paper and review rights remain separate; the [code landing page](https://github.com/robertdvdk/lico-fact) did not establish a grant. OpenReview contents remain unverified.

## 2. StrongREJECT: illustrative rerun and evaluator validity

This is a new collection, with GL039/GL040 bibliographic overlap. [Yong et al. v2](https://arxiv.org/html/2310.02446v2) reports 43.08% Scots Gaelic bypass on 520 AdvBench instructions using its engagement-based label. [StrongREJECT v2](https://arxiv.org/html/2402.10260v2), Appendix B, reruns one showcased example with GPT-4-0613 at temperature zero, producing three outputs that the authors judged unhelpful for the harmful objective. It supplies no revised 520-prompt rate. Its separate 313-prompt, 37-method evaluation has a different scope.

The original versions date to October 2023/January 2024; StrongREJECT versions to February/August 2024. Exact run dates are unverified. Current [repository documentation](https://github.com/dsbowen/strong_reject) describes evaluation and annotation exports, but none was acquired. The [deprecated official repository](https://github.com/alexandrasouly/strongreject) explicitly grants MIT for code/custom questions while preserving upstream question licenses; the paper is CC BY 4.0. Imported prompts, annotations and model outputs need individual clearance. A small-subset count conflict between the [data card](https://proceedings.neurips.cc/paper_files/paper/2024/file/e2e06adf560b0706d3b1ddfca9f29756-Supplemental-Datasets_and_Benchmarks_Track.pdf) (sections 2.2–2.4, pp. 38–39) and README remains unresolved. No operational prompt content is included.

## 3. Crossref / Retraction Watch: one retraction, two assertions

Enrich CRP006 with [Just et al.’s original record](https://pubmed.ncbi.nlm.nih.gov/29367952/), DOI 10.1038/s41562-017-0234-y. Published 30 October 2017, it reported 91% classification accuracy for 17 ideators and 17 controls. The [retraction notice](https://pmc.ncbi.nlm.nih.gov/articles/PMC10205687/) acknowledges overfitting through dataset-tuned features and supplies no corrected accuracy. It cites a methodological critique; no independent new-data replication is established here.

The [original production REST record](https://api.crossref.org/works/10.1038/s41562-017-0234-y) and [notice record](https://api.crossref.org/works/10.1038/s41562-023-01581-1) each carry publisher and Retraction Watch 43731 assertions in reverse directions. Normalize these four appearances to **one retraction dated 6 April 2023 and two provenance assertions**. The May issue and 24 May PMC availability are different clocks. [Crossmark](https://crossmark.crossref.org/dialog/?doi=10.1038/s41562-017-0234-y) also has a generic history label “Correction”; retain that raw label without overriding the actual retraction notice.

[Crossref documentation](https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/) supports production REST and working-day CSV updates, with less complete correction/concern coverage. Reuse CRP006’s scoped CC0 metadata finding; exclude abstracts and article/notice bodies. Missing relationships do not establish no notice exists. Retraction remains work-scoped, without an author-level misconduct inference.

## 4. ReproHum / ReproNLP: two annotation attempts, one synthesis

This new collection links the [2022 original](https://aclanthology.org/2022.acl-short.94/), [2025 reproduction](https://aclanthology.org/2025.gem-1.55/), [2026 individual report](https://aclanthology.org/2026.gem-main.90/) and [2026 overview](https://aclanthology.org/2026.gem-main.83/). Reused outputs for 50 input sentences are reevaluated for semantic preservation in more-positive rewrites.

The augmented-zero-shot original estimate is approximately 86.47, digitized from a figure. The first attempt reports 64.99 with 95% interval 58.46–71.52; the second reports 67.31. Units are **points on a 0–100 judgment scale**, not accuracy percentages. The original figure’s standard-error bars and the reproduction’s confidence interval remain distinct.

The individual reports say the attempts ran in parallel, despite different publication years. Exact run dates remain unknown; the overview is not a third human experiment. It also prints original zero-shot 60.71 where both individual reports give 69.71; this conflict and changing QRA/CV* conventions stay unresolved. Changed annotators, calibration and interface test measurement reproducibility, not temporal model deterioration. The lineage spans ReproGen 2021–2022 and ReproNLP 2023–2026. [ACL’s CC BY 4.0 policy](https://aclanthology.org/faq/copyright/) excludes third-party material; it does not automatically license raw annotations, imported text, model outputs or code.

## 5. Princeton leakage register: qualified discovery evidence

The [register](https://reproducible.cs.princeton.edu/) is a new discovery family; its selected cases are not a replication-failure census. The register remains unavailable in this review. Indexed official material gives a May 2024 snapshot of 41 critiques, 648 affected studies and 30 fields. Those counts are separate from the 2023 paper’s 22 reviews, 294 papers and 17 fields.

[Muchlinski et al.](https://doi.org/10.1093/pan/mpv024) has a 2016 issue identity and a later Cambridge hosting date. Indexed primary excerpts of [Kapoor and Narayanan’s corrective paper](https://doi.org/10.1016/j.patter.2023.100804) and its [author deposit/supplement](https://par.nsf.gov/servlets/purl/10513990) support an attributed finding: correcting train/test imputation leakage removes the substantive random-forest advantage over logistic regression. This is a same-data reanalysis, not an independent new-data trial or formal retraction.

This review did **not** obtain complete paper/supplement text or verified numerical AUC tables; original and corrected AUC values remain null. The indexed paper notice declares CC BY 4.0, while register, capsule and upstream-data rights remain unknown. No capsule or corpus was acquired. SP002’s A-Lab correction is related in evidence type, not the same study.

## 6. PRISM-Bench: version-local withdrawal

Enrich CRP007/GL040. [Version 1](https://arxiv.org/abs/2510.23594v1), submitted 27 October 2025, introduced visual-puzzle first-error detection. [Version 4](https://arxiv.org/abs/2510.23594v4), submitted 1 December 2025, was withdrawn with a submitter-reported ground-truth labeling problem attributed to GPT hallucinations. The [current record](https://arxiv.org/abs/2510.23594) still identifies withdrawn v4 as latest when checked.

No independently verified replication, replacement benchmark or corrected score is established. Keep these unknowns explicit. Descriptive metadata is CC0 under the existing arXiv rights finding; v1 links CC BY 4.0, while withdrawn v4 says no license for that version. Never inherit manuscript rights onto a dataset or replace historical status/rights with the latest page.

## 7. METR productivity: reuse AP002’s exact studies

The [early paper v2](https://arxiv.org/html/2507.09089v2) covers February–June 2025: 16 developers and 246 completed tasks, with 136 AI-allowed and 110 disallowed. Forecast time reduction was 24%; the adjusted observed completion-time increase was 19%, with reported 95% interval 2–39%. This is an adjusted relative time effect, not an unadjusted duration ratio or reciprocal output-rate change.

The [24 February 2026 follow-up](https://metr.org/blog/2026-02-24-uplift-update/) began in August 2025. Returning participants’ time-change estimate is −18% [−38%, +9%]; new participants’ is −4% [−15%, +9%]. The intervals span zero, and selection, pay and concurrent-agent time accounting undermine a reliable current uplift estimate. Their confidence level and subgroup completed-task counts are unverified here. This is an inconclusive contextual follow-up, not an exact failed replication or retraction.

AP002 already contains both studies, the [README treatment-label correction](https://github.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/commit/7ff2d7670235f531dff77eff58355bd77392f396), code/CSV rights holds and unresolved uncertainty-comment discrepancy. Reuse those published study identities and evidence qualifications. Paper v2 is CC BY 4.0; code/data remain unspecified. No participant rows were refetched. GL004 horizons and SP003 RE-Bench are different METR subseries.

## 8. SWE-bench audits: validity and recommendation events

Enrich GL007 with GL014 publisher provenance and CRP003 overlap. The [13 August 2024 release](https://openai.com/index/introducing-swe-bench-verified/) introduced 500 Verified tasks. The [23 February 2026 audit](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) deliberately selected 138 difficult tasks; its 59.4% material-issue figure applies only to that subset. No integer numerator is inferred from rounding.

The `pylint-dev__pylint-4551` example concerns an unstated required function name. The [upstream PR](https://github.com/pylint-dev/pylint/pull/4551) confirms the change identity; the audit supplies the benchmark-validity argument. This does not imply the maintainers’ tests are defective for their original purpose.

On [8 July 2026](https://openai.com/index/separating-signal-from-noise-coding-evaluations/), OpenAI withdrew its earlier Pro recommendation after another audit. This is a recommendation change, not a journal-paper retraction. Keep Verified and Pro distinct; the Pro review paths cover overlapping flagged tasks and their counts must not be summed. All remain developer-produced audit findings, separate from contamination claims and model performance. Complete audit-label exports and redistribution grants were not verified; upstream tasks, tests, issue text and code have separate rights.

## Bounded mapping specification

Reuse CRP006 for the two already-checked Crossref DOI records. Expected output is one original-to-notice event, two source assertions, date 2023-04-06, and no automatically inferred scientific outcome or corrected metric.

Proposed acceptance conditions:

- DOI URL/case normalization, repeated ingestion and reverse relations do not duplicate events
- Distinct notices and event types retain their own chronology; raw labels remain visible
- Missing notice IDs remain unresolved rather than colliding on a shared null key
- Incomplete dates retain precision; fetch failure differs from metadata absence
- Any future fresh lookup is limited to these two DOIs and four requests including retries, respects Retry-After and stops at an access denial
- Abstracts, full text and automatic author/claim failure labels are excluded

These are proposed conditions, not implemented or executed tests. There is no new adapter, validator, runtime collection or canonical admission.

## Completed work and next actions

Completed bounded checks cover original/response linkage, consequential metrics and date roles, access, artifact-specific rights and current-catalog overlap. This source review did not independently reproduce experiments, establish general reuse rights or implement the mapping specification.

Eight separate follow-ups remain unstarted. Unknown rights are unresolved clearance questions, not proof reuse is forbidden. These selected observations do not supply a population failure rate or catastrophe probability.

### NR001-A1 / NR001-F1: Clarify LICO source inconsistencies

Source NR001; P1; status `held_optional_documentary_followup_not_started`.

Inspect at most the LICO replication v1 https://arxiv.org/html/2410.13989v1, its abstract/version record https://arxiv.org/abs/2410.13989v1 and the official proceedings https://reproml.org/proceedings/. Check Table 2 versus sections 3.3–3.4 architecture labels, the meaning of ±, and cohort 2023 versus the arXiv MLRC 2024 comment. Return an attributed discrepancy map without silently repairing the source. Reuse CRP001 family identity. Stop after these three documents. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR002-A1 / NR002-F1: Separate StrongREJECT artifact rights

Source NR002; P1; status `held_optional_documentary_followup_not_started`.

Inspect only the current README/license at https://github.com/dsbowen/strong_reject and the earlier README/license at https://github.com/alexandrasouly/strongreject, at most four small text documents. Establish the exact grant for custom-generated data versus imported questions and human annotations. Do not fetch prompts, responses, eval archives or model weights. Preserve the existing paper-v2 Appendix B three-run single-example scope and original 43.08% as different evidence units. Stop after a scoped rights map, keeping ungranted artifacts unknown. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR003-A1 / NR003-F1: Map one editorial chain

Source NR003; P1; status `held_optional_documentary_followup_not_started`.

Using the checked production Crossref records for original DOI 10.1038/s41562-017-0234-y and notice DOI 10.1038/s41562-023-01581-1, prepare a metadata-only mapping into the existing claim-result-provenance relationships. If freshness is required, fetch only those two URLs under https://api.crossref.org/works/ with at most four requests including retries. Deduplicate publisher and Retraction Watch 43731 assertions and both relation directions into one event dated 2023-04-06. Preserve raw labels and unknown corrected accuracy. Exclude abstracts and notice bodies. Stop at the mapping or first denied access; no new adapter. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR004-A1 / NR004-F1: Reconcile ReproNLP synthesis values

Source NR004; P1; status `held_optional_documentary_followup_not_started`.

Compare only https://aclanthology.org/2025.gem-1.55.pdf, https://aclanthology.org/2026.gem-main.90.pdf and https://aclanthology.org/2026.gem-main.83.pdf. Reconcile the original zero-shot 69.71 in individual papers versus 60.71 in the overview without guessing a correction. Preserve the consistent augmented-zero-shot original estimate 86.47 and each attempt, the digitization qualifier, 0–100 judgment-point unit, confidence-interval method and shared original outputs. The reports say experiments ran in parallel; publication years are not run years. Stop after the three-paper discrepancy map; no raw annotations. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR005-A1 / NR005-F1: Verify leakage correction scope

Source NR005; P1; status `held_optional_documentary_followup_not_started`.

Review the original record DOI 10.1093/pan/mpv024 and Kapoor–Narayanan corrective paper DOI 10.1016/j.patter.2023.100804, with at most one directly linked public supplement, three documents total. Determine exactly which imputation/evaluation changes affect the random-forest-versus-logistic-regression comparison. Do not infer a corrected numerical score when no checked table supplies one. The Princeton register remains unavailable; do not bypass access restrictions or download its corpus/capsule. Separate 2016 issue identity from later hosting dates and dated register counts from population rates. Stop at a gate or after the source-located correction map. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR006-A1 / NR006-F1: Preserve PRISM version status

Source NR006; P1; status `held_optional_documentary_followup_not_started`.

Inspect only https://arxiv.org/abs/2510.23594v1, https://arxiv.org/abs/2510.23594v4 and https://arxiv.org/abs/2510.23594. Prepare a status/rights chronology linked to existing CRP007. Preserve v1 submission 2025-10-27 and withdrawn v4 2025-12-01, with original claims retained separately from author-reported reason. A changed latest status is not evidence of a replacement benchmark without an explicit link. Do not acquire manuscript sources or dataset files. Stop after these three metadata pages. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR007-A1 / NR007-F1: Preserve METR estimand boundaries

Source NR007; P1; status `held_optional_documentary_followup_not_started`.

Start with the published adoption-productivity AP002 catalog at https://github.com/mishakgg/pdoom-live/blob/6cf8c1c89a387a5b26022dd9ea0a216d45b2b629/data/evidence-program/research/adoption-productivity.json. At most two fresh documents are allowed: https://arxiv.org/html/2507.09089v2 and https://metr.org/blog/2026-02-24-uplift-update/. Clarify completion-time sign, adjusted coefficient semantics, reported uncertainty and the difference between a negative randomized effect and selection-limited follow-up intervals spanning zero. Preserve the 2026-02-23 README coding correction and unresolved HC3-versus-nonrobust-comment discrepancy without re-executing code. No CSVs or participant joins. Stop after an estimand/version map; paper CC BY 4.0 does not clear code/data. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.

### NR008-A1 / NR008-F1: Separate SWE-bench audit events

Source NR008; P1; status `held_optional_documentary_followup_not_started`.

Inspect at most the 2024 introduction https://openai.com/index/introducing-swe-bench-verified/, February audit https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/, July audit https://openai.com/index/separating-signal-from-noise-coding-evaluations/ and upstream https://github.com/pylint-dev/pylint/pull/4551. Map 500-problem release, selected 138-problem audit, 59.4% subset result, and withdrawn Pro recommendation as different events. Check for an explicit audit-label reuse grant; unknown remains unknown. Do not download task datasets or run tests. Stop after this four-document event map. Read-only public documentary research only. No login, outreach, repository changes, source execution, model calls, bulk data or participant-level acquisition. Do not retry or bypass an access denial. Return exact source versions/locators, verified facts versus unknowns, artifact-specific rights and the stopping condition; no pooled failure rate or p(doom) conversion.
