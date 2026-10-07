# Chinese safety-evaluation research catalog

Reviewed 7 October 2026 against repository main `6c2a4aa531cd5b8e5411c25ee08569d707a682b1`. This is an additive discovery and verification catalog: **seven proposed families new relative to the frozen inventory, plus one C-SEM enrichment of CN020**. The [64-family inventory](../../../data/evidence-program/source_inventory.json) remains unchanged. All eight candidates are unadmitted and `candidate_not_collected`; none starts a collector or becomes a production observation.

The [machine-readable catalog](../../../data/evidence-program/research/chinese-safety-evaluations.json) carries artifact URLs, inspected revisions/blob identifiers, access/rights qualifications and source-linked findings. ZHS IDs are provisional research IDs. “Research verified” means the stated primary material was inspected, not that an experiment was replicated, every item was audited, or reuse was approved. New-relative-to-inventory comes from bounded name/owner/URL comparison, not an exhaustive repository or internet absence proof.

## Review outcome

FLAMES is the narrowest first **future adapter specification** because its selected README and license can be pinned and bounded. Chinese SafetyQA and JADE offer distinct factuality/abstention and multi-artifact lineage evidence, with important rights boundaries. C-SEM is a semantic-capability input lead, not a safety-outcome series. M³ stays on direct-verification hold.

The checks preserve several corrections to the initial shortlist: SuperCLUE denominator conflict and substantive March table revision; existing but limited judge validation; distinct LiveSec historical versions and current-page metadata; and M³ index-only access. No source prompt payload, full result table, raw submission or executable adapter is published here.

## ZHS001 FLAMES

Chinese adversarial value-alignment benchmark with a small pinned historical results table.

Classification: new_relative_to_frozen_inventory. Research state: primary_research_verified. Operational admission: none.

Rights: Apache-2.0 is declared for the selected repository README. No inference about scorer weights, public prompt payloads, third-party content or the separate paper.

- The selected table has 17 unique model labels and 187 scalar cells. These are reported values, not 187 independent experiments. Harmless rates and graded harmless scores remain separate metrics. [flames_readme](https://github.com/AI45Lab/Flames/blob/234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc/README.md)
- The table-update marker is December 11, 2023; the pinned artifact commit is May 21, 2024. Exact experiment dates, model checkpoints, protocol and table denominator remain unestablished. [flames_readme](https://github.com/AI45Lab/Flames/blob/234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc/README.md)
- The README describes 2,251 study prompts and 1,000 publicly released prompts. Neither count can be assigned as the historical table denominator without an explicit population match. [flames_readme](https://github.com/AI45Lab/Flames/blob/234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc/README.md)
- Reported author organizations are Shanghai AI Lab and Fudan NLP Group. Institutional overlap for individual model rows requires separate identity/affiliation evidence. No independent replication was performed. [flames_readme](https://github.com/AI45Lab/Flames/blob/234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc/README.md)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS002 Chinese SafetyQA

Chinese safety-domain factual knowledge, answer correctness and abstention; distinct from refusal robustness.

Classification: new_relative_to_frozen_inventory. Research state: primary_research_verified. Operational admission: none.

Rights: MIT is declared for repository software/documentation. Dataset CC BY-NC-SA 4.0 and paper CC BY 4.0 are separate artifact-specific declarations.

- The paper reports 2,000 underlying questions in QA and MCQ forms, not 4,000 independent cases. Supplied reference answers were inspected as source labels, not independently adjudicated. [csqa_paper](https://arxiv.org/html/2412.15265v2), [csqa_sample](https://github.com/LivingFutureLab/ChineseSafetyQA/blob/5be00913f99e24965378b557f1f0ecb7443caba3/data/chinese_safetyqa.jsonl)
- QA uses a model judge and MCQ uses option matching. The GPT-4o paper-v2 spot check is CO 59.35, NA 0.30, IN 40.35, CGA 59.53 and F-score 59.44. F-score is the source-defined combination, not ordinary accuracy. [csqa_paper](https://arxiv.org/html/2412.15265v2)
- Keep the December 11, 2024 README announcement, December 20 data-file change and December 17/23 arXiv submissions separate. These do not establish evaluation dates. [csqa_readme](https://github.com/LivingFutureLab/ChineseSafetyQA/blob/5be00913f99e24965378b557f1f0ecb7443caba3/README_zh.md), [csqa_dates](https://arxiv.org/abs/2412.15265v2), [csqa_data_history](https://api.github.com/repos/LivingFutureLab/ChineseSafetyQA/commits?path=data/chinese_safetyqa.jsonl&per_page=1)
- The Hugging Face main card and its commit page opened. Commit db66ec32331fcc3aed02fc4bdb01d416517a2262 was identified, but the immutable card endpoint was not successfully reopened. [csqa_dataset_card](https://huggingface.co/datasets/OpenStellarTeam/Chinese-SafetyQA/blob/main/README.md), [csqa_card_commit](https://huggingface.co/datasets/OpenStellarTeam/Chinese-SafetyQA/commit/db66ec32331fcc3aed02fc4bdb01d416517a2262)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS003 JADE

Related red-team, training-lineage, multimodal hallucination and agent-security artifacts; versions remain one family.

Classification: new_relative_to_frozen_inventory. Research state: primary_research_verified. Operational admission: none.

Rights: Root MIT software/documentation wording does not settle all data/image/report rights. HAL/MCP datasets state academic-research-only use. English paper v3 separately declares CC BY-NC-ND 4.0; Chinese-report rights remain unresolved.

- The Chinese report gives 74.13% average, 49.00% minimum and 93.50% maximum violation rates for its group of eight Chinese open models. These are group statistics from an attack-selected setting, not individual scores or ordinary-use harm rates. [jade_page](https://whitzard-ai.github.io/jade.html)
- JADE3 training triples derive from earlier JADE evaluation questions. HAL documentation reports 200 bilingual VQA records over 100 images; a bounded pair shares the same image. Preserve dependencies and do not double-count language variants. [jade3](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/jade-db-v3.0/README.md), [jade_hal](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/jade-hal-v1.0/README.md), [jadehal_pair](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/jade-hal-v1.0/jade_hal_vqa.csv#L1-L3)
- MCP documentation describes six categories and 33 subclasses, while its public subset mainly covers privacy leakage. No executable server example or attack workflow was acquired or run. [jade_mcp](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/jade-mcp-v1.0/README.md)
- Repository revision 812de63691d129757b8a55851d0c3440d2714523 is an artifact pin, not an experiment date. Current docs also mention a later BadPhoneAgent item, outside this review. [jade_root](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/README.md)
- Chinese primary documentation is available, but all-item original Chinese authorship and the direction of HAL translation are not established. [jade_root](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/README.md), [jadehal_pair](https://github.com/whitzard-ai/jade-db/blob/812de63691d129757b8a55851d0c3440d2714523/jade-hal-v1.0/jade_hal_vqa.csv#L1-L3)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS004 LiveSecBench

Version-changing Chinese-context evaluation with historical paper snapshots and a partially accessible current landing page.

Classification: new_relative_to_frozen_inventory. Research state: primary_research_verified. Operational admission: none.

Rights: Repository Apache-2.0 and paper CC BY-NC-SA 4.0 declarations are separate. Full questions are withheld; no reuse grant for the current leaderboard database is established.

- Historical v251030 / arXiv v1 (November 4, 2025) describes six dimensions; reasoning is excluded from Overall. The abstract names 18 models, while its methods/table name 22. Keep this count discrepancy. [live_v1](https://arxiv.org/html/2511.02366v1)
- Paper v2 (December 20, 2025) describes v251215: 57 models, five dimensions and DeepSeek-V3.2 judging. The overall value 76.90 for v1 label DeepSeek-R1-0528 and 62.43 for v2 label DeepSeek/DeepSeek-R1-0528* are cross-protocol values, not evidence of model regression. [live_v1](https://arxiv.org/html/2511.02366v1), [live_v2](https://arxiv.org/html/2511.02366v2), [live_v2_metadata](https://arxiv.org/abs/2511.02366v2)
- The current official landing page opens and labels March 2026 with four displayed dimensions and a changed synthesis method. Its score area remains a loading placeholder. Landing metadata is not a verified current results export. [live_page](https://livesecbench.intokentech.cn/)
- The benign factuality sample is dated November 20, 2025, later than v251030. It cannot identify that earlier paper population. Software/changelog dates are not measurement dates. [live_sample](https://github.com/ydli-ai/LiveSecBench/blob/35af1f81cf62fe2133db9d26d8b74964236c1267/livesecbench/question_set/factuality/sample_data.json#L1-L21), [live_changes](https://github.com/ydli-ai/LiveSecBench/blob/35af1f81cf62fe2133db9d26d8b74964236c1267/docs/CHANGELOG.md)
- Output-format documentation describes locally generated files, not a verified public API. Do not backfill historic judges from current defaults, pool versions, or assume every rewritten item was originally authored in Chinese. [live_format](https://github.com/ydli-ai/LiveSecBench/blob/35af1f81cf62fe2133db9d26d8b74964236c1267/docs/RESULT_FORMAT.md), [live_root](https://github.com/ydli-ai/LiveSecBench/blob/35af1f81cf62fe2133db9d26d8b74964236c1267/README.md), [live_v1](https://arxiv.org/html/2511.02366v1)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS005 CHiSafetyBench

Chinese risk recognition and risky-request refusal, with distinct populations and dialogue-history variants.

Classification: new_relative_to_frozen_inventory. Research state: primary_research_verified. Operational admission: none.

Rights: No reuse grant was established for the inspected repository data, README or figures. The paper uses arXiv nonexclusive distribution terms, not a general CC reuse grant.

- The paper reports 1,567 MCQs and 563 QA prompts; these are distinct task populations, not one interchangeable denominator. Only a small benign MCQ sample was inspected. [chi_safetybench_artifact_2](https://github.com/UnicomAI/UnicomBenchmark/blob/a06da90aac1a5665ddbdcd159c5ba29077e27df8/CHiSafetyBench/dataset/v1/mcq.json#L1-L9), [chi_safetybench_artifact_3](https://arxiv.org/html/2406.10311v2)
- Paper-v2 Table 2 reports ChatGLM3-6B RR-1 65.36%, RR-2 65.19% and HR 3.91%. RR-1 combines refusal types; RR-2 is responsible refusal; HR is harmful response. Preserve metric definitions and unknown experiment dates. [chi_safetybench_artifact_3](https://arxiv.org/html/2406.10311v2)
- Qwen-72B is the reported QA judge. Chinese payload has mixed lineage: SafetyBench-derived material, manual construction and translated/adapted HarmfulQA. Chinese text does not prove original Chinese authorship. [chi_safetybench_artifact_3](https://arxiv.org/html/2406.10311v2)
- June 2024 release, August 31 artifact changes and September 2 paper v2 are distinct date types. No fixed subsequent results cadence was verified. [chi_safetybench_artifact_1](https://github.com/UnicomAI/UnicomBenchmark/blob/a06da90aac1a5665ddbdcd159c5ba29077e27df8/CHiSafetyBench/README.md), [chi_safetybench_artifact_3](https://arxiv.org/html/2406.10311v2)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS006 SuperCLUE-Safety / SC-Safety

Historical multi-round adversarial results with important table-revision and denominator conflicts.

Classification: new_relative_to_frozen_inventory. Research state: primary_research_verified. Operational admission: none.

Rights: Repository/table/question reuse rights remain unresolved. The model-column label 许可 describes model availability, not a benchmark license. Paper terms are arXiv nonexclusive distribution.

- Question-count descriptions conflict: paper abstract says 4,912 questions; Dataset Statistics says 4,912 pairs; Chinese README says 4,912 questions / 2,456 pairs. The denominator remains unresolved. [superclue_safety_artifact_1](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README.md), [superclue_safety_artifact_4](https://arxiv.org/html/2310.05818v1)
- March 15, 2024 revision 3b9789520c13fdcdfb7ba5326b1c741e2459305e adds model rows and swaps some responsibility/instruction category values. The unchanged January 4 announcement is not the current table experiment date. [superclue_safety_artifact_1](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README.md), [superclue_safety_artifact_3](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README_202312.md)
- At that March revision, Yi-34B-Chat has total 89.30, traditional safety 85.89, responsibility 94.06 and instruction attack 88.07. These are source-defined scores; category tables repeat parts of the main table. [superclue_safety_artifact_1](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README.md)
- Judge validation exists: the paper reports 77% exact agreement and 85% within one point for a limited Chinese-Alpaca-2-13B comparison. This is limited validation, not absent validation or proof of universal judging accuracy. [superclue_safety_artifact_4](https://arxiv.org/html/2310.05818v1)
- No full question/answer corpus, public results API or ongoing measurement cadence was established. Historical filenames and commit dates alone cannot identify evaluation time. [superclue_safety_artifact_1](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README.md), [superclue_safety_artifact_2](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README_2023.md), [superclue_safety_artifact_3](https://github.com/CLUEbenchmark/SuperCLUE-Safety/blob/3b9789520c13fdcdfb7ba5326b1c741e2459305e/README_202312.md)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS007 M³-SafetyBench

Publisher-indexed Chinese technical-report lead; direct article/PDF access remains blocked.

Classification: new_relative_to_frozen_inventory. Research state: index_only_direct_access_blocked. Operational admission: none.

Rights: No open reuse license for the report, data or supplements was verified.

- Both the DOI page and direct PDF returned HTTP 403; the publisher index timed out. Only publisher-indexed text was available. No access-control bypass or successful primary full-text read is claimed. [m3_doi](https://www.sciengine.com/doi/10.1360/SSI-2025-0254), [m3_pdf](https://www.sciengine.com/cfs/files/pdfs/view/1674-7267/656CB3099A23415A9200E79A74D1D42C.pdf), [m3_publisher_index](https://scis.scichina.com/ssi-cs-information-security.html)
- Indexed text describes content/function safety across general and education settings and an online date of November 7, 2025. Reported large prompt totals are not proof of an accessible dataset. [m3_pdf](https://www.sciengine.com/cfs/files/pdfs/view/1674-7267/656CB3099A23415A9200E79A74D1D42C.pdf), [m3_publisher_index](https://scis.scichina.com/ssi-cs-information-security.html)
- Indexed Table 6 displays a Qwen2.5-14B-Instruct overall score of 95.94, but the separately indexed weighting description does not straightforwardly reproduce it. Direct method context is needed; do not reconstruct the composite or label this an author error. [m3_table_index](https://www.sciengine.com/doi/pdf/2C376132D17A4F8B9290DE2BA867E2E3), [m3_methods_index](https://www.sciengine.com/doi/pdfView/2C376132D17A4F8B9290DE2BA867E2E3)
- All indexed results remain discovery leads awaiting direct artifact verification. No numerical value here is admitted as a verified evaluation observation. [m3_table_index](https://www.sciengine.com/doi/pdf/2C376132D17A4F8B9290DE2BA867E2E3)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## ZHS008 C-SEM within FlagEval

Chinese lexical/semantic capability inputs enriching CN020, not another independent FlagEval family or measured safety series.

Classification: existing_family_enrichment. Research state: primary_research_verified. Operational admission: none.

Rights: FlagEval toolkit Apache-2.0 does not establish a separate grant for C-SEM CSV inputs or their source materials.

- Public v1 contains four CSV task files and bilingual documentation. A benign header/first row was inspected; no complete corpus or model-performance result was acquired. [csem_directory](https://api.github.com/repos/flageval-baai/FlagEval/contents/csem?ref=0d48d4847e238cea8a1555fa0ff26cb93a81afd1), [csem_sample](https://github.com/flageval-baai/FlagEval/blob/0d48d4847e238cea8a1555fa0ff26cb93a81afd1/csem/LLSRC_v1.csv)
- Public C-SEM and hosted FlagEval sets update asynchronously. Hosted testing uses a larger, richer set and a 5-shot protocol; public v1 cannot be presumed to reproduce hosted scores. [csem_readme](https://github.com/flageval-baai/FlagEval/blob/0d48d4847e238cea8a1555fa0ff26cb93a81afd1/csem/README-zh.md)
- The inspected component pin 0d48d4847e238cea8a1555fa0ff26cb93a81afd1 is dated November 21, 2023. Version and artifact dates do not establish an evaluation date or fixed update schedule. [csem_readme](https://github.com/flageval-baai/FlagEval/blob/0d48d4847e238cea8a1555fa0ff26cb93a81afd1/csem/README-zh.md), [csem_history](https://api.github.com/repos/flageval-baai/FlagEval/commits?path=csem&per_page=1)
- This resolves part of CN020 input-discovery metadata, not its leaderboard-result or rights gap. Semantic capability alone does not establish safer behavior. [csem_readme](https://github.com/flageval-baai/FlagEval/blob/0d48d4847e238cea8a1555fa0ff26cb93a81afd1/csem/README-zh.md), [csem_license](https://github.com/flageval-baai/FlagEval/blob/0d48d4847e238cea8a1555fa0ff26cb93a81afd1/LICENSE), [flageval_meta](https://github.com/FlagOpen/FlagEval/blob/main/README.md)

Artifact pins and access qualifications are recorded in the JSON catalog. Unknown experiment dates, model checkpoints, rights and denominators remain unknown.

## Bounded FLAMES adapter specification

Status: **proposed, not implemented or executed**. This belongs to future isolated evaluation staging, not person-belief/forecast extraction or the current production import. The catalog contains no contract-ready example record.

A separately assigned implementation may read only the following two content artifacts at commit `234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc`, with at most **two content fetches and 131,072 bytes per file**. Any unapproved redirect, extra content fetch, oversized response or pin mismatch must stop the run. Neither prompt files nor scorer weights are needed.

| Artifact | Bytes | Git blob SHA | SHA-256 |
| --- | ---: | --- | --- |
| [flames_readme](https://github.com/AI45Lab/Flames/blob/234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc/README.md) | 7310 | `f3f6cb666cabbeeda92d00d9311bbf27b654f164` | `f7142cbb5622268e0770332860d695397ca894d1c708da74bf4c109b17fb495f` |
| [flames_license](https://github.com/AI45Lab/Flames/blob/234bcb7a4a9da44c4177d2c2005e3bf8a582a5fc/LICENSE) | 11357 | `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64` | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |

Parse only `Leaderboard`: **17 unique model labels and 187 scalar values**. These values comprise one overall rate, five dimension rates and five dimension scores per model; they are not 187 independent experiments. Preserve the English source labels and record Chinese evaluation language separately. Source label translations would be new derivatives needing their own provenance.

Use exact-decimal strings for future parsed values. The bounded GPT-4 fixture checks are overall harmless rate `40.01%`, Safety harmless rate `27.51%`, and Safety harmless score `67.7`. Rates use percent; the graded score keeps its source-defined metric rather than an invented probability scale. Retain raw strings, table/row/column locators and immutable artifact identifiers.

Keep the table marker **2023-12-11** separate from the artifact commit **2024-05-21T07:23:50Z**, future retrieval time and the unknown experiment date. Exact model checkpoints, protocol and table denominator are unestablished. Neither 1,000 public prompts nor 2,251 described study prompts can silently fill the denominator. A label such as GPT-4 does not identify a modern checkpoint. Affiliation overlap needs row-specific evidence, not an automatic independence label.

Required future acceptance behavior:
- Use only the two immutable artifact URLs and verify Git blob SHA, SHA-256 and size against this catalog; reject content drift, unexpected redirects, oversize responses and extra fetches.
- Parse only the named historical table. Preserve table, row and column locators, raw strings, source labels and rate-versus-score units.
- Require the pinned fixture cardinality and three bounded numeric spot checks; malformed cells/headers fail or remain explicitly missing, never zero-filled.
- Keep source update, artifact commit, retrieval and unknown experiment dates separate. Do not infer the table population from public-subset or study counts.
- Retain exact model labels and separate institutional-overlap review. Language translations require separate provenance.
- Deduplicate by pinned source/row/metric identity; an OpenCompass mirror cannot add an independent measurement.
- Require separately reviewed staging/compatibility and rights decisions before any real observation can be admitted. This specification contains no production-ready example record.

The selected README’s Apache-2.0 declaration is evidence scoped to that artifact; it does not settle all prompt, scorer, third-party or paper rights. Preserve applicable license/attribution in any separately authorized artifact use. A verified OpenCompass integration adds a distribution/dependency link to **CN019**, not another independent result.

## What this enables and what remains open

This catalog improves discovery, date/version handling and future adapter scoping. It does not create operational admission, a storage/credential grant, live collection, benchmark execution, forecast observations, a public scoring change or deployment. Any implementation must follow the [task plan](../implementation_tasks.md), [dataset compatibility limits](../dataset_spec.md) and existing [source policy](../../SOURCE_AND_PROVENANCE_POLICY.md). Artifact-specific access and rights must be rechecked when use is actually proposed.

Run the existing [offline checks](../../../tools/evidence_program/README.md) to check catalog references, provenance shape, frozen inventory identity and inactive admission markers. These checks do not contact sources, validate linguistic/scientific claims, prove legal rights or implement the adapter.

## Next actions and focused follow-ups

- **Completed:** bounded source verification, artifact-specific rights/access labeling, FLAMES pin and table checks, and corrections to SuperCLUE and LiveSec version/denominator claims. M³ remains explicitly index-only. The research catalog and its offline consistency tests are prepared.
- **Next repository task, not implemented:** add an isolated offline FLAMES `Leaderboard` parser and tests using the two pinned artifacts specified above. Preserve exact-decimal strings and raw labels; test 17 models/187 scalars, malformed cells, pin drift, duplicate reprocessing and unknown checkpoints/dates/denominators. Produce reviewable staging output only after agreeing its compatibility shape. Keep network collection, admission, database import and scoring disabled. This catalog supplies the specification, not that parser or its outputs.
- **Retained holds:** M³ direct full-text/methods and rights; CHiSafetyBench and SuperCLUE reuse grants; JADE HAL/MCP academic-only conditions and unresolved older-data/Chinese-report rights; C-SEM CSV/source-material rights; SafetyQA dataset noncommercial/share-alike obligations; LiveSec withheld questions and unavailable current score rows. FLAMES scorer/prompt rights remain outside the selected README scope. These need artifact-specific evidence or use decisions, not blanket inheritance from software licenses.

Two focused prompts address the remaining evidence gaps; they do not repeat the completed broad source search.

### Follow-up prompt: M³ methods and reuse evidence

Do read-only public research on M³-SafetyBench, DOI 10.1360/SSI-2025-0254. The publisher DOI/PDF returned 403 in the October 7, 2026 review; only indexed text was available. Locate openly accessible publisher or author material that directly establishes Table 6’s metric definitions, composite weights, denominator and reuse terms. Clarify the reported Qwen2.5-14B-Instruct overall value 95.94 without treating the indexed arithmetic discrepancy as a proven error. Return exact source/version links and separate directly read evidence from index-only clues. Respect access restrictions; no circumvention, outreach, bulk acquisition or repository edits.

### Follow-up prompt: LiveSec historical result provenance

Do read-only public research on LiveSecBench’s v251030 and v251215 releases, documented at https://arxiv.org/html/2511.02366v1 and https://arxiv.org/html/2511.02366v2. Find any officially linked, versioned result export or methodology supplement that preserves model labels, judge, metric definitions, question populations and experiment dates for each release. The March 2026 site https://livesecbench.intokentech.cn/ showed four dimensions but only loading placeholders for scores in the review. Keep those landing-page claims separate. Use published public links; do not guess private endpoints, bypass restrictions, run evaluations or infer a cross-version trend. Report an absent/unavailable export honestly.
