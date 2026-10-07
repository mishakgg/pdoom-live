# Global source inventory: priorities and limits

Verified 7 October 2026. This inventory contains 40 distinct source families, GL001–GL040. It is a prioritized source universe, not an exhaustive inventory of the internet, and an acquisition plan rather than a collected dataset: every record is `candidate_not_collected`. No paid signup, credentials, live ingestion, model evaluations, or external changes were made.

Full [64-source inventory](../../data/evidence-program/source_inventory.json), [global source rows](../../data/evidence-program/global_sources.json) and [Chinese source rows](../../data/evidence-program/chinese_sources.json) are committed as native JSON. See also the [CSV index](../../data/evidence-program/source_inventory.csv).

## How to read the inventory

- “Non-China” describes source institutions in this workstream. Global sources can include Chinese models, facilities or survey observations; those records must not be discarded or duplicated when the China inventory is joined.
- `opened-primary` means an official publisher page, report, repository or dataset page was read. It does not certify successful download of all underlying files. `documentation-only` marks sources where access/schema documentation was available but actual data access was not established.
- `data_url` may be a direct file, repository, dataset page or official download catalog. `access_method` explains which. A linked catalog is never counted as collected observations. A null URL means no sufficiently verified data entry point was recorded.
- `explicit-license` is scoped to the material described in `rights_notes`; it can include noncommercial or share-alike limits. It is not blanket clearance for all upstream inputs, model outputs or article text. “Unknown” is a clearance task, not evidence that reuse is forbidden.
- Historical coverage records distinguish publication dates, survey reference periods and model-release dates. Unknown coverage remains unknown. Languages indicate inspected/documented coverage, not exhaustive availability or equivalent quality across languages.

Inventory checks: 34 opened-primary, 6 documentation-only; 24 non-null data/download entry points; 17 scoped explicit-license, 5 terms-restricted, 18 unknown. Priorities: 19 P0, 18 P1, 3 P2. P0 means high analytical value and first clearance/acquisition attention, not automatic permission to ingest.

## Recommended acquisition order

1. **Start with a small, rights-clear structured backbone.** Epoch's models, hardware and facility tables have documented downloads and CC BY 4.0 statements. Add Eurostat enterprise adoption, ONS BICS and Brazil Cetic aggregate tables with their survey definitions, uncertainty and applicable exceptions. [Epoch models](https://epoch.ai/data/ai-models), [Eurostat reuse](https://ec.europa.eu/eurostat/web/main/help/copyright-notice), [ONS data](https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/businessinsightsandimpactontheukeconomy), [Cetic tables](https://cetic.br/en/arquivos/pesquisa/2025/empresas/)
2. **Clear and version the core measurement/forecast evidence.** METR, LiveBench, SWE-bench, AI Impacts and FRI are high-value P0 candidates. Before collection, resolve artifact-specific rights and pin evaluation, question, scaffold and survey versions. Code licenses cannot stand in for all data licenses. [METR artifacts](https://github.com/METR/eval-analysis-public), [LiveBench artifacts](https://github.com/LiveBench/LiveBench), [SWE-bench registry](https://github.com/SWE-bench/experiments), [AI Impacts survey](https://wiki.aiimpacts.org/ai_timelines/predictions_of_human-level_ai_timelines/ai_timeline_surveys/2023_expert_survey_on_progress_in_ai), [FRI replication](https://github.com/forecastingresearch/xpt-lib)
3. **Build a document manifest for safety evidence.** Official OpenAI, Anthropic and DeepMind cards, UK AISI and Apollo reports need document/table provenance and overlap tracking. Treat developer reports, external evaluations and government aggregates separately. [OpenAI cards](https://deploymentsafety.openai.com/), [Anthropic cards](https://www.anthropic.com/system-cards), [DeepMind cards](https://deepmind.google/models/model-cards/), [UK AISI](https://www.aisi.gov.uk/frontier-ai-trends-report), [Apollo](https://www.apolloresearch.ai/science)

## Findings that materially change implementation

- **Forecast APIs are permission-sensitive.** Metaculus's current official documentation and September 2026 terms restrict automated access and AI/ML/commercial uses. Manifold's free bulk dumps are noncommercial and dated July 2024. Artificial Analysis's API terms restrict structured redistribution. Keep these outside a redistributable bundle until the intended use is cleared. [Metaculus terms](https://www.metaculus.com/terms-of-use/), [Manifold data](https://docs.manifold.markets/data), [Artificial Analysis data terms](https://artificialanalysiscdn.com/legal/ProDataPlatformTerms.pdf)
- **Incident metadata and news text have different rights.** AIID expressly licenses selected collections while excluding report full text and other material. OECD AIM is an automated incident-and-hazard media monitor, requiring classification checks and event-level deduplication. [AIID exclusions](https://incidentdatabase.ai/terms-of-use/), [OECD AIM](https://oecd.ai/en/incidents)
- **One adoption series has a documented break.** Census changed AI-use wording in November 2025. Preserve separate regimes rather than interpret the level jump as entirely behavioral. [Census explanation](https://www.census.gov/library/stories/2026/05/ai-use-businesses.html)
- **Some repositories are not live result feeds.** HELM entered maintenance mode in June 2026. SWE-bench entries point to separately controlled artifacts. Benchmark task collections such as ARC-AGI, IndicGenBench and Japan AISI presets are inputs to evaluations, not already-collected model scores. [HELM policy](https://crfm-helm.readthedocs.io/en/latest/maintenance_mode/), [SWE-bench repository](https://github.com/SWE-bench/experiments)

## Geographic coverage and remaining gaps

The inventory adds Japan AISI's explicitly licensed bundled evaluation data; Korea's official survey release; Japan MIC's adoption summary; IndicGenBench; Singapore's SEA-HELM; and Brazil Cetic. Japan's detailed MIC appendix remains an access/verification task; Korea's exact attachment endpoints and AI-question universe need inspection. These are explicitly weaker acquisition states than verified structured-file documentation.

[Japan AISI](https://github.com/Japan-AISI/aisev/blob/main/README-en.md) includes its bundled data in its Apache 2.0 statement. [IndicGenBench](https://github.com/google-research-datasets/indic-gen-bench#license) and [SEA-HELM](https://github.com/aisingapore/SEA-HELM/blob/main/docs/datasets_and_prompts.md) have mixed dataset licenses, including noncommercial restrictions. Their language coverage helps expose English-centric evaluation bias, but does not supply representative national risk forecasts.

Africa, the Middle East, most Latin America beyond Brazil, Central Asia and Pacific populations remain thinly covered for comparable AI adoption, locally grounded safety outcomes and expert forecasts. ITU connectivity data provides denominator/context evidence, not a substitute for missing AI observations. Future additions should prioritize primary local statistical/evaluation producers and native-language review over extra English-language summaries.

## Evidence boundaries

Keep forecasts/surveys, capability evaluations, compute/cost, safety evaluations, incidents, adoption, policy, risk taxonomies, scholarly discovery and contextual syntheses separate. Compute is not capability; a benchmark score is not real-world harm; an incident count is not a population rate; an expert forecast is not an observed probability of catastrophe. Stanford AI Index, OECD aggregates and system cards often reuse sources already listed, so preserve dependency links rather than treating repeated publication as independent evidence.

## Taxonomies, scholarly discovery and primary statements

[MIT AI Risk Repository](https://airisk.mit.edu/risks) supplies a CC BY 4.0 taxonomy/source-mapping foundation; its categories are not probability estimates. [LEAP](https://leap.forecastingresearch.org/reports) extends the forecast layer longitudinally. Its latest inspected safety-policy report was released October 5, 2026, but its raw-data export and general reuse rights remain unverified.

[OpenAlex](https://help.openalex.org/access/sync/) and [arXiv](https://info.arxiv.org/help/api/tou.html) explicitly license descriptive metadata CC0. This supports reproducible literature discovery, deduplication and source tracking. Manuscript text, figures and transcripts need separate rights checks; a metadata record or PDF link is not a collected, licensed evidence record. OpenAlex's public snapshot and paid services must also be distinguished.

Interviews, podcasts, speeches, blog posts and social posts are a further person-specific evidence layer. Add only verified original accounts, official recordings or publisher transcripts for named people, with utterance date, exact question/context, stable URL and timestamp/page. Check transcript, audio and quotation rights individually. No blanket platform scraping or assumption that publicly accessible commentary can be republished as a transcript dataset. Treat a person's statement as their forecast or position, not institutional consensus.
