# Research session review queue

Status snapshot: 8 October 2026, 11:54:24 UTC. All 26 original reviews are integrated; this is a dated repository status, not live source admission or collection status.

The 26 research sessions below are listed in arrival order. Their substantive source reviews and repository integration are complete. Sessions 24–26 were merged in [PR 330](https://github.com/mishakgg/pdoom-live/pull/330); all four post-merge checks for the exact merge commit were observed successful at this cutoff. Open source-specific holds remain open. The [follow-up queue](followups/follow-up-queue.md) separately tracks three earlier reviewed bundles, four deep-session submissions and seven delivered prompts. The [labor measurement follow-up](followups/labor-measurement.md), deep bundle A / prompt 1, was merged in [PR 338](https://github.com/mishakgg/pdoom-live/pull/338) at 58de347f with all four post-merge checks verified. The [experimental effects follow-up](followups/experimental-effects-review.md), deep bundle B / prompt 2, is independently reviewed and included in this candidate; C’s separate review is starting and D remains queued. These are not additional original sessions, and candidate inclusion is not a claim of remote merge or source admission.

Snapshot counts: 26 integrated; 0 prepared or awaiting CI; 0 queued.

## Status definitions

- **Review integrated:** Reviewed documentation is merged and post-merge checks passed. Source admission, adapter implementation and unresolved evidence holds are tracked separately.
- **Awaiting CI:** The reviewed changes are published in a pull request; integration is still pending.
- **Review prepared; integration pending:** Source-review handoffs are complete; independent batch review, repository publication and CI/integration remain pending. This is not a merged or admitted-source status.
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
| 14 | Labor-market effects and skill demand | Review integrated | [Research guide](labor-market.md) · [PR 325](https://github.com/mishakgg/pdoom-live/pull/325) | One offline licensed German Eurostat slice reader implemented; earlier reference years, source-specific comparability, BTOS export, derivative links and canonical mapping remain held |
| 15 | Forecast and survey reconstruction | Review integrated | [Research guide](forecast-surveys.md) · [PR 326](https://github.com/mishakgg/pdoom-live/pull/326) | Four-summary licensed LEAP manual ledger reader implemented; rights/access, instrument versions, denominator/weight/overlap, model export lineage and canonical mapping remain held |
| 16 | Incidents and near-misses | Review integrated | [Research guide](incidents-near-misses.md) · [PR 327](https://github.com/mishakgg/pdoom-live/pull/327) | Two-change offline NHTSA publication-correction ledger; prior ASI005/ASI007 evidence reused; access, rights, uncertainty, identity and canonical mapping held |
| 17 | Inference cost and price–performance | Review integrated | [Research guide](inference-price-performance.md) · [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) | Separate source review complete with explicit holds; 4 actions and 4 bounded prompts; implementation deferred |
| 18 | Claim-to-result provenance | Review integrated | [Research guide](claim-result-provenance.md) · [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) | Separate source review complete with explicit holds; 7 actions and 7 bounded prompts; implementation deferred |
| 19 | Model identity and retirement histories | Review integrated | [Research guide](model-identity-retirement.md) · [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) | Separate source review complete with explicit holds; 7 actions and 7 bounded prompts; implementation deferred |
| 20 | Undercovered languages and regions | Review integrated | [Research guide](undercovered-languages.md) · [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) | Separate source review complete with explicit holds; 8 actions and 8 bounded prompts; implementation deferred |
| 21 | Mitigation effectiveness | Review integrated | [Research guide](mitigation-effectiveness.md) · [PR 329](https://github.com/mishakgg/pdoom-live/pull/329) | Separate source review complete with explicit holds; 7 actions and 7 bounded prompts; implementation deferred |
| 22 | Negative results and replications | Review integrated | [Research guide](negative-replications.md) · [PR 329](https://github.com/mishakgg/pdoom-live/pull/329) | Separate source review complete with explicit holds; 8 actions and 8 bounded prompts; implementation deferred |
| 23 | Compute supply-chain bottlenecks | Review integrated | [Research guide](compute-supply-chain.md) · [PR 329](https://github.com/mishakgg/pdoom-live/pull/329) | Seven primary-supported collections and one SK hynix rights-only candidate; 8 actions and 8 bounded prompts; implementation deferred |
| 24 | Chinese governance in practice | Review integrated | [Research guide](chinese-governance.md) · [Catalog](../../../data/evidence-program/research/chinese-governance.json) · [PR 330](https://github.com/mishakgg/pdoom-live/pull/330) | Separate source review complete with explicit holds; 6 actions and 6 bounded prompts; implementation deferred |
| 25 | Benchmark drift and contamination | Review integrated | [Research guide](benchmark-drift.md) · [Catalog](../../../data/evidence-program/research/benchmark-drift.json) · [PR 330](https://github.com/mishakgg/pdoom-live/pull/330) | Separate source review complete with explicit holds; 8 actions and 8 bounded prompts; implementation deferred |
| 26 | Electricity and deployment bottlenecks | Review integrated | [Research guide](electricity-deployment.md) · [Catalog](../../../data/evidence-program/research/electricity-deployment.json) · [PR 330](https://github.com/mishakgg/pdoom-live/pull/330) | Separate source review complete with explicit holds; 8 actions and 8 bounded prompts; implementation deferred |

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
- Ten separate actions and eight self-contained bounded read-only prompts preserve rights, access, identity, uncertainty and mapping holds. At the original session-13 review cutoff, item 16 was still queued; its later separate review reuses the relevant item-13 evidence identities rather than creating another item-13 receipt. No live collection, source execution, canonical admission, deployment or pooled risk inference.

### Session 14 Labor-market effects and skill demand

The [review](labor-market.md) was merged in [PR 325](https://github.com/mishakgg/pdoom-live/pull/325) at [71df61f](https://github.com/mishakgg/pdoom-live/commit/71df61f85bd8534f8fe95180cc13c9e31ded687c). All four post-merge checks were observed successful at 07:26:31 UTC on 8 October 2026. Its four collections remain unadmitted: BLS OEWS, Indeed AI Tracker, Eurostat ICT training and O*NET Task Ratings. Census BTOS workforce remains a held GL023/AP005 follow-up.

- Completed bounded work: fresh primary-source checks, frozen64 and all thirteen earlier catalogs (70 collections, 505 artifact references, 65 comparison cells including held BTOS); one licensed 3,506-byte Eurostat slice and bounded offline JSON-stat reader.
- Preserve panel-pooled BLS wage rates; Indeed text-mention shares and Canada disclosure-boilerplate break; Eurostat general ICT training versus AI-specific skills; O*NET frequency-category percentages and unchanged measurement vintages. No causal AI employment estimate or exposure score.
- Reader retains ten survey-year cells, 2024=26.41 percent, absent source-status member, exact decimal fidelity, survey/reference/update/retrieval dates, dimension/category order and separate observation/snapshot identity. Earlier reference years remain unknown; only 2024→2023 is documented.
- Nine actions and seven standalone bounded prompts retain workbook schema, classification/keyword/history, earlier questionnaires, rating lineage, BTOS access/rights, derivative presentation and canonical mapping holds. No network refresh job, source/model execution, person records, live collection or deployment.

### Session 15 Forecast and survey reconstruction

The [review](forecast-surveys.md) was merged in [PR 326](https://github.com/mishakgg/pdoom-live/pull/326) at [b5adbb5](https://github.com/mishakgg/pdoom-live/commit/b5adbb5bb94146fb8c4ec74976f3efa0a24723de). All four post-merge checks were observed successful at 08:20:50 UTC on 8 October 2026. Seven collections remain unadmitted: ESPAI/GL010, XPT/GL011 and LEAP/GL038 enrichments; NLP metasurvey, Müller–Bostrom, Swedish public expectations and AI Futures Model. The LEAP and AgentDojo fixture directories have scoped LF checkout rules; previous fixture bytes and hashes are unchanged.

- Completed bounded work: frozen 64 plus all fourteen prior catalogs (74 collections, 538 artifact references, 98 comparison cells); primary documentary checks; one manually curated CC BY 4.0 LEAP instrument/table ledger and bounded offline validator. Exactly four published group summaries; no HTML extractor or respondent data.
- Preserve exact question, unconditional policy context and 2050 horizon; original page versus derivative hashes, source percentages and exact normalized probability strings, respondent quartiles, cell n and unknown effective n/overlap/weights. The expert 157 versus derived category-sum 149 discrepancy and by/before resolution wording remain unresolved.
- ESPAI framing/reanalysis and XPT own/meta-belief stages stay distinct. XPT metadata defaults are not forecasts; Q3 full >10% versus metadata >1% is held. NLP agreement is not event probability; Müller–Bostrom group membership overlaps and date summaries exclude Never answers.
- Swedish negative-occurrence recoding and author-translation/edition provenance remain explicit. AIFM simulations are not respondents; 10000 configured versus 9612 summarized and historical export-to-code linkage remain held. Current static quantile conventions are not historical reproduction; code license does not propagate to exports.
- Ten separate actions and eight self-contained bounded read-only prompts retain access/rights, instrument, denominator, weighting, translation, version and canonical mapping holds. No source execution, microdata, private beliefs, rationale harvesting, rollout archives, live collection, pooled forecasts, canonical admission or deployment.

### Session 16 Incidents and near-misses

The [review](incidents-near-misses.md) was merged in [PR 327](https://github.com/mishakgg/pdoom-live/pull/327) at [82fd463](https://github.com/mishakgg/pdoom-live/commit/82fd46330539bd484c80190c69868d71b2052f6e). All four post-merge checks were observed successful at 08:54:31 UTC on 8 October 2026. Its eight research collections remain unadmitted with their source-specific holds.

- Completed bounded work: comparison with frozen 64 and all fifteen prior catalogs (81 collections, 580 artifact references, 120 comparison cells); eight primary-source reviews; two manually curated NHTSA publication-correction records with a bounded offline ledger reader. No PDF parser or live collector.
- Three new producer families: FDA, NZ OPC and NTSB. SGO, ODI, FTC enforcement, Anthropic and OpenAI enrich existing producer families. New artifacts or collections do not establish new events.
- Both NHTSA corrections reuse ASI005-F04; OpenAI April 2025 postmortems reuse ASI007. Stable assertion and artifact revision identities are separate; unavailable earlier content stays unavailable. No new crashes, before-narratives, engagement, causal harm or rates are inferred.
- FDA systems are not patients; supplement uncertainty and AI-containing versus AI-caused defect remain explicit. NZ failure estimates are not a hard upper bound; 1735/1742 alerts conflict and repeated scans are not people. ODI reviewed counts and its explicit report duplicate stay distinct.
- NTSB retains multi-factor cause and title-only revision. FTC complaint, stipulated remedy and respondent compliance retain roles. Provider request fractions and conditional OpenAI 1.2% potential-exposure population remain attributed and bounded.
- Ten actions and eight standalone prompts preserve rights/access, artifact versions, denominators, event identity and canonical mapping holds. No sensitive patient/personnel records, source corpus, narratives, source/model/target execution, bulk collection, canonical import or deployment.

### Session 17 Inference cost and price–performance

The [separate review](inference-price-performance.md) and [JSON record](../../../data/evidence-program/research/inference-price-performance.json) were merged together in [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) at [6cf8c1c](https://github.com/mishakgg/pdoom-live/commit/6cf8c1c89a387a5b26022dd9ea0a216d45b2b629). All four post-merge checks were observed successful at 10:06:19 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Keep the four collections. MLPerf is the best bounded measurement pilot; ML.ENERGY is the new family with the largest energy-data value but unresolved public-summary rights and quality; Epoch contributes original token-use aggregates and mixed-provenance historical prices; DeepSeek supplies factual tariff events. No inspected source links immutable identity, achieved quality, measured energy and net charges into one complete series.

- 4 collections; 6 corrections or consequential qualifications; 4 next actions and 4 copy-ready bounded prompts.
- All source-specific rights, access, version, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 18 Claim-to-result provenance

The [separate review](claim-result-provenance.md) and [JSON record](../../../data/evidence-program/research/claim-result-provenance.json) were merged together in [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) at [6cf8c1c](https://github.com/mishakgg/pdoom-live/commit/6cf8c1c89a387a5b26022dd9ea0a216d45b2b629). All four post-merge checks were observed successful at 10:06:19 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Keep seven collections: five new collection/infrastructure families and two existing-family enrichments. Rank ReScience, HF archives, Crossref/RW. Ranking reflects marginal provenance value, not blanket acquisition or redistribution clearance.

- 7 collections; 7 corrections or consequential qualifications; 7 next actions and 7 copy-ready bounded prompts.
- All source-specific rights, access, version, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 19 Model identity and retirement histories

The [separate review](model-identity-retirement.md) and [JSON record](../../../data/evidence-program/research/model-identity-retirement.json) were merged together in [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) at [6cf8c1c](https://github.com/mishakgg/pdoom-live/commit/6cf8c1c89a387a5b26022dd9ea0a216d45b2b629). All four post-merge checks were observed successful at 10:06:19 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain all seven collections as provenance research candidates. Google, Azure and publisher-owned revision metadata remain the top three. Names, hosted versions, repository states, weight objects and evaluated runs need separate evidence. Correct AWS archive/region claims and preserve Azure/DeepSeek contradictions.

- 7 collections; 7 corrections or consequential qualifications; 7 next actions and 7 copy-ready bounded prompts.
- All source-specific rights, access, version, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 20 Undercovered languages and regions

The [separate review](undercovered-languages.md) and [JSON record](../../../data/evidence-program/research/undercovered-languages.json) were merged together in [PR 328](https://github.com/mishakgg/pdoom-live/pull/328) at [6cf8c1c](https://github.com/mishakgg/pdoom-live/commit/6cf8c1c89a387a5b26022dd9ea0a216d45b2b629). All four post-merge checks were observed successful at 10:06:19 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain eight scoped collections: six originating collections and two enrichments of inventory families. INE, MERA and KoBBQ remain the best three; NIA correction is an immediate provenance warning with unresolved base definitions. All operational admission remains not_admitted.

- 8 collections; 8 corrections or consequential qualifications; 8 next actions and 8 copy-ready bounded prompts.
- All source-specific rights, access, version, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 21 Mitigation effectiveness

The [separate review](mitigation-effectiveness.md) and [JSON record](../../../data/evidence-program/research/mitigation-effectiveness.json) were merged together in [PR 329](https://github.com/mishakgg/pdoom-live/pull/329) at [9cfda7e](https://github.com/mishakgg/pdoom-live/commit/9cfda7eb65c1b6c257c9d9f0c8e96d53073b56e5). All four post-merge checks were observed successful at 11:22:28 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain seven study packages with explicit holds. LLMail, CaMeL and Redwood rank highest for controlled-comparison value; this is not a ranking of general safeguard effectiveness. Five study packages add to the initial inventory and two enrich existing families. CaMeL uses the already-cataloged AgentDojo benchmark.

- 7 collections; 8 corrections or consequential qualifications; 7 next actions and 7 copy-ready bounded prompts.
- Completed source checks remain distinguished from unstarted follow-ups. Source-specific rights, access, version, denominator and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 22 Negative results and replications

The [separate review](negative-replications.md) and [JSON record](../../../data/evidence-program/research/negative-replications.json) were merged together in [PR 329](https://github.com/mishakgg/pdoom-live/pull/329) at [9cfda7e](https://github.com/mishakgg/pdoom-live/commit/9cfda7eb65c1b6c257c9d9f0c8e96d53073b56e5). All four post-merge checks were observed successful at 11:22:28 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain eight collections: three new families and five enrichments against current catalogs. MLRC reports, StrongREJECT and Crossref editorial links have the highest scientific starting value. The smallest structured step reuses CRP006 for one verified editorial chain; it remains a specification only.

- 8 collections; 12 corrections or consequential qualifications; 8 next actions and 8 copy-ready bounded prompts.
- Completed source checks remain distinguished from unstarted follow-ups. Source-specific rights, access, version, denominator and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 23 Compute supply-chain bottlenecks

The [separate review](compute-supply-chain.md) and [JSON record](../../../data/evidence-program/research/compute-supply-chain.json) were merged together in [PR 329](https://github.com/mishakgg/pdoom-live/pull/329) at [9cfda7e](https://github.com/mishakgg/pdoom-live/commit/9cfda7eb65c1b6c257c9d9f0c8e96d53073b56e5). All four post-merge checks were observed successful at 11:22:28 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain eight new documentary collection families and prioritize TSMC, Micron and ASML. Seven collections have primary-supported samples; SK hynix remains rights-only with unverified milestones. One rights-gated ASML specification is deferred. No historical series, independent physical validation or usable-compute estimate is admitted.

- 8 collections; 8 corrections or consequential qualifications; 8 next actions and 8 copy-ready bounded prompts.
- Completed source checks remain distinguished from unstarted follow-ups. Source-specific rights, access, version, denominator and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 24 Chinese governance in practice

The [separate review](chinese-governance.md) and [JSON record](../../../data/evidence-program/research/chinese-governance.json) were merged together in [PR 330](https://github.com/mishakgg/pdoom-live/pull/330) at [972f2bb](https://github.com/mishakgg/pdoom-live/commit/972f2bbdc3e123c83ce9ea695c9f265fe6720032). All four post-merge checks were observed successful at 11:54:24 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain six research collections: five new families plus CN023 provincial enrichment. Prioritize enforcement/reinspection, CNCERT organized testing and procurement corrections/awards. Institutional reports do not establish completed compliance, independent audit or model safety. One CNCERT specification remains deferred; no operational admission.

- 6 collections; 7 corrections or consequential qualifications; 6 next actions and 6 copy-ready bounded prompts.
- Completed checks remain separate from unstarted follow-ups. Source-specific rights, access, version, denominator, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 25 Benchmark drift and contamination

The [separate review](benchmark-drift.md) and [JSON record](../../../data/evidence-program/research/benchmark-drift.json) were merged together in [PR 330](https://github.com/mishakgg/pdoom-live/pull/330) at [972f2bb](https://github.com/mishakgg/pdoom-live/commit/972f2bbdc3e123c83ce9ea695c9f265fe6720032). All four post-merge checks were observed successful at 11:54:24 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain eight qualified research collections: five new families and three enrichments. Prioritize EvalPlus revision provenance, lm-eval measurement changes and LiveBench retroactive revisions. Preserve measurement identity and evidence-specific contamination semantics; one EvalPlus mapping specification remains deferred, with no benchmark run or operational admission.

- 8 collections; 10 corrections or consequential qualifications; 8 next actions and 8 copy-ready bounded prompts.
- Completed checks remain separate from unstarted follow-ups. Source-specific rights, access, version, denominator, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Session 26 Electricity and deployment bottlenecks

The [separate review](electricity-deployment.md) and [JSON record](../../../data/evidence-program/research/electricity-deployment.json) were merged together in [PR 330](https://github.com/mishakgg/pdoom-live/pull/330) at [972f2bb](https://github.com/mishakgg/pdoom-live/commit/972f2bbdc3e123c83ce9ea695c9f265fe6720032). All four post-merge checks were observed successful at 11:54:24 UTC on 8 October 2026. Research admission and unresolved evidence holds are unchanged.

Retain eight new documentary families. Prioritize ERCOT, Georgia PSC and EirGrid for analytical value while retaining EirGrid row/rights holds and blocked ERCOT August/Batch Zero values as unverified. EIA, CSO tables and the LBNL data file have the clearest scoped reuse basis. One conditional two-PDF ERCOT specification remains deferred; no physical-capacity or operational-compute series is admitted.

- 8 collections; 10 corrections or consequential qualifications; 8 next actions and 8 copy-ready bounded prompts.
- Completed checks remain separate from unstarted follow-ups. Source-specific rights, access, version, denominator, identity and comparability holds remain explicit. Implementation is deferred; no operational collection or canonical admission.

### Separate post-intake performance audit

Retain the search-person timing sensitivity observed during session 11 CI. One unchanged 500 ms budget failed at 512.9 ms; the same source head passed on retry at 365.6 ms cold and 342.9 ms hot, with the counterpart run and all post-merge checks successful. A repeated failure requires investigation before merge. This research update does not change query code or relax the threshold. The sessions 21–23 batch also observed 508.2 ms against the unchanged 500 ms budget on its first push check; same-head PR and diagnostic rerun observations were 338.2 ms and 452.8 ms. All latest exact-head checks and post-merge checks subsequently passed. These measurements do not diagnose a cause or justify relaxing the budget.

## Scope

This index records review progress and links to repository-native research guides. Integrated research catalogs remain unadmitted candidate evidence. The first three reviews retain their unimplemented source-reader proposals. Session 4 implements a fixed two-file annotation reader, session 5 a fixed one-file graph structure reader, session 6 a bounded offline gzip reader with synthetic-only CI, session 7 a manual aggregate ledger validator, session 8 an in-memory curated contrast checker, session 9 a bounded manual physical-results table reader, session 10 a two-file Common Crawl aggregate reader with synthetic-only public fixtures, and session 11 a manual paper-aggregate validator plus explicitly provisional synthetic-only bit arithmetic; session 12 a fixed four-file AlgoPerf reader with separately licensed fixtures and role-specific target semantics. Session 13 adds a bytes-only AgentDojo metadata decoder with synthetic public fixtures. Session 14 adds one bounded offline Eurostat JSON-stat reader with a separately licensed German aggregate fixture. Session 15 adds one bounded offline LEAP manual instrument/table ledger reader with four separately licensed published group summaries; it is not an HTML extractor. Session 16 adds a bounded manual NHTSA publication-correction ledger. Sessions 17–26 add research documentation and structured metadata only; proposed implementations remain deferred. No operational collector is enabled. Refresh status and unresolved actions when later reviewed changes are merged.

## Snapshot maintenance

This file records status at its stated time, not live main/CI state. The 26/0/0 snapshot above is backed by the verified final-batch merge and post-merge checks. Later reviewed changes should record their own dated status and PR/commit evidence, with follow-up work maintained separately. Do not promote queued sessions, source admission, adapter implementation or unresolved evidence holds merely because a research-review PR merges.
