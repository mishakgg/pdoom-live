# Research session review queue

Status snapshot: 8 October 2026, 04:21 UTC. This is a pre-integration snapshot for session 10.

The 26 research sessions below are listed in arrival order. Review and integration proceed sequentially. Nine reviews are integrated, one review is prepared for independent review and integration, and 16 remain queued. Session 10 is active; it is not yet merged at this snapshot.

Snapshot counts: 9 integrated; 1 prepared or awaiting CI; 16 queued.

## Status definitions

- **Review integrated:** Reviewed documentation is merged and post-merge checks passed. Source admission, adapter implementation and unresolved evidence holds are tracked separately.
- **Awaiting CI:** The reviewed changes are published in a pull request; integration is still pending.
- **Review prepared; integration pending:** Source findings and repository changes are prepared; independent review, publication and CI/integration remain pending. This is not a merged or admitted-source status.
- **Queued:** Substantive review has not started. Findings, rights, access and remaining actions have not been assessed.

## Arrival order

| Sequence | Research session | Review status | Repository references | Unresolved action status |
| ---: | --- | --- | --- | --- |
| 1 | Chinese safety evaluations | Review integrated | [Research guide](https://github.com/mishakgg/pdoom-live/blob/5f6ff0c15c0461f98dd059177384811bfa9eb839/docs/evidence-program/research/chinese-safety-evaluations.md) · [PR 312](https://github.com/mishakgg/pdoom-live/pull/312) | FLAMES adapter unimplemented; eight artifact holds; two focused follow-up prompts prepared |
| 2 | Real-world adoption and productivity | Review integrated | [Research guide](https://github.com/mishakgg/pdoom-live/blob/d35063f098be9dc59c386edd10f6088527156684/docs/evidence-program/research/adoption-productivity.md) · [PR 313](https://github.com/mishakgg/pdoom-live/pull/313) | StatCan adapter and executable fixtures unimplemented; five evidence holds; five focused follow-up prompts prepared |
| 3 | Organizational safety practices | Review integrated | [Research guide](organizational-safety.md) · [PR 314](https://github.com/mishakgg/pdoom-live/pull/314) | HAIP reader and durable fixtures unimplemented; rights review, Microsoft certificate/PDF and Apollo original-report holds; five bounded prompts |
| 4 | Open-model diffusion and accessibility | Review integrated | [Research guide](open-model-diffusion.md) · [PR 315](https://github.com/mishakgg/pdoom-live/pull/315) | Two-file offline reader implemented with separately licensed research fixtures; production mapping, broader histories, access and artifact rights remain held |
| 5 | Concentration and shared dependencies | Review integrated | [Research guide](concentration-dependencies.md) · [PR 316](https://github.com/mishakgg/pdoom-live/pull/316) | One licensed fixed-graph offline reader implemented; ATRS semantic extraction, historical comparability, rights and canonical mapping remain held; seven focused prompts |
| 6 | Historical capability backfills | Review integrated | [Research guide](historical-capability-backfills.md) · [PR 317](https://github.com/mishakgg/pdoom-live/pull/317) | Bounded offline WMT08 reader; synthetic-only CI; private real-artifact acceptance separate; score redistribution rights, historical comparability and canonical mapping remain held |
| 7 | AI-assisted scientific progress | Review integrated | [Research guide](scientific-progress.md) · [PR 318](https://github.com/mishakgg/pdoom-live/pull/318) | Manual aggregate correction ledger validator implemented; source extraction, article byte pins, uncertainty, original exports, numerical validation, historical reuse and canonical mapping remain held |
| 8 | Persuasion and information ecosystems | Review integrated | [Research guide](persuasion-information.md) · [PR 319](https://github.com/mishakgg/pdoom-live/pull/319) | Curated published-effect ledger and synthetic checks implemented; source extraction, participant CSV proposal, Spitale workbook/rights, Ofcom rights/geography, Costello editorial resolution/effects and canonical mapping remain held |
| 9 | Robotics and physical-world capability | Review integrated | [Research guide](robotics-physical.md) · [PR 320](https://github.com/mishakgg/pdoom-live/pull/320) | Bounded manual BARN table reader with separately licensed fixture implemented; trial identity/means, RoboArena export semantics, RRC rights/index, PhAIL cohorts/metrics, STRANDS rights/units and canonical mapping remain held |
| 10 | Training-data availability and feedback loops | Review prepared; integration pending | [Research guide](training-data-feedback.md) · [Catalog](../../../data/evidence-program/research/training-data-feedback.json) | Bounded offline Common Crawl aggregate reader implemented; synthetic-only public CI; rights, audit panel, experiment versions/coverage, FineWeb2 denominator bridge, Epoch input discrepancy and canonical mapping remain held |
| 11 | Human reliance and decision quality | Queued | Pending review | Not yet assessed |
| 12 | Algorithmic efficiency and scaling | Queued | Pending review | Not yet assessed |
| 13 | Agent autonomy/security evaluations and incidents/near-misses | Queued | Pending review | Not yet assessed |
| 14 | Labor-market effects and skill demand | Queued | Pending review | Not yet assessed |
| 15 | Forecast and survey reconstruction | Queued | Pending review | Not yet assessed |
| 16 | Incidents and near-misses | Queued | Pending review | Not yet assessed |
| 17 | Inference cost and price–performance | Queued | Pending review | Not yet assessed |
| 18 | Claim-to-result provenance | Queued | Pending review | Not yet assessed |
| 19 | Model identity and retirement histories | Queued | Pending review | Not yet assessed |
| 20 | Undercovered languages and regions | Queued | Pending review | Not yet assessed |
| 21 | Mitigation effectiveness | Queued | Pending review | Not yet assessed |
| 22 | Negative results and replications | Queued | Pending review | Not yet assessed |
| 23 | Compute supply-chain bottlenecks | Queued | Pending review | Not yet assessed |
| 24 | Chinese governance in practice | Queued | Pending review | Not yet assessed |
| 25 | Benchmark drift and contamination | Queued | Pending review | Not yet assessed |
| 26 | Electricity and deployment bottlenecks | Queued | Pending review | Not yet assessed |

## Open actions for reviewed sessions

### Session 1 Chinese safety evaluations

[PR 312](https://github.com/mishakgg/pdoom-live/pull/312) is merged. All four post-merge checks were observed green by 23:20 UTC on 7 October 2026.

- Implement and test the proposed bounded offline FLAMES parser before claiming adapter completion.
- Retain all eight artifact-specific holds covering FLAMES, Chinese SafetyQA, JADE, LiveSecBench, CHiSafetyBench, SuperCLUE-Safety, M³-SafetyBench and C-SEM. Research integration did not clear these holds.
- Use the two focused M³ methods/reuse and LiveSec historical-provenance prompts in the [research guide](https://github.com/mishakgg/pdoom-live/blob/5f6ff0c15c0461f98dd059177384811bfa9eb839/docs/evidence-program/research/chinese-safety-evaluations.md).

### Session 2 Real world adoption and productivity

[PR 313](https://github.com/mishakgg/pdoom-live/pull/313) is merged. All four post-merge checks were observed green by 23:50 UTC on 7 October 2026.

- Finish lossless native provenance/date/flag mapping and durable bounded fixtures before implementing the proposed three-point StatCan adapter. The existing schema provides a mapping candidate; a schema change has not been established as necessary.
- Retain the five evidence holds for METR data/code rights and uncertainty conventions; QJE final methods and replication manifest/terms; Cui package rights and version/date identity; Census workbook evidence; and SDTIU full methods and rights.
- The [research guide](https://github.com/mishakgg/pdoom-live/blob/d35063f098be9dc59c386edd10f6088527156684/docs/evidence-program/research/adoption-productivity.md) contains the five focused follow-up prompts and detailed completion conditions.

### Session 3 Organizational safety practices

The [source review](organizational-safety.md) was merged in [PR 314](https://github.com/mishakgg/pdoom-live/pull/314) at [4ecece6](https://github.com/mishakgg/pdoom-live/commit/4ecece6abd322932f70f121aef2e99fc3be467bb). Four post-merge checks passed. All five collections remain unadmitted.

- Completed bounded checks: current access to both Fujitsu PDFs; both METR-anticipated textual edits; original AISI paper/version/license and evolving-protocol relationship; source-family comparison. None establishes safety effectiveness.
- Prepare the two-report/five-question/up-to-six-clause HAIP reader only after durable fixtures and lossless compatibility mapping are reviewed. The source reader is unimplemented.
- Retain artifact-specific rights holds, Microsoft underlying certificate and 2026 PDF access gaps, and the targeted Apollo original-report gap.
- Five self-contained prompts and eight action entries are in the guide and catalog; three entries are completed bounded work, five are open or held.

### Session 4 Open-model diffusion and accessibility

The [source review](open-model-diffusion.md) and offline two-revision reader were merged in [PR 315](https://github.com/mishakgg/pdoom-live/pull/315) at [3a98128](https://github.com/mishakgg/pdoom-live/commit/3a981281b59c91d29dd1b5157dfd90eac087c004). All four post-merge checks were observed green by 01:01 UTC on 8 October 2026. Two exact annotation YAMLs are acquired as separately licensed research test fixtures. Operational collection and source admission remain disabled.

- Implemented bounded reader: 14 parent and 12 child criteria, one criteria-set change removing `api` and `package`, and zero inferred model-access or model-license events. No evidence links or model files are fetched.
- Preserve open weights, open source, practical access and successful reproduction as different concepts; model licenses do not inherit annotation rights.
- Remaining actions and focused prompts are in the guide and catalog. Historical Hub export contents/rights, Epoch date and category mapping, OLMo reproduction evidence and PeaTMOSS dataset access/rights are separately qualified.

### Session 5 Concentration and shared dependencies

The [source review](concentration-dependencies.md) and fixed-graph offline reader were merged in [PR 316](https://github.com/mishakgg/pdoom-live/pull/316) at [bc00b60](https://github.com/mishakgg/pdoom-live/commit/bc00b609473c19c76869839598b63e1c8ace9ccc). All four post-merge checks passed. The five collections remain unadmitted, with 28 artifact references, 23 qualified findings and eight corrections retained.

- Completed bounded reader: one 3,532-byte deps.dev generated graph, 18 indexed nodes and 23 edges, licensed CC BY 4.0 with separate attribution outside `data/`. Structure validation does not establish installed deployment, service use or concentration risk.
- Preserve five evidence bases: ownership/economic rights, contractual access, disclosed operational use, resolved software dependencies and survey concentration. Unknown denominators, parties, dates and rights remain explicit.
- ATRS role labels and publication dates stay separate; OMB's 46 submissions/45 labels are different units and some flags reflect consolidation recoding; FTC parity remains anonymous, staff-qualified and historical.
- Two actions are completed; seven follow-ups cover manual ATRS mapping, deps.dev snapshot history, Bank comparability/access and reuse, OMB count definitions/rights, FTC third-party rights and lossless canonical mapping. No general semantic extractor or operational collector is enabled.

### Session 6 Historical capability backfills

The [source review](historical-capability-backfills.md) and bounded offline WMT08 reader were merged in [PR 317](https://github.com/mishakgg/pdoom-live/pull/317) at [e5121ee](https://github.com/mishakgg/pdoom-live/commit/e5121ee888393db656610be749dfc2d03897c751). All four post-merge checks passed. The five historical source families remain unadmitted.

- The bounded WMT08 reader uses synthetic-only CI. Separate private local acceptance checks the exact 16,071-byte gzip and 2,584 score rows/17 metric labels; the source file and full extracted results are not public fixtures because their reuse rights remain unknown.
- Event, publication, artifact-generation, transport and preservation dates remain separate. Original runs, corrected assertions, rescoring and genuinely later evaluations do not become interchangeable observations.
- Missing scores remain distinct from diagnosed failure. A competition entry, surviving table or weak score does not prove all attempted or abandoned work is covered.
- Preserve TREC access-conditional raw archives and unresolved score transcription, SAT penalties versus runtime, WMT cohort-dependent human comparison and VOC protocol breaks. Follow-up prompts retain artifact rights/access and lossless mapping holds. No collector, canonical import, capability curve or p(doom) is enabled.

### Session 7 AI-assisted scientific progress

The [source review](scientific-progress.md) and manual aggregate validator were merged in [PR 318](https://github.com/mishakgg/pdoom-live/pull/318) at [4fa67bd](https://github.com/mishakgg/pdoom-live/commit/4fa67bdb36e27c8b144b54ba99d3a9396208cd24). All four post-merge checks were observed successful at 02:57:45 UTC on 8 October 2026. The five collections remain unadmitted.

- Completed bounded work: five primary-source documentary reviews and all-six-catalog overlap comparison; a local manual A-Lab aggregate ledger validator with synthetic regressions. It is not a PDF/web extractor.
- Preserve one campaign, original indexed-primary 41/58 assertion, corrected 36/4/17 of 57 targets and 105/353 recipes. Article hashes, calendar dates and labor remain null; reanalysis is not independent experimental replication.
- Current I4R table matches published means; SD-versus-SE and regeneration stay held. RE-Bench partial summaries do not establish a complete original export or run/task version join. AlphaTensor numerical checks were not executed. CASP17 final assessment is pending and historical raw-score rights are scope-unverified.
- Six focused prompts cover aggregate lineage/uncertainty, safe aggregate provenance, original engineering export, safe certificate design, assessment rights/status and canonical mapping. No source admission, operational collection, universal productivity rate or p(doom) mapping is enabled.

### Session 8 Persuasion and information ecosystems

The [source review](persuasion-information.md) and curated contrast validator were merged in [PR 319](https://github.com/mishakgg/pdoom-live/pull/319) at [ee3e0d2](https://github.com/mishakgg/pdoom-live/commit/ee3e0d2fa2c5a594fec276f08f4c985147e9f130). All four post-merge checks were observed successful at 03:30:09 UTC on 8 October 2026. Four producer families/five collections remain unadmitted.

- Completed bounded work: current primary-source/documentary review, all-seven-catalog comparison and a hand-curated DebateGPT correction ledger. Three assertions represent two current contrasts and one superseded direct-personalization p value. No participant CSV acquisition or parsing.
- Preserve corrected p = .0678 only for personalized versus nonpersonalized GPT-4, with OR 1.487 and CI 0.971–2.276; the human comparator is a different estimand. Published effects are not percentages of people persuaded or population causal impact.
- Ofcom’s verified 8,556 pooled response base is not a verified unique-person count or cumulative reach; UK/GB discrepancy and YouGov copyright remain visible. OET consent routing, withdrawn/corrected waves and age/weight breaks remain.
- Spitale static scoring documentation is not proven final-workbook execution; current artifact rights and contents remain unverified. Costello’s journal concern remains active with resolution unverified; corrected numerical effects are withheld.
- Five self-contained bounded follow-up prompts and seven separate action entries preserve source/version, rights, comparability, editorial and mapping holds. No influence optimization, deceptive content, source execution, live collection or canonical admission.

### Session 9 Robotics and physical-world capability

The [source review](robotics-physical.md) and bounded BARN reader were merged in [PR 320](https://github.com/mishakgg/pdoom-live/pull/320) at [d196d9c](https://github.com/mishakgg/pdoom-live/commit/d196d9c89b8ba12d584a2f19e8ded1623ab0142a). All four post-merge checks were observed successful at 04:07:31 UTC on 8 October 2026. Five source families remain unadmitted with their original holds.

- Completed bounded work: current primary-source review, frozen 64 plus all-eight-catalog/43-collection/327-artifact comparison, and one manually curated BARN Table II offline validator. One CC BY 4.0 derivative fixture is retained outside data/CC0; it is not a full-source byte pin or HTML scraper.
- Preserve all 60 displayed outcomes (20 successful, 40 failed) separately from credited 6/9, 5/9, 5/9, 0/9. Positions are not chronological/native run IDs, tied credit membership is ambiguous, published means differ from fastest-three derivations, and resets/practice/checkpoints remain unknown.
- RoboArena session overlap is byte-verified for one pinned YAML. Checked-in integrity notice is commented out of current rendering; export filtering, duration units and archived progress scale remain unverified. No personal evaluator details retained.
- PhAIL Table 2 caption conflicts with code-defined Safety OR Stalled; Appendix F also claims episode-based safety rates but differs. Separate per-operation drops+safety metadata is a third measure. Card/paper/website cohort arithmetic is not membership proof.
- RRC2020 stays a documented mixed-job archive with CC BY-NC-SA restrictions; later RL correction is not a 2020 correction. STRANDS 177/148 recovery attempts concern 2015 specifically; requested assistance can coexist with lifetime. Dataset/sheet rights and some units remain unknown.
- Eight action entries and six self-contained bounded prompts preserve the remaining identity, rights, unit, cohort, metric and mapping holds. No robot/harness/model/source-script execution, raw trajectory/video archives, live collection or canonical admission.

### Session 10 Training-data availability and feedback loops

The [source review](training-data-feedback.md) prepares five collections: Common Crawl statistics, DPI/Consent, Collapse or Thrive, FineWeb2 and Epoch data stock. Independent review, publication and CI/integration remain pending at this snapshot.

- Completed bounded work: primary-source review, exact current-base comparison of frozen64 and all nine previous catalogs (48 collections, 362 artifact references, 45 comparison cells), and a two-file/three-crawl offline reader. Private exact-artifact acceptance is separate from public synthetic-only tests.
- Common Crawl page sums and four-decimal shares reconcile for 486 category rows. Unknown-language urls is a page-residual placeholder; normalized cardinality stays null and language URL totals do not partition global URLs. Capture/release dates never become unknown content-publication dates.
- FineWeb2 derives from Common Crawl and cannot add independent raw supply. Paper 1320/1868 domain concentration differs from later 1870 filtered-train subsets. DPI audits existing material; restrictions are not licenses or affirmative consent.
- Collapse reference-data role does not mean human authorship. Code/manuscript covariance and export-era/current filename differences remain explicit; configured grids are not completed runs. Epoch raw/quality/effective repetition measures and paper/input discrepancies remain separate, without execution or annual-stock claims.
- Eight separate next actions and six standalone bounded prompts retain CSV/metadata/result/code rights, Consent panel access, source-version/denominator bridges and canonical mapping holds. No corpus/page content, experiment/model/source execution, live collector or deployment.

## Scope

This index records review progress and links to repository-native research guides. Integrated research catalogs remain unadmitted candidate evidence. The first three reviews retain their unimplemented source-reader proposals. Session 4 implements a fixed two-file annotation reader, session 5 a fixed one-file graph structure reader, session 6 a bounded offline gzip reader with synthetic-only CI, session 7 a manual aggregate ledger validator, session 8 an in-memory curated contrast checker, session 9 a bounded manual physical-results table reader, and session 10 a two-file Common Crawl aggregate reader with synthetic-only public fixtures; no operational collector is enabled. Refresh status and unresolved actions when later reviewed changes are merged.

## Snapshot maintenance

This file records status at its stated time, not live main/CI state. After independent review, merge and post-merge checks, a later authorized update may record a new dated snapshot with verified PR/commit evidence. Until then, session 10 remains prepared in this historical snapshot even if this document itself is subsequently merged. Do not promote queued sessions, source admission, adapter implementation or unresolved evidence holds merely because a research-review PR merges.
