# Rights and release follow-up delta

Reviewed 8 October 2026. Six bounded documentary inquiries are complete; all ten raw-file reuse questions remain held. This is an additive qualification of original sessions 10, 12 and 17. It does not close their broader actions or admit any source.

[Machine-readable delta](../../../../data/evidence-program/research/followups/rights-release.json) · [Follow-up queue](follow-up-queue.md)

## How to read this update

The earlier [training-data](../training-data-feedback.md), [algorithmic-efficiency](../algorithmic-efficiency.md) and [inference](../inference-price-performance.md) catalogs remain historical records. The JSON here binds exact existing collection, artifact, action and prompt IDs; for records without an ID it gives the exact catalog pointer and pinned URL. It separates completed review, narrowly superseded assertions and still-held evidence. IPP002/IPP003 already exist; the submitted packet's older `82fd463` snapshot does not justify new families or replacement IDs.

A completed negative rights inquiry is useful work. Unknown applicability is neither permission nor a legal finding of prohibition. Repository-level licensing can cover data where applicable; a separately named-file grant is not a universal legal requirement. No target file or private source receipt is republished by this delta.

## IPP002: ML.ENERGY

- Completed: [pinned publisher announcements](https://github.com/ml-energy/leaderboard/blob/7885788e837b80ad172e02e6e8c47e8d0b85520e/src/config/announcements.ts#L14-L28) date the leaderboard v3.0 announcement to 1 December 2025 and a separate diagnostics-blog/arXiv announcement to 29 January 2026. These are announcement dates, not verified run dates or an independently checked paper-publication date.
- Narrowly superseded: the v3 release-date-unknown portion of `/collections/1/historical_coverage` and the not-started description of the bounded IPP-A02 / IPP-P02 documentary component. Broader historical coverage remains unknown.
- Still held: the compiled GPQA JSON grant, actual runs, immutable model/checkpoint identity, achieved quality and export-to-run linkage. The [separate HF dataset declaration](https://huggingface.co/datasets/ml-energy/benchmark-v3) does not establish compiled-JSON applicability; its gate remained closed.
- Target: `/collections/1/artifacts/0` in the inference catalog, exact pin `7885788e837b80ad172e02e6e8c47e8d0b85520e`. No existing artifact ID is present. Its Git-tree blob identity and 161,530-byte metadata are verified as metadata; target bytes were not fetched or hashed.

## TD001: Common Crawl

- Completed: the bounded rights inquiry. This review checked the pinned [README](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/README.md), [Apache license](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/LICENSE) and [current Terms](https://commoncrawl.org/terms-of-use). The supplied FAQ check is inherited, not a fresh check.
- Still held: applicability to `td001_languages` and `td001_monthly` at the exact version/intended use, plus lossless mapping. TD-A03 / TD-P01 retain those residuals; no raw-reuse hold is superseded.
- Keep repository Work, statistical files and captured webpages separate. The two CSVs were not reacquired; their target hashes remain inherited. Public fixtures remain synthetic-only.

## TD002: DPI

- Completed: four-file metadata-rights review and fresh full-byte fingerprints for `td002_template` and `td002_alpaca`. The [README legal notice](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/README.md#L219) designates code as Apache-2.0. JSON license fields concern the described datasets; they do not themselves license DPI metadata.
- Still held: metadata grant applicability, record ancestry and the independent Consent historical-panel locator/schema/access/rights questions under TD-A04 / TD-P02. No dated metadata release or license-effective date was established in the checked documents.
- Byte verification does not authorize public fixtures. Conflicting upstream and inferred license labels remain attributed assertions.

## TD004: FineWeb2

- Completed: the [pinned card changelog](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/blob/af9c13333eb981300149d5ca60a8e9d659b276b9/README.md) records v2.0.0 on 8 December 2024, v2.0.1 on 8 January 2025, v2.1.0 on 27 June 2025 and v2.1.1 on 27 October 2025. The [CSV-update commit](https://github.com/huggingface/fineweb-2/commit/d0defb24f193bb9a5a11b8b14524a03c4858e1b6) is dated 27 October 2025, 18:15:37 UTC.
- This adds chronology; it does not supersede the earlier paper/CSV denominator warning. Same-day events do not prove release-equivalent membership. The old mutable-card observation remains its own record.
- Still held: `td004_csv` applicability, exact statistical/paper denominator bridge, processing differences and overlap under TD-A06 / TD-P04. Dataset ODC-By, code Apache and underlying content are separate scopes. The card was freshly verified; CSV target bytes and their SHA-256 were not reverified.

## IPP003: Epoch and Artificial Analysis

- Completed: bounded header/provenance/rights review under IPP-A03 / IPP-P03. The [current article](https://epoch.ai/data-insights/llm-inference-price-trends) distinguishes original and mixed inputs, a 12 March 2025 article date, later download updates, and repricing events carried in Release Date. Current Epoch-work CC BY language does not establish historical or third-party field applicability.
- The [pinned evaluation-cost notebook](https://github.com/epoch-research/llm-benchmark-efficiency/blob/34b923314338360d1b1bbed6ec30d9299e54fdae/llm_evaluation_cost_trends.ipynb), inspected as inert source, substitutes measured model labels and collapses high/medium reasoning variants. Cell 15's left join is overwritten by a right join; cell 18 drops missing Model or total_tokens. These are documented selection rules, not verified row counts or checkpoint equivalence.
- The [exporter](https://github.com/epoch-research/llm-benchmark-efficiency/blob/34b923314338360d1b1bbed6ec30d9299e54fdae/save_evaluation_data.ipynb), cell 18, includes Release Date although the committed original header omits it, and reads but does not export reasoning_effort. Do not backfill either field.
- Still held: exact historical permission, mixed-field rights, row/score/version lineage and actual retained membership. Three header-byte hashes were verified; none is a whole-CSV SHA-256. Notebook response-byte hashes and derived source-cell projection hashes are labeled separately; no notebook was executed. Targets reuse `/collections/2/artifacts/0`, `/1`, `/2` and their exact pinned URLs; no artifact IDs are invented. The not-started description is superseded only for the completed bounded component.

## AE002: NanoGPT

- Completed: MIT scope, the [Track 3 reproducibility rule](https://github.com/KellerJordan/modded-nanogpt/blob/4ea6b937337a4889b8cfe3f38a93d120048d8f71/records/track_3_optimization/README.md#L184), and [the exact owner acceptance comment](https://github.com/KellerJordan/modded-nanogpt/pull/271#issuecomment-4358326452), dated/updated 1 May 2026, 07:27:24 UTC. The comment has no grant language.
- Still held: contributed log/component applicability under AE-A04 / AE-P02. Timing and claimed-versus-rerun performance remain separate questions. Acceptance does not establish reuse consent. `ae002_log` was not reacquired; its hash remains inherited.

## Remaining work and boundaries

Use the precise residuals in the JSON. Reopen exhausted rights checks only for new applicability evidence, a newly authorized route or a materially different intended use. Do not repeat the verified announcement, changelog, header or substitution checks as new research.

The 16 sourced findings are documentary annotations. No adapter, canonical/runtime mapping, empirical reproduction, source/model execution, acquisition gate, raw-file fixture, broader collection or p(doom) conversion is implemented. IPP001, IPP004, TD003, TD005 and the other AE collections are outside this bundle.
