# Physical-world and inference comparability follow-up

Reviewed 8 October 2026. The bounded documentary review is complete for RP004, IPP001 and RP002. Exact membership, metric reconciliation, exclusion application and power normalization remain held.

[Machine-readable delta](../../../../data/evidence-program/research/followups/physical-inference-comparability.json) · [Follow-up queue](follow-up-queue.md)

The historical [robotics](../robotics-physical.md) and [inference](../inference-price-performance.md) catalogs keep their original bytes and IDs. This update binds prior artifact, assertion, action, prompt and hold pointers. It adds no source family or operational evidence. The older packet's missing inference catalog is historical: reuse IPP001 and preserve its GL008 Training-producer relationship.

## RP004: PhAIL selection history is partly explained

Two author-declared changes now have direct documentary support:

- The [6 May omission correction](https://github.com/Positronic-Robotics/phail-paper/commit/8c20fbf7d8163270b29b70b6ad75e420b99d5d64) declares 28 previously omitted zero-success episodes, split ACT 18, SmolVLA 8 and GR00T 2, and a historical total changing from 1,015 to 1,043. The committer time is 20:12:06 UTC, distinct from the author time. No episode membership was enumerated; a later interface's equal total is not a join key.
- The [27 May migration](https://github.com/Positronic-Robotics/phail-paper/commit/87ac6f74ece0a94a415aa08bb69dc9cc61846e67) declares 187 excluded candidate URLs: 119 spoons-ablation and 68 USB-C Boxes candidates. These are not independently verified unique episodes, and 68 does not replace the older audit's 72.

The [pinned loader](https://github.com/Positronic-Robotics/phail-paper/blob/18ce72d5703dcbbbb10a980336aa5a1622601fb4/build/markup/loader.py) documents manual-review preference, agreement/operator-zero-success auto-validation, ablation and metadata/duration filters, and optional object/model filters. Its human-label branch can force drop/safety fields to zero. Those are processing rules, not observed zero human failures. The source was inspected without execution.

Path histories are pinned to the containing revision. The audit and per-operation aggregate last changed on 6 May; the leaderboard aggregate on 27 May; the table builder has a separate 6 May path change. A shared checkout does not establish synchronized generation or matched populations. Last-change time is not generation time.

The [paper](https://arxiv.org/html/2605.29710v1), Section 4.3/Table 2 and Appendix E, distinguishes actor roles (599 policy, 396 human reference) from annotation streams (995 total, 573 agreement, 422 manual review). Candidate URLs form another unit. No complete cross-tabulation was established.

### Separate training-count assertions

The [release whitepaper](https://phail.ai/releases/v1.0/whitepaper.pdf), visually checked on pages 3–4, says 352 training episodes in prose but lists object rows 167/112/83/88 without a printed total. The arXiv Appendix C instead has batteries 87 and a printed total of 449. Preserve all assertions without choosing a repaired total or inventing a transition. The PDF's 7 October Last-Modified header is hosting metadata; non-commercial dataset wording does not identify an exact license or authorize copying the PDF.

The [HF card](https://huggingface.co/datasets/phail-anon/phail-v1.0/blob/5bc590213c5d2615eefeb47bc23a700f8c57022a/README.md), paper and release continue to declare policy/human/training vectors 524/40/449, 599/396/449 and 594/unknown/352. The new history narrows the absence-of-explanation question, but RP-A6 / RP-P4 remain held for complete membership bridges, reason counts and generation lineage. Safety-only caption, Safety OR Stalled builder proxy, Appendix F episode rates and older drops-plus-safety per-operation measures remain distinct. Reset/setup exposure and 120-/240-second horizon identity are also unresolved.

## IPP001: publication and summary/session association

As of 8 October 2026, 12:06:21.407 UTC, the [official table](https://docs.mlcommons.org/inference_results_v5.1/) lists Lenovo 5.1-0061 as Datacenter / Available / Closed, SR680a_V3_B200SXMx8_TRT, Llama2-70B Offline. The 99 and 99.9 tiers retain separate identities and both display 102,909 tokens/s. No applicable entry was found in the inspected [published change log](https://mlcommons.org/results-change-log/). This bounded current-status finding is not permanent approval or proof no unpublished change exists. The [round announcement](https://mlcommons.org/2025/09/mlperf-inference-v5-1-results/) is dated 9 September 2025.

Complete pinned [summary](https://github.com/mlcommons/inference_results_v5.1/blob/5ea4f62ef62536e6bf4d78a9b440fb9035ddfb4a/closed/Lenovo/results/SR680a_V3_B200SXMx8_TRT/llama2-70b-99/Offline/performance/run_1/mlperf_log_summary.txt), [client](https://github.com/mlcommons/inference_results_v5.1/blob/5ea4f62ef62536e6bf4d78a9b440fb9035ddfb4a/closed/Lenovo/results/SR680a_V3_B200SXMx8_TRT/llama2-70b-99/Offline/performance/power/client.json) and [server](https://github.com/mlcommons/inference_results_v5.1/blob/5ea4f62ef62536e6bf4d78a9b440fb9035ddfb4a/closed/Lenovo/results/SR680a_V3_B200SXMx8_TRT/llama2-70b-99/Offline/performance/power/server.json) file bytes establish the documentary association with power session `2025-07-28_07-18-36`; session names and UUID pairs agree. For the 1,886-byte summary:

- File-byte SHA-1: `a696dae6a2f3858a15b76daf0ee6a0583c70e177`, matching the client fingerprint
- File-byte SHA-256: `cb7b02d59165d4f2f5f299228e74814f0d0c8c782568b2b88e6141aa14333152`
- Git-framed blob SHA-1: `314b07a539f214492b6067eab11ea452c1efba61`

These hashes were recomputed from complete repository-file bytes reconstructed from base64. They are not a newly observed raw HTTP capture. The JSON links the exact summary and both manifests. The summary separately reports 376.512 samples/s and 102,909 tokens/s. Shared power/ranging/run_1 trees between tiers do not establish the number of physical runs or independent replications.

IPP-A01 / IPP-P01's bounded publication check is complete at the stated time; its not-started wording is superseded for that component. Energy/task remains null. Still missing are the matched LoadGen begin/end interval, its official whole-system AC mean watts, achieved request/token denominator, exact LoadGen revision and approved v5.1 power-release/rules mapping. Session equality is not interval equality. Preserve the existing CUDA 12.8/12.9 conflict; the packet's missing second value cannot erase it. No spl.txt, detailed LoadGen trace, checker, benchmark or power-normalized comparison was used.

## RP002: exact snapshot metadata, unknown exclusion application

The [pinned global metadata](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/global_metadata.yaml) and [card](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/README.md) specify creation at 17 July 2026, 19:24:30.388816 UTC, with 3,883 evaluation sessions, 10,783 policy episodes and 27,148 separately typed MP4 videos. The counts were already cataloged; the exact timestamp and scoped byte verification are the additions. These are publisher aggregates, not an enumerated membership audit.

The full metadata/card and targeted paper check did not establish an applied exclusion-rule version, excluded count or export-to-notice mapping. Exclusion application stays null. RP-A4 / RP-P2's bounded metadata/exclusion-link check is complete; broader membership, score/UI bridge, duration units, exact checkpoints and deployed notice/application remain held. The prior February/July overlap still covers one sampled session only. This review did not recheck the deployed frontend or promote a supplied zero-text page result to independent evidence.

## Verification limits and next work

The 12 sourced findings include eight independently matched complete document/repository-file digests, each with its own acquisition/hash scope. This does not certify all 46 supplied capture claims. Source bodies and personal evaluator fields are not published. The 24 supplied acceptance cases remain unimplemented proposals, and no canonical/runtime mapping is claimed.

Any next work should target a new bounded membership/version/metric correction for PhAIL, an exact official matched-interval/power/work/protocol document for MLPerf, or a July-export-specific exclusion mapping for RoboArena. Do not repeat settled arithmetic, known tier identity or the verified summary/session check as new research. No execution, media/trace sweep, generalized reliability score, source admission, rights clearance or p(doom) conversion follows.
