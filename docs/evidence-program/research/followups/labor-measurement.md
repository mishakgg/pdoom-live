# Labor measurement lineage follow-up

Decision: accept the bounded BLS and O*NET findings, with precise qualifications; accept the narrower Indeed article result while retaining the historical-comparison hold. Repository access and ID association are now resolved. Full lossless canonical mapping and operational admission remain held.

This version includes an independently cleared, additive research delta for deep prompt 1 / bundle A, enriching original Session 14. Source admission, ingestion, adapters and lossless canonical mapping remain unapproved. Bundle B’s separate substantive review is starting; C/D remain queued. Candidate preparation does not establish remote publication, CI or merge.

[Reviewed delta](../../../../data/evidence-program/research/followups/labor-measurement.json) · [Historical catalog](../../../../data/evidence-program/research/labor-market.json) · [Historical guide](../labor-market.md) · [Follow-up queue](follow-up-queue.md)

The source review and independent clearance are machine documentary reviews; neither is human verification.

## Provenance and sequencing

- Original campaign session: 14, Labor-market effects and skill demand.
- New coverage-follow-up prompt: sequence 1, Resolve labor measurement lineage.
- Immutable intake: bundle A intake manifest, SHA-256 `7362c9e8e5f23b8dec8527dc7d22060f2cdf260f178cbe0a5918d52867c7263f`.
- Original submitted files retain their verified hashes: pasted text `a16843625e5168938b05b2eb6bc118cbb307bc292450c46e72e13c624e0810ba`; PDF `3e89d6918171610994d50a530c6eff26fb27ae4729a22b1d19c38610978f2708`; JSON `470c7e6f374f1fd7fee6ccafa0a7fd5267c8684b6e64edb220b981689f3e86ba`.
- The external session's inspected commit remains null. The reviewer separately inspected [main at 87dda3d](https://github.com/mishakgg/pdoom-live/tree/87dda3d74f9f9874e82d83d1628b53f9da4b5526), including AGENTS, priorities, 64-family inventory, original queue, labor guide/catalog, follow-up queue/prompt, and existing schema/dictionary/unit registry. That was the source-review main snapshot. Candidate integration separately reconciles hash-verified scoped files at [2266b566](https://github.com/mishakgg/pdoom-live/tree/2266b56681812cde175257734dc16ed1c88c1323), including PR 337’s later intake and prompt log.
- The [repository mapping](../../../../data/evidence-program/research/followups/labor-measurement-repository-mapping.json) includes exact Git blob and SHA-256 checks for 15 source-review repository files and keeps submitted and reviewer provenance distinct. The delta also binds the independently cleared source outputs by SHA-256; public remapping does not change their historical inspection claims.

LM001/LM002/LM004 are research candidate/collection IDs. Their family IDs are respectively bls-oews, indeed-ai-tracker and onet-task-ratings; all three inventory_source_id values remain null. The catalog confirms LM-A03/LM-P01, LM-A04/LM-P02 and LM-A06/LM-P04. LM003/GL022 and GL023/AP005 were not reassigned or researched.

## Accepted findings and exact limits

### LM001: workbook branch completed

The reviewer independently downloaded the single [official May 2025 national ZIP](https://www.bls.gov/oes/special-requests/oesm25nat.zip) under the 2 MiB cap, then statically inspected its ZIP/XML structure under the 10 MiB expansion cap. No spreadsheet application, macros or formulas were executed.

- ZIP: 279,525 actual bytes; SHA-256 `b5855a37f3e03e779f6fbf173d3bbc94aeeff33426aef32fa95ce6d025bab1af`.
- XLSX member: 289,615 bytes; SHA-256 `852250997ceff9b721ff68f63e877d818f9c1ec8b1b69dd367958faedd5282b2`.
- Conservative nested expanded size: 1,986,341 bytes. A printer-settings binary is metadata, not executable code; it was not executed. There are zero formula nodes.
- All 32 header fields and all 64 cells in `national_M2025_dl!A2:AF2` and `A149:AF149` match the submitted ledger, including raw XML values/types/styles and decoded values. Four sheet identities and dictionary rows are confirmed.

The All Occupations row has 155,495,730 jobs; mean wages USD 33.54 hourly / 69,770 annual; median wages 24.51 / 50,980. The Software Developers row has 1,687,890 jobs; mean wages 71.20 / 148,100; median wages 65.38 / 135,980. Preserve these separate statistics, not a reconstructed annual value from a rounded hourly number.

EMP_PRSE is 0.0 as displayed for all occupations and 0.6 for software developers; MEAN_PRSE is 0.1 and 0.4. `xl/styles.xml` confirms number format 0.0 for the raw zero cell. Neither statistic supplies median uncertainty. Four national cross-industry blanks are dictionary-supported not-applicable values; empty ANNUAL/HOURLY flags stay distinct from a missing wage and from false numerical values. The two rows contain no *, **, # or ~ marker; marker acceptance cases are explicitly synthetic.

The [release](https://www.bls.gov/news.release/archives/ocwage_05152026.htm), Technical Note and Table 1, confirms May 2025 reference, 15 May 2026 publication, 2018 SOC, 2022 NAICS and November 2022 through May 2025 panels. The [FAQ](https://www.bls.gov/oes/oes_ques.htm), MB3 and comparisons-over-time sections, confirms the 2021 method boundary and six-panel rotation. Four shared panels in adjacent releases is an inference from rotation, not a covariance estimate. Annual wages are wage rates, not realized earnings.

The [MB3 listing](https://www.bls.gov/oes/oes-mb3-methods.htm) separates 2015–2020 alternatives. Its [methods paper, p. 2](https://www.bls.gov/oes/mb3-methods.pdf) states same sampling methods and direct comparability to ordinary estimates. Preserve shared survey-program lineage and method-specific alternatives, not independent replication. No historical panel was downloaded.

This resolves the old lm001_zip headers-only limitation and the named LM-A03 workbook question. Row-specific N, median/percentile SE or CI, and cross-release covariance remain unverified/unpublished in inspected records. BLS statistical reuse remains scoped to its [public-domain policy and exceptions](https://www.bls.gov/opub/copyright-information.htm).

### LM004: named lineage branch completed with residual holds

Two bounded 16,384-byte prefixes were independently fetched and hashed:

- [31.0 CSV](https://www.onetcenter.org/dl_files/database/db_31_0_csv/task_ratings.csv): excerpt SHA-256 `f111680bfaf1fa8d3470d95a561f4a71b7abb9e7b1b281e20f386c70ea5963ff`.
- [28.3 text](https://www.onetcenter.org/dl_files/database/db_28_3_text/Task%20Ratings.txt): excerpt SHA-256 `39c64513862dc5f589c7b5fde08496de229ade24b0f8358872b1e04294547dac`.

The nine task 8823 records match on 11 common non-category fields. Seven FT categories also match literally. IM/RT Category is blank in 31.0 and n/a in 28.3, so their match requires documented scale-specific not-applicable normalization. The submitted ledger correctly preserves this; its pasted summary is less precise. Never call the prefixes or full files identical.

Chief Executives / task 8823 / FT / category 1 retains 5.92 percent, N 76, SE 4.2651 percentage points, published CI [1.3474, 22.4442] percent, suppression N, Incumbent and update 08/2023. Category 1 is Yearly or less, not a working-time share. The [uncertainty appendix](https://www.onetcenter.org/dictionary/31.0/csv/appendix_incumbent.html) documents the percentage-RSE log transformation; a naive SE/value calculation must not replace the source flag.

The [longitudinal workbook](https://www.onetcenter.org/dl_files/Longitudinal_Data_Updates.xlsx) is independently verified: 346,734 bytes, 2,977,328 expanded bytes, SHA-256 `f5c5e6853b8a5dd6520812929e9e711f6afc860c71a45f8255c94a83a731e260`. Tasks!A2:L2 traces Chief Executives to 08/2023 / 28.0 and prior update entries; A113:F113 traces Software Developers to 08/2025 / 30.0. The current/prior database license explicitly covers downloadable archive material with version attribution and conditions. It does not supply full OnLine body rights.

The [update history](https://www.onetcenter.org/dictionary/30.3/text/appendix_updates.html) confirms 28.2 precision, 29.0 retention and 25.1 transition rules. 28.3 text has 12 fields while its Excel dictionary and 31.0 CSV have 15; format enrichment is not a new survey. [Emerging Tasks](https://www.onetcenter.org/dictionary/31.0/excel/emerging_tasks.html) are proposed collection content, distinct from incumbent ratings and predecessor aggregates. Task disappearance is not automation evidence.

[OnLine's source section](https://www.onetonline.org/link/summary/15-1252.00) and [BLS EP Table 1.2, row 15-1252](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm) preserve OEWS wages versus EP 1,717.8 thousand employment. The 29,910 gap is arithmetic, not reconciled accounting or an identified cause. Exact task fieldwork, original May 2024 bytes and a complete employment reconciliation stay held.

### LM002: article verified, historical comparison held

The [Canada article](https://hiringlab.indeed.com/en-ca/2026/07/08/ontario-job-postings-highlight-the-widespread-use-of-ai-in-hiring-processes/), main comparison, interpretation section and Methodology, supports Ontario 9% in October 2025 and 28% in May 2026 as monthly averages of daily posting shares. The 19-percentage-point difference is arithmetic on rounded figures. Recruitment-disclosure interpretation is the producer's measurement qualification. It is not a causal legal-effect estimate or a pinned national-CSV result. Counts and uncertainty stay null. The [FAQ](https://hiringlab.indeed.com/indeed-data-faq-2/) distinguishes postings, stocks and flows from jobs/hires.

The submitted session's pinned tree/README access restrictions were respected; this review did not retry them or open the excluded Ontario legal page. No earlier revision or dictionary/backfill history was acquired.

Crucially, the new session's access failure does not invalidate prior reviewed evidence. Current main already preserves bounded pinned CSV schema/coverage, seven-day trailing averaging, monthly refresh, the pinned tree's absence of GenAI_posting.csv, and CC BY 4.0 for Hiring Lab-generated aggregates in LM002-F01/F02/F03/F06/F07. Retain those as prior verified findings with their original scope; do not upgrade them to a newly observed historical comparison or erase them because the external session could not reproduce access. Article/body rights remain separate.

## Public-safe provenance closure

The revised delta is self-contained for source resolution: 34 artifact metadata records carry exact URLs, locators, source revision and separately labelled submitted/reviewer rights assessments. Every observation artifact pointer and lineage endpoint resolves inside the delta. All 11 selected observations, all 32 original acceptance inputs/expected decisions/rationales, and 10 lineage edges are retained. The three OnLine/EP observations explicitly retain reference year 2025 and, for employment, the 2025–2035 source window. No full downloaded source bodies are embedded.

Every copied observation now labels its inherited status/evidence_basis and microsecond retrieval clocks as submitted-session provenance. Independent reviewer recheck receipts are separate. Each acceptance case has an explicit reviewer-current disposition, especially where repository access is resolved or prior Indeed facts remain verified. Historical access failures are preserved without becoming current conclusions.

One display correction was added during independent review: the submitted BLS source_display_value strings omit grouping commas for cells with style s=2 and built-in format #,##0. Raw XML and decoded values were correct. The review layer keeps those strings as submitted_source_display_value and adds reviewer_style_derived_display, including 155,495,730; 1,687,890; and 135,980. This is a static number-format interpretation, not a spreadsheet-application rendering check.

## Repository mapping and validation

The [contract mapping](../../../../data/evidence-program/research/followups/labor-measurement-contract-mapping.json) gives 18 field-group mappings to actual existing schema pointers and maps all 32 submitted manual cases. It closes the access-only gap but identifies substantive limits:

- Existing canonical decimals are strings, not JSON numbers. Unit count requires jobs semantics; currency_nominal requires USD basis and rate denominator/context.
- The value union handles points, intervals, bounds and typed missingness, but one result cannot simultaneously type a point, SE and CI. Source suppression, PRSE, full dimensions, panel clocks and dependence lack dedicated typed fields.
- Collective actors do exist. Do not falsely claim aggregate subjects are impossible, or substitute the source publisher as measured population. Actual subject identity and scope still need reviewed mapping.
- The registry lacks a percentage_point unit. Do not convert 19 percentage points into percent_change.
- Unknown sample size is omitted with a reason; zero/null in sample_size is invalid. Unknown fieldwork stays unknown. An excerpt digest cannot populate an implied whole-file identity.
- Semantic source fidelity is not guaranteed by syntax: a fabricated zero and a wrong FT working-time description can pass primitive schema checks and must still be rejected by documentary review.

Source review executed: [158 evidence/input/blob/cell checks](../../../../data/evidence-program/research/followups/labor-measurement-review-validation.json) and [26 synthetic Draft 2020-12 schema-fragment cases](../../../../data/evidence-program/research/followups/labor-measurement-schema-fragment-cases.json), all with expected outcomes. The external session's original 32 cases remain manual semantic checks (14 observed, 18 synthetic). Full canonical labor-record validation, repository-wide tests and CI were not run by the source review. Candidate integration checks are separately reported and cannot turn the fragment probes into full canonical validation. No claim of full schema admission is made. All four PDF pages were rendered and visually inspected; tables are legible and agree with the ledger subject to the normalization clarification.

## Action disposition and remaining work

The [reviewed actions](../../../../data/evidence-program/research/followups/labor-measurement-actions.json) close LM-A03 / LM-P01 for the bounded workbook review and LM-A06 / LM-P04 for the named lineage questions, with the residual holds above. LM-A04 / LM-P02 is partly completed: the article is reviewed and the historical comparison stays held. LM-A09 / LM-P07 has a completed component review while lossless mapping and full canonical semantic validation stay held.

The original labor catalog is a fingerprinted historical review and remains byte-preserved. This linked follow-up precisely supersedes its BLS headers-only/workbook-uninspected statements for the two named rows and its uninspected O*NET longitudinal-workbook branch for the selected cells. Neither supersession extends to a complete archive or new raw-data reuse. The frozen 64-family inventory, LM003/GL022 Eurostat fixture and reader, and GL023/AP005 BTOS holds are unchanged.

The public JSON carries all 34 artifact metadata records, 11 selected observations, 32 original manual acceptance cases (14 observed, 18 synthetic) with reviewer-current dispositions, and 10 lineage edges. Supporting references use public URLs and repository paths. Original PDFs and raw ZIP/XLSX/CSV/page bodies are not vendored. Source rights, version attribution and exceptions remain artifact-specific; the repository’s metadata license does not replace the O*NET data license or Indeed aggregate attribution obligations.

This is new deep prompt sequence 1, not a replacement original session or an additional original-session count. Its independently reviewed delta is included in this candidate. Publication, exact-commit CI and remote merge must be verified separately. Remaining research holds require unavailable historical/design evidence, a separately authorized mapping decision or specific rights; no denied-route retry, large acquisition or new adapter is warranted.

## Attribution and source-rights notice

BLS is the source of the selected OEWS and Employment Projections statistical facts. Its [reuse policy](https://www.bls.gov/opub/copyright-information.htm) retains image, emblem and third-party exceptions.

Selected O*NET® 31.0 and 28.3 database facts and longitudinal metadata are attributed to the U.S. Department of Labor, Employment and Training Administration, and the National Center for O*NET Development under the [database license and prior-version terms](https://www.onetcenter.org/license_db.html) and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changes here are bounded selection, documentary annotation and the explicitly disclosed IM/RT not-applicable normalization; original source values and versions are retained. No endorsement is implied. O*NET® is a trademark of USDOL/ETA.

Indeed Hiring Lab is the source of the attributed Ontario article facts and of the previously reviewed pinned aggregates. The prior aggregate-data CC BY 4.0 grant is preserved with its original scope; it does not license the full article, FAQ or underlying job advertisements. The repository’s dedication applies to its own review metadata and annotations and does not replace these source-specific conditions.
