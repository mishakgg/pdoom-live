# Survey instrument and denominator follow-up

Reviewed 8 October 2026. Bounded documentary checks are complete for FS001, FS002, FS003 and LM003. They establish specific report, caption, instrument and model-period facts while preserving unresolved administration, denominator, weighting, edition and rights questions.

[Machine-readable delta](../../../../data/evidence-program/research/followups/instrument-denominator.json) · [Follow-up queue](follow-up-queue.md)

The historical [forecast-survey](../forecast-surveys.md) and [labor-market](../labor-market.md) catalogs keep their original bytes. Exact existing artifact/finding/action/prompt/hold IDs are linked in the JSON. New documentary versions are related records: arXiv v3 is not the existing landing-page bytes, and the Eurostat 2022-model manual is not the older `lm003_reference` artifact supporting 2024→2023.

## FS001: ESPAI report evidence and questionnaire editions

The [2024-wave report](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf) supports the following documentary reconstruction. It was read as extracted text; native PDF bytes, graphical Figure 3 nodes and visual table alignment were not independently verified.

- Population and clocks, §2.1, printed p.4: 19,874 contacted addresses after known failures, 2,052 complete/partial returns and 1,580 eligible included participants. Of these, 1,502 reached the final question and 78 were partial; reaching the final question does not establish every-item completeness. Fieldwork was 9–24 December 2024; publication was September 2026.
- Framing, §§2.4–2.5, pp.6–7: participant-level half/half assignment retained through the survey. Assignment probabilities are routing, not analysis weights or realized item counts.
- Direct-risk variants, §3.9 and Table 4, pp.22–23/27: valid-item n is 744/392/353. The reported 2:1:1 routing implies assignment probabilities 1/2, 1/4, 1/4. Two horizons remain unspecified; the third is 100 years relative to elicitation, with no invented calendar cutoff. The outcome includes permanent severe disempowerment as well as extinction, and the control variant preserves its different mechanism. The publisher-combined n=1,489 is not a fourth sample; no pooling was performed here.
- Construct boundary, §3.8 and the comparison on p.28: direct-risk questions do not assume eventual HLMI. The separate long-run impact allocation does, has five categories summing to 100%, and n=1,538. Do not transfer its condition or denominator.
- HLMI, §3.2 and Appendix E/Table 6, pp.12/43: fixed-probability/fixed-year valid n=537/471 stays separate from fitted n=985. Report-supported probability thresholds are 10/50/90%; exact 2024 fixed-year horizons remain null.
- FAOL, the same sections: fixed-year/fixed-probability valid n=233/234 stays separate from fitted n=456. The four occupation names are report labels, followed by nomination/forecasting of a late occupation and then FAOL. Exact administered occupation prompts, FAOL horizons/probability thresholds and the scientific-disruption condition's FAOL scope remain unverified.

The reported pointwise mean-CDF aggregation gives equal contribution to each fitted respondent distribution. That is not a survey-weight vector, effective sample size or proof of identical case sets across fitting losses. No distributions were fitted or re-estimated.

### Required edition qualification

FS001-F05/F06 cite `fs001_02`, the 2023 questionnaire. Their exact 10/20/40 and 10/20/50 horizons must not populate 2024 fields. The standalone 2024 questionnaire route was not retried; report-derived constructs and routing are not an independent report-to-administered-instrument match. Separate report/questionnaire rights remain unresolved; website CC0, another paper's CC BY and code licenses do not transfer automatically.

### 2022 elicitation, different analysis editions

[arXiv v3](https://arxiv.org/html/2401.02843v3), §3.2.1 footnote 1, and the September 2026 report, p.1 footnote 1, support 2059 → 2060 → 2059 as analyses of the same 2022 elicitation. The first is a retrospective author assertion in this review; the original 2022 page was not reread. The inspected v3 was uploaded 8 October 2025, distinct from the survey/report's “2023” context. Code/cleaning changes are the authors' explanation; no respondent belief change or new elicitation is inferred.

v3 Appendix B.2/Table 6 supplies 2022 HLMI cleaned-response n=461 for that edition only. Common cross-revision n and unchanged case identity stay null. The [16 December 2024 reanalysis note](https://blog.aiimpacts.org/p/reanalyzing-the-2023-expert-survey) concerns the 2023 survey; it is context, not resolution of this specific shift.

FS-A03 / FS-P01 / FS-H01 retain the standalone-instrument, exact-field, rights, mirror/panel and common-case holds after the bounded report reconstruction is marked complete.

## FS002: XPT thresholds remain conflicting

At the existing pin, [QuestionInfo.csv](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/QuestionInfo.csv), logical record 3, says >10% mortality; [questionMetadata.csv](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/data/questionMetadata.csv) says >1% in all four stage subtitles. Exact file-byte hashes and Git-framed blob identities were recomputed separately. Administered Q3 threshold stays null.

The 20 June 2022 clarification concerns the five-year period's inclusive 15 June 2022 start and end before resolution. The 28 June clarification concerns proximate causation and substantial AI involvement in the preceding year. Neither changes the threshold. The README's description of clarifications issued to forecasters does not certify the conflicting interface subtitle. Appendix 6 was not retried.

Q4 is extinction OR global population below 5,000, with its distinct causation definition. The 59 sets, 236 stage rows and four stages are metadata units, not respondent counts. Defaults emit no forecasts; ordinal timestampId is not elapsed time; predicted other-group beliefs are not observed group aggregates. Item-stage n, weights and effective n remain unknown. Pinned MIT software/documentation evidence is material but does not clear every CSV/report's raw redistribution. FS-A04 / FS-P02 / FS-H02 retain these holds.

## FS003: LEAP's caption has a narrow scope

The [Wave 12 report](https://leap.forecastingresearch.org/reports/wave12), Policy Probabilities Question II / Policy Support caption, explicitly connects its equal weighting to all forecast tables. Its immediate subject is within-group policy-support shares, which are not raw headcounts. It does not identify the equal-weighting unit, exact algorithm, table-n meaning, AI Risk Expert weights, effective n or overlap.

The opening still reports 157 experts while category counts 25/34/38/52 sum to 149. The arithmetic gap of eight is not an uncategorized group. [Initial methods](https://forecastingresearch.org/research/longitudinal-expert-ai-panel-leap-working-paper), released 10 November 2025, concern the first three waves. Their Expert/Public raking, equal expertise-category targets and lack of Superforecaster reweighting do not prove Wave 12 implementation.

Keep expected-world policy assumptions, principally AI-caused mortality >10%, the question's “by” 31 December 2050 versus the resolution's “before” boundary, and inclusive period start 31 December 2025. The report's CC BY 4.0 applies to published report content, not linked works or unpublished respondents. No forecast cells were re-extracted. FS-A05 / FS-P03 / FS-H03's caption inquiry is complete; denominator, weight, overlap and discrepancy holds remain.

## LM003: Eurostat model period and denominator roles

The [official manual](https://ec.europa.eu/eurostat/documents/3859598/16403569/KS-GQ-22-011-EN-N.pdf/34b63261-fde1-39b2-2385-f3d3c61fb7a3?t=1680160843392&version=1.0), DOI 10.2785/725625, reproduces the 2022 model questionnaire v1.2. C2 explicitly asks about training during 2021: PDF p.152, printed p.150, questionnaire p.14/23. C2 covers all in-scope enterprises, including those without specialists or internet access. No specialists during 2021 means No to C2a, not exclusion from all C2.

- PDF p.92 / printed p.90: E_ITT2 is ITSPT2=1 OR ITUST2=1, a union rather than the sum of overlapping categories.
- PDF p.78 / printed p.76: ENT is the raised enterprise population; ENT_SAMPLE is the unraised final net sample. PC_ENT is enterprise percentage, not employee or raw-respondent share. German numerical denominators, weights and effective n remain unknown.
- Model scope is enterprises with 10+ employees plus self-employed persons, NACE C–J and L–N plus group 95.1; size 0–9 is optional. Veterinary activities added since 2021 remain a scope annotation, not a quantified German correction.
- The E_ITT2 row's raw 2020 appears in the Notes / Source column. Its semantics remain null and do not replace C2's explicit 2021 reference period. General weighting guidance is not proof of German implementation.

Manual completion is March 2023 at month precision and publication is 2023 at year precision. Its 6,752,784-byte PDF was freshly hashed; PDF pages 4, 78, 92 and 152 were visually inspected. The manual's CC BY 4.0 has stated third-party/cover exceptions and is separate from statistical-data permissions or historical questionnaire rights.

Only 2022-model → 2021 is newly established. German administered 2012/2022 wording, routing and periods remain held, as does the 2012 model period; do not infer 2011 or a blanket year-minus-one rule. Existing 2024→2023 evidence and the aggregate fixture are unchanged. LM-A05 / LM-P03's bounded model-document check is complete, with those residuals preserved.

## Verification and stopping boundary

The JSON contains 27 documentary/guard records and seven exact native-response or reconstructed-file digests. ESPAI web text, Eurostat PDF bytes, extracted text and rendered images have separate evidence scopes; no PDF digest is invented for ESPAI. Eight supplied prior access outcomes remain attributed history, with no failed-route retries.

Ten supplied acceptance implications remain requirements, not executed runtime tests. No respondent records, statistical cube, publisher-program execution, re-estimation, pooling, new family/schema/adapter/validator, source admission or p(doom) conversion is added. Future research should target only the explicit remaining evidence and retain completed bounded checks as complete.
