# Forecast and survey reconstruction

## Follow-up qualification: 8 October 2026

For FS001 / FS-A03, FS002 / FS-A04 and FS003 / FS-A05, the [instrument and denominator follow-up](followups/instrument-denominator.md) ([JSON](../../../data/evidence-program/research/followups/instrument-denominator.json)) records completed bounded report/instrument/caption checks. It explicitly limits FS001-F05/F06 to the 2023 questionnaire, keeps 2024 exact instrument fields and cross-edition n unresolved, preserves XPT's conflicting thresholds and qualifies LEAP weighting. Original catalog bytes and all residual rights/denominator holds remain intact.

Reviewed 8 October 2026 against `mishakgg/pdoom-live@71df61f85bd8534f8fe95180cc13c9e31ded687c`. Seven curated collections remain unadmitted: three enrichments (GL010, GL011, GL038), three new historical/survey study families and one new forecast collection. The frozen 64 register, all 14 prior catalogs, contracts and previous reader/fixture bytes remain unchanged. A narrow LF checkout rule is added to the earlier AgentDojo synthetic-fixture directory to preserve its existing byte hashes.

The implemented slice is a bounded offline reader for one manually curated CC BY 4.0 LEAP instrument/table selection, not a live collector or HTML extractor. It yields four published group summaries with exact decimal probability strings. No respondent files, private beliefs, demographic records, profiles or simulation trajectories were acquired for this integration.

[Machine-readable catalog](../../../data/evidence-program/research/forecast-surveys.json) · [Review queue](research-session-review-queue.md) · [Offline reader](../../../tools/evidence_program/read_leap_aggregates.py) · [Fixture notice](../../../tools/evidence_program/tests/fixtures/forecast-surveys/NOTICE.md)

## Priority and inference boundary

Reconstruction value: ESPAI framing/reanalysis, XPT definitions and stages, then LEAP publishable aggregate pilot. Implementation readiness differs from research ranking.

Survey agreement, event probabilities, elicited quantile years, author-recoded occurrence/timeline distributions, named endorsed judgments and conditional model exports are distinct evidence types. There is no pooled forecast, inferred individual belief, generic p(doom) field or canonical import. Aggregate records are not claims about every person in a field.

## FS001 AI Impacts ESPAI instruments and reanalyses

**Register relationship:** GL010. enrichment_existing_family.

**Coverage and updates:** 2016, 2022, 2023 and 2024 elicitation waves; September 2026 publication of the 2024 wave. Irregular survey, report and analysis revisions.

**Access:** Report and instrument inspection plus pinned data README; no respondent CSV or Google Sheet acquisition. 2024 questionnaire attachment read failed.

**Measurement and population:** Group summaries of elicited probabilities, probability-quantile dates and instrument framing. Researchers from stated AI publication frames; invitation, response, eligibility and item denominators differ.

### Verified findings

- Title page gives September 2026; recruitment section dates fieldwork 2024-12-09 through 2024-12-24. Publication date and elicitation date differ. Keep fieldwork and publication separate. [fs001_01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf)
- The six-venue 2023-author frame excluded ineligible returns after fielding. Reported 10% uses all returns; retained respondents comprised 1,502 complete and 78 partial. Address count excludes known bounces/failures. Do not use 1,580 as the denominator for every question or equate the approximately 10% rate with eligible-retained/invitations. [fs001_01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf)
- Table 4 matches. This is an unconditional future-AI question with no explicit horizon in its wording. Keep an absent horizon null; do not impute 2100 or a century. [fs001_01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf)
- Table 4 lists means 18.5% and 17.5%, medians 9% and 5%, respectively. Each participant received one variant; pooled n=1,489 is not a fourth independent sample. Use distinct question IDs and a pooled aggregate marked as derived from the variants. [fs001_01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf)
- HLMI fixed-years horizons are 10/20/40 years; fixed-probabilities are 10/50/90%. Occupation/FAOL fixed-years horizons are 10/20/50 years; both present-day occupation sequence and elicitation framing matter. HLMI assumes uninterrupted scientific activity; long-run impact allocation assumes eventual HLMI. Do not propagate the HLMI disruption condition into every instrument item without text evidence. [fs001_02](https://wiki.aiimpacts.org/_media/ai_timelines/predictions_of_human-level_ai_timelines/ai_timeline_surveys/2023_espai_paid.pdf)
- HLMI concerns unaided machines outperforming workers on every task economically and in performance; intrinsic human advantages are excluded. FAOL concerns all occupations being fully automatable. Long-run impact probabilities allocate 100% across five categories. Do not equate a conditional long-run-impact category with the unrestricted extinction question. [fs001_02](https://wiki.aiimpacts.org/_media/ai_timelines/predictions_of_human-level_ai_timelines/ai_timeline_surveys/2023_espai_paid.pdf)
- README names Sheet 1aOydfhZHuVwU_fwTgE0_O_-8p-uMrRDYV5R5QnwOMGI as the source of the named cleaned CSV. Separately describes combined-cleaned-personal-anon.csv as 3,270 individual responses and fields.csv as incomplete. Mirror relationship is verified from README only; no CSV/Sheet content or row equality was acquired or checked. [fs001_03](https://github.com/tadamcz/espai/blob/5bea2ed3014d5360d1599bad989d3252d3b8ba3c/data/README.md)
- The 2022 publisher page reports 2059; the 2023 preprint reports 2060 and attributes the shift from 2059 to code/cleaning; the September 2026 report returns to 2059 with a corresponding footnote. Store analysis edition/aggregation revision separately from fieldwork wave and respondent belief change. [fs001_01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf)
- Appendix C prints both URLs. The questionnaire web read returned an internal error; successful attachment-content retrieval is not verified. No attempt to acquire the respondent CSV was made. Published link availability is weaker than verified attachment access; instrument details from the report must be labeled report-derived. [fs001_01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf)
- Publisher footer limits CC0 to research pages and excludes blog posts. arXiv current 2023-study paper links CC BY 4.0. No checked statement unambiguously extends these to separately hosted respondent files or all 2024 attachments. Leave attachment/data reuse unresolved; do not substitute the reanalysis code license. [fs001_04](https://aiimpacts.org/)
- No respondent identifiers were inspected. The 2022 primary page describes a deliberately matched-panel subgroup using earlier participants and matched questions; the reviewed materials do not establish a usable public cross-wave key. Do not assume either perfect independence or public linkage across waves; distinguish panel subgroup, sample composition, and aggregate reanalysis. [fs001_05](https://aiimpacts.org/2022-expert-survey-on-progress-in-ai/)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "source_reported_group_summary",
    "variant": "Future AI extinction or similarly permanent severe disempowerment",
    "item_n": 744,
    "mean_percent": "18.3",
    "median_percent": "10",
    "horizon": null,
    "horizon_missing_reason": "not_explicit_in_question",
    "population_total_retained": 1580,
    "source_locator": "2024 report Table 4 row 1",
    "other_variants": [
      {
        "variant": "loss_of_control",
        "item_n": 392,
        "mean_percent": "18.5",
        "median_percent": "9"
      },
      {
        "variant": "next_100_years",
        "item_n": 353,
        "mean_percent": "17.5",
        "median_percent": "5"
      }
    ],
    "qualification": "Separate question variants, not independent studies. Relative century horizon belongs to elicitation, not publication. No respondent reconstruction."
  },
  "denominators": {
    "contacted_addresses_excluding_known_failures": 19874,
    "complete_or_partial_returns": 2052,
    "retained": 1580,
    "retained_complete": 1502,
    "retained_partial": 78,
    "item_n": [
      744,
      392,
      353
    ],
    "response_rate_note": "Approximately 10% uses 2052 returns, not retained 1580."
  }
}
```

### Artifact access, rights and version evidence

- **fs001_01** [Primary evidence for ESPAI-01](https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf): Printed pp. 1, 4; section 2.1. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs001_02** [Primary evidence for ESPAI-05](https://wiki.aiimpacts.org/_media/ai_timelines/predictions_of_human-level_ai_timelines/ai_timeline_surveys/2023_espai_paid.pdf): PDF pp. 2-9 and 17-18 (zero-based P1-P8 and P16-P17). Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs001_03** [Primary evidence for ESPAI-07](https://github.com/tadamcz/espai/blob/5bea2ed3014d5360d1599bad989d3252d3b8ba3c/data/README.md): Sections named after the three files. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs001_04** [Primary evidence for ESPAI-10](https://aiimpacts.org/): Footer; arXiv:2401.02843 license link. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs001_05** [Primary evidence for ESPAI-11](https://aiimpacts.org/2022-expert-survey-on-progress-in-ai/): Methods, Population, lines 71-74. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs001_06** [2023 study paper edition and license](https://arxiv.org/abs/2401.02843): License link and version history. Access: primary_documentary_review. Rights: explicit_license_paper_only; CC-BY-4.0. The paper only; no inheritance to response files or separately hosted 2024 attachments. Rights evidence: [source](https://arxiv.org/abs/2401.02843).
- **fs001_07** [2024 questionnaire publisher link](https://aiimpacts.org/wp-content/uploads/2026/09/2024-Expert-Survey-on-Progress-in-AI.pdf): Report Appendix C. Access: published_link_only_content_unverified. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- mirror_of: Named cleaned 2023 CSV → README-linked Google Sheet. README provenance only; bytes/rows not compared.
- reanalysis_of: 2022 HLMI summaries 2059/2060/2059 → 2022 elicitation wave. Calculation/cleaning changes are not new responses.
- publication_of: September 2026 report → December 2024 elicitation wave. Separate fieldwork and publication clocks.
- No universal researcher consensus claim; nonresponse and eligibility matter.
- 2024 attachment rights and questionnaire content remain unresolved.
- Public cross-wave respondent linkage was not verified or attempted.
- HLMI, FAOL and conditional long-run impact allocation are distinct items.

## FS002 FRI XPT questionnaire and revision metadata

**Register relationship:** GL011. enrichment_existing_family.

**Coverage and updates:** Main tournament June–October 2022; public comparisons 2023/2024 and later follow-up releases. Irregular research releases and revisions.

**Access:** Pinned QuestionInfo and questionMetadata CSVs plus README, DESCRIPTION and license; no forecast/participant CSVs.

**Measurement and population:** Question configuration and clarification history, separate from respondent forecasts. 80 analyzed domain experts and 89 superforecasters; 32 experts specialized in AI. Item-stage sample sizes differ.

### Verified findings

- Pinned QuestionInfo record 4 and questionMetadata agree on event, threshold, and three horizons. Definition includes direct/proximate causation and multi-source events that include AI. Keep near-extinction threshold rather than shortening the event to literal extinction only. [fs002_01](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/QuestionInfo.csv)
- The 6/28/22 note uses a but-for test involving substantial AI involvement within one year before the event. AI that merely assists an event humans could launch anyway need not count. Preserve clarification date as instrument revision metadata. This is not a new forecast or respondent wave. [fs002_01](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/QuestionInfo.csv)
- Metadata has forecastMin=0, forecastMax=100; stage 1/2/3/4; year1/2/3=2030/2050/2100; yourBeliefs, expertBeliefs, superBeliefs labels. Prediction of another group’s beliefs is a distinct measure, not the group’s observed mean. [fs002_02](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/data/questionMetadata.csv)
- All four q4 metadata records have defaultForecast50=50. It is a configuration field in question metadata without respondent/forecast identification. The file does not document actual runtime UI behavior; no source code or UI was executed. Reject metadata defaults as observations. Actual interface-use semantics remain untested. [fs002_02](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/data/questionMetadata.csv)
- CSV-aware local parsing found 59 QuestionInfo records; metadata has 236 rows, 59 unique sets and 59 per stage. Expanding stage-1 metadata by nonempty horizons times countries, with one for absent dimensions, gives 172, matching the follow-up report. Do not count 236 as questions, 172 as participants, or multi-stage metadata as additional people. [fs002_02](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/data/questionMetadata.csv)
- Follow-up report gives these counts, public comparison responses in 2023/2024, selective expert application/recruitment, and Good Judgment assistance recruiting superforecasters. Cohort sizes are not item-by-stage usable-answer denominators. This is a selected cohort, not a probability sample of AI researchers. [fs002_03](https://forecastingresearch.org/research/near-term-xpt-accuracy)
- Publisher pages explicitly label these dates. Publication/revision time is distinct from June-October 2022 fieldwork. [fs002_04](https://forecastingresearch.org/research/existential-risk-persuasion-tournament)
- Git commit metadata dates the pin to 2025-06-19T19:50:22Z and describes publication of 2024 follow-up updates and continued public survey results. No files from those response releases were read. The current replication branch matched this pin on 8 October 2026. The 19 June 2025 commit date and 2 September 2025 follow-up publication are separate clocks; a follow-up release does not imply all-new people. [fs002_05](https://github.com/forecastingresearch/xpt-lib/commit/251acb5254448c9bdb4caa4b5011481c2c149aef) [fs002_09](https://api.github.com/repos/forecastingresearch/xpt-lib/branches/replication)
- README explains calendar dates replace precise times to protect anonymity. Timestamp tracking errors caused exclusions in some cases; numerical storage differences can cause minor discrepancies with published results. Ordinal spacing is not elapsed time; preserve grouping and study stage. No respondent-level replication was attempted. [fs002_06](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/README.md)
- LICENSE.md contains the MIT software/documentation grant; DESCRIPTION says anonymized data and code and declares MIT + file LICENSE. These are material evidence, not an explicit separate permission statement for each respondent file. Retain both sources; do not claim no license exists or assert unqualified rights for every data artifact. [fs002_07](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/LICENSE.md)
- For q3 AI Catastrophic Risk, QuestionInfo says more than 10% deaths, whereas metadata subtitle says more than 1% in all four stages. Q4 is consistent. Add cross-artifact wording/threshold mismatch tests. Preserve both and escalate the mismatch; do not silently substitute shortened metadata. [fs002_01](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/QuestionInfo.csv)
- DESCRIPTION says over 200 participants; the publisher reports 169 analyzed/convened. The checked package description does not explain its denominator. Keep the formal report’s cohort denominator and flag the package prose mismatch; do not infer a new cohort or collapse recruitment and analysis counts. [fs002_08](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/DESCRIPTION)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "instrument_metadata_not_forecast",
    "question_set": 4,
    "event": "AI-caused extinction or global population below 5000",
    "horizon_years": [
      2030,
      2050,
      2100
    ],
    "probability_bounds_percent": [
      0,
      100
    ],
    "stages": [
      1,
      2,
      3,
      4
    ],
    "belief_targets": [
      "yourBeliefs",
      "expertBeliefs",
      "superBeliefs"
    ],
    "defaultForecast50": "50",
    "default_is_observation": false,
    "clarification_date": "2022-06-28"
  },
  "denominators": {
    "question_sets": 59,
    "metadata_rows": 236,
    "stage_count": 4,
    "expanded_subquestions_per_stage_own_beliefs": 172,
    "analyzed_experts": 80,
    "analyzed_superforecasters": 89,
    "ai_specialist_experts": 32,
    "item_stage_n": null,
    "package_description": "over 200 participants; denominator unresolved"
  }
}
```

### Artifact access, rights and version evidence

- **fs002_01** [Primary evidence for XPT-01](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/QuestionInfo.csv): CSV logical record 4 (setName 4. AI Extinction Risk). Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_02** [Primary evidence for XPT-03](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/data/questionMetadata.csv): four records for setName 4. AI Extinction Risk. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_03** [Primary evidence for XPT-06](https://forecastingresearch.org/research/near-term-xpt-accuracy): Introduction, lines 85-90. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_04** [Primary evidence for XPT-07](https://forecastingresearch.org/research/existential-risk-persuasion-tournament): Publication headers. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_05** [Primary evidence for XPT-08](https://github.com/forecastingresearch/xpt-lib/commit/251acb5254448c9bdb4caa4b5011481c2c149aef): Git commit metadata message/date. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_06** [Primary evidence for XPT-09](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/README.md): Notes. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_07** [Primary evidence for XPT-10](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/LICENSE.md): Full license; DESCRIPTION License/Description fields. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_08** [Primary evidence for XPT-12](https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/DESCRIPTION): Description field. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs002_09** [Current replication branch metadata](https://api.github.com/repos/forecastingresearch/xpt-lib/branches/replication): Observed 8 October 2026; branch SHA equals reviewed 251acb5254448c9bdb4caa4b5011481c2c149aef pin. Access: selected_connector_branch_metadata_reviewed. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- clarification_of: 2022-06-28 but-for clarification → Question-set 4. Instrument version, not new forecast.
- publication_of: 2023 original report and 2025 accuracy follow-up → 2022 tournament. New reports do not imply new people; later public/follow-up observations retain separate identities.
- No elapsed-time interpretation of ordinal timestampId.
- Own beliefs and predictions about others are distinct measures.
- Interface defaults are not observations and runtime UI behavior was not tested.
- Q3 full instrument and metadata subtitle conflict; package population prose has another denominator mismatch.

## FS003 FRI LEAP published wave summaries

**Register relationship:** GL038. enrichment_existing_family.

**Coverage and updates:** Wave labels approximately August 2025–August 2026; selected Wave 12 fieldwork 25 August–15 September 2026, released 5 October 2026. Approximately monthly wave labels with irregular publication delays; no collection schedule enabled.

**Access:** Three bounded public pages reviewed. One selected report-derived ledger with four group cells is validated offline; no general HTML extractor or documented export API.

**Measurement and population:** Published medians and between-respondent quartiles of elicited event probabilities. Publisher-defined Expert, Public, Superforecaster and AI Risk Expert groups; cross-group disjointness unknown.

### Verified findings

- The selected unconditional catastrophe-2050 row has Expert 2% (0.9%, 7%), n157; Public 5% (2%, 13%), n540; Superforecaster 1.6% (0.3%, 3.3%), n49; AI Risk Expert 5.2% (2%, 19%), n132. Parentheses give respondent-distribution quartiles, not confidence intervals or individual uncertainty. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- The event requires principally AI-caused deaths exceeding 10% of people alive at the start of a five-year period. It is not literal extinction. Direct/proximate causation includes a but-for test with substantial AI involvement within the prior year. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- Unconditional means the expected world, including anticipated future AI policy. Status quo and P1–P5 are different conditions; selecting them would change the estimand. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- The five-year period must start on or after 31 December 2025 and end before the resolution date. The question uses by 31 December 2050; preserve the different boundary wording without inventing a reconciliation. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- Fieldwork was 25 August–15 September 2026; the aggregate timestamp is 19 September 2026 at 03:32 UTC; first release was 5 October 2026. The embedded lastUpdated label supplies the rendered first-release date, not a separate verified revision date. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- Expert category counts 25, 34, 38 and 52 sum to 149, while the report and selected expert cell use 157. The sum is a derived discrepancy check, not a corrected unique-participant count. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- General methods reweight Expert and Public, while Superforecaster is not reweighted. Wave 12 cell-specific implementation was not independently verified; AI Risk Expert weighting, effective n and cross-group disjointness remain unknown. [fs003_03](https://forecastingresearch.org/research/longitudinal-expert-ai-panel-leap-working-paper) [fs003_01](https://leap.forecastingresearch.org/reports/wave12)
- The Wave 12 footer links its report content to CC BY 4.0. The selected derivative retains attribution outside data/CC0; this is not permission to acquire unpublished microdata or linked works. [fs003_01](https://leap.forecastingresearch.org/reports/wave12)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "four_source_reported_aggregate_cells",
    "question_id": "leap-ai-catastrophe-by-2050-unconditional",
    "condition": "unconditional",
    "horizon": "2050-12-31",
    "group_count": 4,
    "fixture_path": "tools/evidence_program/tests/fixtures/forecast-surveys/leap-wave12-catastrophe2050.json",
    "original_html_sha256": "2f236aa3d8125e60770412d081008b1d53e797732e308f6eb2a1e32ca2658c38",
    "derivative_sha256": "96179dd430710539c687a6122df198736748673bba550b3020889d852a9a0324",
    "qualification": "Manually curated licensed instrument and aggregate ledger. No HTML extraction implementation or source-authentication guarantee from local hashes alone."
  },
  "denominators": {
    "cell_n_by_group": {
      "Expert": 157,
      "Public": 540,
      "Superforecaster": 49,
      "AI Risk Expert": 132
    },
    "wave_expert_n": 157,
    "expert_category_counts": {
      "computer_scientists": 25,
      "industry_professionals": 34,
      "economists": 38,
      "policy_think_tank_staff": 52
    },
    "derived_category_sum": 149,
    "unique_participants": null,
    "effective_sample_sizes": null,
    "group_overlap": "unknown"
  }
}
```

### Artifact access, rights and version evidence

- **fs003_01** [Wave 12 report, exact selected instrument and aggregate table](https://leap.forecastingresearch.org/reports/wave12): Outcome Forecasts, Question (I), Catastrophic Risk, Unconditional; footer. Access: exact_original_html_body_reviewed. Rights: explicit_license_published_report; CC-BY-4.0. Published report content on the Wave 12 page. No inference of access or licensing of unpublished respondent microdata, third-party linked works, source code, or images. Rights evidence: [source](https://leap.forecastingresearch.org/reports/wave12). SHA-256 `2f236aa3d8125e60770412d081008b1d53e797732e308f6eb2a1e32ca2658c38` (exact_downloaded_html_body).
- **fs003_02** [Reports index](https://leap.forecastingresearch.org/reports): Wave labels and release dates. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs003_03** [General methods](https://forecastingresearch.org/research/longitudinal-expert-ai-panel-leap-working-paper): Sampling and reweighting descriptions. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- published_aggregate_of: Four Wave 12 group summaries → One question, unconditional condition, 2050 horizon. Stable identity, instrument definition, source-page revision and derivative revision remain separate.
- Cell n is not effective sample size or a verified unique-person count.
- General weighting documentation is not proof of Wave 12 cell-specific implementation.
- The 157 expert total and 149 sum of category counts remain unresolved.
- Catastrophe is not extinction; unconditional includes expected policy and differs from status quo.
- Question says by the resolution date; criteria require the five-year period to end before it. Both texts are retained.

## FS004 NLP Community Metasurvey

**Register relationship:** new named study/collection. new_study_or_forecast_collection_relative_to_reviewed_register.

**Coverage and updates:** May–June 2022 fieldwork; August 2022 preprint and July 2023 ACL publication. Single study; no recurring wave or respondent revision schedule verified.

**Access:** ACL PDF and landing page support instrument and aggregate review. Dashboard structured export is unverified.

**Measurement and population:** Agreement shares and mean predicted group agreement, not elicited event probabilities. 480 completions; 327 eligible NLP researchers. Eligible author population estimate differs from invitation count.

### Verified findings

- Q3-4 reports 36% agreement and 37% mean predicted agreement. Neither is a catastrophe probability; the statement asks whether severe AI/ML-caused catastrophe this century is plausible. [fs004_01](https://aclanthology.org/2023.acl-long.903.pdf)
- Agreement combines agree and weakly agree among respondents taking a side. Three non-answer categories and skipped items are excluded; item n is unknown, not 327. [fs004_01](https://aclanthology.org/2023.acl-long.903.pdf)
- The meta-question uses 0–20%, 20–40%, 40–60%, 60–80% and 80–100% bins, summarized at their midpoints. The separate meta-answer denominator was not established; do not reconstruct integer respondents from rounded values. [fs004_01](https://aclanthology.org/2023.acl-long.903.pdf)
- The report has 480 completions and 327 eligible respondents, with an estimated 6323 eligible authors. The reproduced instructions use an earlier approximately 5650 population estimate; neither is a verified invitation count. [fs004_01](https://aclanthology.org/2023.acl-long.903.pdf)
- Appendix E promises that individual responses will not be publicly released. Treat this as an instrument-and-aggregate collection despite article CC BY 4.0. [fs004_01](https://aclanthology.org/2023.acl-long.903.pdf)
- The 2022 preprint, 2023 ACL paper and dashboard describe one fieldwork study. No complete cross-edition diff, recurring panel schedule or respondent revision history was verified. [fs004_01](https://aclanthology.org/2023.acl-long.903.pdf)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "published_agreement_and_meta_agreement",
    "question_id": "Q3-4",
    "agreement_percent": "36",
    "mean_predicted_agreement_percent": "37",
    "item_n": null,
    "meta_item_n": null,
    "mean_meta_method": "bin_midpoints",
    "horizon_text": "this century",
    "horizon_day": null,
    "source_locator": "Figure 3c and Appendix E"
  },
  "denominators": {
    "completions": 480,
    "eligible_analyzed": 327,
    "estimated_population_report": 6323,
    "estimated_population_instructions": 5650,
    "invitations": null,
    "item_n": null,
    "meta_item_n": null
  }
}
```

### Artifact access, rights and version evidence

- **fs004_01** [Published instrument and aggregate figures](https://aclanthology.org/2023.acl-long.903.pdf): Figure 3c Q3-4 and caption; Appendix E, Figure 20; methods. Access: primary_documentary_review. Rights: explicit_license_published_paper; CC-BY-4.0. Published paper, instrument and tables only; no respondent-data permission. Rights evidence: [source](https://aclanthology.org/2023.acl-long.903/).
- **fs004_02** [Publication and license metadata](https://aclanthology.org/2023.acl-long.903/): ACL edition and footer. Access: primary_documentary_review. Rights: explicit_license_published_paper; CC-BY-4.0. This artifact only. No permission inferred for linked works, respondent files or other releases. Rights evidence: [source](https://aclanthology.org/2023.acl-long.903/).
- **fs004_03** [Project page](https://nlpsurvey.net/): Study timing and published materials. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs004_04** [Preprint version metadata](https://arxiv.org/abs/2208.12852): v1 26 August 2022. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- publication_of: 2023 ACL paper → 2022 NLP metasurvey. Not a separate respondent wave from preprint or dashboard.
- Q3-4 item denominators are unknown and may differ between agreement and meta-question.
- Meta-agreement is a mean of bin midpoints, not an exact continuous elicitation.
- 6323 estimated eligible authors and earlier 5650 instrument estimate are different versions; neither is verified invitations.
- Instructions promise individual responses will not be released publicly.

## FS005 Müller–Bostrom four-group AI progress survey

**Register relationship:** new named study/collection. new_study_or_forecast_collection_relative_to_reviewed_register.

**Coverage and updates:** November 2012–May 2013 fieldwork; 2014 short publication, 2016 full report and 2025 arXiv deposit. Single historical study; no periodic release cadence verified.

**Access:** Full report instrument/methods inspected; public project page exposes report link. Raw-response access not verified or pursued.

**Measurement and population:** Reported summaries of elicited probability-quantile years and conditional impact allocations. PT-AI, AGI, EETN and TOP100 memberships overlap; group totals are not unique people.

### Verified findings

- TOP100 reports a median 2050 and mean 2072 for respondents’ 50%-probability HLMI years. Reported standard deviation is 110 years; valid item n is unknown and 29 is group returns. [fs005_01](https://arxiv.org/pdf/2508.11681)
- PT-AI has 43 returns/88 invitations; AGI 72/111; EETN 26/approximately 250; TOP100 29/100. Memberships overlap: people were invited once but counted in every applicable group. Reported totals do not establish unique respondents. [fs005_01](https://arxiv.org/pdf/2508.11681)
- HLMI refers to capability across most human professions at least comparable to an ordinary worker. This differs from later ESPAI every-task and economic-performance definitions; preserve the uninterrupted-science assumption for the relevant item. [fs005_01](https://arxiv.org/pdf/2508.11681)
- Never was an explicit response option and was excluded from displayed year summaries. Do not replace never with zero probability, an arbitrary year or missingness. [fs005_01](https://arxiv.org/pdf/2508.11681)
- Q3’s reproduced instrument says any human where the narrative says every human. Use the instrument-specific version; do not silently harmonize the quantifier. [fs005_01](https://arxiv.org/pdf/2508.11681)
- Q4 allocates probabilities across long-run impact categories conditional on HLMI eventually existing. The extreme-negative category is not an unconditional fixed-horizon extinction probability. [fs005_01](https://arxiv.org/pdf/2508.11681)
- The 2025 deposit republishes historical 2012–2013 evidence, with 2014 and 2016 publication lineage. No new 2025 respondent sample or current belief update is implied; open third-party redistribution rights remain held. [fs005_01](https://arxiv.org/pdf/2508.11681)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "summary_of_elicited_quantile_years",
    "group": "TOP100",
    "elicited_probability_quantile": "0.5",
    "median_year": 2050,
    "mean_year": 2072,
    "sd_years": 110,
    "item_n": null,
    "group_returns": 29,
    "never_treatment": "excluded_from_published_date_summaries",
    "condition": "Science continues without major adverse interruption"
  },
  "denominators": {
    "groups": [
      {
        "group": "PT-AI",
        "returns": 43,
        "invitations": 88
      },
      {
        "group": "AGI",
        "returns": 72,
        "invitations": 111
      },
      {
        "group": "EETN",
        "returns": 26,
        "invitations": 250,
        "invitations_approximate": true
      },
      {
        "group": "TOP100",
        "returns": 29,
        "invitations": 100
      }
    ],
    "unique_respondents": null,
    "group_overlap": "explicit",
    "item_n": null
  }
}
```

### Artifact access, rights and version evidence

- **fs005_01** [Full report](https://arxiv.org/pdf/2508.11681): Sections 2.1–3.4; Appendix 1. Access: primary_documentary_review. Rights: distribution_license_not_open_reuse; no blanket open-data grant. arXiv distribution permission is not a third-party open reuse license. No full report or questionnaire is vendored. Rights evidence: [source](https://arxiv.org/abs/2508.11681).
- **fs005_02** [Deposit and license record](https://arxiv.org/abs/2508.11681): v1 deposited 9 August 2025. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs005_03** [Original project page](https://www.pt-ai.org/ai-polls/): Report link. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs005_04** [Author-hosted early manuscript](https://nickbostrom.com/papers/survey.pdf): Related publication; byte identity to later deposit not established. Access: related_author_copy_not_byte_compared. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- publication_of: 2014 short paper, 2016 full report and 2025 deposit → 2012–2013 study. One underlying study; do not use deposit date as elicitation date.
- Do not sum groups into 170 unique respondents.
- Never answers were excluded from date summaries; do not encode them as a large year or zero probability.
- TOP100 29 returns do not establish valid item n.
- No open third-party report or data redistribution permission verified.
- Instrument any human differs from narrative every human; preserve the wording version.

## FS006 Swedish public expectations about AI development

**Register relationship:** new named study/collection. new_study_or_forecast_collection_relative_to_reviewed_register.

**Coverage and updates:** 24 June–21 October 2024 fieldwork; 2025 preprint and 2026 journal publication. One cross-sectional study; no repeated-wave release verified.

**Access:** Preprint and author-posted published article inspected; publisher page unavailable. Original Swedish instrument and public microdata export not verified.

**Measurement and population:** Binary occurrence answers and affirmative-only timeline bins, combined by the authors for publication. Random invitation sample of 4046 Swedish adults; 1026 responses; cited preprint item base 937.

### Verified findings

- The random invitation sample was 4046 adults, with 1026 respondents and a reported 25.4% response rate. Online responses were followed by paper questionnaires; population nonresponse limits generalization. [fs006_01](https://arxiv.org/pdf/2504.04180)
- Preprint Table 1 reports superintelligence item n 937, with 66.1% Never and 10.8% beyond 20 years. The base combines negative occurrence answers with affirmative respondents providing usable timeline bins; it is not all 1026 respondents. [fs006_01](https://arxiv.org/pdf/2504.04180)
- The full printed percentages sum to 100.1%. Preserve source rounding; do not renormalize or infer integer counts. [fs006_01](https://arxiv.org/pdf/2504.04180)
- Never is the authors’ recoding of will-not-occur answers to the binary occurrence item. It was not a response option in the affirmative-only timing question and does not mean a reported 0% event probability. [fs006_01](https://arxiv.org/pdf/2504.04180)
- Appendix A is explicitly an English translation of the Swedish questionnaire. Original Swedish wording remains unrecovered; retain original and recovered language separately. [fs006_01](https://arxiv.org/pdf/2504.04180)
- The 2026 journal uses Figure 2 for timelines; its Table 1 is a different analysis. Pin n 937 to the preprint table. Journal text repeats 66.1%/10.8%, but journal item n was not independently reverified. [fs006_01](https://arxiv.org/pdf/2504.04180) [fs006_04](https://www.researchgate.net/publication/404701158_When_Will_AI_Transform_Society_Swedish_Public_Predictions_on_AI_Development_Timelines)
- The journal was available online 10 May 2026 and says data may be requested from the corresponding author. This is publication/access documentation, not a public data export or permission to contact the author. [fs006_04](https://www.researchgate.net/publication/404701158_When_Will_AI_Transform_Society_Swedish_Public_Predictions_on_AI_Development_Timelines)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "published_combined_occurrence_timeline_distribution",
    "source_edition": "arXiv:2504.04180v1",
    "source_locator": "Table 1 superintelligence row",
    "item_n": 937,
    "never_percent": "66.1",
    "beyond20_years_percent": "10.8",
    "full_row_percent": [
      "0.3",
      "2.8",
      "6.4",
      "7.6",
      "6.1",
      "10.8",
      "66.1"
    ],
    "rounded_sum_percent": "100.1",
    "original_language": "sv",
    "recovered_language": "en",
    "translation_status": "author_translation",
    "condition": "Timeline answered only after affirmative occurrence answer"
  },
  "denominators": {
    "invited": 4046,
    "responded": 1026,
    "reported_response_rate_percent": "25.4",
    "preprint_item_n": 937,
    "journal_item_n": null,
    "unique_across_editions": "same_study_not_independent_samples"
  }
}
```

### Artifact access, rights and version evidence

- **fs006_01** [Preprint translated instrument and table](https://arxiv.org/pdf/2504.04180): Methods, Table 1 and Appendix A. Access: primary_documentary_review. Rights: explicit_license_preprint_only; CC-BY-4.0. Preprint text, author translation and tables, not unreleased data. Rights evidence: [source](https://arxiv.org/abs/2504.04180).
- **fs006_02** [Preprint version and license](https://arxiv.org/abs/2504.04180): v1 posted 5 April 2025. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs006_03** [Journal publisher page](https://www.sciencedirect.com/science/article/pii/S2451958826001685): Site unavailable during review; do not claim body inspection. Access: primary_access_unavailable. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs006_04** [Corresponding author’s posted published article](https://www.researchgate.net/publication/404701158_When_Will_AI_Transform_Society_Swedish_Public_Predictions_on_AI_Development_Timelines): Journal first-page license, methods, Figure 2 and data availability. Access: primary_author_posted_article_reviewed. Rights: explicit_license_published_article; CC-BY-4.0. Published article only, not unreleased respondent data. Rights evidence: [source](https://www.researchgate.net/publication/404701158_When_Will_AI_Transform_Society_Swedish_Public_Predictions_on_AI_Development_Timelines).
- **fs006_05** [Institutional publication listing](https://www.umu.se/en/staff/sara-kalucza/): Corroborates title, authors, volume and year. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- publication_of: 2025 preprint and 2026 journal → 2024 Swedish cross-section. One sample; table numbering and presentation differ.
- English Appendix A is an author translation, not recovered original Swedish wording.
- Never recodes a negative occurrence answer; it is not an elicited numerical zero.
- Timeline bins are relative to fieldwork, not publication or an invented calendar day.
- Item n 937 is pinned to preprint Table 1; journal Table 1 is a different analysis.
- Data on request is not public access, and no outreach or microdata request is authorized.

## FS007 AI Futures Model dated forecasts and exports

**Register relationship:** new named study/collection. new_study_or_forecast_collection_relative_to_reviewed_register.

**Coverage and updates:** 11 export-registry entries labeled 29 December 2025 through 16 August 2026; public repository begins 9 September 2026. Irregular model, forecast and definition revisions.

**Access:** Small registry/metadata/summary files and static export methods inspected at one commit. No rollout archives or execution. Forecast page extraction displayed only loading text.

**Measurement and population:** Named endorsed all-things-considered judgments distinct from conditional model/export summaries. Three named forecaster labels in registry, not 11 respondents or thousands of people.

### Verified findings

- The pinned registry has 11 labeled exports, spanning 29 December 2025 through 16 August 2026, with Daniel, Eli and Brendan labels. Registry entries and simulation draws are not additional forecasters. [fs007_01](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/simulations.json)
- The Daniel 16 August 2026 AC CSV row reports 9535 achieved, 77 not achieved and 9612 total rollouts; p50 is 2027.9218. Metadata configures 10000 samples. The 388-run difference is unresolved; keep original count roles. [fs007_02](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/daniel-08-16-26/milestone_pdfs_overlay_statistics.csv) [fs007_03](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/daniel-08-16-26/metadata.json)
- The export label is 16 August 2026 but exportedAt is 2026-08-10T20:06:18.623067 with no timezone. modelVersion is null; preserve label, computation/export, publication, public-commit and retrieval clocks separately. [fs007_03](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/daniel-08-16-26/metadata.json)
- Current static exporter code may append typical simulation-end values for unachieved runs before calculating quantiles. Without a typical end it uses achieved values. Do not call all reported quantiles achieved-only or claim exact historical reproduction. [fs007_06](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/scripts/export/generate_overlay_distributions.py)
- The current empirical CDF keeps unachieved runs unreached at finite times, unlike endpoint substitution in quantiles. KDE filtering/scaling is another convention; the original p50 label stays source-reported until exact export lineage is established. [fs007_06](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/scripts/export/generate_overlay_distributions.py)
- The 16 August 2026 blog explicitly says forecasts assume progress as fast as technically feasible. Earlier written descriptions and actual forecaster assumptions conflicted; this creates a definition/version boundary. [fs007_08](https://blog.aifutures.org/p/q25-2026-timelines-update-uplift)
- Public history at the inspected pin starts with an initial commit on 9 September 2026. Dated exports predate it; a current code pin and retained labels do not establish earlier implementation lineage. [fs007_07](https://github.com/AI-Futures-Project/aifm-public/commit/1c40ecdb246c25980515441a66571931c5604e11)
- The repository licenses its code under MIT. Exported forecast data, prose and third-party input rights need separate clearance; no AIFM source bytes are vendored. [fs007_04](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md) [fs007_05](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/LICENSE)
- Model inputs reference METR capability/uplift evidence and Epoch products already represented in the register. Keep dependency links; these are not new independent experiments. Endorsed named judgments and conditional model outputs remain separate. [fs007_08](https://blog.aifutures.org/p/q25-2026-timelines-update-uplift) [fs007_04](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md)

### Sample and denominator roles

```json
{
  "sample": {
    "kind": "source_reported_model_export_summary",
    "forecaster_label": "Daniel",
    "export_label": "2026-08-16",
    "milestone": "AC",
    "configured_numSamples": 10000,
    "total_rollouts": 9612,
    "num_achieved": 9535,
    "num_not_achieved": 77,
    "p50": "2027.9218",
    "p50_semantics": "source_label_retained_historical_export_linkage_unresolved",
    "exportedAt": "2026-08-10T20:06:18.623067",
    "export_timezone": null,
    "modelVersion": null,
    "people_count": null
  },
  "denominators": {
    "registry_entries": 11,
    "named_labels": 3,
    "configured_samples": 10000,
    "summary_total_rollouts": 9612,
    "achieved": 9535,
    "not_achieved": 77,
    "unexplained_configured_difference": 388,
    "respondents": null
  }
}
```

### Artifact access, rights and version evidence

- **fs007_01** [Dated export registry](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/simulations.json): 11 entries and named labels. Access: primary_documentary_review. Rights: export_data_rights_unresolved; no blanket open-data grant. MIT code grant does not establish forecast export, website or third-party data reuse rights. Rights evidence: [source](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md#license). SHA-256 `e9530bd00059790392b7906afaa68f6c49dee4e1b2466e90ada5e866167d22d5` (exact_bytes_confirmed_by_git_blob).
- **fs007_02** [One small model summary CSV](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/daniel-08-16-26/milestone_pdfs_overlay_statistics.csv): AC row, physical line2. Access: primary_documentary_review. Rights: export_data_rights_unresolved; no blanket open-data grant. MIT code grant does not establish forecast export, website or third-party data reuse rights. Rights evidence: [source](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md#license). SHA-256 `d8839b8d5dd351f02d5f38c9879e3c4132bbf5d6e69241b40a8e0e42132a15c6` (exact_bytes_confirmed_by_git_blob).
- **fs007_03** [Export metadata](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/app/forecast/data/simulations/daniel-08-16-26/metadata.json): numSamples, exportedAt, modelVersion, timeRange. Access: primary_documentary_review. Rights: export_data_rights_unresolved; no blanket open-data grant. MIT code grant does not establish forecast export, website or third-party data reuse rights. Rights evidence: [source](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md#license). SHA-256 `6305eb5258845fac1e8684263ed2ae9f671eed321705e09cef83c03776eda7a3` (exact_bytes_confirmed_by_git_blob).
- **fs007_04** [Project definitions and code rights](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md): Milestones and License section. Access: primary_documentary_review. Rights: code_mit_only; MIT. MIT code grant does not establish forecast export, website or third-party data reuse rights. Rights evidence: [source](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md#license). SHA-256 `489a59bdd1bcbecf97308e65ab06449e63809820030819eb6f4836cfea216708` (exact_bytes_confirmed_by_git_blob).
- **fs007_05** [Code license](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/LICENSE): MIT software grant. Access: primary_documentary_review. Rights: code_mit_only; MIT. MIT code grant does not establish forecast export, website or third-party data reuse rights. Rights evidence: [source](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md#license). SHA-256 `93dc52eba54c47e9ffd5dc6c4d861dd8b8b5d1a0d3795da626f9f7bf671dfbf7` (exact_bytes_confirmed_by_git_blob).
- **fs007_06** [Static current export semantics](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/scripts/export/generate_overlay_distributions.py): Quantiles, KDE and CDF methods; never executed. Access: primary_documentary_review. Rights: code_mit_only; MIT. MIT code grant does not establish forecast export, website or third-party data reuse rights. Rights evidence: [source](https://github.com/AI-Futures-Project/aifm-public/blob/1c40ecdb246c25980515441a66571931c5604e11/README.md#license). SHA-256 `a362933355de62c2ec76668af6ed177356cb7d96ddb2d5dfbb50df887668868e` (exact_bytes_confirmed_by_git_blob).
- **fs007_07** [Initial public commit metadata](https://github.com/AI-Futures-Project/aifm-public/commit/1c40ecdb246c25980515441a66571931c5604e11): parents=[]; Initial release; 2026-09-09T20:00:40Z. Access: primary_git_commit_metadata_reviewed. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs007_08** [August forecast update](https://blog.aifutures.org/p/q25-2026-timelines-update-uplift): 16 August 2026 conditionality clarification and input dependencies. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs007_09** [About and changelog](https://www.aifuturesmodel.com/about): Irregular changes; explicit technical-feasibility detail is in August blog. Access: primary_documentary_review. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.
- **fs007_10** [Forecast interface](https://www.aifuturesmodel.com/forecast): Web extraction only loading text. Access: body_values_not_verified. Rights: unknown; no blanket open-data grant. This artifact only. No permission inferred for linked works, respondent files or other releases.

### Lineage and limitations

- model_calibration_input: METR TH1.1, developer uplift and Epoch products → GL004/ASI004/AP002 and GL001/OM003/AE003/TD005. Related input families are not duplicate named forecast observations; exact input-version joins remain held.
- definition_revision: August 2026 technical-feasibility clarification → Earlier forecasts with inconsistent slowdown descriptions. Do not pool across changed conditioning.
- Configured simulations, retained rollouts and achieved outcomes use different counts.
- Current exporter implementation does not prove exact August export lineage.
- Export data, website prose and third-party input rights remain unresolved despite MIT code.
- Milestones AC, SC, SAR, TED-AI and ASI differ; no generic HLMI or p(doom) mapping.
- Technical-feasibility conditioning changed or was clarified; do not stitch a smooth unqualified series.

## Cross-catalog comparison

Compared the frozen 64 inventory and all 14 prior catalogs: 74 collections, 538 artifact references and 98 candidate-by-catalog assessments. New here means absent as a named study/collection in the inspected register; it does not claim no citation, person or related statement exists anywhere in the repository.

The machine catalog preserves all 98 cells, exact URL match/related-artifact results and SHA-256/Git blob fingerprints. Matching a producer, scholarly discovery service, generic rights page or calibration input is not identical evidence. Cross-person linkage was not attempted.

- [adoption-productivity](../../../data/evidence-program/research/adoption-productivity.json): 5 collections / 41 artifacts. AP002 METR developer experiments are a documented input to AIFM uplift calibration; not a new independent study when cited in a forecast. Public named forecaster judgments are separate from developer task forecasts and measured outcomes. Other business/worker surveys have different frames/items.
- [agent-security-incidents](../../../data/evidence-program/research/agent-security-incidents.json): 7 collections / 41 artifacts. ASI004 METR TH1.1 is a documented AIFM input family; archived/current benchmark estimates and model-dependent forecasts differ. No exact copied YAML-byte match or run crosswalk established here. Other incidents/security tasks are not survey forecast events.
- [algorithmic-efficiency](../../../data/evidence-program/research/algorithmic-efficiency.json): 5 collections / 35 artifacts. AE003 Epoch language-model algorithmic-progress is related producer/model input context; AIFM ECI/calibration does not establish identical observations or the same fitted-estimator lineage. No pooling effective compute projections with empirical fitted progress.
- [chinese-safety-evaluations](../../../data/evidence-program/research/chinese-safety-evaluations.json): 8 collections / 49 artifacts. Safety test/task sets and modelresponse metrics are distinct from peopleforecast/survey collections; shared model names/topics provide no study/item identity.
- [concentration-dependencies](../../../data/evidence-program/research/concentration-dependencies.json): 5 collections / 28 artifacts. Organizational adoption and concentration surveys (including CD003) have different sampling frames, questions and units; no respondent crosswalk or identical study established.
- [historical-capability-backfills](../../../data/evidence-program/research/historical-capability-backfills.json): 5 collections / 46 artifacts. Historical benchmark rounds are model/task performance observations, not forecastelicitation waves; publicationyear proximity and modelnames do not establish independent forecast evidence.
- [human-reliance](../../../data/evidence-program/research/human-reliance.json): 5 collections / 25 artifacts. Human-AI intervention studies and beliefcalibration outcomes are distinct experiments; no participantlinkage, matching item or common study established with shortlisted forecasts.
- [open-model-diffusion](../../../data/evidence-program/research/open-model-diffusion.json): 5 collections / 37 artifacts. OM003 enriches Epoch all_ai_models.csv, alreadyGL001. AIFM uses Epoch capabilities/model input evidence; same producer notproven same exact modeltable records. Do not add inputsource republications as independent forecasts.
- [organizational-safety](../../../data/evidence-program/research/organizational-safety.json): 5 collections / 50 artifacts. OS002 covers Anthropic/METR reports and internal survey criticism. AIFM August update cites Anthropic internal productivity survey estimates, so keep input study/report dependencies, missing-response caveats and source-version boundary; no exact same survey wave/table match established by generic organization match.
- [persuasion-information](../../../data/evidence-program/research/persuasion-information.json): 5 collections / 30 artifacts. Persuasion experiments and Ofcom surveys measure different respondents/items/outcomes. XPT persuasion tournament name does not make it the same intervention/study as DebateGPT or conspiracydialogue experiments.
- [robotics-physical](../../../data/evidence-program/research/robotics-physical.json): 5 collections / 35 artifacts. Physical trials and reliability metrics concern model/robotattempts, not surveyrespondents; no common study or question found.
- [scientific-progress](../../../data/evidence-program/research/scientific-progress.json): 5 collections / 46 artifacts. SP003 RE-Bench shares METR publisher and adjacent documentation but is distinct from TH1.1 and developer uplift experiments. No assumption AIFM uses RE-Bench runs based solely on METR overlap.
- [training-data-feedback](../../../data/evidence-program/research/training-data-feedback.json): 5 collections / 42 artifacts. TD005 Epoch data-stock analysis is different product from AIFM ECI/compute inputs. Shared producer and discussion of data bottlenecks do not establish same artifact or observation; no model projection pooled as empirical stock.
- [labor-market](../../../data/evidence-program/research/labor-market.json): 4 collections / 33 artifacts. BLS/Indeed/Eurostat/O*NET employment, posting,training andtaskrating aggregates are distinct measures/frames; forecasting futureautomation is not observed employmentchange or causal AIeffect.

Metaculus GL012 and Manifold GL013 are not additional sources here; existing restrictions stay unchanged. OpenAlex/arXiv discovery records and different publication editions do not count as additional independent surveys. AIFM calibration inputs keep dependencies to METR and Epoch rather than duplicating the underlying experiments.

## Implemented bounded LEAP ledger reader

Input is exactly the fixed JSON ledger and manifest filenames. Limits: 32 KiB ledger, 8 KiB manifest, 1000 JSON nodes, depth 12 and 32-character decimal tokens. No network, arbitrary file references, imports from source repositories or source/model execution. Symlinks and unexpected fields are rejected.

The original 600,997-byte HTML body and the curated derivative have different SHA-256 values. Only the small derivative is checked in, under its CC BY 4.0 notice outside data/CC0. Hashes identify bytes; offline CI cannot independently authenticate an original page that is not present. Source verification is distinct from deterministic fixture validation.

```bash
python tools/evidence_program/read_leap_aggregates.py tools/evidence_program/tests/fixtures/forecast-surveys
python tools/evidence_program/check.py
```

### Semantics and acceptance

- Exact selected question, background, catastrophe resolution criteria, shared policy instructions, unconditional condition and 2050 horizon are pinned as one reviewed instrument definition.
- Source percentage strings remain intact; normalized probability strings use exact decimal division by 100 without floats or rounding.
- Exactly four publisher group labels and all 12 numerical summary cells are reproduced. Cell n remains a separate integer or null with a reason; no wave-n fallback.
- Between-respondent quartiles cannot become CIs, individual uncertainty or personal probabilities. General weighting context is retained separately from unknown wave-specific implementation.
- Expert 157 and category 25/34/38/52 (derived sum 149) remain separate with an unresolved discrepancy flag; no pooled unique-person count is emitted.
- Fieldwork, minute-precision UTC aggregate generation, first release and retrieval remain separate. Embedded lastUpdated is not independently a revision date.
- Stable observation IDs use study/wave/question/group. Instrument-definition digest and original source/derivative result revisions are separate. Same content is idempotent; changed definitions fail closed for review; accepted source/derivative revisions get distinct result IDs without overwriting history.
- Nonfinite, signed, exponent, whitespace, boolean, out-of-range and overprecision percentage inputs are rejected. Missing n, duplicate keys, bad order, wrong conditions, invalid dates, hash drift and excess input structure are tested.
- A validated manual transcription is still labeled as such, not human-verified canonical data or a tested web extractor.

## Corrections and remaining holds

- ESPAI 2024 denotes fieldwork, while publication occurred in September 2026; item n never inherits the retained sample total.
- ESPAI 2022 HLMI restatements are analysis revisions; the public matched-panel design does not establish a usable public linkage key.
- ESPAI 2023 CSV mirror provenance is README-verified only; no respondent files were acquired or byte-compared.
- XPT defaultForecast50 is configuration, not a forecast; timestampId is ordinal, not elapsed time.
- XPT q3 full wording exceeds 10% deaths while metadata subtitle exceeds 1%; q4 is separately consistent.
- XPT 59 sets, 236 stage metadata rows and 172 expanded subquestions count different units; package over 200 prose is not the analyzed 169 cohort.
- LEAP page serialization permitted this manual selection, but no HTML extractor or stable API is implemented.
- LEAP original-page bytes and curated derivative hashes are separate; only the attributed derivative is vendored outside data/CC0.
- LEAP cell n, category counts, between-respondent quartiles, effective sample size and weighting are different concepts.
- LEAP unconditional includes anticipated policy; status quo is a different condition. Catastrophe is not extinction.
- LEAP by/before horizon boundary and 157-versus 149 discrepancy are preserved rather than repaired.
- NLP 36% agreement and 37% bin-midpoint predicted agreement are neither event probabilities nor identical denominator measures.
- Müller–Bostrom subgroup totals overlap; date summaries excluding responses marked Never and TOP100 returns do not establish a pooled population or item n.
- Swedish Never is recoded negative occurrence, not numerical 0%; author English translation and preprint table identity remain explicit.
- Swedish printed bins sum 100.1% from rounding; no renormalization or inferred integer counts.
- AIFM configured 10000, exported 9612, achieved 9535 and not-achieved 77 are simulations with unresolved filtering, not people.
- AIFM current exporter may substitute simulation endpoints into quantiles; exact August lineage is unverified, so p50 remains source-labeled.
- AIFM dated labels, timezone-unspecified export, publication, initial public commit and conditioning revision are separate; MIT code rights do not license all data.

### FS-H01 FS001
2024 instrument attachment content and artifact-specific rights; aggregate reanalysis/mirror/panel lineage.

Release condition: A bounded public documentary comparison with explicit artifact licenses and unchanged question conditions; no respondent acquisition.

### FS-H02 FS002
Q3 >10% versus >1% threshold, package population mismatch, source-version and file-specific rights.

Release condition: Document the administered definition and license scope using only original instrument/report metadata; do not turn defaults into observations.

### FS-H03 FS003
Wave 12-specific weighting, effective/cell n semantics, 157-versus-149 discrepancy and group overlap.

Release condition: Public methodology/correction evidence must establish these semantics without linking or acquiring respondents.

### FS-H04 FS004
Q3-4 agreement and meta-item n, aggregation/version documentation and structured aggregate export.

Release condition: Published item-level aggregate documentation only; preserve confidentiality promise and unknown denominators.

### FS-H05 FS005
Item denominators, overlap and never handling, instrument/narrative difference, report/data reuse.

Release condition: Source-published documentation clarifies these points; no microdata or full-report copying.

### FS-H06 FS006
Original Swedish wording, edition-specific table alignment and access/rights.

Release condition: Public original instrument plus edition/translation provenance; no on-request data or author outreach.

### FS-H07 FS007
10000-versus-9612 count path, historical export-to-code/input linkage and export-data rights.

Release condition: Dated static methods and metadata identify exact historical version and scope; no execution or rollout files.

### FS-H08 all
Lossless canonical mapping for distinct study/instrument/aggregate/model-result records.

Release condition: Read-only contract mapping demonstrates dates, conditions, denominators, rights and version lineage can be represented without modifying frozen contracts or importing data.

## Actions

- **FS-A01 — completed_bounded_review**: Verify seven primary collections and compare frozen 64 plus all 14 prior catalogs. Seven scoped reviews; 74 prior collections, 538 artifact references and 98 candidate-by-catalog cells.
- **FS-A02 — completed_offline_implementation**: Validate a selected licensed LEAP instrument and four aggregate cells offline. Manual ledger reader with exact decimal output, version identity, provenance and strict bounded-input regression tests; no HTML extractor.
- **FS-A03 — held_documentary_review**: 2024 instrument attachment content and artifact-specific rights; aggregate reanalysis/mirror/panel lineage. A bounded public documentary comparison with explicit artifact licenses and unchanged question conditions; no respondent acquisition.
- **FS-A04 — held_documentary_review**: Q3 >10% versus >1% threshold, package population mismatch, source-version and file-specific rights. Document the administered definition and license scope using only original instrument/report metadata; do not turn defaults into observations.
- **FS-A05 — held_documentary_review**: Wave 12-specific weighting, effective/cell n semantics, 157-versus-149 discrepancy and group overlap. Public methodology/correction evidence must establish these semantics without linking or acquiring respondents.
- **FS-A06 — held_documentary_review**: Q3-4 agreement and meta-item n, aggregation/version documentation and structured aggregate export. Published item-level aggregate documentation only; preserve confidentiality promise and unknown denominators.
- **FS-A07 — held_documentary_review**: Item denominators, overlap and never handling, instrument/narrative difference, report/data reuse. Source-published documentation clarifies these points; no microdata or full-report copying.
- **FS-A08 — held_documentary_review**: Original Swedish wording, edition-specific table alignment and access/rights. Public original instrument plus edition/translation provenance; no on-request data or author outreach.
- **FS-A09 — held_documentary_review**: 10000-versus-9612 count path, historical export-to-code/input linkage and export-data rights. Dated static methods and metadata identify exact historical version and scope; no execution or rollout files.
- **FS-A10 — held_documentary_review**: Lossless canonical mapping for distinct study/instrument/aggregate/model-result records. Read-only contract mapping demonstrates dates, conditions, denominators, rights and version lineage can be represented without modifying frozen contracts or importing data.

## Standalone bounded follow-up prompts

Prepared prompts are not dispatched, scheduled or authorization for respondent-data acquisition. Each ends after one documentary question is answered or remains blocked.

### FS-P01 FS001

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS001. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect at most the 2024 questionnaire, report Appendix C/Table 4, publisher license page and one 2022/2023 reanalysis note. Reconcile three extinction variants, HLMI/FAOL framing and 2059/2060/2059 lineage; report missing access without attempting CSVs. Starting URLs: https://aiimpacts.org/wp-content/uploads/2026/09/ESPAI2024.pdf ; https://aiimpacts.org/wp-content/uploads/2026/09/2024-Expert-Survey-on-Progress-in-AI.pdf ; https://aiimpacts.org/. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P02 FS002

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS002. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect pinned QuestionInfo question-set 3 and 4, their questionMetadata rows, publisher Appendix 6 and package rights metadata, at most five documents. Resolve or retain >10% versus >1%, preserve defaultForecast50 as configuration and ordinal timestampId as ordering; do not inspect forecast rows. Starting URLs: https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/QuestionInfo.csv ; https://github.com/forecastingresearch/xpt-lib/blob/251acb5254448c9bdb4caa4b5011481c2c149aef/data/questionMetadata.csv ; https://forecastingresearch.org/research/existential-risk-persuasion-tournament. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P03 FS003

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS003. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect only Wave 12, its public methodology and at most one linked correction notice. Determine whether cell n semantics, effective n, group overlap, exact wave weights or 157 versus 149 are publicly resolved. Preserve uncertainty and the by/before horizon distinction. Starting URLs: https://leap.forecastingresearch.org/reports/wave12 ; https://forecastingresearch.org/research/longitudinal-expert-ai-panel-leap-working-paper. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P04 FS004

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS004. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect only ACL Figure 3c, its caption, methods, Appendix E and the public dashboard documentation. Check whether Q3-4 agreement/meta-item denominators or aggregate-only export documentation are supplied. Preserve bin-midpoint calculation and confidentiality promise. Starting URLs: https://aclanthology.org/2023.acl-long.903.pdf ; https://aclanthology.org/2023.acl-long.903/ ; https://nlpsurvey.net/results/. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P05 FS005

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS005. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect only historical report Sections 2–3, Appendix 1 and deposit/license metadata. Check group overlap, TOP100 valid item n, excluded never responses and any/every wording; describe rights without copying the whole instrument. Starting URLs: https://arxiv.org/pdf/2508.11681 ; https://arxiv.org/abs/2508.11681 ; https://www.pt-ai.org/ai-polls/. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P06 FS006

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS006. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect the preprint Appendix A/Table 1 and at most two public publisher or institutional instrument/version pages. Seek original Swedish wording only if openly linked; preserve author-translation status, negative-occurrence recoding and preprint-versus-journal table identity. Do not request data from the author. Starting URLs: https://arxiv.org/pdf/2504.04180 ; https://arxiv.org/abs/2504.04180 ; https://www.sciencedirect.com/science/article/pii/S2451958826001685. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P07 FS007

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction FS007. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect at most six small dated metadata, summary, static-method or license files at the pinned public repository. Test documentary linkage of Daniel 2026-08-16 to exportedAt 2026-08-10, null modelVersion and 10000 versus 9612 counts. Distinguish endpoint-substituted quantiles from finite-time CDF; do not run any method or acquire rollout archives. Starting URLs: https://github.com/AI-Futures-Project/aifm-public/tree/1c40ecdb246c25980515441a66571931c5604e11 ; https://blog.aifutures.org/p/q25-2026-timelines-update-uplift. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.

### FS-P08 all

Read-only bounded documentary review for mishakgg/pdoom-live, Forecast and survey reconstruction all. Read docs/evidence-program/source_priorities.md, data/evidence-program/source_inventory.json and data/evidence-program/research/forecast-surveys.json first. Inspect existing repository schemas, methodology and this catalog only. Produce a lossless field-by-field proposal for instrument definitions, aggregate denominators/weights, translated occurrence/timeline questions, named judgments and model exports. Keep stable identity separate from definition/source/derivative versions and source rights. Identify unsupported fields without modifying schemas. Starting URLs: https://github.com/mishakgg/pdoom-live/blob/71df61f85bd8534f8fe95180cc13c9e31ded687c/docs/evidence-program/README.md. Return verified artifact URLs and locators, distinct fieldwork/export/publication/retrieval clocks, artifact-specific rights, corrected facts, unresolved holds and a small acceptance-test proposal. Stop when this bounded question is answered or a source is unavailable; report a useful negative answer. No login, outreach, bypass, bulk download, respondent CSV/Sheet, microdata, demographics, individual profiles, private beliefs, rationale harvesting, source scripts/notebooks/model execution, rollout archives, recurring collection, repository edits, canonical import, deployment or generic p(doom) conversion. Do not sum groups or pool forecasts without established comparability and explicit authorization.


## Byte-pinned fixture checkout portability

An isolated Git index/checkout with core.autocrlf=true reproduced CRLF conversion and hash failures for both the new LEAP JSON and the prior AgentDojo synthetic JSON. Each affected fixture directory now has a narrow *.json text eol=lf rule. Existing source/fixture bytes, prior readers, tests, catalogs and frozen contracts are unchanged. This explicit preservation exception adds only the prior fixture directory’s .gitattributes file. Two regression tests perform actual isolated autocrlf checkouts, compare every JSON byte and run both readers successfully.
