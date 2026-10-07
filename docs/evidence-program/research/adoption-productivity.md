# Real-world AI adoption and productivity

Reviewed 7 October 2026 against repository commit `0d593337b6f5921a1b5ebdef2052bdf8dee0cd84`. The [JSON catalog](../../../data/evidence-program/research/adoption-productivity.json) retains all 41 artifact references, access/rights scopes, study identities and next actions. The [64-source inventory](../../../data/evidence-program/source_inventory.json), frozen contract and prior research remain unchanged. All five collections remain **research-only, unadmitted and uncollected**.

## Decision and boundaries

Best first additions: **1. Statistics Canada**, for a bounded structured adoption extract and scoped reuse terms; **2. METR productivity**, for randomized real-task access with rights/method holds; **3. Generative AI at Work**, for routine customer-support outcomes outside coding, with nonrandom-rollout and replication limits.

Four collections are new relative to the inventory; Census enriches GL023. Collection count is not experiment count. CSBC and SDTIU are separate; METR has two studies, distinct from GL004 autonomous horizons; Cui has three main trials plus ancillary evidence.

Reported adoption, administrative outcomes and causal estimands stay separate. Use does not establish routine deployment. Administrative measurement does not establish causality. No labor-market outcomes, participant rows, raw upload, full source dataset, signed URLs, scoring or production import are included. Repository licensing does not override linked artifact rights.

## What verification changed

- StatCan private-sector values 6.2/12.4/19.0 percent were independently rechecked. Source-native dates, flags, metadata and denominator guards are strengthened. The prior out-of-order-response claim was not reproduced.
- METR late release is pinned; early/later missing-review-time conventions differ, and paper HC3 versus early code-comment nonrobust SE remains unresolved.
- Final QJE results/rights were verified through an author-hosted final PDF. The final appendix was not independently reverified, and replication manifest/terms remain unresolved; a manuscript formula is dimensionally inconsistent.
- Cui’s headline is a precision-weighted mean of site W-IV estimates. Preserve ITT, ancillary trial evidence and an unresolved site-date discrepancy separately.
- Census workbook-header success was not reproduced. Catalogue extent is indexed-primary evidence; collection/reference/release dates around the wording break differ.

## AP001 Statistics Canada business AI use and linked productivity

Two distinct evidence units: CSBC weighted adoption aggregates and SDTIU-linked administrative productivity associations. Shared publisher is not shared study identity.

**Coverage/cadence:** CSBC retrospective AI-use module verified for Q2 2024, Q2 2025 and Q2 2026. SDTIU companion pools 2019/2021 waves and was summarized 22 April 2026. CSBC tables explicitly Occasional, despite the broader quarterly survey. SDTIU summary is a static research result.

**Access:** Public table pages, three WDS metadata objects and bounded discrete points without authentication. No complete cube, firm-level panel or administrative microdata downloaded.

**Rights:** Applicable public StatCan tables/publications use the Statistics Canada Open Licence. Preserve prescribed attribution/adaptation notices, not merely a license URL. Underlying publisher paper and confidential inputs have separate unresolved rights/access.

Primary references: [statcan_licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence); [statcan_table_2024](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3310082501); [statcan_table_2025](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3310100401); [statcan_table_2026](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3310116701); [statcan_metadata](https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata); [statcan_points](https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods); [statcan_sdtiu_summary](https://www150.statcan.gc.ca/n1/pub/36-28-0001/2026004/article/00002-eng.htm).

Findings, reported by the primary sources rather than independently recomputed:

- Private-sector values are 6.2%, 12.4%, 19.0%; all-industry values are 6.1%, 12.2%, 19.2%. Each private coordinate is 1.25.1.0.0.0.0.0.0.0 and independently validated against its own metadata.
- The 2026 24.8% LLM figure is conditional on AI use, not all-business adoption, and must be excluded from the proposed adapter.
- Q2 collection windows are 2 April–6 May 2024, 1 April–5 May 2025, and 1 April–6 May 2026. Native refPer January 1 and refPerRaw March 1 are separate source fields; their dates are not collection dates.
- Inspected points: statusCode 3 (A/excellent), symbolCode 0, securityLevelCode 0/public, decimals 1, scalarFactorCode 0, frequencyCode 18/Occasional; metadata unit 239/percent. Grade A denotes an SE category (0 to under 2.5 percentage points), not an exact SE or confidence interval.
- SDTIU Figure 2 gives 16.8%, 10.2%, and 5.1% productivity associations under successively richer controls. First two p<0.01; last not significant. They are nested specifications, not three independent causal effects.
- Fresh response arrived in request order; the earlier claimed out-of-order response was not independently reproduced. Match responses by product/coordinate defensively without claiming an observed ordering failure.

**Sample fields:** WDS: productId, coordinate, vectorId, responseStatusCode; refPer, refPer2, refPerRaw, refPerRaw2; value, decimals, scalarFactorCode; statusCode, symbolCode, securityLevelCode, frequencyCode; metadata memberUomCode, member definitions, footnotes and corrections; native releaseTime (Eastern semantics, no asserted UTC offset); separate wave, collection window and respondent-relative recall; SDTIU result: study, specification, association, significance, source figure.

**Overlap and limits:** Table cells, WDS and comparative articles reproduce the same wave estimates. SDTIU HTML/PDF and three nested specifications share one study; never attach these coefficients to CSBC adoption rows. No source observations admitted; response hashes identify reviewed artifacts but executable fixtures are absent. Do not infer quarterly history beyond inspected module waves. No exact SDTIU formula, sample N, standard errors or public linked microdata established.

## AP002 METR real-work developer productivity experiments

Task-randomized AI access on experienced developers’ own repositories; recorded duration is separate from predictions and representative adoption.

**Coverage/cadence:** Early study: February–June 2025; announcement 10 July and paper v2 25 July 2025. Later experiment began August 2025 and was reported 24 February 2026. Episodic studies and publication/repository revisions; not a regular statistical series.

**Access:** Public versioned paper, official blogs and pinned repositories. Header and first three rows of each CSV were read; no complete acquisition or regression execution.

**Rights:** Paper v2 explicitly CC BY 4.0. Both repository API license fields were null; CSV and code reuse rights remain unspecified. No paper-to-data license inheritance.

Primary references: [metr_early_paper](https://arxiv.org/html/2507.09089v2); [metr_early_csv](https://github.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/blob/7ff2d7670235f531dff77eff58355bd77392f396/data_complete.csv); [metr_early_code](https://github.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/blob/7ff2d7670235f531dff77eff58355bd77392f396/regression.py); [metr_late_csv](https://github.com/METR/Measuring-Late-2025-AI-on-OSS-Devs/blob/55f007216a26493f0a9b7650ab3191cad7fb9e7f/data.csv); [metr_late_code](https://github.com/METR/Measuring-Late-2025-AI-on-OSS-Devs/blob/55f007216a26493f0a9b7650ab3191cad7fb9e7f/regression.py); [metr_late_update](https://metr.org/blog/2026-02-24-uplift-update/).

Findings, reported by the primary sources rather than independently recomputed:

- Early randomization reports approximately 19% longer completion time with AI. Forecasts and recorded outcomes remain distinct.
- 23 February 2026 correction changes README coding to 1=AI allowed and 0=AI disallowed; it does not change the CSV.
- The output labeled speedup is exp(adjusted treatment coefficient)-1; a positive value means longer time. It is not the unadjusted ratio of mean durations.
- Early code imputes missing review time by treatment-specific means; late code zero-fills and excludes ditched issues. Completed and started subsets differ. Preserve raw missingness and explicit transformations.
- Paper v2 names HC3 uncertainty while an early code comment names nonrobust SE; no recomputation resolved that discrepancy. Preserve named publication and implementation conventions.
- Later report gives elapsed-time estimates of -18% for returning and -4% for new developers, both with intervals spanning zero. Selection and measurement changes limit interpretation. These are source-reported results, not recomputed estimates.

**Sample fields:** early CSV: dev_id, issue_id (identifiers documented, no values retained); predicted_time_no_ai; predicted_time_ai_allowed; prior_task_exposure_1_to_5; external_resource_needs_1_to_3; ai_treatment; initial_implementation_time; post_review_implementation_time; late CSV: issue status, study dates and panel membership (schema differs).

**Overlap and limits:** Early paper/blog/CSV are one experiment. Late returning participants create dependence, while tasks are new. No cross-release participant crosswalk established; GL004 horizons are distinct evidence. No CSV or code rights grant verified. No independent execution, uncertainty reconciliation or participant linkage. No macro-productivity, routine organization-wide deployment or p(doom) inference.

## AP003 Generative AI at Work customer-support rollout

Administrative operational productivity in routine customer support, with nonrandom staggered deployment; public result tables rather than an established open microdataset.

**Coverage/cadence:** Manuscript v2 Appendix A.1 documents September 2019–June 2021 records. Final article published 4 February 2025; QJE 140(2), May 2025, pages 889–942. One underlying rollout with manuscript, appendix and final-publication revisions.

**Access:** Author-hosted final publisher PDF directly opened. Publisher landing currently inaccessible; manuscript arXiv v2 separately opened. Code-deposit citation verified, manifest and terms unresolved.

**Rights:** Final article explicitly CC BY-NC 4.0; commercial reuse is not generally cleared. Manuscript and replication deposit rights are separately unverified; no public participant data established.

Primary references: [qje_final_pdf](https://danielle.li/assets/docs/GenerativeAIatWork.pdf); [qje_manuscript_v2](https://arxiv.org/html/2304.11771v2); [qje_replication](https://doi.org/10.7910/DVN/FSV1X7).

Findings, reported by the primary sources rather than independently recomputed:

- Final paper reports 5,172 agents and roughly 15% greater productivity. Table II col.3 is +0.301 resolutions/hour, SE 0.0329 clustered by agent, N=12,295 agent-months. The coefficient is not a percent and N is not the agent count.
- Published prose gives 15.2% relative to the pretreatment baseline. The Table II dependent-variable mean 2.176 is not that baseline and must not be substituted for it.
- The final analysis uses nonrandom staggered rollout with managerial allocation and constrained training/license capacity. Administrative productivity and customer-survey satisfaction are different measurement types.
- arXiv v1 reports about 5,000 agents and 14%; later manuscript/final report 5,172 and about 15%. These are revisions of overlapping evidence.
- Manuscript v2 corroborates September 2019–June 2021 and documented identifiers/timestamps. Its Appendix A.2.3 describes a dimensionally inconsistent division for resolutions/hour; do not implement that wording as a formula. Final-appendix construction remains unresolved.

**Sample fields:** result-table metadata only: publication_version; study_id; outcome; estimand; table_and_column; coefficient; standard_error; standard_error_method; regression_observation_count; observation_unit; normalization_baseline; underlying appendix field descriptions are not public-download columns.

**Overlap and limits:** QJE, arXiv versions, NBER 31161 and institutional summaries concern the same rollout. Keep publication-specific sample/estimate identities; do not count repeated dissemination as independent evidence. Final 52-page appendix was not independently reopened; no signed download link retained. Public raw data, replication file types and deposit rights remain unverified. Outcome construction and exact normalization need verification before derived measurement code. No labor-market outcomes included.

## AP004 Cui and colleagues workplace developer experiments

Three main employer experiments estimate recorded code output under randomized Copilot access, retaining adoption IV, assignment ITT and ancillary evidence separately.

**Coverage/cadence:** Main experiments during 2022–2023; observation windows extend through 2024. June 2025 author manuscript; final publication 27 February 2026 despite DOI containing 2025. Static experiments with manuscript and publication revisions; not a continuous productivity series.

**Access:** Publisher landing, public appendix and author manuscript opened. Supplement links replication files, but downstream retrieval failed; package contents are unknown.

**Rights:** Copyright 2026 INFORMS observed; no applicable open license established for paper, appendix, author manuscript or replication package.

Primary references: [cui_publisher](https://pubsonline.informs.org/doi/10.1287/mnsc.2025.00535); [cui_appendix](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2025.00535/suppl_file/mnsc.2025.00535.sm1.pdf); [cui_manuscript](https://www.mertdemirer.com/Papers/Demirer_AI_productivity.pdf); [cui_supplement](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2025.00535).

Findings, reported by the primary sources rather than independently recomputed:

- Main sample is 4,867 developers (1,521+316+3,030). The 26.08% (SE 10.3) headline is a precision-weighted mean of site W-IV estimates for adoption induced by assignment, not one pooled regression or an ITT/time-speedup estimate.
- Appendix Table 5 two-site early-window pull-request ITT is 4.66% (SE 3.56), not significant; Microsoft 29 weeks and Accenture 21 weeks. Its site set, windows and estimand differ from the main W-IV result.
- Appendix E/Table 8 also reports an abandoned first Accenture trial, N=204, pull-request W-IV -39.18% (SE 36.78), with imputed control adoption. Retain it as qualified ancillary evidence, outside the three main trials and headline pool.
- Table 1 gives Microsoft experiment Sep 2022–Apr 2023/observed Jan 2022–Apr 2024; Accenture Jul–Dec 2023/observed Jul 2022–Mar 2024; anonymous Sep–Oct 2023/observed Jun 2023–Feb 2024. Section 2.2 says anonymous trial started October 2023: exact start remains unresolved.
- Studied tool is 2022–23 Copilot autocomplete. Initial Microsoft adoption can mean registration; later definition uses observed usage. Postregistration is reported, not preregistration.

**Sample fields:** study_id; site_id; publication_version; experimental_window; observation_window; assignment; adoption_definition; outcome; estimand; estimate; standard_error; normalization_baseline; analysis_sample; table; specification.

**Overlap and limits:** Three main site experiments share derived pooled results; pooled estimate is not a fourth trial. Earlier versions overlap, but an exact two-company version crosswalk is unverified. Ancillary abandoned Accenture trial is outside headline N and pool. No exact model checkpoint or serving configuration established. No replication manifest, microdata, executable reproducibility or redistribution right verified. Do not quietly resolve anonymous-company start dates or collapse revisions. No labor-market outcomes extracted.

## AP005 US Census BTOS AI-use core and supplement

Existing GL023 enrichment: reported adoption with explicit question, denominator, recall-window and wording-regime boundaries; workbook availability and cells remain unverified.

**Coverage/cadence:** Core AI questions from September 2023. Second AI supplement collected 17 November 2025–8 February 2026. Search-indexed catalogue lists 11 September 2023–20 September 2026, but workbook extent and date roles were not inspected. Biweekly aggregate releases; individual businesses report once per 12 weeks for a year. Supplement timing and six-month recall are separate.

**Access:** Official story, questionnaire, CES paper and overview read. Direct download catalogue/help render JS shells; primary indexed content qualified separately. National.xlsx open returned Internal Error; no headers/body/cells inspected.

**Rights:** Workbook internal notices uninspected. DS027 is general US government-work policy with foreign/nonemployee exceptions, not a verified worldwide license. CES paper explicitly requires author clearance for republication.

Primary references: [btos_story](https://www.census.gov/library/stories/2026/05/ai-use-businesses.html); [btos_questionnaire](https://www.census.gov/hfp/btos/downloads/BTOS%20Core%20and%20AI%20Content.pdf); [btos_ces](https://www2.census.gov/library/working-papers/2026/adrm/ces/CES-WP-26-25.pdf); [btos_catalogue](https://www.census.gov/hfp/btos/data_downloads); [btos_national](https://www.census.gov/hfp/btos/downloads/National.xlsx); [btos_rights_policy](https://www2.census.gov/foia/ds_policies/ds027.pdf).

Findings, reported by the primary sources rather than independently recomputed:

- Official article reports 19.8% current AI use as of 3 May 2026. This is article-derived, not a verified workbook cell; retain its period wording pending actual workbook mapping.
- First revised wording collection was 17–30 November 2025, referring to 3–16 November, released 4 December 2025. Release-date wording in help is not a contradictory collection date.
- Q23 asks current two-week use; Q24 and Q30–32 concern prior-six-month functions/tasks; Q32 is conditional on Q31 Yes; Q33 is expected future use. Preserve question and denominator identity.
- Catalogue range through 20 September 2026 is supported at primary search-index level only; live workbook schema, rights notices, uncertainty fields and values remain uninspected.
- Employer-business frame and six-panel reporting cadence are documented; the approximately 1.2 million sample is not a completed-response count or biweekly census.

**Sample fields:** documented questionnaire fields, not verified workbook columns; Q23 current two-week AI use; Q24 15 functions in prior six months; Q30 employee AI task use; Q31 employee GenAI task use; Q32 conditional GenAI task categories; Q33 expected next-six-month use; questionnaire version, wording regime, reference/collection/release dates, population and response category.

**Overlap and limits:** Deduplicate matching item/population/period/release across story, workbook and CES representations. Core two-week use, six-month retrospective functional/task use and expected use are distinct observations; preserve November 2025 wording break. Previously claimed XLSX content-type success was not reproduced; no fetched/parsed workbook claim. Public aggregate access is separate from approved-project-only microdata access. General government copyright policy cannot silently clear all linked artifacts.

## Proposed StatCan adapter

`statcan_csbc_private_ai_use` is **proposed, not implemented**. The integration’s small offline helper validates catalog consistency only. Source-response fixture packaging and a lossless record mapping remain open; no frozen-contract reinterpretation is implied. Offline design work is feasible, but source acquisition, operational admission and contract evolution remain distinct steps.

The frozen v0.1.0 schema already supports `resource_observation`, `resource_kind=adoption`, `measurement.observation_mode=reported`, and `percent` units. This is the concrete mapping candidate; a schema change is not established as necessary. Remaining design work is a lossless treatment of native flags, metadata and distinct date roles through source artifacts, upstream references, method and scope. No full records have been emitted or validated.

Exactly three output points: Canada/private-sector/affirmative retrospective use, products `33100825`, `33101004`, `33101167`, coordinate `1.25.1.0.0.0.0.0.0.0`, yielding reviewed values 6.2/12.4/19.0 percent. The values are historical verification targets, not permanent-value assertions. No source observations are embedded as importable records.

Acquisition design: only three metadata objects and three private-sector points. Extra denominator controls from verification do not expand collector scope. Pin code-map evidence or separately review any extra request. Identity uses product, coordinate and native reference period; metadata, footnotes, values and release information all participate in revision handling.

Acceptance requirements, **not executed adapter tests**:

1. Reviewed fixtures yield exactly 6.2, 12.4 and 19.0 percent for three source identities. Later source revisions create reviewable versions, not permanent-value assertions.
2. Validate Canada/private-sector/affirmative retrospective-use members for each product. Reject all-industry 19.2 and conditional-LLM 24.8 from private adoption output.
3. Reject expected-use items, application shares, duplicate keys, missing keys and unexpected products or coordinates.
4. Require SUCCESS, object responseStatusCode 0 and exactly one point for latestN 1; transport success is distinct from per-point quality.
5. Preserve both native refPer/refPerRaw and ending fields, wave and collection windows; recall is respondent-relative 12 months. Native January/March values are not collection dates.
6. Preserve native releaseTime and documented Eastern semantics. No invented UTC Z or inferred timezone offset.
7. Shuffled input order yields the same identities/output. This is a defensive test, not an independently reproduced source-order failure.
8. Retain exact decimal strings, percent unit239, scaling, precision, frequency and raw quality/symbol/security codes separately. Missing/suppressed values never become zero or invented exact SE.
9. Idempotent re-ingestion; changed value, metadata, footnote, population or question retains predecessor and requires review. Mirrors add provenance, not observations.
10. Every point remains descriptive reported adoption with unspecified deployment maturity; no measured productivity, causal effect, firm panel or p(doom) generated.
11. Bound acquisition to three allowlisted metadata objects and three points, configured byte/time limits and no bulk downloads. Negative controls are local reviewed fixtures, not additional collector requests.
12. Export applicable official reproduction/adaptation attribution, product/reference metadata and licence URL; do not inherit rights for confidential or third-party inputs.
13. Network disabled in deterministic tests; raw source fixtures, if later packaged, require durable bytes/hash and provenance rather than reconstructed report snippets.

## Next-action log

Bounded work already handled: all five primary-source reviews; exact METR later pin; StatCan denominator/flag/date checks; QJE final-publication fallback; Cui estimand/trial distinctions; Census date-role clarification. Local catalog validation and regression coverage add safe checks without claiming adapter completion.

- **AP-A01 / completed_bounded_work / completed:** Bounded verification and research-only integration: reconcile five collections, exact artifact access levels, inventory relationships, corrected estimands/dates, source pins, and explicit holds. Done when: Dated source metadata and findings below; deterministic catalog tests verify consistency only. No admission, live collector or raw source bundle.
- **AP-A02 / offline_implementation_design / pending_contract_review:** Prepare durable bounded StatCan fixtures and an explicit lossless mapping before implementing the three-point adapter. Offline design is feasible within research scope; a frozen-contract change or operational collection must stay separately reviewed. Done when: Existing v0.1.0 core mapping candidate is resource_observation/adoption/reported/percent. Finish lossless native provenance/date/flag handling and durable reviewed fixture bytes/hashes; execute proposed offline tests without contract drift. Current catalog validator is complete; source-payload parser remains unimplemented.
- **AP-A03 / rights_and_method_hold / pending_rights_review:** Before data/code retention or recomputation, establish artifact-specific METR reuse rights and reconcile publication-version uncertainty conventions. Done when: Explicit applicable CSV/code permission or unresolved rights hold; named HC3 versus nonrobust convention and preserved early/late imputation/filtering. No participant crosswalk inferred.
- **AP-A04 / access_dependent / blocked_access:** Before derived QJE outcomes, inspect a lawfully accessible final appendix and public replication manifest/terms; resolve productivity construction and normalization without bypassing current failures. Done when: Stable manifest, file types, scoped rights and source-backed formula; distinguish code/synthetic/confidential inputs. If still inaccessible, keep published results only.
- **AP-A05 / access_dependent / blocked_access:** Before Cui package acquisition or exact historical linkage, verify public manifest/README/rights and publication/site date crosswalk. Done when: Stable package metadata without full archive, separate code/data rights, main versus ancillary trial identities, and a resolved or explicitly unresolved anonymous-company start date.
- **AP-A06 / access_dependent / blocked_access:** Before a BTOS adapter, inspect bounded workbook metadata and one national AI-use sample if safely supported; reconcile actual date/uncertainty/rights fields. Done when: Actual workbook size, sheets/headers, exact cell provenance and period semantics, rights notices and suppression/uncertainty; stop if safe bounded access cannot be established.
- **AP-A07 / access_dependent / blocked_access:** Before SDTIU derived outcomes, obtain lawfully accessible full methods or an authorized excerpt for DOI 10.3138/cpp.2025-065. Done when: Productivity numerator/denominator, transformation, administrative source, N/selection, SE, specification interpretation and separate paper rights; no confidential firm-level records.

## Focused research follow-ups

Five independently copyable prompts remain because the missing evidence has different source/access boundaries. Use only before the corresponding acquisition or derived analysis; do not repeatedly retry an exhausted route. AP-A02 is an offline implementation-design action above, not another source-research prompt.

### AP-A03

Paper rights do not license separate CSV/code; statistical conventions conflict.

Source URLs: https://arxiv.org/html/2507.09089v2 ; https://github.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/tree/7ff2d7670235f531dff77eff58355bd77392f396 ; https://github.com/METR/Measuring-Late-2025-AI-on-OSS-Devs/tree/55f007216a26493f0a9b7650ab3191cad7fb9e7f . Before any authorized METR recomputation, resolve only public artifact-specific data/code rights for the two pinned releases and the paper-v2 HC3 versus early-code nonrobust comment discrepancy. Preserve both waves’ raw missingness, imputation and filtering. Return source-backed resolution or an explicit hold. No author contact, login, execution, participant linkage or collection. Read-only bounded public-source research only. No login, outreach, access-control bypass, bulk acquisition, repository change or operational admission.

### AP-A04

Final appendix was not independently reverified, replication manifest/terms remain unresolved, and a manuscript formula is dimensionally inconsistent.

Source URLs: https://academic.oup.com/qje/article/140/2/889/7990658 ; https://doi.org/10.7910/DVN/FSV1X7 ; https://arxiv.org/html/2304.11771v2 . Verify only public final-appendix outcome construction and replication manifest/terms for QJE DOI 10.1093/qje/qjae044 and deposit 10.7910/DVN/FSV1X7. Inspect the resolutions/hour formula and normalization; distinguish file types and rights. Respect recorded access failures/denials, use stable links, and stop at access controls. No signed URLs, participant records, login, author contact or code execution. Read-only bounded public-source research only. No login, outreach, access-control bypass, bulk acquisition, repository change or operational admission.

### AP-A05

Package content/rights and anonymous-site exact start remain unresolved.

Source URLs: https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2025.00535 ; https://www.mertdemirer.com/Papers/Demirer_AI_productivity.pdf . For Cui DOI 10.1287/mnsc.2025.00535, inspect only accessible public supplement metadata, manifest/README and code/data rights. Compare primary version identities and Table 1 September–October 2023 versus Section 2.2 October start without silently choosing one. Preserve three main trials and the separate ancillary abandoned Accenture trial. No full archive, login, contact, participant download or access bypass; return unresolved where necessary. Read-only bounded public-source research only. No login, outreach, access-control bypass, bulk acquisition, repository change or operational admission.

### AP-A06

Neither workbook headers nor body were obtained; article date wording is not cell provenance.

Source URLs: https://www.census.gov/hfp/btos/data_downloads ; https://www.census.gov/hfp/btos/downloads/National.xlsx ; https://www.census.gov/library/stories/2026/05/ai-use-businesses.html . At the official BTOS catalogue and National.xlsx endpoint, establish workbook size and safe bounded access first. Inspect only metadata/headers and a tightly bounded national AI-use sample when feasible; otherwise report the blocker. Record sheets, question IDs, units, uncertainty/suppression and rights notice, and reconcile article 19.8% as of 3 May 2026 with actual collection/reference/release semantics. Preserve the November 2025 wording break. No microdata, bulk download, login or admission. Read-only bounded public-source research only. No login, outreach, access-control bypass, bulk acquisition, repository change or operational admission.

### AP-A07

Public summary lacks exact variable construction and uncertainty; publisher paper returned 403.

Source URLs: https://www150.statcan.gc.ca/n1/pub/36-28-0001/2026004/article/00002-eng.htm ; https://utppublishing.com/doi/10.3138/cpp.2025-065 . For Li/Liu DOI 10.3138/cpp.2025-065, verify a lawfully accessible full-text methods source or authorized excerpt without bypassing the publisher 403. Identify productivity numerator/denominator, deflation/transformation, administrative datasets, analysis windows, N, selection, SE and percentage interpretation. Preserve three nested specifications and separate rights. Do not request or seek confidential firm records. Read-only bounded public-source research only. No login, outreach, access-control bypass, bulk acquisition, repository change or operational admission.

## Offline verification

Run `python tools/evidence_program/check.py`. It keeps the unchanged frozen 71-test contract suite and prior research checks, and adds catalog-consistency regressions. Passing is not proof of source truth, rights, statistical validity, an implemented adapter or successful production import. Raw API response hashes identify reviewed artifacts; durable executable fixtures were not packaged. See the [tooling guide](../../../tools/evidence_program/README.md).
