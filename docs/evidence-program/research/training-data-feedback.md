# Training-data availability and feedback loops

Reviewed 8 October 2026 against `mishakgg/pdoom-live@d196d9c89b8ba12d584a2f19e8ded1623ab0142a`. This is a prepared research review and bounded offline reader, awaiting independent review and integration at this snapshot. All five collections remain unadmitted. The [catalog](../../../data/evidence-program/research/training-data-feedback.json) contains source-specific metadata, qualifications and follow-up work.

## Decision

Prioritize Common Crawl aggregate statistics, Data Provenance Initiative, and Collapse or Thrive. Common Crawl supplies repeated capture/language measurements; DPI describes ancestry, generators and rights assertions; controlled feedback experiments vary retention conditions. FineWeb2 would rank ahead of the experiment collection for ease of structured ingestion. Epoch contributes a distinct modeled-stock product from a known producer.

These measurements do not establish a global stock of fresh, licensed, deduplicated and useful training data. Public visibility does not grant training or redistribution permission. Words, page captures, URLs, estimated digests, dialogs, experiment generations and modeled tokens stay distinct. No proxy becomes p(doom).

## Baseline and duplicate review

The frozen 64 inventory and all nine previous research catalogs are byte-preserved. The comparison covers 48 previous collections, 362 artifact references and 45 candidate-by-catalog cells. Exact current-base catalog Git/SHA-256 pins and reviewed IDs are in the catalog.

- GL001 and prior OM003 share the Epoch producer, but AI Models/accessibility enrichment and data-stock analysis are different products. An exact model-input join is unverified. GL002/GL003 are other Epoch products, not this evidence.
- OM004 OLMo has Common Crawl ancestry. This warns against additive raw-supply totals; it does not establish that its material overlaps the three selected 2026 crawl rows.
- OM001 contains third-party Hub metadata snapshots; Hugging Face hosting is not producer identity. The same applies to Chinese SafetyQA, DebateGPT and robotics artifacts hosted there.
- Common Crawl → FineWeb2 is raw-source ancestry with later processing. DPI audits a described corpus; the audit adds no content supply. Consent weights domains underlying C4, RefinedWeb and Dolma. Epoch derives estimates from input evidence.
- Gaussian CSV/Parquet and paper figures refer to one named sweep or its presentation. The export code supports that relationship; payload equality is unverified.
- OpenAlex/arXiv discovery metadata is not an independent underlying study observation. No exact artifact/study duplication was established against the nine prior catalogs; this is not proof of zero underlying content intersection.

## Collections and source qualifications

### TD001 · Common Crawl aggregate crawl statistics

**Classification:** new_source_family_candidate. **Measurement:** observational_crawl_aggregate.

Archive identifiers extend to 2008–2009; meaningful primary-language classification begins CC-MAIN-2018-34. Earlier all-unknown rows are unavailable classification. Approximately monthly crawl releases; statistics have independently versioned repository revisions.

**Access:** Public aggregate CSVs at pinned GitHub revision; two bounded files acquired privately for exact-byte acceptance. No WARC/WET/corpus/page retrieval or live collector.

Verified source and artifact references:

- [td001_languages](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/languages.csv): language counts and shares. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b. Exact-byte SHA-256 `4f3b987a60d72a356c480d788a930388ebe05225307aec7fc280513f6f9b0cff`.
- [td001_monthly](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/crawlsize/monthly.csv): monthly page/URL/digest cardinalities. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b. Exact-byte SHA-256 `b49fb0e4acd9cd3a4676cc4bad17eca9645e38dcecfea1dfc3f2436a1c7b98a7`.
- [td001_new_urls](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/crawlsize/monthly_new.csv): new-to-archive URL estimates. reference_only_not_reader_input. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b.
- [td001_methods](https://commoncrawl.github.io/cc-crawl-statistics/plots/crawlsize): counting methodology. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td001_language_methods](https://commoncrawl.github.io/cc-crawl-statistics/plots/languages.html): language detection and historical missingness. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td001_license](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/LICENSE): repository license. public_primary_read. Rights: Repository software license; separate aggregate-CSV coverage was not verified. Does not license captured webpages. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b.
- [td001_terms](https://commoncrawl.org/terms-of-use): source-owner rights and service terms. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td001_july](https://commoncrawl.org/blog/july-2026-crawl-archive-now-available): July capture/release announcement. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td001_august](https://commoncrawl.org/blog/august-2026-crawl-archive-now-available): August capture/release announcement. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td001_september](https://commoncrawl.org/blog/september-2026-crawl-archive-now-available): September capture/release announcement. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td001_count_code](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plot/crawl_size.py): reported counts and estimated digest implementation. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b.
- [td001_residual_code](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plot/table.py): unknown language residual construction. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b.
- [td001_multicount_code](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/crawlstats.py): scalar MultiCount fallback semantics. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 1053c982a91ba0bb4323c5f00ec3230d9cd54e4b.

Observed example or schema (a curated projection, not a vendored source body):

```json
{
  "crawl": "CC-MAIN-2026-39",
  "digest estim.": "2117305135",
  "page": "2171285702",
  "url": "2158769646"
}
```
Native fields preserved; digest is estimated, page counts captures, URL counts distinct URLs within the crawl.

```json
{
  "crawl": "CC-MAIN-2026-39",
  "primary_language": "eng",
  "pages": "908943016",
  "urls": "902497159",
  "%pages/crawl": "41.8620"
}
```
This is a page-share measurement, not universal tokens or human-authored/usable supply.

```json
{
  "crawl": "CC-MAIN-2026-39",
  "primary_language": "<unknown>",
  "pages": "66390805",
  "urls": "66390805",
  "%pages/crawl": "3.0577"
}
```
Unknown remains an explicit category in the page denominator. Its native urls field is a residual-page-derived placeholder, not independently measured unique URLs.

- All three bounded crawls have 162 language rows; summed page counts exactly equal their monthly page count, including unknown. Private exact-byte acceptance validates these files; public CI uses only synthetic CSVs. 162 is category-row count including unknown, not a count of detected languages. [td001_languages](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/languages.csv) [td001_monthly](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/crawlsize/monthly.csv)
- All bounded language shares match count-based shares within 0.00005 percentage points; rounded shares sum to 99.9995, 99.9998 and 100.0001 respectively. Do not require the sum of rounded shares to equal exactly 100. [td001_languages](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/languages.csv) [td001_monthly](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/crawlsize/monthly.csv)
- September pages were captured 4–17 September 2026 and released 19 September. Capture and release dates do not fill unknown original content-publication date. [td001_september](https://commoncrawl.org/blog/september-2026-crawl-archive-now-available)
- Unknown language urls repeats a page residual through MultiCount scalar fallback; it is not an independent URL-cardinality observation. Exact language-page sums reconcile; language URL sums are not a partition of monthly URLs. [td001_languages](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plots/languages.csv) [td001_residual_code](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/plot/table.py) [td001_multicount_code](https://github.com/commoncrawl/cc-crawl-statistics/blob/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b/crawlstats.py)

Interpretation and unresolved boundaries:

- Page captures, URL cardinality and estimated digest cardinality are different metrics. URL/digest deduplication does not establish near-deduplicated usable training text.
- New URL means new to the archive, not new publication, human authorship or information. Crawl choices and repeat visits limit population inference.
- CLD2 primary-language shares use page captures including <unknown>; HTML-only detector input is not a population or token denominator.
- Digest estimates and cumulative/new-URL HyperLogLog estimates must retain estimate semantics. Do not impose exact equality or estimate ordering as a ground-truth invariant.
- The 2025-13 increase in fetch truncation from 1 MiB to 5 MiB limits byte/completeness comparability.
- Aggregate CSV rights remain unverified, separate from repository Apache-2.0 and source-owner page terms.
- Unknown.urls is populated from the page-count residual; preserve raw value but do not label it independently observed unique URLs. Language URL sums exceed monthly URLs by 235851, 215687 and 180735; no URL-sum invariant or missing-URL correction is justified.

### TD002 · Data Provenance Initiative and Consent in Crisis

**Classification:** new_source_family_candidate. **Measurement:** dataset_metadata_audit_and_restriction_study.

Original October 2023 audit of more than 1,800 selected text datasets; inspected metadata revision 26 March 2025. Consent historical captures January 2016–April 2024. Contributor-driven metadata revisions; regular refresh not verified.

**Access:** Public schema and per-collection keyed JSON; papers and schema readable. Exact downloadable Consent historical domain-month panel is unverified. No described corpus download.

Verified source and artifact references:

- [td002_template](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/data_summaries/_template.json): illustrative metadata template, not JSON Schema. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: ce6662deccf011574427b6f112df479d261960b8.
- [td002_alpaca](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/data_summaries/Alpaca.json): observed dataset metadata. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: ce6662deccf011574427b6f112df479d261960b8.
- [td002_readme](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/README.md): field definitions and code license. public_primary_read. Rights: README explicitly licenses code; metadata JSON reuse license remains unknown. Version: ce6662deccf011574427b6f112df479d261960b8.
- [td002_paper](https://arxiv.org/abs/2310.16787v3): original audit paper. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 2310.16787v3.
- [td002_consent](https://arxiv.org/html/2407.14933v2): Consent in Crisis methods and Table 2 schema. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 2407.14933v2.
- [td002_consent_pdf](https://arxiv.org/pdf/2407.14933v2): page 4 and Appendix A.2.1 denominator and absence-of-consent caveats. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 2407.14933v2.
- [td002_web_docs](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/src/web_analysis/README.md): output-path documentation without verified panel download. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: ce6662deccf011574427b6f112df479d261960b8.

Observed example or schema (a curated projection, not a vendored source body):

```json
{
  "alpaca": {
    "Unique Dataset Identifier": "alpaca",
    "Languages": [
      "English"
    ],
    "Text Metrics": {
      "Num Dialogs": 52002
    },
    "Model Generated": [
      "OpenAI GPT-3"
    ],
    "Human Annotation": "No",
    "Inferred Metadata": {
      "HF Date": "2023-03-13",
      "HF Yaml License": "CC BY-NC 4.0",
      "GitHub License": "Apache License 2.0"
    }
  }
}
```
Projection of a metadata record; separate assertions do not resolve licensing or establish the provenance of every example. Collection JSON is keyed by dataset identifier and may contain multiple records.

- The original study denominator exceeds 1,800 datasets; it is not a verified current repository record count. Do not equate study scope and current metadata coverage. [td002_paper](https://arxiv.org/abs/2310.16787v3)
- Consent Table 2 and methods describe historical domain restriction variables but an exact raw panel download remains unverified. Supporting paper-level evidence only; no implemented panel ingestion. [td002_consent](https://arxiv.org/html/2407.14933v2)
- Pinned tree has 110 direct JSON files under data_summaries including its template; collection files can contain multiple dataset records. 109 non-template files are not a current dataset count. [td002_template](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/data_summaries/_template.json) [td002_alpaca](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/data_summaries/Alpaca.json) [td002_readme](https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/blob/ce6662deccf011574427b6f112df479d261960b8/README.md)
- Consent excludes unretrievable/no-longer-functioning domains and uses domains existing at each time; no restriction is not consent. Paper v2 PDF page 4 and Appendix A.2.1; administrators need not be rightsholders. [td002_consent_pdf](https://arxiv.org/pdf/2407.14933v2)

Interpretation and unresolved boundaries:

- Audited dataset ancestry, declared generators, annotations and licenses are assertions with incomplete coverage, not a census of private training.
- Code license, dataset license assertions, inferred platform labels and metadata-file reuse license are distinct scopes. Empty ancestry/generator is missing information.
- Dialogs/turns/characters cannot be combined with pretraining tokens. Documented synthetic provenance does not quantify the global synthetic fraction.
- Consent restriction labels are distinct from licenses, negotiated access, actual training use and affirmative consent; absence of restrictions is not consent.
- Historical availability gaps, exclusions and corpus weighting alter Consent denominators.

### TD003 · Collapse or Thrive synthetic-feedback experiment histories

**Classification:** new_source_family_candidate. **Measurement:** controlled_synthetic_feedback_experiments.

Gaussian exports saved September 2024; evolving preprint and ICML 2025 publication. Main longitudinal axis is fitting generation, not calendar time. Static saved experiments with repository/manuscript revisions.

**Access:** Public export entries and producer/consumer code inspected read-only. Parquet file 3,985,711 bytes and alternative CSV 71,875,443 bytes exist; neither result export acquired or executed.

Verified source and artifact references:

- [td003_publication](https://proceedings.mlr.press/v267/kazdan25a.html): ICML 2025 publication. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: ICML-2025.
- [td003_manuscript](https://arxiv.org/html/2410.16713v3): manuscript and covariance estimator. public_primary_read. Rights: This manuscript only; does not establish code/export reuse rights. Version: 2410.16713v3.
- [td003_parquet](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/notebooks/00_gaussian_fitting/data/sweeps=k3mipjqi_runs_histories.parquet): saved Gaussian histories. repository_entry_and_size_verified_not_downloaded. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 3874173141dcf7f344b805cfa4ef126fc6a587d8.
- [td003_csv](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/notebooks/00_gaussian_fitting/data/sweeps=k3mipjqi_runs_histories.csv): alternate saved Gaussian histories. repository_entry_and_size_verified_not_downloaded. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 3874173141dcf7f344b805cfa4ef126fc6a587d8.
- [td003_producer](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/src/fit_gaussians/fit_gaussians.py): logging and covariance implementation. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 3874173141dcf7f344b805cfa4ef126fc6a587d8.
- [td003_sweep](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/sweeps/fit_gaussians/default.yaml): configured sweep. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 3874173141dcf7f344b805cfa4ef126fc6a587d8.
- [td003_analysis](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/notebooks/00_gaussian_fitting/00_gaussian_fitting.py): analysis identifies sweep; current helper consumption of legacy cache filename unverified. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 3874173141dcf7f344b805cfa4ef126fc6a587d8.
- [td003_helpsteer](https://huggingface.co/datasets/nvidia/HelpSteer2): reference-corpus composition. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td003_export_helper](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/169abbfae4080b0dce804aad56189eb2868d0664/src/analyze.py): export-era filename and sampling/skip helper. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 169abbfae4080b0dce804aad56189eb2868d0664.
- [td003_current_helper](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/src/analyze.py): current hash-based export filenames. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 3874173141dcf7f344b805cfa4ef126fc6a587d8.
- [td003_export_producer](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/169abbfae4080b0dce804aad56189eb2868d0664/src/fit_gaussians/fit_gaussians.py): September 2024 producer schema and estimator. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 169abbfae4080b0dce804aad56189eb2868d0664.

Observed example or schema (a curated projection, not a vendored source body):

```json
[
  "Model-Fitting Iteration",
  "Setting",
  "Data Dimension",
  "Num. Samples per Iteration",
  "Squared Error of Fit Mean (Numerical)"
]
```
Observed producer field names, not a verified numerical row in the saved export; covariance retention is a separate measurement.

- The wider publication discusses replacement, accumulation and fixed-size retention; the saved Gaussian sweep is configured for Replace and Accumulate. Broader KDE and language-model findings remain paper-level. Neither configured conditions nor schema establish actual run completeness or universal collapse. [td003_publication](https://proceedings.mlr.press/v267/kazdan25a.html) [td003_sweep](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/sweeps/fit_gaussians/default.yaml)
- HelpSteer2 responses are model-generated and human-rated; real is the study reference-data role. Do not emit human_authored=true. [td003_helpsteer](https://huggingface.co/datasets/nvidia/HelpSteer2) [td003_manuscript](https://arxiv.org/html/2410.16713v3)
- Pinned implementation uses bias=True; the v3 manuscript describes an unbiased covariance estimator. Preserve the discrepancy without claiming it invalidates the conclusions. [td003_producer](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/src/fit_gaussians/fit_gaussians.py) [td003_manuscript](https://arxiv.org/html/2410.16713v3) [td003_export_producer](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/169abbfae4080b0dce804aad56189eb2868d0664/src/fit_gaussians/fit_gaussians.py)
- Saved sweep filenames link through export-era helper; current helper uses hashed names. History sampling and skipped histories prevent treating the configured sweep grid as observed coverage. No full export acquisition, row equality or reproduction claim. [td003_export_helper](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/169abbfae4080b0dce804aad56189eb2868d0664/src/analyze.py) [td003_current_helper](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/src/analyze.py) [td003_analysis](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/notebooks/00_gaussian_fitting/00_gaussian_fitting.py) [td003_sweep](https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive/blob/3874173141dcf7f344b805cfa4ef126fc6a587d8/sweeps/fit_gaussians/default.yaml)

Interpretation and unresolved boundaries:

- Gaussian, kernel-density and language-model experiments are different regimes with limited frontier-training external validity.
- Replacement/accumulation changes retained-data quantities; equal sample budgets need not imply equal measured computation.
- Producer schema and configured grid do not prove complete export/run coverage; no numerical export row or public W&B/result completeness asserted.
- Experimental real-data role is not human authorship: HelpSteer2 responses are generated by a mixture of ten in-house LLMs and rated by humans.
- Code uses np.cov(..., bias=True), whereas manuscript v3 describes n−1/unbiased covariance; retain both rather than resolving without evidence.
- Code/results rights are unknown; manuscript CC BY-NC-SA does not license repository artifacts.
- Export-era helper samples run histories with samples=10000 and skips empty/failed histories; configured 5000 runs / 500000 iteration rows are not observed export counts. Current helper hashes sweep filenames; old sweep-name filenames need export-era version linkage.
- Export-era Gaussian settings are Replace and Accumulate; latest producer adds Accumulate-Subsample but the saved 2024 sweep is not shown to contain it. Current lowercase model_fitting_iteration is sweep enumeration, not native Model-Fitting Iteration. Multivariate Fit Covariance is intentionally NaN, not zero. The .feather companion is a zero-byte placeholder. Final proceedings equations were not independently verified; estimator comparison is arXiv v3-specific.

### TD004 · FineWeb2 release composition statistics

**Classification:** new_curation_family_candidate. **Measurement:** curated_commoncrawl_derived_corpus_statistics.

96 Common Crawl snapshots from 2013 through April 2024; later versioned output releases. Irregular releases: v2.0.0 2024-12-08; v2.0.1 2025-01-08; v2.1.0 2025-06-27; v2.1.1 2025-10-27.

**Access:** Bounded public language-distribution CSV and card/paper/code metadata inspected; no text/parquet corpus download, streaming or pipeline execution.

Verified source and artifact references:

- [td004_csv](https://github.com/huggingface/fineweb-2/blob/d0defb24f193bb9a5a11b8b14524a03c4858e1b6/fineweb2-language-distribution.csv): language/script/split/size composition. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: d0defb24f193bb9a5a11b8b14524a03c4858e1b6. Exact-byte SHA-256 `0c6e6fbcef62cb034aff493187dee8d327c6bb2c08bb14a81a9c7221b091e0a5`.
- [td004_card](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/blob/main/README.md): dataset card and release dates. public_primary_read. Rights: Dataset/database declaration additionally subject to Common Crawl terms; CSV-specific and underlying webpage rights separately unverified. Version: read main on 2026-10-08; page identifies README commit af9c13333eb981300149d5ca60a8e9d659b276b9.
- [td004_paper](https://arxiv.org/html/2506.20920v1): paper-release composition and methods. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 2506.20920v1.
- [td004_code_license](https://github.com/huggingface/fineweb-2/blob/d0defb24f193bb9a5a11b8b14524a03c4858e1b6/LICENSE): pipeline repository license. public_primary_read. Rights: Pipeline code only; not a blanket license for source content or separately unverified statistics CSV. Version: d0defb24f193bb9a5a11b8b14524a03c4858e1b6. Exact-byte SHA-256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
- [td004_readme](https://github.com/huggingface/fineweb-2/blob/d0defb24f193bb9a5a11b8b14524a03c4858e1b6/README.md): explicit code versus dataset license scope. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: d0defb24f193bb9a5a11b8b14524a03c4858e1b6.

Observed example or schema (a curated projection, not a vendored source body):

```json
[
  {
    "subset": "aai_Latn",
    "split": "train",
    "words": "473139",
    "documents": "615",
    "utf8_bytes": "2687643",
    "parquet_bytes": "834074"
  },
  {
    "subset": "aai_Latn",
    "split": "test",
    "words": "4348",
    "documents": "8",
    "utf8_bytes": "25449",
    "parquet_bytes": "21010"
  },
  {
    "subset": "aai_Latn_removed",
    "split": "train",
    "words": "-",
    "documents": "9145",
    "utf8_bytes": "3964814",
    "parquet_bytes": "1328536"
  }
]
```
Projection of native size columns; dash means unavailable words, not zero. Not complete source rows or corpus examples.

- The paper reports 1,320 of 1,868 language-script subsets with over half their documents from Bible/Wikipedia domains. Paper-version, document/domain-based statistic; later October 2025 CSV counts 1,870 filtered-train subsets. [td004_paper](https://arxiv.org/html/2506.20920v1)
- FineWeb2 card date identifies crawling; release time and original content publication are separate. No webpage content or example text retained. [td004_card](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/blob/main/README.md)

Interpretation and unresolved boundaries:

- Words and documents are native quantities, not a universal token count. English is handled by the original FineWeb collection.
- Deduplication is global within language; cross-language/cross-corpus uniqueness is not guaranteed.
- Removed/unclassified material has different filtering/deduplication status; missing word count dash is null, not zero.
- Rehydration repeats retained material; it does not create new unique content.
- Language/script detection, filtering and topical/domain concentrations qualify coverage. Domain concentration is a document-domain measure, not token fraction or semantic annotation of every passage.
- Paper 1,320/1,868 concentration denominator must not be joined to later CSV 1,870 filtered-train subsets as the same release.
- ODC-By dataset declaration and Apache code declaration do not clear underlying page or statistics-specific reuse rights.
- Later CSV has 75 filtered-train rows missing Bible or Wikipedia ratios. Its 1320 test rows are not the paper concentration numerator despite numerical equality; missing domain ratios stay unknown.

### TD005 · Epoch data-stock analysis and replication inputs

**Classification:** known_producer_new_product; related inventory GL001. **Measurement:** modeled_stock_and_effective_repetition.

October 2022 and June 2024 analytical versions; inspected code revision 10 July 2024, prior implementation retained in v1. Historical pivot-word input columns 2013–2022. Occasional analytical revisions, not an empirical annual stock service.

**Access:** Public article, versioned paper, bounded input CSV and source read; no notebook, model, script or training execution.

Verified source and artifact references:

- [td005_article](https://epoch.ai/publications/will-we-run-out-of-data-limits-of-llm-scaling-based-on-human-generated-data): article and analytical-version interpretation. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission.
- [td005_paper](https://arxiv.org/html/2211.04325v2): versioned stock estimates. public_primary_read. Rights: This paper only; does not establish licenses of replication code or each third-party input CSV. Version: 2211.04325v2.
- [td005_repo](https://github.com/epoch-research/data-stock/tree/83da8edaa853f036f1bbd521df9e789335d64b3b): replication revision. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 83da8edaa853f036f1bbd521df9e789335d64b3b.
- [td005_pivot](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/data/google_pivot_words.csv): historical pivot-word input. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 83da8edaa853f036f1bbd521df9e789335d64b3b. Exact-byte SHA-256 `a08e7d4d28f5d73ca89d4d56b99a1e4fcca276d34ca6faabd994ce1e4fd38d1b`.
- [td005_adjust](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/src/stock_adjust.py): raw/quality/repetition adjustment implementation. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 83da8edaa853f036f1bbd521df9e789335d64b3b. Exact-byte SHA-256 `3b067ed0d4f39107b0d8def0189cf90181b05e178eabf358fc1d7bb891c08e88`.
- [td005_indexed](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/src/indexed_web.py): indexed-page distribution input. public_primary_read. Rights: Artifact-specific reuse rights not established; public access is not permission. Version: 83da8edaa853f036f1bbd521df9e789335d64b3b. Exact-byte SHA-256 `79c710ac27f4394065dcbf4cd67516607275d48a9d6fe5fa25438bb8a88c458a`.

Observed example or schema (a curated projection, not a vendored source body):

```json
{
  "category": "Indexed web",
  "median": "510",
  "lower": "130",
  "upper": "2100",
  "interval_level": "95%",
  "unit": "trillion tokens",
  "evidence_type": "modeled_stock_estimate",
  "year": 2024,
  "adjustment_state": "raw",
  "tokenizer_basis": "cl100k_base",
  "upstream_interval_label": "95% CI"
}
```
Table 1 modeled stock; not licensed usable stock or repetition-adjusted effective stock. Interval follows modeled log-normal uncertainty and Monte Carlo propagation, not an empirical sample CI.

- The replication separates raw stock, quality adjustment and gains from repeated training. Do not count repeated exposure as distinct new documents. [td005_adjust](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/src/stock_adjust.py)
- Different analytical versions changed assumptions; source observations and future projections have different date roles. Not an annual measured stock time series or universal ceiling. [td005_article](https://epoch.ai/publications/will-we-run-out-of-data-limits-of-llm-scaling-based-on-human-generated-data) [td005_paper](https://arxiv.org/html/2211.04325v2) [td005_pivot](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/data/google_pivot_words.csv)
- Pinned indexed_web.py uses 75–1000 billion indexed pages; manuscript v2 describes 100–1200 billion with median 250 billion. Input CSV contains 105 pivot rows versus the manuscript account of 100 pivot words. Source/code version discrepancies, not independent numerical reproduction; models were not run. [td005_indexed](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/src/indexed_web.py) [td005_pivot](https://github.com/epoch-research/data-stock/blob/83da8edaa853f036f1bbd521df9e789335d64b3b/data/google_pivot_words.csv) [td005_paper](https://arxiv.org/html/2211.04325v2)

Interpretation and unresolved boundaries:

- Raw, quality-adjusted and repetition-adjusted effective stock are distinct modeled quantities with assumptions and uncertainty.
- Repeated exposure increases effective training opportunity without increasing distinct source documents.
- Estimated public stock does not establish licensed, deduplicated, task-useful data successfully used in a training run.
- 2022/2024 changes in model assumptions preclude treating them as one consistently measured annual stock series.
- Conditional utilization dates do not establish a hard universal ceiling; source inputs require their own rights treatment.
- GL001 describes AI Models. Same producer does not authorize silently adding this product or declaring exact input record matches.
- Paper and pinned code differ in indexed-page assumptions and pivot-word row counts; no verified bridge or reproduced estimate is asserted.

## Common Crawl reader: implemented, narrow and offline

[read_common_crawl_statistics.py](../../../tools/evidence_program/read_common_crawl_statistics.py) accepts two supplied regular local CSV files at commit `1053c982a91ba0bb4323c5f00ec3230d9cd54e4b`. Default mode verifies their exact SHA-256 identities before emitting only CC-MAIN-2026-30, CC-MAIN-2026-34 and CC-MAIN-2026-39. It does not acquire files, follow URLs, run source scripts or admit observations. Raw bytes stay outside the repository because aggregate CSV-specific redistribution rights remain unknown.

| Artifact | Native header | Verified bytes | Rows |
| --- | --- | ---: | ---: |
| plots/languages.csv | crawl,primary_language,pages,urls,%pages/crawl | 509409 | 12534 |
| plots/crawlsize/monthly.csv | crawl,digest estim.,page,url | 6302 | 128 |

Headers and field order are exact. All input rows are validated within strict bounds; historical rows outside the three permitted output IDs are excluded. Historical all-unknown classifications are not manufactured language-distribution observations. Native strings remain traceable alongside normalized semantics.

- `page`: reported page captures; `url`: reported unique URLs within the crawl; `digest estim.`: estimated distinct content digests, retaining `is_estimate=true`. Digest estimates are not forced to obey exact-count inequalities.
- Language `pages` and `%pages/crawl` use the full crawl page denominator including `<unknown>`. Each of the three actual files has 162 category rows including unknown, not 162 detected languages.
- Unknown-language native `urls` repeats a page residual through upstream scalar fallback. It remains raw source evidence, while normalized unknown unique-URL measurement is unavailable. Language URL totals do not partition monthly unique URLs. Observed excesses are 235851, 215687 and 180735; the reader does not repair or force them to equal.
- Page sums reconcile exactly. Each language percentage must reproduce within 0.00005 percentage points. Rounded percentage sums are 99.9995, 99.9998 and 100.0001; exact 100 is not a required invariant.
- Source revision and input hash qualify observation IDs; underlying crawl IDs are separate. Repeated import yields deterministic identities. Reordering/byte mutation fails exact-pin mode; synthetic mode has a separate namespace and makes no actual-source hash claim.
- Capture dates and release dates come from release announcements. Content-publication and statistics-publication dates remain unknown; repository revision time is not either publication date. Day-precision dates have unknown timezone.
- CSV rights and underlying-page rights remain unknown. Apache-2.0 describes source software; it does not become a license for captured content. No usable/licensed tokens, global synthetic share, human-authored share or catastrophe probability is emitted.

| Crawl | Captured | Released | Page captures | Distinct URLs | Estimated digests |
| --- | --- | --- | ---: | ---: | ---: |
| CC-MAIN-2026-30 | 2026-07-07–2026-07-25 | 2026-07-28 | 2149001456 | 2135935679 | 2108543089 |
| CC-MAIN-2026-34 | 2026-08-07–2026-08-20 | 2026-08-24 | 2139617681 | 2127461002 | 2074297350 |
| CC-MAIN-2026-39 | 2026-09-04–2026-09-17 | 2026-09-19 | 2171285702 | 2158769646 | 2117305135 |

### Bounds, validation and synthetic-only CI

The reader is standard-library-only. Inputs are limited to 1 MiB/64 KiB and 20000/256 rows; fields to 128 bytes, physical lines to 1024 bytes, language categories per crawl to 512, and count magnitude to 10^12. Exact headers, finite bounded decimal integers, four-place percentages, duplicate crawl/language keys, missing selected crawls, malformed/control-bearing strings and incompatible counts fail closed. POSIX descriptor-relative file opening rejects symlink components, traversal, network-style paths and nonregular files; an unsupported safe-open platform fails. A mounted filesystem can still be remote; filesystem locality is not established.

[Synthetic fixtures and notice](../../../tools/evidence_program/tests/fixtures/training-data/NOTICE.md) are self-authored. Public regression tests test this parser contract without source bytes or external calls. Synthetic output is explicitly marked, uses distinct observation identities and never claims real capture/release dates or verified source bytes. The exact real pair was separately accepted privately for three summaries and 486 language observations. Those extracted results are not public fixtures.

```bash
python -m unittest discover -s tools/evidence_program/tests -p "test_training_data*.py"
python tools/evidence_program/check.py
# Only for already supplied, authorized local source files:
python tools/evidence_program/read_common_crawl_statistics.py /approved/languages.csv /approved/monthly.csv
# Synthetic fixture exercise (output is explicitly synthetic):
python tools/evidence_program/read_common_crawl_statistics.py tools/evidence_program/tests/fixtures/training-data/synthetic-languages.csv tools/evidence_program/tests/fixtures/training-data/synthetic-monthly.csv --synthetic-fixture
```

Passing offline checks establishes internal consistency and bounded parsing, not source truth, legal permission, independent scientific reproduction or canonical compatibility. The frozen contracts, inventory, previous readers and production runtime remain unchanged. No operational collector, source-script/notebook/model execution, corpus/page acquisition, training run or deployment is enabled.

## Corrections retained from review

- Repository baseline advanced from research-time 6c2a4aa to d196d9c; frozen64 and all nine earlier catalogs compared anew.
- FineWeb2 paper 1320/1868 domain-composition claim is version-specific; later CSV has 1870 filtered-train language-script rows. Do not mix denominators.
- Common Crawl share sums may deviate from 100 through rounding; exact page sums and per-row tolerance are separate tests.
- Current pinned Collapse producer code confirms bias=True; manuscript covariance formula remains a separately recorded discrepancy.
- HelpSteer2 real-data experimental role is distinct from model-generated responses and human ratings.
- Unknown CSV/metadata/results/code rights remain scoped unknowns; no source license propagates to content or other artifacts.
- DPI template is illustrative, not JSON Schema; 109 non-template JSON collection files are not a current dataset-record count.
- Consent denominator, domain exclusion and absence-of-consent caveats are verified in v2 PDF; parsed HTML omitted those details.
- Collapse export-era filenames and sampling differ from current helper; configured run/row totals cannot become observed export coverage.
- Epoch paper indexed-page assumptions and pivot-word counts differ from pinned code/input; keep estimates, inputs and versions separate without reproduction claims.
- Common Crawl unknown.urls is a residual-page scalar, not a measured unknown-language URL cardinality; preserve native value without enforcing URL-sum equality.

## Next actions

- **TD-A01 completed**: Verify five source collections, current frozen64 and all nine prior catalogs; preserve scoped corrections and rights.
- **TD-A02 completed**: Implement/test bounded two-file offline Common Crawl reader with synthetic public fixtures and separate private real-artifact acceptance.
- **TD-A03 held**: Aggregate CSV-specific rights and lossless canonical mapping remain unknown; retain private real acceptance and synthetic-only public CI.
- **TD-A04 held**: Audit-metadata reuse rights, per-record ancestry assertions, and exact Consent historical-panel access/schema/rights remain unverified.
- **TD-A05 held**: Saved export completeness, CSV/Parquet row equivalence, estimator/filename versions and code/results licenses remain unresolved; no history acquisition or model execution.
- **TD-A06 held**: Statistics CSV rights, exact release-denominator bridge, per-subset processing differences and cross-corpus overlap remain unresolved; no corpus acquisition.
- **TD-A07 held**: Replication-code/input rights, indexed-page/pivot-count discrepancy and exact GL001 input join remain unresolved; no model execution.
- **TD-A08 pending_separate_review**: Review lossless canonical mapping and admission separately; no contract/runtime/collector changes are part of this review.

## Standalone bounded follow-up prompts

These are research specifications for separately selected work, not running jobs or authority to acquire new corpora or change the repository. Unknown rights/access and source discrepancies remain holds.

### TD-P01 · Clarify aggregate CSV rights

Start with Common Crawl statistics at https://github.com/commoncrawl/cc-crawl-statistics/tree/1053c982a91ba0bb4323c5f00ec3230d9cd54e4b and https://commoncrawl.org/terms-of-use. Inspect only LICENSE, README, the statistics documentation and up to two directly linked rights pages (maximum five small documents, 256 KiB each). Determine whether aggregate CSV reuse/redistribution has an explicit grant separately from software and captured webpages. Do not fetch CSVs or contact maintainers. Return exact evidence URLs, scope, version and unresolved rights. Existing bounded reader and synthetic-only fixtures confer no rights. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, source-script/notebook/model execution, corpus/page-content acquisition, training, live collection or source admission. No repository edits, canonical admission or deployment. Stop when the bounded report is complete; report unavailable evidence and unknown rights without substitutes.

### TD-P02 · Verify provenance audit boundaries

At https://github.com/Data-Provenance-Initiative/Data-Provenance-Collection/tree/ce6662deccf011574427b6f112df479d261960b8 inspect only README, data_summaries/_template.json, data_summaries/Alpaca.json and src/web_analysis/README.md (up to 64 KiB each), plus https://arxiv.org/pdf/2407.14933v2 pages 4 and 26 and repository tree metadata. Determine metadata license scope and whether an exact historical domain-month panel locator exists. Do not acquire panel or described datasets. Keep 109 collection JSON files separate from dataset-record count, and preserve human annotation versus authorship, time-varying denominators and no-restriction versus consent. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, source-script/notebook/model execution, corpus/page-content acquisition, training, live collection or source admission. No repository edits, canonical admission or deployment. Stop when the bounded report is complete; report unavailable evidence and unknown rights without substitutes.

### TD-P03 · Audit experiment version linkage

Inspect https://github.com/RylanSchaeffer/KoyejoLab-Collapse-or-Thrive at revisions 3874173141dcf7f344b805cfa4ef126fc6a587d8 and 169abbfae4080b0dce804aad56189eb2868d0664: root/tree metadata, src/analyze.py, src/fit_gaussians/fit_gaussians.py, sweeps/fit_gaussians/default.yaml and notebooks/00_gaussian_fitting/00_gaussian_fitting.py (maximum nine text files, 128 KiB each). Compare public manuscript https://arxiv.org/html/2410.16713v3 and HelpSteer2 card https://huggingface.co/datasets/nvidia/HelpSteer2. Return a source-version map for export filename changes, samples=10000/skipped histories, bias=True versus manuscript estimator, code/results rights and reference-data composition. Do not acquire Parquet or CSV result histories. Configured grid is not observed coverage. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, source-script/notebook/model execution, corpus/page-content acquisition, training, live collection or source admission. No repository edits, canonical admission or deployment. Stop when the bounded report is complete; report unavailable evidence and unknown rights without substitutes.

### TD-P04 · Reconcile FineWeb2 versions

Inspect metadata only: https://github.com/huggingface/fineweb-2/blob/d0defb24f193bb9a5a11b8b14524a03c4858e1b6/fineweb2-language-distribution.csv (at most 600 KiB), its LICENSE/README, https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/blob/main/README.md and https://arxiv.org/html/2506.20920v1. Preserve native full header, version, script, split and missing dash. Explain whether any explicit bridge relates October 2025 CSV 1870 filtered-train subsets to paper 1320/1868 domain concentration; do not invent one. Distinguish words from universal tokens, filtered/removed/und subsets, within-language deduplication and rehydration. Return CSV-specific rights evidence and unresolved content rights. Do not read corpus rows or parquet. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, source-script/notebook/model execution, corpus/page-content acquisition, training, live collection or source admission. No repository edits, canonical admission or deployment. Stop when the bounded report is complete; report unavailable evidence and unknown rights without substitutes.

### TD-P05 · Reconcile stock model assumptions

Inspect only https://arxiv.org/html/2211.04325v2, the Epoch publication page, and README.md, src/indexed_web.py, src/stock_adjust.py, src/google_index_size_estimate.py, data/google_pivot_words.csv at https://github.com/epoch-research/data-stock/tree/83da8edaa853f036f1bbd521df9e789335d64b3b (five repository text files, each at most 32 KiB). Record paper 100–1200 billion indexed pages versus code 75–1000 billion, and paper 100 pivot words versus 105 input rows. Determine whether primary version history documents a bridge without running source code. Keep 510 [130,2100] trillion modeled tokens, quality adjustment and effective repetition distinct. Return separately scoped paper/code/input rights and do not claim numerical reproduction or an annual licensed-stock series. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, source-script/notebook/model execution, corpus/page-content acquisition, training, live collection or source admission. No repository edits, canonical admission or deployment. Stop when the bounded report is complete; report unavailable evidence and unknown rights without substitutes.

### TD-P06 · Review canonical mapping

Read the repository source inventory, training-data-feedback catalog/guide and existing frozen evidence-program field dictionary/schema at the exact commit selected for review. Use only repository metadata and synthetic examples; no new external acquisition. Prepare a mapping review for two-file Common Crawl output covering revision-specific IDs, crawl identity, raw fields, language unknowns, reported versus estimated counts, dates and scoped rights. List fields that would be lost and the smallest separately reviewable contract change if any. Do not change schemas, reader, inventory or production import and do not imply canonical admission. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, source-script/notebook/model execution, corpus/page-content acquisition, training, live collection or source admission. No repository edits, canonical admission or deployment. Stop when the bounded report is complete; report unavailable evidence and unknown rights without substitutes.

## Conclusion

Top additions: Common Crawl, Data Provenance Initiative, Collapse or Thrive. Strongest limitation: heterogeneous sources do not jointly establish licensed, deduplicated, usable data or frontier feedback effects. Smallest implemented step: a two-file, three-crawl, bounded offline statistics reader with synthetic-only public CI and private exact-artifact acceptance.
