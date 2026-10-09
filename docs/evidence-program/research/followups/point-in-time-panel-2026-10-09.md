# Session 02: substantive review, with bounded unresolved evidence

Completed 9 October 2026 following a bounded authorized source review. This addendum supersedes the earlier blanket source-deferred portions of the offline review; the earlier review and all uploaded originals remain intact.

## Result

**Partial research package; still 0/12 strict-ready training candidates.** The source extents, selected raw joins, native score preservation, three primary-paper checks, historical A bytes and intended evaluation configuration are now independently verified at the scopes below. The remaining scientific blocker is the missing aggregate-to-execution chain. A valid shape schema does not close it.

The source-review pass made no canonical import, repository/inventory edit, production adapter, benchmark/model run, training, public release, archive write, OpenAlex request or new bulk Epoch download. This repository change packages that completed review as research only.

## Source checks now closed

### Exact Epoch archived copy

A fresh read of the existing archived CSV verified the complete expected SHA-256 d845f68989881cb922ee6fd131d2bce6fb9c88dce5978eb0719a4c053476eff9 and 6,826,880 bytes. Parsing reproduces 3,626 rows, 57 fields and all claimed population/missingness counts. All twelve candidate extracts resolve to the specified ten distinct rows with no raw-field mismatch; all twelve example compute-note strings also match exactly.

Confirmed populations include 1,410 populated compute cells, 2,344 parameter cells, 20 rows containing the Benchmarks method token, seven of those with numeric compute, and 132 populated-compute rows without a method. All current row modification dates fall after the 2024 cutoff. This establishes the exact 2026 source vintage, not historical availability of each field.

Only the review-created temporary materialization was deleted after full-hash and row checks. Its absence was checked. The original archive and prior local research were not altered. The private transfer receipt is excluded from any public candidate.

### EvalPlus chronology and protocol

The complete results file at commit ba37a9f43a5706e87762951029baab25880cd0d6 is byte-identical to A: 32,977 bytes and SHA-256 4d293d4450da091dab4ee4ab333d73b34973066a5dc122c8eef3ada6421b00cb. Git metadata gives author and committer time 2024-04-20T03:06:04Z, before T. The precise graph-ancestry relationship to the selected A commit was not separately traversed; the dated same-byte repository state itself is verified.

This is repository chronology, not an independently observed first-public timestamp or an inference time. A still cannot be labeled an unseen future target just because the selected snapshot is April 21. B cannot silently replace an as-of-T target.

The exact A/B HTML files both declare HumanEval+ 0.1.9. MBPP+ changes from 0.1.0 to 0.2.0 while B retains the 399-task sentence. They describe greedy pass@1 and activated inference weights for the size field. The retained migration's 21 deletions and 18 prompt replacements remain static code counts, not observed per-run denominators. The inspected release metadata separately acknowledges the nominal 399→378 change.

Sources: [dated commit](https://github.com/evalplus/evalplus.github.io/commit/ba37a9f43a5706e87762951029baab25880cd0d6), [same-byte results](https://github.com/evalplus/evalplus.github.io/blob/ba37a9f43a5706e87762951029baab25880cd0d6/results.json), [A protocol](https://github.com/evalplus/evalplus.github.io/blob/3b9f5b48c92a492a48fde6c0e1bffb9295812caf/leaderboard.html), [B protocol](https://github.com/evalplus/evalplus.github.io/blob/65db7ffdb66ae3fee800bee8d998b412f0a6e648/leaderboard.html).

### Intended selectors are verified, execution is not

Static inspection of the pinned code verifies default code-llama-34b routing to Python-34B and code-llama-multi-34b routing to the general base variant. The GPT-4-1106-preview path uses a JSON response format with corresponding prompt text. The DeepSeek route constructs different base/instruct handles and allows a separate version suffix. These are possible implementation paths; there is no evidence tying a specific invocation to a given aggregate row. The code was never executed. [Pinned selector source](https://github.com/evalplus/evalplus/blob/9a73d2b7bc878a67e41205bddf7e5104db5a30a7/codegen/model.py).

### Primary-paper feature evidence

- **StarCoder2:** v1 header is dated 29 February 2024. Table 6 and footnote 24 verify 5.94e22, 1.55e23 and 3.87e23 FLOPs for 3B/7B/15B, estimated with 6ND and already including base plus long-context training. Do not add its 200B long-context phase a second time. These are developer-reported estimates, not metered compute. [Paper v1, Section 6/Table 6](https://arxiv.org/html/2402.19173v1).
- **DeepSeek-Coder:** v1 header is dated 25 January 2024. The original from-scratch family includes 6.7B and 33B; 2T base-training tokens and 2B instruction tuning from base are verified. Keep the separately described v1.5 warm-start branch distinct. The supplied 6ND calculations reproduce arithmetically, but require the stage qualification below. [Paper v1, Sections 3.3, 3.6, 3.7 and 5](https://arxiv.org/html/2401.14196v1).
- **Code Llama:** v3 header is dated 31 January 2024. Prose explicitly gives 1T code-training tokens for 70B and differentiates its Python-derived Instruct branch from smaller variants. Only the base 70B branch receives LCFT. Generic 500B language also remains in the Python paragraph and table caption. This supports preserving scope/source tension; the exact claimed Figure 8 labels still need visual verification. [Paper v3, Sections 2.1–2.2 and Appendix B](https://arxiv.org/html/2308.12950v3).

Paper version dates establish documentary availability for these inputs. They do not establish release of any exact loaded weight set or the model state used by EvalPlus.

## Material qualification added by this review

**DeepSeek's 6ND estimate needs narrower stage labeling.** Section 3.6 describes an additional 1,000-step long-context extension following the initial stage. The rounded 2T statement is not reconciled to an exact all-stage token ledger. Therefore 8.04e22 and 3.96e23 should be labeled analyst reconstructions from the disclosed 2T phase, with the additional stage's accounting unresolved. Do not promote them to complete lifetime/pretraining totals or silently put them on the same complete-cost scope as StarCoder2 Table 6. Do not invent a corrected numeric total by assuming every batch's token count.

This qualification does not change the native Epoch cells or require deleting the reconstructable feature; it changes its analytical scope. J08 may reference it as a base-ancestor phase estimate while its descendant total remains missing.

## What the bounded manifest search found

One publisher release-list response covering ten releases was read. The v0.2.0 entry lists 22 output ZIP assets, including DeepSeek-Coder-6.7B-base, CodeLlama-34B and GPT-4-1106-preview names. Their metadata has no digest, and a filename is not a binding to A/B rows, loaded revision, task/scorer identity, actual denominator or generation time. No StarCoder2 asset or DeepSeek-33B-base asset appears in that inspected list. The similarly named starcoder asset must not be treated as StarCoder2.

No qualifying aggregate-to-run manifest was found in the inspected release metadata or other reviewed artifacts. This is a bounded negative finding, not proof that none exists elsewhere. No output ZIP was downloaded. Asset creation time is publication metadata, not execution time. [Publisher releases](https://github.com/evalplus/evalplus/releases).

## Remaining bounded source limitations

Exactly twelve distinct primary artifacts/responses were attempted: three papers, one figure, two pinned cards, two protocol files, selector code, one commit record, its results file and one release-list response. Nine were successfully read. GitHub web-reader cache failures were resolved through read-only pinned GitHub access to the same artifacts.

The direct Figure 8 SVG and two pinned card pages were unavailable through the web reader. Their failed reads establish a tool limitation, not absence or falsehood. In particular:

- Do not label Figure 8's alleged 500B/100B/260M/20B values or exact arrows newly independently verified.
- Do not treat the two supplied truncated DeepSeek base-card strings as complete document hashes.
- Exact card/checkpoint revisions and ancillary release-day claims remain documentary holds where not independently inspected. The primary papers and native explicit handles support named variants without resolving runtime identity.

The original scoped rights records remain in force as historical evidence; this pass made no new grant expansion or public-release decision.

## Analytical disposition after source verification

All twelve prior join dispositions remain appropriate: seven partial, two ambiguous, three rejected direct equivalences. None has an executed model/service identity linked to the aggregate. All 24 snapshot run/output/evaluation bindings remain missing. The complete raw-data check does not manufacture those links.

Prioritize the three StarCoder2 base models first, then the two DeepSeek base models with explicitly bounded phase-compute scope. A small publisher manifest for HumanEval/HumanEval+ would cover at most 20 publication-metric assertions across five labels, not automatically five independent runs.

Before any partial admission, define per-metric run/protocol bindings, explicit selected feature/target IDs per view, executed identity separate from the Epoch-row/ancestry relationship, and one reusable J07/J08 compute-estimate identity. Enforce historical clocks, source-native values, denominator evidence, circular-compute exclusion, logical uniqueness and dependency grouping. The earlier 41 negative tests remain relevant: 35 are schema-valid and six are rejected; the supplied conservative baseline has no bounded semantic errors.

## Integrated research package

The [data package](../../../../data/evidence-program/research/followups/point-in-time-panel-2026-10-09) includes all four supplied artifacts with exact original/package hashes, the known issued assignment, historical offline results, current source findings, all 41 negative mutations and a portable offline replay. The submitted artifacts are historical claims; [source corrections](../../../../data/evidence-program/research/followups/point-in-time-panel-2026-10-09/source-corrections.json) and [final disposition](../../../../data/evidence-program/research/followups/point-in-time-panel-2026-10-09/final-disposition.json) govern interpretation without changing native values.

The supplied audit and schema JSON files are byte-identical. The examples JSON changes only eight occurrences of two unverified source-native Colab Drive URLs, replaced consistently with stable SHA-256 locator tokens; the same token replacements appear in two review receipts. Three private attachment links in the narrative are sanitized. A per-field redaction record preserves copy hashes without exposing the original locator mapping. All numerical values and units remain unchanged. Exact native-note comparisons refer to the unchanged private originals, not the redacted public note text. Private archive/Library/message identifiers, transfer receipts and local paths are omitted. Raw primary-source sidecars are not republished. Applicable [attribution and rights boundaries](../../../../data/evidence-program/research/followups/point-in-time-panel-2026-10-09/NOTICE.md) remain attached.

The exact issued assignment is preserved, but its identity as the executed session prompt is not established. Remaining-only tasks in next-actions.json and followup-prompt.txt have not been launched. Earlier offline results remain valid at their dated scope; their blanket Epoch and primary-source deferrals are superseded by this review.

This is assignment 2 of the [six issued briefs](prompts/research-assignments-2026-10-09.md): one additional session and four supplied artifacts. The original 26-session queue, prior three follow-up bundles, seven later submissions and separately integrated session 01 retain their existing counts and contents. No canonical contract, source inventory, live collector or training row is changed. The integration base was main 91744b127309ca384de4d375e05ff0114fa440d6; remote publication, exact-commit CI and merge remain separate verifications.
