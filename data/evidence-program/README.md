# Evidence program data files

These are research-register metadata, audit findings, proposed analytical recipes and synthetic preparation examples. No collected source body or live production dataset is added here. Start with the [program index](../../docs/evidence-program/README.md).

- [source_inventory.json](source_inventory.json) combines all 64 source records, their coverage mappings and the audit baseline. [global_sources.json](global_sources.json) contains GL001–GL040; [chinese_sources.json](chinese_sources.json) contains CN001–CN024. These partitions agree exactly with the combined record list.
- [coverage_mapping.json](coverage_mapping.json) preserves independent stage flags and pinned evidence links for each source. [coverage_references.json](coverage_references.json) records audited link paths and Git blob identifiers for offline link-membership checks.
- [baseline_metrics.json](baseline_metrics.json) carries the 28 metrics with units, denominators, interpretation and audit limits. Historical `main_matches_baseline` is a recorded check at the stated time, not a continuously updated assertion about main.
- [source_inventory.csv](source_inventory.csv), [coverage_mapping.csv](coverage_mapping.csv) and [baseline_metrics.csv](baseline_metrics.csv) are deterministic inspection views of the JSON. Array/object cells use compact JSON; empty cells represent absent/null values. These CSVs must not be treated as new independent observations.
- [chinese/aliases.json](chinese/aliases.json) is a conservative lookup with automatic merging disabled. [chinese/query_lexicon.json](chinese/query_lexicon.json) contains unexecuted retrieval templates. [chinese/test_cases.json](chinese/test_cases.json) contains 25 wholly invented semantic test vectors with 41 partial contract fragments. [chinese/reference_manifest.json](chinese/reference_manifest.json) pins the schema, specification and inventory they reference.
- [analysis_recipes.json](analysis_recipes.json) is a proposed analysis checklist, not a production configuration. [methodology_example_checks.json](methodology_example_checks.json) is the reproducible 19-check synthetic arithmetic result.

- [implementation_tasks.json](implementation_tasks.json) records the unexecuted Step 6 plan, dependency order, existing/proposed paths, authorization gates and acceptance evidence. Its task IDs and titles match the [readable plan](../../docs/evidence-program/implementation_tasks.md); it is not an executable configuration.

Changes to source records or metrics must update the combined inventory and corresponding CSV views together. Keep source IDs stable; add explicit reviewable revisions rather than silently turning candidate sources into collected evidence. The [offline checker](../../tools/evidence_program/README.md) verifies that the redundant views agree.

Third-party source rights are not changed by the repository's [data license](../LICENSE). Follow each source record's artifact-specific rights notes before any acquisition, retention or publication.

## Full-content intake review, 9 October 2026

The [reviewed intake result](../../docs/evidence-program/research/followups/full-content-intake-2026-10-09.md) is now included alongside the issued assignment. One separate session and eight supplied artifacts are included as qualified research only. The review records twelve semantic enforcement gaps; all eight acquisition cases remain unexecuted. No acquisition readiness, source admission, collector change or additional independent-study coverage follows. The twenty package files preserve their dated pre-publication review snapshot unchanged; their candidate/publication fields describe that historical snapshot, while this queue records their inclusion in this version. Remote publication, merge and exact-commit CI are separate verification steps.

The original 26-session queue, three earlier follow-up bundles and seven later deep-session submissions retain their historical counts.

## Point-in-time model-panel review, 9 October 2026

The [reviewed panel result](../../docs/evidence-program/research/followups/point-in-time-panel-2026-10-09.md) is included alongside assignment 2. One separate session and four supplied artifacts are included as reviewed research only. The archived Epoch source reparse verifies 3,626 rows, 57 fields and 192 selected raw cells; 24 native EvalPlus objects and 96 metric slots reproduce. Nine of twelve bounded primary reads succeeded, with three reader limitations. All twelve strict candidates remain held: no aggregate-to-execution binding exists in the inspected evidence. DeepSeek 6ND is a disclosed-2T-phase reconstruction with extra long-context accounting unresolved; StarCoder2 Table 6 already includes long-context. The supplied schema accepts 35 of 41 unsafe mutations and remains a research proposal.

This addition does not change session 01, the original 26-session queue or earlier follow-up/deep-bundle counts. No training rows, canonical contracts, source inventory or live collectors are admitted or changed.

## Current research review status

The [dated original-session queue](../../docs/evidence-program/research/research-session-review-queue.md) records all 26 original reviews integrated at its verified 8 October 2026 cutoff, separately from evidence admission. The [follow-up queue](../../docs/evidence-program/research/followups/follow-up-queue.md) preserves three earlier reviewed bundles and separately logs seven returned deep-session bundles (20 files). The four earlier A–D research deltas retain their merge proofs: A’s labor delta merged and post-merge verified at 58de347f, B’s experimental-effects delta merged and post-merge verified at a075f76f, C’s independently reviewed safeguard delta merged and post-merge verified at 050e91bc, and D’s independently reviewed model/tariff delta merged and post-merge verified at 78ded6f5 ([PR 343](https://github.com/mishakgg/pdoom-live/pull/343)). The E/F/G receipt-only update is merged and post-merge verified in [PR 345](https://github.com/mishakgg/pdoom-live/pull/345) at 246f746e. E’s compute/power documentary delta is merged in [PR 346](https://github.com/mishakgg/pdoom-live/pull/346) at [aff81514](https://github.com/mishakgg/pdoom-live/commit/aff815147b12235177da9f66f4c09c2c1508f3eb); all four exact-commit post-merge checks were observed successful at 2026-10-08T22:11:29Z. At the 2026-10-08T22:49:21Z snapshot, all ten received follow-up bundles have completed bounded source review. F’s Chinese-comparability documentary delta is merged in [PR 348](https://github.com/mishakgg/pdoom-live/pull/348) at [b8724361](https://github.com/mishakgg/pdoom-live/commit/b8724361863e78a7ad1e270b285f22705662fa3d); all four exact-commit post-merge checks were observed successful at 2026-10-08T22:49:21Z. G / prompt 6 (incidents/enforcement) has an independently cleared documentary delta included in this candidate. Their original eight-file receipt total (722,010 bytes) and all seven returned prompts remain recorded. All 64 original E/F/G acceptance specifications remain unexecuted. Source, identity, dates, comparability, rights, remedy-outcome and admission holds remain. G candidate publication and exact-commit CI/merge are separate; no collector or incident observation is admitted. Receipt and prompt delivery do not establish findings or completed checks; reviewed research and candidate inclusion do not establish source admission, ingestion or remote merge.

Reviewed follow-up deltas included in this version:

- Bundle 1: [Rights and releases](../../docs/evidence-program/research/followups/rights-release.md) · [JSON](research/followups/rights-release.json)
- Bundle 2: [PhAIL, MLPerf and RoboArena comparability](../../docs/evidence-program/research/followups/physical-inference-comparability.md) · [JSON](research/followups/physical-inference-comparability.json)
- Bundle 3: [Survey instruments and denominators](../../docs/evidence-program/research/followups/instrument-denominator.md) · [JSON](research/followups/instrument-denominator.json)
- Deep bundle A / prompt 1: [Labor measurement lineage](../../docs/evidence-program/research/followups/labor-measurement.md) · [JSON](research/followups/labor-measurement.json), including the bounded BLS workbook and O*NET lineage review, qualified Indeed article result and partial contract mapping; residual holds remain.
- Deep bundle B / prompt 2: [Experimental effects and uncertainty](../../docs/evidence-program/research/followups/experimental-effects-review.md) · [JSON](research/followups/experimental-effects-review.json), preserving METR published uncertainty versus unverified execution, I4R edition/statistic lineage and Costello documentation versus unresolved journal/effect holds; no canonical admission.
- Deep bundle C / prompt 4: [Safeguard and evaluator lineage](../../docs/evidence-program/research/followups/safeguard-lineage-review.md) · [JSON](research/followups/safeguard-lineage-review.json), preserving CaMeL static evidence versus production/runtime, coexisting rights notices, AISI failure/change/unknown outcome and separate developer-attributed Apollo cohorts; all six hold groups remain.
- Deep bundle D / prompt 3: [Hosted-model and tariff events](../../docs/evidence-program/research/followups/model-tariff-review.md) · [JSON](research/followups/model-tariff-review.json), preserving all four conflicted Azure schedule assertions and their source revision lineage, exact R1 tariff categories, alias conflicts and V3 null boundaries; all seven held records and prior catalog IDs remain. No automatic price/lifecycle join or canonical admission.
- Deep bundle E / prompt 7: [Compute and power capacity accounting](../../docs/evidence-program/research/followups/compute-power-review.md) · [JSON](research/followups/compute-power-review.json), retaining operator/facility identity, anonymous Georgia split, generation/load and rating/stage boundaries; all seven source, rights, capture and semantic-mapping holds remain. No automatic capacity aggregation or canonical admission.
- Deep bundle F / prompt 5: [Chinese safety-evaluation comparability](../../docs/evidence-program/research/followups/chinese-comparability-review.md) · [JSON](../../data/evidence-program/research/followups/chinese-comparability-review/delta.json), retaining separate historical snapshot, denominator, judge/rubric, date, rights and cross-release comparability holds. All 20 original cases remain unexecuted; no common safety score, p(doom), canonical admission or collection.
- Deep bundle G / prompt 6: [Incident corrections and enforcement outcomes](../../docs/evidence-program/research/followups/incident-enforcement-review.md) · [JSON](../../data/evidence-program/research/followups/incident-enforcement-review/delta.json), preserving OPC conflicts, distinct FTC legal/remedy/claim chains, Shanghai authority/Jiangsu republication and anonymous case/cohort boundaries. All 20 original cases remain unexecuted; no independent remedy completion, incidence rate, canonical admission or collection.

## Additive research catalogs

[Chinese safety-evaluation research](research/chinese-safety-evaluations.json) uses separate provisional ZHS IDs. It contains source metadata and scoped findings for seven proposed new families plus one CN020 enrichment; no prompt corpus, full result table or production-ready observation is embedded. All candidates remain unadmitted. The original 64-source inventory and audit are unchanged. Read the [review and proposed adapter specification](../../docs/evidence-program/research/chinese-safety-evaluations.md) before interpreting its fields.

[Adoption and productivity research](research/adoption-productivity.json) records five provisional AP collections, including GL023 enrichment and a distinct METR productivity family. Separate study/wave identities, scoped artifact access/rights, interpretation guards and next actions remain research-only. No participant records or operational observations are embedded. See the [review and proposed StatCan adapter](../../docs/evidence-program/research/adoption-productivity.md).

[Organizational safety research](research/organizational-safety.json) records five provisional OS collections with separate authority/commitment/action/assessment classes, artifact-specific rights and access, completed bounded checks and open follow-ups. No company safety scores, raw source bodies or operational records are embedded. See the [review and proposed HAIP reader](../../docs/evidence-program/research/organizational-safety.md) and [dated review queue](../../docs/evidence-program/research/research-session-review-queue.md).

[Open-model diffusion research](research/open-model-diffusion.json) records five provisional OM collections: four new-family candidates and a GL001 accessibility enrichment. It separates metadata, assessor judgments, checkpoint listings, static reuse edges and practical access. Two pinned annotation files are acquired only as separately licensed research fixtures outside `data/`; the [guide and implemented offline reader](../../docs/evidence-program/research/open-model-diffusion.md) preserve one criteria-set change without inferring model-access or license events. Operational collection and source admission remain disabled.

[Concentration/dependency research](research/concentration-dependencies.json) records five provisional CD collections with distinct evidence bases, scoped rights/access, eight corrections and explicit counting/time limits. It contains no raw source bodies or participant/agency rows. One exact deps.dev generated graph is retained only as a CC BY 4.0 research fixture outside `data/`; the [guide and offline structure reader](../../docs/evidence-program/research/concentration-dependencies.md) preserve indexed nodes/edges without inferring installed use, market shares or failure probabilities. All collections remain unadmitted; ATRS semantic extraction and canonical import remain separate proposals/holds.

[Historical capability-backfill research](research/historical-capability-backfills.json) records five provisional HC families, scoped artifact provenance/rights and guarded date, revision, failure and comparison claims. It does not change the frozen source inventory. The [guide and offline WMT08 reader](../../docs/evidence-program/research/historical-capability-backfills.md) distinguish synthetic-only CI from separately verified private real-artifact acceptance. The actual score gzip and full extracted results are not vendored, and their rights remain unknown; the ACL paper license does not propagate to the gzip. Original metadata and limited sourced examples do not grant rights to linked data or enable canonical import.

## Scientific-progress review

[Scientific progress catalog](research/scientific-progress.json) reviews I4R AI-Games, corrected A-Lab, METR RE-Bench, AlphaTensor and CASP as five unadmitted collections. It preserves report/correction/independent-assessment distinctions, artifact-specific rights and all-six-catalog duplicate comparisons. [A-Lab correction ledger](research/alab-correction-ledger.json) is original manually curated aggregate metadata: two current claims and one qualified historical assertion, one campaign and separate target/recipe denominators. No source bodies, participant records, protocols, sequences or coordinates are copied. The [guide](../../docs/evidence-program/research/scientific-progress.md) distinguishes implemented offline structural validation from proposed source extraction and unresolved provenance/rights holds.

## Persuasion and information research

[Persuasion/information catalog](research/persuasion-information.json) records four producer families and five collections, including two separate Ofcom surveys. The [guide](../../docs/evidence-program/research/persuasion-information.md) distinguishes laboratory effects, content judgments and perceived exposure. A [curated DebateGPT correction ledger](research/debategpt-correction-ledger.json) retains two current contrasts and one superseded p value; no participant data or source datasets are copied. Corrected uncertainty, Costello’s unresolved journal concern, Ofcom rights/geography and Spitale artifact-access/recoding holds remain explicit. These limited facts and metadata do not relicense third-party sources or admit them to the canonical dataset.

## Robotics and physical-world capability research

The [robotics catalog](research/robotics-physical.json) adds five unadmitted candidate families: BARN, RoboArena, RRC2020/TriFinger, PhAIL and STRANDS. The [guide](../../docs/evidence-program/research/robotics-physical.md) keeps physical/simulation/staged/sustained regimes, source versions, assistance and denominators separate. One bounded offline curated BARN Table II validator preserves 60 reported outcomes and separate contest credit. Its CC BY 4.0 source-derived fixture and attribution stay under tools/, outside this data dedication; source facts/metadata do not relicense source materials. PhAIL cohort/metric conflicts, RoboArena export semantics, RRC restrictions and STRANDS rights/units remain held.

## Training-data availability and feedback loops

The [training-data catalog](research/training-data-feedback.json) reviews five unadmitted collections: Common Crawl statistics, Data Provenance Initiative/Consent in Crisis, Collapse or Thrive, FineWeb2 and Epoch data stock. The [guide](../../docs/evidence-program/research/training-data-feedback.md) separates captures, URL/digest cardinality, words, provenance audits, experimental generations and modeled effective stock. One bounded offline Common Crawl reader uses synthetic-only public fixtures; real aggregate CSVs remain unvendored because their specific reuse rights are unknown. Source metadata and hashes do not relicense original artifacts or page content. All nine prior catalogs and the frozen64 remain unchanged.

## Human reliance and decision quality

The [human-reliance catalog](research/human-reliance.json) adds five unadmitted experimental families with documentary schema examples, precise artifact rights/access and all-ten-catalog comparison. The [Okamura aggregate ledger](research/okamura-aggregate-ledger.json) is a manually curated factual summary of one published study, not participant data or workbook extraction. No raw participant rows, minors records or clinical files are vendored. The [guide](../../docs/evidence-program/research/human-reliance.md) separates implemented aggregate checks and provisional synthetic decoder tests from blocked workbook acquisition/acceptance. Source metadata and facts do not relicense source artifacts, waive privacy review or admit canonical records.

## Algorithmic efficiency review

[Curated catalog](research/algorithmic-efficiency.json) and [guide](../../docs/evidence-program/research/algorithmic-efficiency.md) preserve five unadmitted source families, clocks/targets/tuning distinctions, artifact rights and bounded follow-up prompts. Apache-2.0 AlgoPerf fixtures and their derivatives live under tools/, outside data/CC0, with original and derivative hashes/omissions disclosed. They are not canonical imported observations.

## Agent security and incident research

[Seven-collection catalog](research/agent-security-incidents.json) preserves benchmark conditions, family/event/artifact identity, rights and official-source corrections. The [guide](../../docs/evidence-program/research/agent-security-incidents.md) separates completed offline metadata work from held acquisition/mapping and eight bounded documentary prompts. Only self-authored synthetic trace-shaped fixtures are public, under tools/; no generated conversations or source payloads are relicensed by data/CC0.

## Labor-market research review

[Curated catalog](research/labor-market.json) and [guide](../../docs/evidence-program/research/labor-market.md) add four unadmitted collections, a held GL023/AP005 workforce follow-up, all-thirteen-catalog overlap review and seven bounded prompts. The one German Eurostat aggregate fixture is separately licensed under tools/, outside this directory’s CC0 dedication. No live collection, source admission, causal estimate or exposure score.

## Forecast and survey reconstruction

[Seven-collection catalog](research/forecast-surveys.json) and [guide](../../docs/evidence-program/research/forecast-surveys.md) preserve three existing-family enrichments and four new named study/forecast collections, all-fourteen-catalog comparison and eight bounded prompts. A small CC BY 4.0 LEAP instrument/table derivative lives under tools/, outside this data/CC0 dedication. Source metadata and factual summaries do not relicense source reports, unpublished responses or model exports. No pooled forecast, unique-participant sum, live collection or canonical admission.

## Incident and near-miss primary evidence

[Eight-collection catalog](research/incidents-near-misses.json) and [guide](../../docs/evidence-program/research/incidents-near-misses.md) compare all fifteen earlier catalogs, reuse existing NHTSA and OpenAI claims, and distinguish source/artifact/event/claim novelty. A bounded offline two-change NHTSA fact ledger sits under tools/ with a scoped notice. No raw narratives, sensitive patient/personnel records, source corpus, operational collection, canonical import or deployment.

## Research reviews 17–20

Four separately reviewed sessions share one documentation publication batch. Each keeps its own source decisions, corrections, next actions and copy-ready bounded prompts. The original inventory, earlier catalogs and product behavior remain unchanged.

- Session 17: [Inference cost and price–performance](../../docs/evidence-program/research/inference-price-performance.md) · [JSON](research/inference-price-performance.json)
- Session 18: [Claim-to-result provenance](../../docs/evidence-program/research/claim-result-provenance.md) · [JSON](research/claim-result-provenance.json)
- Session 19: [Model identity and retirement histories](../../docs/evidence-program/research/model-identity-retirement.md) · [JSON](research/model-identity-retirement.json)
- Session 20: [Undercovered languages and regions](../../docs/evidence-program/research/undercovered-languages.md) · [JSON](research/undercovered-languages.json)

All four remain unadmitted research metadata. Linked source licenses, unknowns and access restrictions are not changed by the repository’s data dedication. No new source adapter, source corpus, participant records, source/model execution, live collector, canonical import or deployment. The only tooling change permits a contiguous prepared block in the existing dated queue checker, with focused queue regressions.

## Research reviews 21–23

Three separately reviewed sessions share this documentation publication batch. Each keeps its own evidence decisions, corrections, completed checks, open actions and bounded copy-ready prompts.

- Session 21: [Mitigation effectiveness](../../docs/evidence-program/research/mitigation-effectiveness.md) · [JSON](research/mitigation-effectiveness.json)
- Session 22: [Negative results and replications](../../docs/evidence-program/research/negative-replications.md) · [JSON](research/negative-replications.json)
- Session 23: [Compute supply-chain bottlenecks](../../docs/evidence-program/research/compute-supply-chain.md) · [JSON](research/compute-supply-chain.json)

All three remain unadmitted research metadata with artifact-specific rights and evidence holds. Proposed implementations are deferred. No adapter, new validator, source corpus, participant record, source/model execution, live collector, canonical import or deployment is added. The existing shared checks are reused.

## Research reviews 24–26

The final three original source reviews share one documentation publication batch. Each keeps its own evidence decisions, corrections, completed checks, open actions and bounded copy-ready prompts.

- Session 24: [Chinese governance in practice](../../docs/evidence-program/research/chinese-governance.md) · [JSON](research/chinese-governance.json)
- Session 25: [Benchmark drift and contamination](../../docs/evidence-program/research/benchmark-drift.md) · [JSON](research/benchmark-drift.json)
- Session 26: [Electricity and deployment bottlenecks](../../docs/evidence-program/research/electricity-deployment.md) · [JSON](research/electricity-deployment.json)

All three remain unadmitted research metadata with source-specific rights, access and evidence holds. Proposed implementations are deferred. No adapter, new per-report validator, source corpus, personal record, benchmark execution, live collector, canonical import or deployment is added. Existing shared checks are reused.
