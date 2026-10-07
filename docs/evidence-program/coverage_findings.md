# STEP 2: repository coverage audit

## Scope and conclusion

Audited `mishakgg/pdoom-live` at **f5274396885dbb654fc2861a78fa5be8f42fad38**. Read-only checks of `main` at 17:04 and 17:28 UTC on 2026-10-07 returned the same commit. No repository changes, collector executions, tests, production queries or new live collection were performed.

All **64 candidate source families** are mapped in [coverage_mapping.json](../../data/evidence-program/coverage_mapping.json): 40 global and 24 Chinese-focused. This is a bounded planning inventory, not all relevant sources worldwide. The repository has substantial provenance, belief-extraction and review infrastructure. Its saved content is much narrower than its catalog and adapter footprint, especially for the proposed quantitative datasets and original Chinese evidence.

The audit inspected the complete recursive file tree, both source registries, September belief-source configuration, 27 relevant catalog payloads, the recurring runtime and channel-collection path, both saved observation/candidate corpora, the September canonical export, coverage reports, and relevant collector/schema/storage code. Unrelated catalog bodies were not exhaustively searched. Negative findings are scoped accordingly; production may differ.

## How to read the mapping

Stages are separate booleans, not mutually exclusive labels:

- Catalog scaffold can exist with zero entries. Catalog metadata consists of titles, links, dates and rights labels, not article bodies or measured results.
- Direct target coverage is separated from related publisher catalogs, identity profiles and third-party discussion.
- Adapter presence includes relevant standalone catalog code and generic platform support. Its scope is stated explicitly. It does not prove a target is configured or has run.
- Runner support for a platform is distinct from wiring the particular source.
- Saved observations, extracted candidates and reviewed/public evidence require their own artifacts. Tests, fixtures and source-code confirmation constants are not operational data.

`target_status` is a navigation summary only. Read its adjacent flags and notes. `false` means not established in the named checked-in evidence, rather than a claim that the source has no data anywhere. Each row retains the priority assigned in STEP 1; this audit does not introduce a new ranking or implementation plan.

## Source-family findings

**Compute, infrastructure and benchmark datasets.** Epoch's catalog explicitly includes the AI-models, hardware and data-center landing pages, but says datasets and chart data are not stored. Saved Epoch essays concern personal timelines and are not those quantitative tables. METR has time-horizon research metadata; CRFM has HELM landing/release metadata. Neither establishes saved task-level runs or evaluation results. MLCommons has catalog code but an empty catalog documenting blocked retrieval. LiveBench, SWE-bench, ARC Prize, IndicGenBench and SEA-HELM lack verified target datasets in the inspected corpus. Generic GitHub/Hugging Face support must not be mistaken for benchmark ingestion. [Epoch catalog](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/data/catalogs/epoch_pages.json), [METR catalog](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/data/catalogs/metr_pages.json)

**Surveys and forecasts.** FRI has direct XPT and LEAP report metadata, including wave pages; the response/panel/replication data are not stored. AI Impacts has general survey discovery pages, not the requested 2023 response dataset. No Metaculus or Manifold target collection was found. These source-level gaps are separate from the repository's existing native personal-forecast evidence. [FRI catalog](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/data/catalogs/fri_pages.json)

**Safety, incidents and policy.** OpenAI's research catalog is empty; Anthropic and DeepMind research metadata do not constitute system/model-card ingestion. AISI and Apollo have relevant report/research landing metadata, not run-level results. AIID's dedicated collector is deliberately limited to metadata for one confirmed incident, incident 1; it is not a snapshot/taxonomy importer. OECD's standalone collector reads one Policy Navigator initiative, not the Incidents and Hazards Monitor. EU AI Act metadata exists, but regulation text and implementation-event records are not saved. [AIID collector](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/collectors/aiid.py), [OECD collector](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/collectors/oecd_ai.py)

**Adoption and contextual indicators.** Eurostat, Census BTOS, ONS BICS, the selected Japanese and Korean adoption statistics, Cetic.br, IEA, TOP500/Green500, ITU and Artificial Analysis have no verified target observations/configuration in the inspected scope. Related national-policy or energy catalog pages are not those statistical series. AI Index report metadata is present, but its data tables are not ingested. MIT AI Risk Repository taxonomy/source mappings were not found.

**Scholarly discovery.** The recurring runtime admits RSS, arXiv, GitHub and OpenAlex. October has 246 OpenAlex author-work source configurations and no `arxiv_api` registry rows. OpenAlex identity/enrichment artifacts and historical smoke results are real existing evidence of metadata work; the inspected 333 saved belief-observation rows do not contain an OpenAlex work corpus or bulk snapshot. arXiv has a saved smoke-success report, not a persisted preprint corpus. GitHub reads repository descriptions/metadata; the recurring route lists a user's repositories. It does not copy READMEs or benchmark files. Hugging Face reads single-card metadata, not dataset contents. [Runtime mapping](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/refresh/runtime.py), [smoke report](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/data/reports/live-collector-smoke.json)

## Chinese-focused coverage

CN001's DeepSeek news index has direct catalog metadata. The complete DeepSeek catalog has **36 rows: 18 Chinese-route/title entries and 18 English counterparts**, collapsing to 18 bilingual URL groups. These are neither 36 independent claims nor collected Chinese article bodies. BAAI, Shanghai AI Laboratory and Tsinghua AIR catalogs are empty, with retrieval limitations recorded; parser code still exists. [DeepSeek catalog](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/data/catalogs/deepseek_pages.json)

For the other 23 Chinese inventory targets, direct saved observations, candidate statements and canonical evidence were not established. Generic GitHub support covers metadata only; generic arXiv support does not make the alignment-survey paper collected. MiniMax's management biography and a Tsinghua researcher profile are related, disabled registry references, not the requested documents. Saved third-party discussions of Qwen, Kimi and ByteDance remain distinct from the official originals.

The stored October report identifies **15 of 328 people** by affiliation with China-headquartered organizations; **0 of those 15** have usable belief evidence in that report. This is not nationality or a zero-risk estimate. Only **2 of 322 registry rows** explicitly carry a Chinese-language value, and both are disabled, reference-only profiles. Missing language fields prevent treating this as an exhaustive language census. English publications from Chinese institutions and Chinese original prose are different dimensions.

**Language-processing coverage is also limited.** The inspected deterministic extractor uses English probability, horizon, stance and topic cues. Its sentence splitter recognizes ASCII `.`, `!`, `?` and newlines, not Chinese `。！？`. The belief-corpus exporter assigns `language: "en"` to emitted source items, while the retained-adapter observation exporter writes `language: None` rather than carrying a source language through. These paths therefore do not establish reliable Chinese extraction or language-preserving export, even if Chinese sources are added. No explicit original-versus-translation linking or cross-language deduplication was found in these inspected extraction/export paths; this is a scoped finding, not a repository-wide absence claim. [Extraction cues](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/extract/statements.py#L22-L140), [sentence boundaries](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/extract/statements.py#L1511-L1518), [belief export](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/export/corpus.py#L53-L74), [adapter export](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/pipeline/pdoom_pipeline/export/versions.py#L49-L70)

## Scoped baseline

[baseline_metrics.json](../../data/evidence-program/baseline_metrics.json) recomputes or cross-checks 28 metrics with explicit units, denominators and source links. The stored report was not regenerated against today's code.

- October cohort: 328 people; 63 with observed/attributable evidence; 22 with usable evidence; 15 with candidates
- Static eligibility: 12 people with public-review-eligible statements and 2 with research-export-eligible statements; neither count verifies live publication or human approval
- Saved observation files: 234 September rows plus 99 October rows, totaling 333 rows, not unique documents or independent people
- Saved candidate files: 40 plus 1, totaling 41; review states are 27 `needs_review`, 12 `unreviewed`, 2 `machine_validated`, and no `human_verified` candidates
- Observation-language people memberships total 330 because categories overlap; they are not a partition of 328 people
- The 216 academic-only source-shape count and 181 academic-only primary-gap count use different rules

The September canonical file has 40 statements and 37 forecasts, but its `live` label and filename do not verify today's deployed state. [Coverage report](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/data/reports/coverage-v2026-10.json)

## Native data-entity gaps, separate from source coverage

The canonical contracts and six migrations are person/source/statement/forecast-centric. Model cards fit source items, and generic metadata can carry extra fields, but native entities for evaluated models/checkpoints, benchmark runs, compute/cost/infrastructure measurements, adoption/economic observations and incident records were not found. Extractor `model_name`/`model_provider` fields describe the extraction system, not evaluated AI models. Metadata collectors do not establish those entities. [Canonical schema](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/schemas.ts), [data-model documentation](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/docs/DATA_MODEL.md)

Belief evidence is native: attributed statements, evidence locators, question/definition/horizon/condition/unit, numeric-versus-qualitative separation, revision relationships and review snapshots. History/comparability helpers already distinguish event time from knowledge/review cutoffs and constrain comparisons by question semantics. They should not be reported as missing. [History helpers](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/history.ts), [comparability](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/docs/FORECAST_COMPARABILITY.md)

Storage protections also exist: bounded scratch, rights/retention controls, private handoff checks, quota/owner/checksum gates, and manifest-before-checkpoint/cleanup. Their presence is not proof of configured credentials, admitted storage, a successful upload or this new collection starting. This audit establishes coverage and gaps only; it does not design the later schema, methodology or implementation tasks. [Collection storage](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/docs/COLLECTION_STORAGE.md)
