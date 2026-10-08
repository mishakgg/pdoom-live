# Mitigation effectiveness

Reviewed 8 October 2026. Seven study packages are suitable for a research catalog with explicit holds. LLMail, CaMeL and Redwood remain the top three for controlled-comparison value. This is not a ranking of general safeguard effectiveness.

Five packages add studies beyond the initial inventory; Anthropic and AISI enrich existing families. CaMeL is a new experiment using the already-cataloged AgentDojo benchmark, not another newly discovered AgentDojo family. None is operationally admitted and no collector was enabled.

## Scope and review state

Session 21 was source-reviewed against historical commit `82fd46330539bd484c80190c69868d71b2052f6e`. Its separate publication batch uses merged base `6cf8c1c89a387a5b26022dd9ea0a216d45b2b629`; these are distinct provenance roles. See the [separate JSON record](../../../data/evidence-program/research/mitigation-effectiveness.json) and [dated review queue](research-session-review-queue.md).

Completed work covers primary aggregate tables, methodology, costs, rights, limited metadata/static-source checks and meaningful overlap with prior collections. No attack corpus, operational payload, participant row, production traffic or source code is included. No source execution, implementation or operational admission occurred. Unverified raw-content claims remain explicit.

## 1. LLMail-Inject

[Paper v1, §4.5/Table 3](https://arxiv.org/html/2506.09956v1) confirms six detectors on two selected tool-calling pools: 25,323 and 3,688. Prompt Shield v1/v2 recalls on the first pool are 0.604/0.678. Twelve factual aggregate observations are a useful bounded starting point. Exact detection counts and intervals are unpublished, so remain null.

The 370,724/90,916 raw submissions and 208,095 unique prompts are different denominators. Changes between competition phases prevent a causal before/after improvement claim. The 0.99 threshold applies to Prompt Shield and TaskTracker; the zero false-positive result is synthetic-benign-only, with no verified benign sample size. Monetary cost is unknown.

The [dataset card](https://huggingface.co/datasets/microsoft/llmail-inject-challenge/blob/main/README.md) declares MIT, as does the analysis software license. The paper instead has an arXiv nonexclusive distribution grant. No raw sample, one-row API, placeholder-output claim or corrections-only maintenance policy was independently reverified. Fixed-release metadata is sufficient here.

## 2. CaMeL / AgentDojo

[Paper v2](https://arxiv.org/html/2503.18813v2) supports o3 High benign utility of 84.5% versus 77.3%, and a separate Claude 3.5 Sonnet security comparison of tool filtering 8/949 versus CaMeL 0/949. Tables 5–6 add the corresponding Claude utility cost: 73.20% versus 63.92% clean, and 72.71% versus 66.70% under attack. Do not attach o3 utility to the Claude attack counts. The inspected tables do not independently establish the clean-task denominator.

The under-attack median token ratios are 2.82 input and 2.73 output, using a proxy tokenizer and excluding tool documentation. Zero observed successes is finite benchmark evidence, with side-channel and task-completion limitations.

The [pinned analysis notebook](https://github.com/google-research/camel-prompt-injection/blob/f083b6b396399d3b3c7f2ddaf613a5945eaf32d8/analysis.ipynb) sets security to zero on errors at lines 93–94. Lines 111–125 contain a count-interval helper that subtracts a count-scale quantity from a proportion. This is a static implementation concern, not a demonstrated correction to published results: paper-generation linkage and corrected intervals remain unresolved. No source code was executed.

Paper rights are CC BY 4.0; code is Apache-2.0; generated logs and benchmark inputs need separate treatment. The README warns of bugs/security limitations and no maintenance. AgentDojo ASI001 supplies a dependency identity, not a proven matching runtime.

## 3. Redwood AI Control

[Paper v5, Table 7](https://arxiv.org/html/2312.06942v5) confirms upfront auditing 15% safety/100% scaled usefulness; trusted monitoring 62%/97%; trusted editing at 20% 92%/94%. Safety concerns an entire simulated 5,000-problem deployment, estimated from responses to 1,500 problems. Usefulness uses benign GPT-4 and normalization between GPT-3.5 and GPT-4 performance. It is not a raw task-accuracy percentage.

The 2% audit allocation plus ten free initial audits uses GPT-4 to simulate high-quality labor under strong audit-detection assumptions. The same problems supported iterative design and evaluation; protocols face differing attack policies. No production reliability or catastrophe probability follows. Published uncertainty and monetary cost remain unestablished.

The [small protocol feed](https://control-leaderboard.redwoodresearch.org/protocols.json), generated September 24, still has zero rows/cells. The [data page](https://control-leaderboard.redwoodresearch.org/data) documents run links and mixed license labels; this does not verify linked downloads or monitor numbers. Live numerical monitor results remain unverified. Original paper: CC BY 4.0; software: MIT; APPS and third-party traces remain separate.

## 4. Constitutional Classifiers

The [2025 study summary](https://www.anthropic.com/research/constitutional-classifiers) supports 86% versus 4.4% attack success on 10,000 automated prompts, 23.7% inference overhead, and a nonsignificant 0.38-percentage-point refusal increase in 5,000 conversations. Its public demo later found one universal bypass under a different eight-question criterion; a dated grading correction is also reported. Keep those cohorts separate.

[Classifiers++ §6/Table 1](https://arxiv.org/html/2601.04603v1) supports a December 2025–January 2026 Sonnet 4.5 shadow window, 0.05% flags, roughly 5.5% escalation, about 198,000 red-team attempts, 1,736 estimated hours and one high-risk vulnerability. Shadow flags do not establish reduced real-world harm. Vulnerability-discovery yield is not unsafe-output prevalence.

The cost value 3.5% is relative to a previous classifier system; [roughly 1% overhead](https://www.anthropic.com/research/next-generation-constitutional-classifiers) is qualified as applying to Opus 4.0 traffic. Neither is a directly matched 2025–2026 causal comparison. Both papers are CC BY 4.0; website, user traffic and unreleased logs have separate unresolved rights.

## 5. Vejandla cognitive forcing

[Published Experiment 2/Table 5](https://www.nature.com/articles/s41598-025-30506-3) confirms 373 retained participants from 430 completers and 2,842 decisions. Delay-by-Black OR is 1.091, 95% CI 0.687–1.733, p=.713; the other two interface interactions also include one. This is imprecise null evidence, not equivalence, clinical accuracy or zero effect. The delay adds 30 seconds per vignette; participant compensation is not deployment cost.

The paper's advice-viewing counts sum to 690 while the on-demand arm has 698 retained decisions. Preserve both pending clarification. OSF metadata confirms three files, v1, sizes and December 2024 deposits. It does not verify their contents, CSV header, script inconsistencies/internal heading or download functionality. The article is CC BY-NC-ND 4.0; [OSF project metadata](https://api.osf.io/v2/nodes/gp569/) has no declared license. Raw-data redistribution remains held.

## 6. Buçinca, Malaya and Gajos

[To Trust or To Think, Table 2](https://kgajos.seas.harvard.edu/papers/bucinca21trust.pdf) confirms adjusted carbohydrate-source overreliance means 0.64 versus 0.48, SE .03 each, p=.003. The separate complete-decision result 0.30 versus 0.26 is nonsignificant. The 663 denominator counts incorrect-AI decisions, not the 199 retained participants. These are adjusted estimates, not event fractions.

Pooled cognitive-forcing versus simple-explanation trust/preference differences were nonsignificant; increased complexity and correlation-based acceptability evidence are different findings. Advice was simulated; the task was nutrition. This is not a direct replication of the police-deployment racial-disparity experiment. [arXiv v1](https://arxiv.org/abs/2102.09692v1) declares CC BY 4.0 while the author PDF retains an ACM notice; data/code availability and rights remain unestablished.

## 7. UK AISI

[Trends report Figure 13](https://www.aisi.gov.uk/frontier-ai-trends-report) supports 10 expert minutes versus strictly more than seven hours, with bypasses found for both anonymized systems. The earlier case reused a public vulnerability; the later required a novel one. Store Model B as >420 minutes and keep query denominators/identities unknown.

The [GPT-5.5 safeguards report](https://www.aisi.gov.uk/blog/our-evaluation-of-openais-gpt-5-5-cyber-capabilities) confirms six expert hours, subsequent stack changes and inability to verify the final configuration because of a configuration problem. Retain failure observed → mitigation changed → effectiveness unverified. No successful-fix outcome is justified. Content rights remain unknown; an institutional domain does not establish OGL.

## Proposed bounded implementation

One LLMail Table 3 specification remains unimplemented: six detectors × two selected pools, exactly 12 aggregate observations. Preserve three-decimal recalls, null exact numerators/uncertainty, threshold applicability and synthetic-only benign false-positive context. Acquisition and factual/table reuse must be resolved first. Proposed acceptance tests are documented in the JSON and were not executed. No adapter, validator, model calls or operational collector was added.

## Next actions and copy-ready prompts

All seven follow-ups are unstarted and bounded to the named evidence. Source review completion does not clear source admission, unresolved rights, runtime linkage or effectiveness claims.

### ME001-A1 / ME001-F1: Prepare aggregate-table admission decision

Source ME001; P1; status `bounded_follow_up_not_started`.

Review only arXiv 2506.09956v1 Table 3 / §4.5. Decide whether 12 factual detector/pool observations can enter a research-only catalog under the intended reuse policy, keeping paper rights separate from MIT dataset/code rights. Retain denominators 25,323 / 3,688, three-decimal recalls, null numerators/uncertainty and synthetic-only benign FPR. Deliver an admission decision and acceptance-test notes, not code or observations from raw submissions. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://arxiv.org/html/2506.09956v1 ; https://huggingface.co/datasets/microsoft/llmail-inject-challenge/blob/main/README.md.

### ME002-A1 / ME002-F1: Resolve score and interval lineage

Source ME002; P1; status `bounded_follow_up_not_started`.

Inspect only published CaMeL errata/README and the pinned analysis.ipynb scoring excerpt at f083b6b396399d3b3c7f2ddaf613a5945eaf32d8, especially lines 93–94 and 111–125. Establish whether any public evidence links that helper to paper-v2 attack-count intervals or corrects it. Separate an implementation concern from a proven published-error correction. Preserve 0/949 as the reported Claude count with execution-status qualification; do not invent corrected intervals. Also record any explicit immutable AgentDojo evaluator version, otherwise leave it unknown. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://arxiv.org/html/2503.18813v2 ; https://github.com/google-research/camel-prompt-injection/blob/f083b6b396399d3b3c7f2ddaf613a5945eaf32d8/analysis.ipynb.

### ME003-A1 / ME003-F1: Maintain simulation and feed boundary

Source ME003; P1; status `bounded_follow_up_not_started`.

Check only the original AI Control v5 study metadata and the small official protocols.json feed. If the feed remains empty, report that fact and stop. If populated, inspect schema/aggregate metadata only after confirming a small response-size boundary and artifact-specific rights; do not retrieve .eval files, monitor-result bundles or attack traces. Preserve original 1,500-generated / 5,000-simulated distinction, 2% + 10 audit allocation, benign usefulness and simulated auditing assumptions. Do not retrieve larger result feeds or bypass access restrictions. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://arxiv.org/abs/2312.06942v5 ; https://control-leaderboard.redwoodresearch.org/protocols.json.

### ME004-A1 / ME004-F1: Separate classifier cohorts and costs

Source ME004; P1; status `bounded_follow_up_not_started`.

Using only arXiv 2501.18837v1, arXiv 2601.04603v1 and their two official Anthropic research summaries, produce a compact cohort map: 2025 automated 10,000 prompts, dated eight-question public challenge, and 2026 Sonnet 4.5 shadow / 198K-attempt study. Resolve any public definition for the shadow traffic denominator; retain unknown if absent. Label 0.38 percentage-point incremental refusals versus 0.05% flag rate, 3.5% of classifier-system overhead versus roughly 1% for Opus 4.0 traffic. No raw queries, traffic, jailbreaks or model calls. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://arxiv.org/html/2501.18837v1 ; https://arxiv.org/html/2601.04603v1 ; https://www.anthropic.com/research/constitutional-classifiers ; https://www.anthropic.com/research/next-generation-constitutional-classifiers.

### ME005-A1 / ME005-F1: Resolve decision-count and rights gaps

Source ME005; P1; status `bounded_follow_up_not_started`.

Review only the Vejandla publisher correction/supplement notices and OSF gp569 project/file metadata for Experiment 2. Seek a published explanation for 560 + 130 = 690 advice-viewing decisions versus 698 retained arm decisions and an explicit artifact license. Preserve 373 participants / 2,842 decisions and all three interaction confidence intervals; do not infer equivalence. Do not download CSV rows or scripts, contact authors, or infer rights from public access. If no clarification exists, retain both counts and the rights hold. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://www.nature.com/articles/s41598-025-30506-3 ; https://api.osf.io/v2/nodes/gp569/.

### ME006-A1 / ME006-F1: Clarify oversight release and rights

Source ME006; P1; status `bounded_follow_up_not_started`.

Check the Buçinca 2102.09692v1 record, DOI 10.1145/3449287 supplemental-material metadata and the author publication listing for an explicit data/code release and rights notice. Inspect at most those three metadata entry points; stop if none is linked. Preserve 199 participants versus 663 incorrect-AI decision instances, adjusted carb-source means 0.64 / 0.48 with SE 0.03 and p=.003, and nonsignificant complete-decision means 0.30 / 0.26. Keep arXiv CC-BY and author-PDF ACM notices separate. No participant downloads or unrequested outreach. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://arxiv.org/abs/2102.09692v1 ; https://doi.org/10.1145/3449287 ; https://kgajos.seas.harvard.edu/papers/bucinca21trust.pdf.

### ME007-A1 / ME007-F1: Check verified remediation outcome

Source ME007; P1; status `bounded_follow_up_not_started`.

Review the existing official AISI GPT-5.5 safeguards report and any explicitly linked dated correction/retest only. Look for verified final-configuration effectiveness after the six-hour expert bypass and subsequent stack changes. If absent, preserve the three states failure observed, mitigation changed, effectiveness unverified. Do not infer success from a vendor fix or unrelated capability score. Retain the separate trends-study bound Model B >420 minutes and unknown identities/query denominators. Record artifact rights as unknown unless explicitly provided; no attack details, raw logs or model tests. This is a bounded aggregate/metadata follow-up for pdoom-live research. no repository edits, adapter implementation, source execution, login, bulk download, participant identifiers, operational attack payloads or external outreach. Respect access controls. Return evidence URLs/locators, resolved fields and remaining holds; stop after these named artifacts. Sources: https://www.aisi.gov.uk/frontier-ai-trends-report ; https://www.aisi.gov.uk/blog/our-evaluation-of-openais-gpt-5-5-cyber-capabilities.
