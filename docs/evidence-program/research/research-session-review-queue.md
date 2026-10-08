# Research session review queue

Status snapshot: 8 October 2026, 07:11 UTC. This is a pre-integration snapshot for session 14.

The 26 research sessions below are listed in arrival order. Review and integration proceed sequentially. Thirteen reviews are integrated, one review is prepared for independent review and integration, and 12 remain queued. Session 14 is active; it is not yet merged at this snapshot.

Snapshot counts: 13 integrated; 1 prepared or awaiting CI; 12 queued.

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
| 10 | Training-data availability and feedback loops | Review integrated | [Research guide](training-data-feedback.md) · [PR 321](https://github.com/mishakgg/pdoom-live/pull/321) | Bounded offline Common Crawl aggregate reader implemented; synthetic-only public CI; rights, audit panel, experiment versions/coverage, FineWeb2 denominator bridge, Epoch input discrepancy and canonical mapping remain held |
| 11 | Human reliance and decision quality | Review integrated | [Research guide](human-reliance.md) · [PR 322](https://github.com/mishakgg/pdoom-live/pull/322) | Manual paper aggregate validator and provisional synthetic-only decoder implemented; workbook permission/schema/acceptance, four data-rights holds, denominator conflicts, cohort/measure lineage and canonical mapping remain held |
| 12 | Algorithmic efficiency and scaling | Review integrated | [Research guide](algorithmic-efficiency.md) · [PR 323](https://github.com/mishakgg/pdoom-live/pull/323) | One licensed offline AlgoPerf trial reader implemented; compatible comparisons, NanoGPT log rights/timing, Epoch sheet/version, OpenAI numerical conflicts/rights, MIT trace-to-figure/rights and canonical mapping remain held |
| 13 | Agent autonomy/security evaluations and incidents/near-misses | Review integrated | [Research guide](agent-security-incidents.md) · [PR 324](https://github.com/mishakgg/pdoom-live/pull/324) | One offline metadata decoder with synthetic public fixtures and private clean acceptance; runtime/trace rights, actual audit logs, version/denominator/authority/revision gaps and canonical mapping remain held |
| 14 | Labor-market effects and skill demand | Review prepared; integration pending | [Research guide](labor-market.md) · [Catalog](../../../data/evidence-program/research/labor-market.json) | One offline licensed German Eurostat slice reader implemented; earlier reference years, source-specific comparability, BTOS export, derivative links and canonical mapping remain held |
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

The [source review](training-data-feedback.md) and offline Common Crawl reader were merged in [PR 321](https://github.com/mishakgg/pdoom-live/pull/321) at [33fef790](https://github.com/mishakgg/pdoom-live/commit/33fef7908a6e449c8acd38f15b8d50d65a4923a3). All four post-merge checks were observed successful at 04:40:09 UTC on 8 October 2026. Five collections remain unadmitted with their original holds.

- Completed bounded work: primary-source review, exact current-base comparison of frozen64 and all nine previous catalogs (48 collections, 362 artifact references, 45 comparison cells), and a two-file/three-crawl offline reader. Private exact-artifact acceptance is separate from public synthetic-only tests.
- Common Crawl page sums and four-decimal shares reconcile for 486 category rows. Unknown-language urls is a page-residual placeholder; normalized cardinality stays null and language URL totals do not partition global URLs. Capture/release dates never become unknown content-publication dates.
- FineWeb2 derives from Common Crawl and cannot add independent raw supply. Paper 1320/1868 domain concentration differs from later 1870 filtered-train subsets. DPI audits existing material; restrictions are not licenses or affirmative consent.
- Collapse reference-data role does not mean human authorship. Code/manuscript covariance and export-era/current filename differences remain explicit; configured grids are not completed runs. Epoch raw/quality/effective repetition measures and paper/input discrepancies remain separate, without execution or annual-stock claims.
- Eight separate next actions and six standalone bounded prompts retain CSV/metadata/result/code rights, Consent panel access, source-version/denominator bridges and canonical mapping holds. No corpus/page content, experiment/model/source execution, live collector or deployment.

### Session 11 Human reliance and decision quality

The [source review](human-reliance.md) and offline validators were merged in [PR 322](https://github.com/mishakgg/pdoom-live/pull/322) at [664963c](https://github.com/mishakgg/pdoom-live/commit/664963c472222c845d3068df898f7537c285ad28). All four post-merge checks were observed successful at 05:17:21 UTC on 8 October 2026. Five families remain unadmitted with their original holds.

- Completed bounded work: public documentary/dictionary/metadata review and frozen64 plus all-ten-catalog comparison, covering 53 earlier collections, 404 artifact references and 50 candidate-by-catalog cells. No participant files were acquired or published.
- Implemented manual Okamura paper aggregate validator: 194 recruits, 116 completers, 78 excluded, 1,740 decisions, 1,282 correct and 1,236/504 automatic/manual. These are published counts, not reproduced workbook results. Synthetic-only five-bit arithmetic uses an explicitly provisional convention; workbook reader and actual-data acceptance remain held.
- Preserve Bastani 839/943 survey versus 2,848 student-session denominators; Bansal 508/35%/100-per-condition conflict and separate unaided arm; Gaube 265/264 conflict, human-authored AI labels and restrictive scoring; Glickman main/extension cohorts, different block designs and signed-bias versus absolute-error outcomes.
- Minors rows, medical/clinical records, participant identifiers and demographics are excluded. Dataset CC BY does not settle the unopened workbook's participant/privacy/schema gate; other four data licenses remain unknown. No lasting deskilling or clinical effectiveness inference.
- Eight action entries and six standalone bounded read-only prompts preserve source acceptance, rights, denominator/measure/version lineage and lossless mapping holds. No study-code execution, simulator/model run, collector, canonical admission or deployment.

### Session 12 Algorithmic efficiency and scaling

The [source review](algorithmic-efficiency.md) and offline AlgoPerf reader were merged in [PR 323](https://github.com/mishakgg/pdoom-live/pull/323) at [0884005](https://github.com/mishakgg/pdoom-live/commit/088400574a33af144ec7ef7bf13ac88f68f1b86c). All four post-merge checks were observed successful at 06:04:27 UTC on 8 October 2026. Five families remain unadmitted with their original holds.

- Completed bounded work: five-family primary-source review; frozen 64 and all eleven earlier catalogs (58 collections, 429 artifact references, 55 candidate-by-catalog cells); one Apache-2.0 offline AlgoPerf trial with 74 checkpoints and one explicitly derived validation crossing. Original and curated derivative hashes remain separate; no training images or data.
- Retrospective scoring uses inclusive validation-only comparison; runtime uses strict validation/test predicates with latched goals. The actual crossing is unchanged, and the stale paper target is explicitly corrected in its appendix. Submission/evaluation/logging/total clocks remain distinct; checkpoints are one trial, not an official aggregate score.
- NanoGPT result 6 has a specific maintainer rerun despite the general non-routine-rerun policy; the original PR has a different seed/configuration. Track timing and target/statistical rules remain separate. Epoch passage-specific model/interval levels and explicit figure-level imputation remain; spreadsheet rows/rights/revision are unresolved.
- OpenAI reported ratios, rounded CSV versus paper inputs, units, links and dates retain source conflicts. MIT nearest-loss extraction is not first crossing; actual-step/all-parameter versus planned-step/nonembedding FLOPs, missing plot inputs/manual constants and duplicate trace blobs remain explicit.
- Eight separate next actions and six bounded read-only prompts preserve compatible-comparison, rights, access, version, accounting and canonical mapping holds. No universal efficiency curve, energy inference, risk conversion, source-code execution, live collection or deployment.

### Session 13 Agent autonomy/security evaluations and incidents/near-misses

The [combined source review](agent-security-incidents.md) was merged in [PR 324](https://github.com/mishakgg/pdoom-live/pull/324) at [ab1434f](https://github.com/mishakgg/pdoom-live/commit/ab1434f30114df6784409d84069e9a8f785a45b1). All four post-merge checks were observed successful at 06:45:55 UTC on 8 October 2026. It remains one original report with seven unadmitted collections: AgentDojo, AIxCC, tau-bench, METR horizons, NHTSA, OAIC/ART and OpenAI sycophancy.

- Completed bounded work: frozen 64 plus all twelve earlier catalogs (63 collections, 464 artifact references); current primary-source review; a bytes-only AgentDojo metadata decoder and synthetic public tests, plus one separate private clean-artifact acceptance. No attacked traces or trajectory corpus.
- Preserve clean security defaults, exception flags, targeted-goal and DoS meanings. Historical source and archive revisions do not establish the runtime; actual attacked outcomes stay uninterpreted. Missing cost, caps, assistance and runtime metadata remain null.
- AIxCC denominator 70→63 is one correction chain; aggregate USD152/45-minute reports are not budgets. Actual audit-log access remains unknown. tau pass^k is all-trial consistency. METR human-time horizons are not agent runtime; suite, regularization, FAQ/current-data and estimated-baseline differences remain.
- NHTSA manufacturer filing, affected equipment and agency-processing corrections preserve authorship/units. OAIC/ART partial reversal, retained findings, no-appeal/concluded statements and store/date discrepancies stay source-attributed. Two OpenAI postmortems are one event, with tentative operator causal assessment and no quantified clinical-harm count.
- Ten separate actions and eight self-contained bounded read-only prompts preserve rights, access, identity, uncertainty and mapping holds. Item 16 remains queued; its potential event/artifact overlap is a later review question, not another item-13 receipt. No live collection, source execution, canonical admission, deployment or pooled risk inference.

### Session 14 Labor-market effects and skill demand

The [review](labor-market.md) prepares four collections from one submitted report: BLS OEWS, Indeed AI Tracker, Eurostat ICT training and O*NET Task Ratings. Independent review, publication and CI/integration remain pending at this snapshot. Census BTOS workforce remains a held GL023/AP005 follow-up.

- Completed bounded work: fresh primary-source checks, frozen64 and all thirteen earlier catalogs (70 collections, 505 artifact references, 65 comparison cells including held BTOS); one licensed 3,506-byte Eurostat slice and bounded offline JSON-stat reader.
- Preserve panel-pooled BLS wage rates; Indeed text-mention shares and Canada disclosure-boilerplate break; Eurostat general ICT training versus AI-specific skills; O*NET frequency-category percentages and unchanged measurement vintages. No causal AI employment estimate or exposure score.
- Reader retains ten survey-year cells, 2024=26.41 percent, absent source-status member, exact decimal fidelity, survey/reference/update/retrieval dates, dimension/category order and separate observation/snapshot identity. Earlier reference years remain unknown; only 2024→2023 is documented.
- Nine actions and seven standalone bounded prompts retain workbook schema, classification/keyword/history, earlier questionnaires, rating lineage, BTOS access/rights, derivative presentation and canonical mapping holds. No network refresh job, source/model execution, person records, live collection or deployment.

### Separate post-intake performance audit

Retain the search-person timing sensitivity observed during session 11 CI. One unchanged 500 ms budget failed at 512.9 ms; the same source head passed on retry at 365.6 ms cold and 342.9 ms hot, with the counterpart run and all post-merge checks successful. A repeated failure requires investigation before merge. This research update does not change query code or relax the threshold.

## Scope

This index records review progress and links to repository-native research guides. Integrated research catalogs remain unadmitted candidate evidence. The first three reviews retain their unimplemented source-reader proposals. Session 4 implements a fixed two-file annotation reader, session 5 a fixed one-file graph structure reader, session 6 a bounded offline gzip reader with synthetic-only CI, session 7 a manual aggregate ledger validator, session 8 an in-memory curated contrast checker, session 9 a bounded manual physical-results table reader, session 10 a two-file Common Crawl aggregate reader with synthetic-only public fixtures, and session 11 a manual paper-aggregate validator plus explicitly provisional synthetic-only bit arithmetic; session 12 a fixed four-file AlgoPerf reader with separately licensed fixtures and role-specific target semantics. Session 13 adds a bytes-only AgentDojo metadata decoder with synthetic public fixtures. Session 14 adds one bounded offline Eurostat JSON-stat reader with a separately licensed German aggregate fixture. No operational collector is enabled. Refresh status and unresolved actions when later reviewed changes are merged.

## Snapshot maintenance

This file records status at its stated time, not live main/CI state. After independent review, merge and post-merge checks, a later authorized update may record a new dated snapshot with verified PR/commit evidence. Until then, session 14 remains prepared in this historical snapshot even if this document itself is subsequently merged. Do not promote queued sessions, source admission, adapter implementation or unresolved evidence holds merely because a research-review PR merges.
