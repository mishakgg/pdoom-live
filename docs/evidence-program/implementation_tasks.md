# Evidence program implementation tasks

Step 6 complete as a proposed task plan • 7 October 2026

## Decision and boundaries

Implement a small, verifiable evidence integration before widening collection. Reuse source-native releases with their original identifiers, methods and rights, then investigate specific remaining gaps. Execute one explicitly assigned ticket at a time in dependency order, finish its acceptance evidence, and only then move to the next. This preserves the requested sequential workflow; the dependency graph does not authorize concurrent execution.

This document and its [machine-readable pack](../../data/evidence-program/implementation_tasks.json) contain 27 bounded tasks: 26 planned and one optional deferred UI port. No implementation ticket has been executed by creating this plan. There are no promised dates or effort estimates. P0 means prerequisite, safety or reliability priority; P1 builds the usable evidence path; P2 adds analytical depth or optional work.

The implementation baseline is `c5b9bf85fc9f30a6c82fea72f77647a4a8c9925c`, including [PR 310](https://github.com/mishakgg/pdoom-live/pull/310). Steps 1–5 are already native repository documentation, JSON/CSV and offline tools. The [coverage audit](coverage_findings.md) remains a historical snapshot at `f5274396885dbb654fc2861a78fa5be8f42fad38`; it is not silently refreshed or treated as production truth. The [64-source inventory](source_priorities.md), [frozen proposed contract](dataset_spec.md), [Chinese guide](chinese_guide.md) and [modelling methodology](modelling_methodology.md) are the authoritative planning inputs.

Deployment is explicitly on hold. This backlog does not authorize collection, recurring jobs, paid models, new credentials, production edits, public imports, deletion or deployment. Code assignments, operational approval and publication decisions remain separate. Verify applicable existing or new authorization; do not ask again for an identical bounded action already approved. Required action-time confirmation still applies. Repository publication of this plan is not publication of an evidence dataset. Real source permissions and genuine human review cannot be supplied by synthetic tests.

## Preserve the completed foundation

Do not reissue the earlier code-review tasks as if their fixes were absent. The following 14 fix PRs are merged. Future tickets extend new consumers and must preserve their regressions.

- [PR 296](https://github.com/mishakgg/pdoom-live/pull/296): Caddy upstream replacement visibility
- [PR 297](https://github.com/mishakgg/pdoom-live/pull/297): Withdrawal semantics without reviving older estimates
- [PR 298](https://github.com/mishakgg/pdoom-live/pull/298): Search dismissal and filter state
- [PR 299](https://github.com/mishakgg/pdoom-live/pull/299): Reverse pagination and microsecond boundaries
- [PR 300](https://github.com/mishakgg/pdoom-live/pull/300): Cross-feed identity and retained provenance
- [PR 301](https://github.com/mishakgg/pdoom-live/pull/301): Rollback traffic and schema refusal
- [PR 302](https://github.com/mishakgg/pdoom-live/pull/302): Client/server contract separation and date formatting
- [PR 303](https://github.com/mishakgg/pdoom-live/pull/303): Refresh fairness and malformed payload rejection
- [PR 304](https://github.com/mishakgg/pdoom-live/pull/304): Backup preservation and configuration
- [PR 305](https://github.com/mishakgg/pdoom-live/pull/305): Review export accepted-claim binding
- [PR 306](https://github.com/mishakgg/pdoom-live/pull/306): Transient collector body release
- [PR 307](https://github.com/mishakgg/pdoom-live/pull/307): Compatible sharp and source-map-js updates
- [PR 308](https://github.com/mishakgg/pdoom-live/pull/308): Final PostgreSQL startup readiness
- [PR 309](https://github.com/mishakgg/pdoom-live/pull/309): Probability token preservation and ambiguous-outcome abstention

Earlier [PR 295](https://github.com/mishakgg/pdoom-live/pull/295) established public visibility and exact approval coverage, and [PR 293](https://github.com/mishakgg/pdoom-live/pull/293) plus [PR 294](https://github.com/mishakgg/pdoom-live/pull/294) established bounded private storage and admitted refresh controls. These are foundations to preserve. The F:-only collection boundary and 25,000,000,000-byte ceiling already exist; the remaining operational gates are not proved by their code or fixture tests.

[PR 32](https://github.com/mishakgg/pdoom-live/pull/32) is closed and unmerged at inspection, with head `5585848df48156e1040f63590b1900e975d410fb`. EP27 is a deferred selective port, not permission to reopen or bulk-merge that branch. Its old tests/screenshots are not current-main acceptance evidence.

A separate [PR 310 npm ci log](https://github.com/mishakgg/pdoom-live/actions/runs/37682467711/job/113001749962) reported eight dependency findings: one moderate, five high and two critical. It did not contain advisory-level detail. EP25 verifies affected packages, dependency paths, reachable use and compatible remediation. Counts alone establish neither exploitation nor production exposure, and do not show that PR 310 introduced the findings. This is distinct from the already-fixed sharp/source-map-js work in PR 307.

## Recommended execution order and exits

Start with EP25's read-only advisory triage, then EP01–EP05 to establish the reuse register, compatibility, lineage, rights and bounded-write integration. Keep source IDs and the frozen contract stable. The first exit is a deterministic, rights-aware staging path whose unknown and unsupported cases fail honestly.

Next build the model identity and selected native dataset adapters in EP06–EP14, one at a time. Each ticket covers one release, wave, table or series, rather than an entire publisher or the internet. EP10–EP11 establish actual Chinese processing and review evidence. Integrate EP15's bounded retrieval/backfill before enabling new acquisition. Offline fixtures and native-release reconciliation are distinct from any authorized live sample.

EP16–EP17 provide a limited existing-helper readiness/pilot path, independent of the proposed new ledger and adapters. They require current bounded-storage regression evidence and operational gates, not completion of EP01–EP05. They are not automatic tasks triggered by merging code. Their completion requires the secure user handoff, verified account/quota/root and synthetic transaction, then satisfaction of the existing one-time metadata-pilot release gates. Prior approval for the unchanged bounded workflow remains valid; no redundant chat approval is required. EP18 only prepares a proposal for one genuine gap after reuse and rights have been checked. Preparing that decision does not require a completed live pilot; missing execution prerequisites are recorded in the proposal. A blocked source stays blocked.

EP19–EP22 provide reconciled coverage, a conservative review bridge, public-facing coverage UI and immutable history. EP23–EP24 implement shadow analyses and resolution admission while public scoring remains disabled. EP26 checks recovery and compiles an independently reviewed release-candidate record. It does not deploy or publish. EP27 remains optional after the evidence journey is accepted.

Dependencies in the machine-readable pack are prerequisites, not permission grants. A blocked operational gate does not prevent independent offline planning, but it must not be bypassed or marked complete. Before each assigned ticket, recheck current main and work already landed; amend the plan if the exact baseline or scope changed.

## Evidence required for every ticket

- Exact resulting commit, changed paths, owner/reviewer roles and links to the accepted scope
- Commands actually run, exit status and test counts; distinguish passed, failed, blocked and never run
- Input release IDs, fixture hashes, transformation versions and reproducible outputs where relevant
- Negative and interrupted/repeated-flow cases, not just the happy path
- Rights, privacy, temporal, scientific and operational limitations that remain
- Migration/rollback implications, with production actions explicitly excluded unless separately approved

Run the existing aggregate check, `python tools/evidence_program/check.py`, for evidence-program changes. Preserve the 71 frozen contract tests and hashes. Pipeline changes also require applicable `PYTHONPATH=pipeline python -m pytest ...` suites; application changes require relevant `npm test -- ...`, lint, typecheck and build checks under supported Node 22, plus disposable-DB or browser tests where the ticket calls for them. New paths below are proposals, so their future test commands are not claimed to exist or pass today. Never point reset/import tests at production.

Existing paths below were verified in the full baseline tree. Proposed paths were absent there; they are suggested ownership boundaries, not claims that modules already exist. A future legitimate implementation can create them without invalidating the historical baseline. Do not mutate the frozen v0.1 package or expand production schemas merely to make a proposed path convenient.

## EP01 Pin reuse releases and coverage opportunities

P0 • Foundation • planned

Owner role: Data curator and data engineer. Dependencies: none.

Create a separate versioned operational register for the existing 64 families. For an initial named artifact in each selected family, record native release/key/schema, acquisition path, artifact-specific rights, expected enumeration if available and why reuse does or does not fill the gap. Keep the research inventory frozen as candidate_not_collected; do not silently reinterpret its dated audit as live status.

Existing paths: [data/evidence-program/source_inventory.json](../../data/evidence-program/source_inventory.json), [data/evidence-program/coverage_mapping.json](../../data/evidence-program/coverage_mapping.json), [tools/evidence_program/check.py](../../tools/evidence_program/check.py).

Proposed paths: `data/evidence-program/admission_register.json`, `tools/evidence_program/admission.py`.

Acceptance tests:

1. All 64 stable IDs reconcile exactly with the inventory; operational states distinguish discovered, approved, attempted, observed and reviewed.
2. A catalog, API adapter or download link cannot satisfy observed status without a verified artifact and run reference.
3. Undefined universes remain unknown; blocked/rights-unknown families remain in discovery counts but not due-admitted-check denominators.
4. Each initial candidate explicitly records reuse-before-new-collection reasoning; fixtures with no need for new collection produce no collection request.

Completion evidence:

- Versioned register, controlled vocabulary, validation report and one reviewed candidate decision per selected domain.
- Audit comparison showing research files unchanged and no admission/collection enabled.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP02 Specify the lossless compatibility bridge

P0 • Foundation • planned

Owner role: Contract and database owner. Dependencies: EP01.

Define and prototype a read-only mapping from proposed exact-revision records to legacy source/person/statement/forecast representations and an explicit unmappable queue. Mark model, measurement, safety and incident records as additive staging types; do not squeeze them into personal forecasts. Preserve the frozen v0.1 package and separately propose any necessary versioned contract evolution.

Existing paths: [tools/evidence_program/contracts/dataset.schema.json](../../tools/evidence_program/contracts/dataset.schema.json), [tools/evidence_program/validate_dataset.py](../../tools/evidence_program/validate_dataset.py), [packages/contracts/src/schemas.ts](../../packages/contracts/src/schemas.ts), [packages/db/migrations/001_init.sql](../../packages/db/migrations/001_init.sql), [docs/INGESTION_CONTRACT.md](../../docs/INGESTION_CONTRACT.md).

Proposed paths: `docs/evidence-program/compatibility-bridge.md`, `tools/evidence_program/bridge_contract.py`.

Acceptance tests:

1. Round-trip a representable source/statement/forecast fixture without changing attribution, exact question, conditions, horizon or accepted interpretation.
2. Large decimals, unsupported bounds/interval semantics, anonymous collectives and incompatible units fail with precise reasons rather than round/truncate or invent IDs.
3. All 71 frozen contract tests and fingerprints pass unchanged; unsupported records remain inspectable in staging.
4. Prototype performs zero DB writes and outputs a deterministic mapping report.

Completion evidence:

- Reviewed mapping/compatibility decision, loss table, synthetic round-trip and rejection reports.
- Explicit future migration boundary and backwards-compatibility strategy, without a migration being executed.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP03 Build immutable upstream staging records

P0 • Foundation • planned

Owner role: Pipeline engineer. Dependencies: EP02.

Add an isolated evidence-stage ledger behind the bounded-write seam. Pin native dataset release and row key, record ordered transformations, preserve immutable exact revisions and known_at, and retain source-original/translation/reporting lineage. It must not write to application seeds or the production canonical importer.

Existing paths: [pipeline/pdoom_pipeline/ingest/store.py](../../pipeline/pdoom_pipeline/ingest/store.py), [pipeline/pdoom_pipeline/ingest/writes.py](../../pipeline/pdoom_pipeline/ingest/writes.py), [pipeline/pdoom_pipeline/export/versions.py](../../pipeline/pdoom_pipeline/export/versions.py), [tools/evidence_program/validate_dataset.py](../../tools/evidence_program/validate_dataset.py).

Proposed paths: `pipeline/pdoom_pipeline/evidence_staging/ledger.py`, `tests/test_evidence_staging_ledger.py`.

Acceptance tests:

1. Identical replay produces identical identity/revision and no duplicate record; changed native data appends a revision without overwriting earlier references.
2. Corrections and tombstones retain predecessor links; source-local keys cannot collide across datasets/releases.
3. A late-discovered old document receives current known_at, and reprocessing cannot backdate it.
4. Interrupted append recovers to the prior valid commit; referenced objects and hashes cannot silently disappear.
5. Adversarial source text asking for tool use, credential disclosure or schema changes remains inert evidence; fixtures demonstrate zero instruction-triggered network/tool activity and no secret material in extraction inputs or outputs.

Completion evidence:

- Ledger format and fixture transcripts for replay/change/crash.
- Golden hashes, dependency-closure report and explicit nonproduction storage routing.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP04 Enforce artifact and derivative rights

P0 • Foundation • planned

Owner role: Rights curator and pipeline engineer. Dependencies: EP01.

Extend existing admission/retention checks to reused releases and their derivatives. Keep metadata, raw storage, excerpts, translation/processing and redistribution permissions distinct, with basis, expiry and revocation lineage. Preserve existing transient-body cleanup and fail-closed source pins rather than replacing them.

Existing paths: [pipeline/pdoom_pipeline/rights.py](../../pipeline/pdoom_pipeline/rights.py), [pipeline/pdoom_pipeline/refresh/runner.py](../../pipeline/pdoom_pipeline/refresh/runner.py), [tests/test_rights.py](../../tests/test_rights.py), [tests/test_refresh_response_retention.py](../../tests/test_refresh_response_retention.py), [docs/SOURCE_AND_PROVENANCE_POLICY.md](../../docs/SOURCE_AND_PROVENANCE_POLICY.md).

Proposed paths: `pipeline/pdoom_pipeline/evidence_staging/rights_gate.py`, `tests/test_evidence_rights_gate.py`.

Acceptance tests:

1. A code license cannot clear underlying benchmark tasks or news text; link-only and metadata-only inputs cannot retain prohibited body sentinels.
2. Expiry/revocation affects every retained original/translation/excerpt revision and reports separately any public artifact requiring reviewed action.
3. Unknown rights cannot become redistribution_allowed from availability, a filename or prose claim.
4. Permission changes are versioned; blocked acquisition neither advances the cursor nor marks an empty successful collection.

Completion evidence:

- Artifact permission matrix with evidence links and a reviewed initial source decision.
- Retention/revocation negative tests and regression results for existing rights controls.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP05 Extend bounded writes to new data paths

P0 • Foundation • planned

Owner role: Storage and pipeline engineer. Dependencies: EP03, EP04.

Route all new evidence-stage writes, parser temporaries, decompression output, retries and logs through the existing F:-only collection gateway. Preserve the exact 25,000,000,000-byte cap, journal reserve, low-disk stop, single-writer lock and verified-manifest-before-cleanup ordering. Add integration coverage for new consumers; do not rebuild BoundedScratch.

Existing paths: [pipeline/pdoom_pipeline/collection_storage/scratch.py](../../pipeline/pdoom_pipeline/collection_storage/scratch.py), [pipeline/pdoom_pipeline/collection_storage/supervisor.py](../../pipeline/pdoom_pipeline/collection_storage/supervisor.py), [pipeline/pdoom_pipeline/refresh/runner.py](../../pipeline/pdoom_pipeline/refresh/runner.py), [tests/test_collection_storage.py](../../tests/test_collection_storage.py), [tests/test_collection_storage_runner.py](../../tests/test_collection_storage_runner.py), [docs/COLLECTION_STORAGE.md](../../docs/COLLECTION_STORAGE.md).

Proposed paths: `tests/test_evidence_storage_integration.py`.

Acceptance tests:

1. Mock byte accounting includes old target plus replacement bytes, parser scratch and retry payloads; no test allocates 25 GB.
2. A new adapter blocked mid-write preserves prior checkpoint and removes only its own incomplete output.
3. Path traversal, symlinks/reparse points and uncontrolled C: or system-temp fallback are rejected.
4. Existing collection-storage and actual-runner suites pass; fake Drive verifies manifest/checkpoint/cleanup order for new artifact descriptors.

Completion evidence:

- Exact command results, bounded-writer coverage map and fault-injection log.
- Zero raw-body sentinel retention under metadata-only policy.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP06 Resolve models and release events

P1 • Domain integration • planned

Owner role: Data model engineer. Dependencies: EP03.

Planning references: GL001, CN001.

Build deterministic model-family/checkpoint/provider-label crosswalks with evidence and separate announcement, preview, API, weights, update and withdrawal events. Preserve parent/fine-tune/distillation relationships without treating a family, product, lab and actor as aliases.

Existing paths: [tools/evidence_program/contracts/model_version.schema.json](../../tools/evidence_program/contracts/model_version.schema.json), [tools/evidence_program/contracts/release_event.schema.json](../../tools/evidence_program/contracts/release_event.schema.json), [data/evidence-program/chinese/aliases.json](../../data/evidence-program/chinese/aliases.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_staging/model_identity.py`, `tests/test_model_identity.py`.

Acceptance tests:

1. A mutable API label across two dates cannot assert one immutable checkpoint.
2. An announcement before access remains a separate event; unknown dates keep precision and do not become midnight UTC.
3. Kimi versus its developer, a model family versus checkpoint, and bilingual name candidates remain distinct unless supported.
4. Duplicate release reporting adds provenance without adding a new released model.

Completion evidence:

- Reviewed identity crosswalk for synthetic multi-provider/bilingual cases and nonmerge decisions.
- Deterministic event-linkage tests and source-version references.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP07 Integrate one Epoch model release

P1 • Domain integration • planned

Owner role: Dataset adapter engineer. Dependencies: EP01, EP04, EP05, EP06.

Planning references: GL001, R02.

Implement a fixture-first importer for one pinned GL001 models release, retaining native rows and upstream measurement methods. Emit model/version links and compute/resource observations only for that release. Keep hardware/facility datasets as separate later extensions, not an implicit crawl.

Existing paths: [data/evidence-program/global_sources.json](../../data/evidence-program/global_sources.json), [data/catalogs/epoch_pages.json](../../data/catalogs/epoch_pages.json), [pipeline/pdoom_pipeline/catalogs/epoch.py](../../pipeline/pdoom_pipeline/catalogs/epoch.py), [tools/evidence_program/contracts/resource_observation.schema.json](../../tools/evidence_program/contracts/resource_observation.schema.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_adapters/epoch_models.py`, `tests/test_epoch_models_dataset.py`.

Acceptance tests:

1. Fixture row count and native IDs reconcile to the selected release subset; replay has no duplicates.
2. Reported versus estimated compute, training phase, total versus active parameters, units and missingness survive round-trip.
3. Decimal values larger than legacy finite precision remain exact in staging and are quarantined by an incompatible bridge.
4. Revised native estimates append revisions; benchmark-derived compute carries the dependency and is excluded from independent compute-performance evidence.

Completion evidence:

- Pinned release/schema/rights decision and transformation manifest.
- Original-versus-normalized field reconciliation and fixture validation; any later permitted live sample separately labelled.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No hardware/facility bulk ingestion, paid API use or invented missing compute.

## EP08 Integrate one benchmark result release

P1 • Domain integration • planned

Owner role: Evaluation data engineer. Dependencies: EP01, EP04, EP05, EP06.

Planning references: GL004, R01.

Implement a fixture-first GL004 METR result-release adapter with suite/scaffold/run identity, human-duration metric definition, p50/p80 distinction, dates and uncertainty. Pin one upstream release; do not merge suite revisions or infer general intelligence from a task horizon.

Existing paths: [data/catalogs/metr_pages.json](../../data/catalogs/metr_pages.json), [tools/evidence_program/contracts/benchmark_run.schema.json](../../tools/evidence_program/contracts/benchmark_run.schema.json), [data/evidence-program/analysis_recipes.json](../../data/evidence-program/analysis_recipes.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_adapters/metr_results.py`, `tests/test_metr_results_dataset.py`.

Acceptance tests:

1. Same model on different suites, scaffolds or success thresholds remains distinct.
2. An upstream correction preserves as-published and revised result versions; a protocol break cannot draw an unqualified continuous series.
3. Missing evaluations, suspected contamination and uncertain model labels remain explicit; task limits block unsupported extrapolation.
4. Duplicate report/translations of one run add citations, not independent measurements.

Completion evidence:

- Release and run crosswalk, extracted-table reconciliation, negative comparability tests and fixture hashes.
- Reviewer-approved metric definition and stated upstream task-range limitations.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No new model evaluations, universal leaderboard or automatic risk conversion.

## EP09 Integrate one original survey wave

P1 • Domain integration • planned

Owner role: Survey data engineer and methodologist. Dependencies: EP01, EP03, EP04, EP05.

Planning references: GL010, R05, R07.

Map one pinned GL010 AI Impacts wave and its native question/statistic rows. Preserve instrument wording, sample/recruitment/response context, weights and question semantics. Where only source aggregates are available, represent the wave collective and separate publisher; do not manufacture respondents or person-level forecasts.

Existing paths: [tools/evidence_program/contracts/actor.schema.json](../../tools/evidence_program/contracts/actor.schema.json), [tools/evidence_program/contracts/forecast.schema.json](../../tools/evidence_program/contracts/forecast.schema.json), [tools/evidence_program/contracts/forecast_question.schema.json](../../tools/evidence_program/contracts/forecast_question.schema.json), [data/evidence-program/global_sources.json](../../data/evidence-program/global_sources.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_adapters/ai_impacts_wave.py`, `tests/test_survey_wave_dataset.py`.

Acceptance tests:

1. Response percentages and median event probabilities cannot share the same interpreted quantity.
2. Wave/question revisions, conditioning and horizon survive normalization; missing response counts remain unknown.
3. An aggregate is attributed to the collective, not publishing organization, and anonymous rows stay anonymous.
4. Percent-to-probability conversion is exact and versioned; overlap across waves is recorded or explicitly unknown.

Completion evidence:

- Native wave/question/statistic crosswalk and instrument evidence references.
- Schema and semantic fixtures, aggregate reconciliation and privacy/rights review.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No Metaculus/Manifold scraping, cross-survey consensus or respondent identification.

## EP10 Preserve Chinese evidence and coordinates

P1 • Language integration • planned

Owner role: Multilingual pipeline engineer. Dependencies: EP03, EP04.

Planning references: CN001, CN018, R05, R06.

Implement language-preserving staging/export and a named Unicode coordinate/alignment transform for Chinese originals and derivatives. Fix only the documented language/sentence-boundary seams, preserving English behavior and the merged probability abstention guards. Original bytes/text, translation lineage and normalization versions remain separate.

Existing paths: [pipeline/pdoom_pipeline/extract/statements.py](../../pipeline/pdoom_pipeline/extract/statements.py), [pipeline/pdoom_pipeline/export/corpus.py](../../pipeline/pdoom_pipeline/export/corpus.py), [pipeline/pdoom_pipeline/export/versions.py](../../pipeline/pdoom_pipeline/export/versions.py), [data/evidence-program/chinese/test_cases.json](../../data/evidence-program/chinese/test_cases.json), [docs/evidence-program/chinese_guide.md](../../docs/evidence-program/chinese_guide.md).

Proposed paths: `pipeline/pdoom_pipeline/evidence_staging/language.py`, `tests/test_chinese_evidence_normalization.py`.

Acceptance tests:

1. Chinese 。！？ sentence boundaries and original language survive the actual extraction/export path; English regressions remain green.
2. All 25 preparation cases run through the real new normalization layer; offsets recover the exact original substring across emoji, fullwidth forms and combining marks.
3. Bounds, negation, conditions, 万/亿 magnitudes and year-only dates retain meaning; ambiguous OCR/兆/idioms abstain.
4. A translation links its exact original revision and cannot add an independent forecaster; unsupported interval/percentage-point forms stay flagged rather than extending frozen enums.
5. Chinese and English instructions embedded in documents cannot override parsing/review policy, issue tool calls or supply human approval; retain or reject them as untrusted source content.

Completion evidence:

- Actual-parser test report distinguishing passed vectors from linguistic adequacy.
- Coordinate convention, alignment examples and before/after language round-trip results.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP11 Adjudicate a multilingual extraction holdout

P1 • Language integration • planned

Owner role: Bilingual reviewers and evaluation lead. Dependencies: EP10, EP04.

Planning references: R05, R06.

Define a small, bounded rights-cleared evaluation set and annotation guide for original Chinese, traditional script, official translations, reported quotations, collective statements and hard negatives. Start with the existing synthetic cases; admitting real examples is a separate rights/reviewer decision. Freeze work/translation/speaker-family/time splits before evaluation.

Existing paths: [data/evidence-program/chinese/test_cases.json](../../data/evidence-program/chinese/test_cases.json), [data/evidence-program/chinese/query_lexicon.json](../../data/evidence-program/chinese/query_lexicon.json), [pipeline/pdoom_pipeline/belief/evaluate.py](../../pipeline/pdoom_pipeline/belief/evaluate.py).

Proposed paths: `docs/evidence-program/multilingual-annotation.md`, `data/evidence-program/evaluation_manifest.json`, `tools/evidence_program/evaluate_extraction.py`.

Acceptance tests:

1. Two actual competent reviewers independently label a declared subset; disagreements and adjudication are recorded without invented reviewer identities.
2. All translations of one work stay in the same split; no outcome-informed tuning uses the holdout.
3. Report field-level critical errors, precision/recall, abstention and coverage by language/type with counts, plus always-abstain/overemit baselines.
4. If real examples or reviewers are unavailable, report the exact blocker and synthetic-only scope; do not claim extractor performance.

Completion evidence:

- Annotation guide, frozen split manifest, consent/rights scope and disagreement ledger.
- Versioned evaluation report with adequacy/threshold decision made before model comparison.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No paid model calls, mass translation, human_verified auto-promotion or claimed national representation.

## EP12 Extract one safety evaluation table

P1 • Domain integration • planned

Owner role: Safety evaluation curator. Dependencies: EP04, EP05, EP06.

Planning references: GL017, R03.

Create a document/table adapter for one selected GL017 evaluation report and one bounded table or result family. Preserve exact page/cell locators, threat model, evaluator, configuration, mitigation state, measurement status, thresholds and limitations. Link reused developer results instead of duplicating them as independent experiments.

Existing paths: [tools/evidence_program/contracts/safety_evaluation.schema.json](../../tools/evidence_program/contracts/safety_evaluation.schema.json), [data/catalogs/uk_aisi_pages.json](../../data/catalogs/uk_aisi_pages.json), [data/evidence-program/global_sources.json](../../data/evidence-program/global_sources.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_adapters/safety_table.py`, `tests/test_safety_table_dataset.py`.

Acceptance tests:

1. Two differing threat models or mitigation settings cannot be pooled merely because both report a percent.
2. Zero observed failures retains trial count and does not emit zero global risk.
3. A third-party report quoting a developer table remains reported evidence with original lineage.
4. Ambiguous headers/footnotes block acceptance; one manually checked table reconciles every emitted result.
5. Preserve source disclosure_level and enforce field-level publication limits; restricted operational evaluation details remain outside public exports even when summary results are admissible.

Completion evidence:

- Artifact/rights pin, table-to-record reconciliation and qualified safety-review signoff.
- Negative comparability and duplicate-lineage tests.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP13 Integrate incident histories without report inflation

P1 • Domain integration • planned

Owner role: Incident data curator and adapter engineer. Dependencies: EP03, EP04, EP05.

Planning references: GL018, R03.

Add a snapshot importer for the permitted GL018 incident metadata/taxonomy collections. Preserve native incident/report IDs, event/report dates, source corrections, verification, causal attribution and severity rubric. The existing one-incident metadata collector is not a bulk importer; extend through a distinct interface.

Existing paths: [pipeline/pdoom_pipeline/collectors/aiid.py](../../pipeline/pdoom_pipeline/collectors/aiid.py), [tools/evidence_program/contracts/incident.schema.json](../../tools/evidence_program/contracts/incident.schema.json), [data/evidence-program/global_sources.json](../../data/evidence-program/global_sources.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_adapters/aiid_snapshot.py`, `tests/test_incident_snapshot_history.py`.

Acceptance tests:

1. Two reports, a translation and a later correction can resolve to one event while remaining separate source revisions.
2. Merge/split/correction histories are reversible and never erase earlier evidence.
3. Report full-text exclusions are enforced, and unnecessary victim identifiers are absent.
4. Counts explicitly distinguish reports, alleged/reviewed events and near misses; a missing exposure denominator prevents rate output.

Completion evidence:

- Pinned collection/license exclusions, native ID/event mapping and change-log fixture.
- Report-versus-event reconciliation and correction/replay tests.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No unlicensed news archive, automatic culpability findings or hazard-to-extinction conversion.

## EP14 Integrate one adoption statistical series

P1 • Domain integration • planned

Owner role: Statistical data engineer. Dependencies: EP03, EP04, EP05.

Planning references: GL022, R04.

Map one bounded GL022 Eurostat enterprise-AI series release with its country/sector/size/time dimensions, population, units, flags and methodological metadata. Preserve native cells rather than flattening diverse denominators into one adoption value.

Existing paths: [tools/evidence_program/contracts/resource_observation.schema.json](../../tools/evidence_program/contracts/resource_observation.schema.json), [data/evidence-program/global_sources.json](../../data/evidence-program/global_sources.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_adapters/eurostat_adoption.py`, `tests/test_adoption_series.py`.

Acceptance tests:

1. Series dimensions, periods and footnote flags reproduce the selected native cells.
2. Missing/suppressed values remain missing; estimated values retain status and weights are not invented.
3. Question/population breaks segment the series and incompatible national measures cannot be ranked together.
4. Signed percent-change and bounded percent/probability fields use the correct declared metric.

Completion evidence:

- Native dimension/codebook map and exact selected-cell reconciliation.
- Fixture tests for suppressed data, denominator differences and breaks.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP15 Resume bounded retrieval and historical backfill

P0 • Acquisition reliability • planned

Owner role: Pipeline engineer. Dependencies: EP03, EP04, EP05.

Add source-release pagination/backfill state for admitted evidence adapters without introducing a schedule. Preserve existing retry limits and fairness; use deterministic request/cursor identity, explicit time/byte/request budgets and transactional state commits after durable staging. Keep historical missing ranges visible.

Existing paths: [pipeline/pdoom_pipeline/fetch.py](../../pipeline/pdoom_pipeline/fetch.py), [pipeline/pdoom_pipeline/ingest/collection_state.py](../../pipeline/pdoom_pipeline/ingest/collection_state.py), [pipeline/pdoom_pipeline/refresh/runner.py](../../pipeline/pdoom_pipeline/refresh/runner.py), [tests/test_refresh_fairness_and_validation.py](../../tests/test_refresh_fairness_and_validation.py).

Proposed paths: `pipeline/pdoom_pipeline/evidence_staging/backfill.py`, `tests/test_evidence_backfill.py`.

Acceptance tests:

1. 429/Retry-After, timeout, malformed page and cancellation consume finite budgets and preserve the last good checkpoint.
2. Reordered/overlapping pages and replay cannot skip or duplicate native rows; an invalid later page cannot commit its cursor.
3. A permanently failing source cannot starve another; source rebinding or changed rights requires renewed admission.
4. A backfill resumes after interruption and marks unenumerable/incomplete historical windows without claiming exhaustive coverage.
5. New consumers preserve redirect-origin admission, DNS/private/loopback/link-local/cloud-metadata SSRF guards, content-type checks, response/decompression caps and parser time/resource budgets. Adversarial fixtures fail before protected requests or unbounded writes, with zero unauthorized outbound calls.

Completion evidence:

- Failure-state transition matrix and deterministic request/cursor traces.
- Existing fairness/payload tests plus crash/replay/backfill results.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No scheduler activation, broader source access or reconstruction by deleting existing state.

## EP16 Verify private Drive operational prerequisites

P0 • Gated operations • planned

Owner role: User and authorized storage operator. Dependencies: none.

Complete the already-designed secure credential, account/quota/root-pin and synthetic write/readback gates through the existing helpers, only when the user resumes the approved handoff. Record redacted pass/fail evidence separately from credentials. Current sign-in or CI success must not substitute for runner OAuth. This existing-helper readiness path is independent of EP01–EP05 and does not certify new evidence adapters, staging or public semantics.

Existing paths: [pipeline/pdoom_pipeline/collection_storage/bootstrap.py](../../pipeline/pdoom_pipeline/collection_storage/bootstrap.py), [pipeline/pdoom_pipeline/collection_storage/drive.py](../../pipeline/pdoom_pipeline/collection_storage/drive.py), [pipeline/pdoom_pipeline/collection_storage/readiness.py](../../pipeline/pdoom_pipeline/collection_storage/readiness.py), [docs/COLLECTION_STORAGE.md](../../docs/COLLECTION_STORAGE.md).

Proposed paths: `docs/evidence-program/private-storage-readiness.md`.

Acceptance tests:

1. Run the existing collection-storage and actual-runner regression suites at the current assigned commit, verify the bounded write hook and source pins, and record exact outcomes before the operational smoke. New ledger/adapter implementation is not a prerequisite.
2. Action-time consent uses the existing approved client and drive.file only; secure credentials/session URLs never enter repository, CLI arguments or logs.
3. API readback verifies the intended account, stable owner permission ID, finite quota and owner-only writable personal root.
4. A synthetic artifact is uploaded/read back with matching size/checksum and manifest identity; wrong account/quota/privacy stops before mutation.
5. All authentication caches and temporary state obey the F: boundary; failed checks leave truthful blocked status.

Completion evidence:

- Redacted readiness record with exact helper versions and gate outcomes, no account email/IDs/secrets in public material.
- Synthetic transaction verification and local cleanup ordering evidence.

Authorization gate: Use the existing approved account/client workflow and complete the secure user handoff plus any required action-time OAuth consent. Verify applicable existing or new authorization for the bounded synthetic transaction; do not repeat consent already valid for an identical action. No live-source collection is included.

Scope exclusions: No full-Drive scope, service-account substitution, credential discovery, live corpus or deployment.

## EP17 Run the pinned metadata pilot once

P1 • Gated operations • planned

Owner role: Authorized collection operator and independent reviewer. Dependencies: EP16.

After the documented release gates pass, run only the existing reviewed eight-feed metadata pilot. Recheck exact URL/method/rights pins and use the existing storage transaction. This verifies operational continuity; it does not acquire the new quantitative datasets or permit raw-body retention.

Existing paths: [pipeline/pdoom_pipeline/collection_storage/pilot.py](../../pipeline/pdoom_pipeline/collection_storage/pilot.py), [pipeline/pdoom_pipeline/collection_storage/pilot_sources.json](../../pipeline/pdoom_pipeline/collection_storage/pilot_sources.json), [pipeline/pdoom_pipeline/collection_storage/supervisor.py](../../pipeline/pdoom_pipeline/collection_storage/supervisor.py), [tests/test_collection_storage_runner.py](../../tests/test_collection_storage_runner.py).

Proposed paths: `docs/evidence-program/metadata-pilot-result.md`.

Acceptance tests:

1. At most the eight pinned feeds run, with extraction/evidence/raw retention disabled and no lead expansion.
2. Each result distinguishes new/changed/unchanged/skipped/failed, and a partial run remains partial.
3. Remote bytes/hashes/owner/privacy/parent/manifest verify before local checkpoint and exact-file cleanup; corruption prevents deletion.
4. Restart after a lost completion response, manifest failure or committed-cleanup interruption neither duplicates upload nor refetches committed work unnecessarily.

Completion evidence:

- Redacted source-run outcomes and verified manifest/checksum summary.
- Independent review of cap/rights/no-public-import invariants and remaining blockers.

Authorization gate: Requires successful EP16, current rights/URL review and the documented one-time release gates. Verify applicable existing or new authorization for these exact feeds; the prior bounded approval remains valid when its scope is unchanged. No recurring or expanded collection authorization is implied.

## EP18 Prepare one genuine evidence gap for collection

P2 • Gap completion • planned

Owner role: Data curator and language/domain reviewer. Dependencies: EP01, EP04.

Planning references: CN001, CN018.

Select at most one material gap after checking admitted upstream releases and their native records. Prefer a missing Chinese original or an absent version/time period when it changes a defined analysis. Prepare a bounded source/URL/window/record/byte request with reviewers, access method, rights and a stopping condition; do not turn a source on by editing the research inventory. Preparing the decision does not require a live pilot or completed language/backfill implementation; record those as unmet execution prerequisites where applicable.

Existing paths: [data/evidence-program/source_inventory.json](../../data/evidence-program/source_inventory.json), [data/evidence-program/coverage_mapping.json](../../data/evidence-program/coverage_mapping.json), [data/evidence-program/chinese/query_lexicon.json](../../data/evidence-program/chinese/query_lexicon.json).

Proposed paths: `data/evidence-program/gap_collection_proposal.json`, `docs/evidence-program/gap-collection-decision.md`.

Acceptance tests:

1. The gap names the exact question/run/version/period and documents why existing releases or references do not fill it.
2. A duplicate, translation or already available upstream record cancels new collection in favor of reuse.
3. The proposal supplies explicit caps, an uncertainty/rights stop and a review route.
4. Blocked access, missing license or unsupported extraction leaves the gap visible; no workaround bypasses the restriction.

Completion evidence:

- One reviewed go/no-go proposal, upstream search record and expected analytical benefit.
- If later authorized, a separately recorded bounded acquisition result; approval itself is not collection completion.

Authorization gate: This ticket prepares a proposal only. Any actual source acquisition must pass source admission and be covered by applicable existing or new authorization for its named scope.

Scope exclusions: No blanket Chinese crawl, prohibited scraping or treating absent evidence as low risk.

## EP19 Compute coverage with honest denominators

P1 • Review and presentation • planned

Owner role: Data quality engineer. Dependencies: EP01, EP03, EP15.

Planning references: R01, R03, R04, R05.

Add a versioned evidence-coverage report alongside existing person coverage. Count source-period opportunities, artifacts, native rows, model runs, survey waves, event clusters and review/publication stages separately. Reconcile stored stage transitions and make missingness, freshness and language overlap inspectable.

Existing paths: [pipeline/pdoom_pipeline/quality/coverage.py](../../pipeline/pdoom_pipeline/quality/coverage.py), [packages/db/src/coverage.ts](../../packages/db/src/coverage.ts), [tests/test_coverage_2026_10.py](../../tests/test_coverage_2026_10.py), [data/evidence-program/baseline_metrics.json](../../data/evidence-program/baseline_metrics.json).

Proposed paths: `pipeline/pdoom_pipeline/evidence_staging/coverage.py`, `tests/test_evidence_coverage.py`.

Acceptance tests:

1. All 64 planning families reconcile; discovered and due-admitted populations differ explicitly.
2. Zero denominator yields null, not zero/100%; overlapping language/domain memberships are not summed as a partition.
3. Catalog-only, failed, observed-no-relevant-record and awaiting-review fixtures receive different states.
4. Duplicate publication does not inflate run/incident/person counts, and fixed-frame comparisons distinguish new evidence from frame expansion.

Completion evidence:

- Versioned formula/denominator definitions, ID-level reconciliation and golden report.
- Current person-coverage regressions unchanged; historical audit files remain dated and unmodified.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP20 Bridge private review and publication policy

P1 • Review and presentation • planned

Owner role: Database and review owner. Dependencies: EP02, EP03, EP04, EP06, EP08, EP09, EP10, EP12, EP13.

Design and implement the minimum disposable-DB bridge for reviewed compatible evidence while keeping new-type staging isolated. Preserve existing accepted-claim snapshot equality, append-only decisions, stale-approval downgrade and public read gates. New additive data types require an explicitly reviewed schema/migration plan; do not overwrite the frozen proposal or broaden existing page eligibility accidentally.

Existing paths: [packages/db/src/import.ts](../../packages/db/src/import.ts), [packages/db/src/review.ts](../../packages/db/src/review.ts), [packages/db/src/public-read.ts](../../packages/db/src/public-read.ts), [packages/db/src/website-visibility.ts](../../packages/db/src/website-visibility.ts), [test/approval-coverage.test.ts](../../test/approval-coverage.test.ts), [test/review-manifest.test.ts](../../test/review-manifest.test.ts), [test/public-visibility.test.tsx](../../test/public-visibility.test.tsx).

Proposed paths: `docs/evidence-program/review-bridge.md`, `test/evidence-review-bridge.test.ts`.

Acceptance tests:

1. Exact unchanged import preserves a real review; changed interpretation, model/run identity, condition, evidence locator or rights requires the appropriate new review.
2. Unknown/restricted private material cannot leak through pages, search, reverse source links, API or downloads.
3. Collective forecasts cannot become fictitious persons and measurements cannot become personal probabilities.
4. Transactional failure leaves existing application data unchanged; compatibility failures remain inspectable with reasons.

Completion evidence:

- Approved policy/mapping and migration/recovery decision if needed, tested only in disposable DBs.
- Real-DB review/import/public-negative fixtures plus existing approval/manifest/visibility suites.

Authorization gate: Future code/DB-design assignment; local disposable databases only. Public import, permission changes and production migration must be covered by applicable existing or new authorization; they are not performed by this ticket.

## EP21 Expose coverage and provenance in the UI

P1 • Review and presentation • planned

Owner role: Product and accessibility engineer. Dependencies: EP19, EP20.

Add bounded coverage/drill-down views to existing data and methodology journeys. Show stage, source frame, definition, dates, exclusions and source-native lineage, with safe routes to approved evidence. Keep private diagnostics out of public endpoints; use labelled synthetic fixtures for UI development.

Existing paths: [apps/web/app/data/page.tsx](../../apps/web/app/data/page.tsx), [apps/web/app/methodology/page.tsx](../../apps/web/app/methodology/page.tsx), [apps/web/components/statement-audit.tsx](../../apps/web/components/statement-audit.tsx), [packages/db/src/queries.ts](../../packages/db/src/queries.ts), [test/data-page-copy.test.tsx](../../test/data-page-copy.test.tsx), [test/research-navigation.test.ts](../../test/research-navigation.test.ts).

Proposed paths: `apps/web/components/evidence-coverage.tsx`, `test/evidence-coverage-ui.test.tsx`.

Acceptance tests:

1. A user can distinguish registered versus observed versus reviewed data and inspect a denominator/exclusion.
2. Empty/unknown/stale/failed states cannot look like zero risk or complete coverage.
3. Server pagination and stable filters bound response/DOM size; reverse links respect public policy.
4. Keyboard, screen reader labels, 320/390/768/1280 widths and 200%/400% reflow show no obscured content or unlabeled chart meaning.
5. Hostile titles, excerpts, source URLs and metadata render as escaped text or sanitized supported markup; script/event-handler and unsafe-link fixtures cannot execute or bypass public field allowlists.

Completion evidence:

- Journey tests and screenshots for desktop/mobile/zoom with source links and counts reconciled to EP19.
- Measured response/render behavior on a declared fixture, not untested production performance claims.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP22 Build immutable historical analysis snapshots

P1 • Analytical validation • planned

Owner role: Data history engineer. Dependencies: EP03, EP20.

Planning references: R06.

Build offline exact-revision snapshots for the proposed evidence ledger using current known-at and review semantics. Keep current-corpus chronology, as-known views and authenticated retrospective reconstruction separate. Select active revisions while preserving audit dependencies, withdrawals and source corrections.

Existing paths: [packages/contracts/src/history.ts](../../packages/contracts/src/history.ts), [packages/contracts/src/comparability.ts](../../packages/contracts/src/comparability.ts), [packages/db/src/public-revision.ts](../../packages/db/src/public-revision.ts), [tools/evidence_program/contracts/snapshot.schema.json](../../tools/evidence_program/contracts/snapshot.schema.json), [test/comparability.test.ts](../../test/comparability.test.ts), [test/withdrawal-semantics.test.ts](../../test/withdrawal-semantics.test.ts).

Proposed paths: `tools/evidence_program/build_analysis_snapshot.py`, `tools/evidence_program/tests/test_analysis_snapshot.py`.

Acceptance tests:

1. An old publication discovered/reviewed after cutoff is absent from an as-known view but may appear in a labelled retrospective view.
2. Coarse/unknown forecast times use conservative admissibility; a later correction cannot rewrite an earlier snapshot.
3. Closed dependency manifests validate; old and new revisions are not counted as independent events.
4. Withdrawn forecasts do not resurrect earlier numbers; changed conditions/horizons remain distinct exact questions.

Completion evidence:

- Snapshot builder, deterministic manifests/hashes and temporal/revision negative tests.
- Human-readable excluded-record report and unchanged existing history/comparability/withdrawal regressions.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

## EP23 Implement two comparable shadow analyses

P2 • Analytical validation • planned

Owner role: Statistician and analysis engineer. Dependencies: EP07, EP08, EP22.

Planning references: R01, R02.

Implement only R01 matched-benchmark and R02 resource/efficiency analysis from frozen eligible snapshots, initially synthetic and shadow-only. Output per-dimension rates, panels, provenance, exclusions and uncertainty method. No public score or cross-domain causal model is included.

Existing paths: [data/evidence-program/analysis_recipes.json](../../data/evidence-program/analysis_recipes.json), [tools/evidence_program/check_methodology_examples.py](../../tools/evidence_program/check_methodology_examples.py), [docs/evidence-program/modelling_methodology.md](../../docs/evidence-program/modelling_methodology.md).

Proposed paths: `tools/evidence_program/analyze_progress.py`, `tools/evidence_program/tests/test_progress_analysis.py`.

Acceptance tests:

1. Reproduce the synthetic 4x/100%-annualized/12-month example and 20-percentage-point/50%-relative/one-third-error-reduction example.
2. Arbitrary/negative/zero-origin scales reject invalid log growth; changing protocol/model/task distribution produces a break or a blocked comparison.
3. Reported/estimated and benchmark-imputed resource evidence retain dependence flags; copied tables do not increase independent sample counts.
4. Inputs insufficient for uncertainty/generalization return a qualified descriptive result or blocked analysis, never a fabricated interval.
5. Outputs label sampling, measurement and epistemic uncertainty separately; preregister task/model/source clustering and matched comparisons, propagate documented measurement uncertainty, and withhold intervals when the evidence cannot support them.

Completion evidence:

- Versioned analysis specification, golden outputs, exclusion audit and paired/cluster-aware validation approach.
- Fixture results and any separately admitted real-run result labelled as shadow analysis.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No universal intelligence index, fitted real causal-risk model or benchmark-to-pdoom mapping.

## EP24 Validate resolution eligibility and shadow scoring

P2 • Analytical validation • planned

Owner role: Forecast methodologist and review owner. Dependencies: EP09, EP22.

Planning references: R07.

Create an offline resolution-corpus admission report and synthetic-only scoring harness for R07. Pin forecast origins, exact questions, evaluation cutoffs, baselines and weights. Preserve frozen open/resolved/ambiguous/void statuses and leave application public scoring disabled.

Existing paths: [packages/contracts/src/forecast-resolution.ts](../../packages/contracts/src/forecast-resolution.ts), [tools/evidence_program/contracts/resolution.schema.json](../../tools/evidence_program/contracts/resolution.schema.json), [data/evidence-program/analysis_recipes.json](../../data/evidence-program/analysis_recipes.json), [tools/evidence_program/check_methodology_examples.py](../../tools/evidence_program/check_methodology_examples.py).

Proposed paths: `tools/evidence_program/assess_resolution_corpus.py`, `tools/evidence_program/tests/test_resolution_corpus.py`.

Acceptance tests:

1. Synthetic Brier example returns 0.175 against 0.25 baseline and 0.30 relative skill; zero baseline returns undefined.
2. Unresolved/future/ambiguous/void cases cannot be scored false; unmet conditions follow the original rule and stay rationale/exclusion context.
3. Repeated forecasts, events and respondents are not counted as independent; cross-method scores require the same cases/origins/weights.
4. Authenticated late-discovered pre-outcome forecasts remain retrospective, never as-known; missing follow-up is not automatically right-censoring.
5. The real-corpus gate can report inadequate evidence without enabling a score; all existing public-score calls remain disabled.
6. Preregister event/person/wave dependence, forecast-origin selection and baseline comparisons; report sampling/measurement/epistemic limits and a separately reviewed calibration-adequacy decision. Insufficient independent events/clusters blocks calibration claims even if arithmetic scores can compute. Passing Brier arithmetic or four synthetic cases cannot establish calibration or justify a public ranking.

Completion evidence:

- Preregistered eligibility/baseline rules, synthetic test report and per-case exclusion reasons.
- Independent method review defining evidence needed before any future real/public calibration claim.

Authorization gate: Future implementation assignment; deterministic fixtures only. Operational actions must be covered by applicable existing or new authorization, including any required action-time confirmation; do not reconfirm an unchanged pre-approved action. Deployment remains on hold.

Scope exclusions: No scoring of unresolved extinction forecasts or public forecaster ranking.

## EP25 Triage the new dependency advisory summary

P0 • Foundation • planned

Owner role: Dependency and security engineer. Dependencies: none.

Obtain an advisory-level read-only npm audit report for the exact current lockfile and inspect the eight findings summarized during PR 310 npm ci: one moderate, five high and two critical. Verify IDs, affected paths, current maintainer guidance, runtime/dev/optional scope, reachable use and compatible remediation. The earlier sharp/source-map-js fix in PR 307 is already merged; do not assume the new counts name the same packages.

Existing paths: [package.json](../../package.json), [package-lock.json](../../package-lock.json), [.github/workflows/e2e.yml](../../.github/workflows/e2e.yml), [.github/workflows/ci.yml](../../.github/workflows/ci.yml).

Proposed paths: `docs/evidence-program/dependency-advisory-triage.md`.

Acceptance tests:

1. Report audit timestamp/registry, exact lock hash, advisory ID/package/version/range/path and primary source for each finding.
2. Separate installed, bundled/deployed and reachable behavior; unknown exploitability/exposure remains unknown.
3. No npm audit fix or --force runs; compatible fixes, mitigations or no-action decisions are reviewed individually.
4. If an authorized dependency change follows, rerun supported Node 22 install/lint/typecheck/build and relevant full/focused runtime tests, preserving current framework compatibility.

Completion evidence:

- Evidence-linked triage matrix and residual-risk decision for all observed findings, plus any new/missing findings on repeat audit.
- Minimal proposed lock diff and tests only if implementation is separately assigned; do not claim this plan fixes advisories.

Authorization gate: Future read-only triage assignment; any package changes follow a reviewed remediation decision. Deployment stays on hold.

Scope exclusions: No assertion of exploitation, production exposure or introduction by PR 310 from counts alone.

## EP26 Prove recovery and release candidate isolation

P1 • Release readiness • planned

Owner role: Release engineer and independent data reviewer. Dependencies: EP05, EP15, EP17, EP20, EP21, EP22, EP23, EP24, EP25.

Implement a bounded manifest-chain recovery reader and assemble a private, rights-eligible release candidate/drill covering staged revisions, matching source/manifest/checkpoint identities and application-compatible exports. Reject missing chain links, cycles and mismatched versions instead of guessing a starting state. Restore into fresh disposable locations, then resume unchanged/changed ingestion. Separate code readiness, private operational validation, dataset publication and website deployment decisions.

Existing paths: [pipeline/pdoom_pipeline/collection_storage/supervisor.py](../../pipeline/pdoom_pipeline/collection_storage/supervisor.py), [scripts/backup/backup.sh](../../scripts/backup/backup.sh), [scripts/restore/drill.sh](../../scripts/restore/drill.sh), [scripts/deploy/publish-dataset.sh](../../scripts/deploy/publish-dataset.sh), [docs/DISASTER_RECOVERY.md](../../docs/DISASTER_RECOVERY.md), [test/refresh-import.test.ts](../../test/refresh-import.test.ts), [tools/evidence_program/check.py](../../tools/evidence_program/check.py).

Proposed paths: `docs/evidence-program/release-candidate-checklist.md`, `pipeline/pdoom_pipeline/evidence_staging/recovery.py`, `tests/test_evidence_recovery_bundle.py`.

Acceptance tests:

1. A multi-batch restore preserves native IDs, public references and revision progression; missing/mismatched parts fail before import.
2. Unverified remote objects cannot justify deleting local originals; full-quota committed cleanup/replay still works.
3. A candidate excludes secrets, prohibited raw bodies, unreviewed/restricted publication fields and all synthetic fixtures.
4. Exact-commit aggregate evidence checks plus touched pipeline/DB/UI suites pass; failed/never-run stages remain explicit.
5. Release report states deployment remains on hold and public import is not performed; unresolved authorization or scientific gates block the corresponding release tier.

Completion evidence:

- Disposable restore/replay trace, checksummed candidate manifest and source-to-export audit.
- Independent signoff and separate blocked/ready statuses for code, storage, data publication and deployment.

Authorization gate: Disposable drills and private candidate preparation only when assigned. Any later publication, production import, migration or deletion/retention change must be covered by applicable existing or new authorization and its required confirmation mode. Deployment remains on hold until the user explicitly lifts that hold.

## EP27 Port only useful research-ledger UI pieces

P2 • Optional presentation • deferred

Owner role: Frontend engineer. Dependencies: EP21.

If requested after the coverage journey is accepted, compare closed/unmerged PR32 head 5585848 with current main and selectively port only useful presentation pieces. Review home/trend/review layout independently; leave PR32 closed and avoid reviving obsolete contracts or bulk-merging its branch. This optional visual work does not block evidence ingestion.

Existing paths: [apps/web/app/page.tsx](../../apps/web/app/page.tsx), [apps/web/components/trend-view.tsx](../../apps/web/components/trend-view.tsx), [apps/web/app/curation/page.tsx](../../apps/web/app/curation/page.tsx), [apps/web/app/curation/[slug]/page.tsx](../../apps/web/app/curation/[slug]/page.tsx), [test/search-lifecycle.test.tsx](../../test/search-lifecycle.test.tsx), [test/application-pagination.test.ts](../../test/application-pagination.test.ts).

Proposed paths: `docs/evidence-program/ui-port-review.md`.

Acceptance tests:

1. A file-by-file keep/port/reject decision explains current relevance; no duplicate redesign or unrelated schema/ingestion changes.
2. Merged dismissal/filter, microsecond pagination, withdrawal and public/review safeguards retain their current tests.
3. Selected journeys pass current keyboard/mobile/zoom checks and targeted Chromium/WebKit tests; inherited old screenshots are not acceptance evidence.
4. No credentials, local-only curation boundary or production settings are altered.

Completion evidence:

- Selective diff, updated current-SHA screenshots/tests and explicit list of deferred elements.

Authorization gate: Deferred until the user requests this visual port; no authority to reopen/merge old PR32 or deploy.

## What completion of this step means

The backlog is complete when its narrative and machine pack agree, IDs and dependencies resolve without cycles, references point to the correct source/recipe IDs, existing/proposed paths match the stated baseline, and independent review finds no concealed authorization or production action. These checks validate the plan. They do not show that the 27 implementation tasks were performed, the sources were collected, the adapters work or the website was deployed.
