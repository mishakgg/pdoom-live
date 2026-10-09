# Historical offline review snapshot

This is the preserved offline-stage assessment. Its blanket Epoch/primary-source deferrals are superseded by the latest source review and final-disposition.json. Its native-data and schema findings remain valid at their stated scope. Private file locators are omitted.

# Session 02: point-in-time panel independent offline review

Review date: 9 October 2026. Status: **offline review complete; source-verification follow-up remains open**.

## Decision

**Partial research package; zero of twelve candidates are ready for strict model-level point-in-time training or independent compute–performance analysis.** The submission's conservative overall decision is supported. Its native EvalPlus descriptive results reproduce exactly. Its JSON Schema is valid, but does not enforce analytical admission.

No originals, canonical schemas, repository inventory, collectors, schedules or other reviews were changed. No source/provider/Drive requests, uploaded-code execution, model execution, benchmark reruns, model training, public release or integration occurred. The local checker and synthetic mutation tests were newly authored for this review; they are not an implemented production adapter.

### What is genuinely ready

- **Original preservation:** all four uploaded originals retain their recorded byte lengths and SHA-256 hashes; all three JSON files parse without duplicate keys.
- **Exact EvalPlus source-version comparison:** both retained source bodies match the submission's complete hashes and earlier Git blob receipts. Each has 101 native keys and 404 metric slots. All 24 selected native objects, including all 96 metrics, match both the audit and examples exactly.
- **Bounded candidate exclusion ledger:** 12 candidates, four conservative family groups, 10 distinct proposed Epoch rows, seven partial mappings, two ambiguous mappings and three rejected direct equivalences. All executed IDs remain null. These counts do not establish 12 independent checkpoints or training runs.
- **Proposed schema and examples as research artifacts:** Draft 2020-12 metaschema validation and example validation pass, including format checking. The baseline retains 76 numeric scores and 20 nulls; all strict analytical views are excluded.

### What remains partial or not ready

- **Epoch row/value audit: partial.** Prior independent capture and verified-archive receipts corroborate the exact 6,826,880-byte hash, 3,626 rows and 57 fields. The full CSV was intentionally cleaned from transfer scratch after archival. This review did not recover or reparse it. The 72 comparable raw cells agree between supplied audit and examples, but this is internal consistency, not a new upstream row check. The expanded compute/citation/missingness populations and selected row positions remain un-reproduced here.
- **New historical source claims: pending independent source checks.** The earlier byte-identical A ancestor, intended selector routing, primary-paper compute tables, release/revision dates, pinned model-card authenticity and Code Llama prose/figure conflict were supplied as claims and links. Existing local evidence is insufficient to close each claim independently. No current-source request was made while the collection task was active.
- **Strict training/hindsight/prospective/independent-compute views: not ready, 0/12.** Every candidate lacks a verified executed model or service snapshot. All 24 example snapshots lack run, output-set and actual evaluation-spec bindings. Actual metric denominators, generation times, task/prompt manifests and scorer/harness bindings remain unknown. Neither copied metadata nor a schema status change can resolve those omissions.
- **Production semantic enforcement: not ready.** Forty-one reviewer-authored negative mutations exercise all eight proposed acceptance cases. Six are rejected; 35 unsafe mutations remain schema-valid. This does not invalidate the cautious supplied baseline or contradict the schema's stated shape-only scope. It does establish that the schema alone cannot be the production admission gate.

## Reproduced numbers

| Population | Independent local result |
|---|---:|
| A native keys / metric slots | 101 / 404 |
| B native keys / metric slots | 101 / 404 |
| A numeric / null metrics | 358 / 46 |
| B numeric / null metrics | 322 / 82 |
| Unchanged / changed full objects | 29 / 72 |
| Changed metric slots | 161 |
| Numeric revisions / numeric-to-null / null-to-numeric | 125 / 36 / 0 |
| Changes: HumanEval / HumanEval+ / MBPP / MBPP+ | 2 / 22 / 69 / 68 |
| A / B nonnull MBPP labels | 78 / 60 |
| Selected candidates / distinct proposed Epoch rows / families | 12 / 10 / 4 |
| Selected snapshot objects / metric slots | 24 / 96 |
| Selected numeric / null metrics | 76 / 20 |
| Strict-ready candidates | 0 / 12 |

All nonmetric native fields are unchanged across A/B. A separate static AST inspection reproduces 21 distinct delete targets and 18 replace calls in the retained migration source. The script was not executed and no benchmark corpus was counted. The nominal 399→378 population is documentary context, not a verified per-run denominator.

Sources: [EvalPlus A](https://github.com/evalplus/evalplus.github.io/blob/3b9f5b48c92a492a48fde6c0e1bffb9295812caf/results.json), [EvalPlus B](https://github.com/evalplus/evalplus.github.io/blob/65db7ffdb66ae3fee800bee8d998b412f0a6e648/results.json), [migration source](https://github.com/evalplus/evalplus/blob/3de226896daa67b54e2683eb6e5f6840ce66018a/tools/mbpp/fix_v010.py). These links identify the source versions associated with locally retained bytes; they were not opened anew in this review.

## All twelve joins

| ID | EvalPlus label → proposed Epoch row | Review disposition |
|---|---|---|
| PIT-J01 | GPT-4 (May 2023) → GPT-4 (Mar 2023) | Keep ambiguous. The native generic product link and month label provide no executed snapshot. Current hardware-derived compute and its reported uncertainty cannot be backdated from the supplied current row. |
| PIT-J02 | GPT-4-Turbo (Nov 2023) → GPT-4 Turbo (Nov 2023) | Keep partial product-only mapping. Supplied numeric compute is blank; the 2.2e25 notes extraction is benchmark-imputed and excluded. An announcement ID is only a candidate identity. |
| PIT-J03 | GPT-4-Turbo (April 2024) → GPT-4 Turbo (Apr 2024) | Keep partial product-only mapping. Native link repeats the November announcement. No executed April service snapshot is established; same benchmark-imputed compute exclusion. |
| PIT-J04 | CodeLlama-34B → Code Llama-34B | Keep ambiguous intended variant. Native result links a general announcement. The submitted selector/Python scope and date conflict need primary verification; no automatic base or Python equivalence. |
| PIT-J05 | CodeLlama-70B → Code Llama-70B | Keep direct total-compute join rejected. Native link explicitly names Python-70B. Supplied generic Epoch total and the paper's training-stage conflict remain separate claims requiring source checking. |
| PIT-J06 | CodeLlama-70B-Instruct → Code Llama-70B | Keep direct join rejected. Native Instruct handle differs from Python/base. Preserve proposed ancestry and hold descendant total; do not sum sibling stages. |
| PIT-J07 | DeepSeek-Coder-6.7B-base → DeepSeek Coder 6.7B | Keep partial named-base mapping. Native handle is explicit; supplied Epoch link agrees. 6 × 6.7e9 × 2e12 = 8.04e22 arithmetic passes. Historical inputs and executed revision remain separate verification gates. |
| PIT-J08 | DeepSeek-Coder-6.7B-instruct → DeepSeek Coder 6.7B | Keep equivalence rejected and proposed base ancestry separate. Native Instruct handle differs. 8.04e22 is scoped as ancestral pretraining; descendant total remains null. |
| PIT-J09 | DeepSeek-Coder-33B-base → DeepSeek Coder 33B | Keep partial named-base mapping. 6 × 33e9 × 2e12 = 3.96e23 arithmetic passes. B MBPP values are native nulls; no forward fill. |
| PIT-J10 | StarCoder2-3B → StarCoder 2 3B | Keep partial named-base mapping. Native handle is explicit; submitted 5.94e22 pre-cutoff paper estimate still needs independent paper check. No executed revision. |
| PIT-J11 | StarCoder2-7B → StarCoder 2 7B | Keep partial named-base mapping. Submitted 1.55e23 paper estimate and later configuration correction need primary verification. Later metadata is not April execution evidence. |
| PIT-J12 | StarCoder2-15B → StarCoder 2 15B | Keep partial named-base mapping. Submitted 3.87e23 paper estimate remains source-pending. No interchange with Instruct/OCI variants. |

For every row above, native EvalPlus values are independently rechecked; Epoch extracts and newly cited documentary assertions are not all independently source-verified. Rejection means rejecting the asserted direct equivalence or analytical use, while preserving originals and possible ancestry.

## Information-time and dependence review

The declared cutoff is 2024-04-20T23:59:59Z. All current Epoch features remain excluded. Nineteen proposed historical/reconstructed features have internally consistent clock bounds at or before T. Three DeepSeek reconstruction assertions reproduce arithmetically; two repeat the same 6.7B ancestor estimate. Source timing/content for these feature inputs is not closed by arithmetic.

The supplied A `repository_chronology_only` classification is appropriately weaker than first-public or inference-time evidence, but the newly claimed pre-T ancestor itself still requires independent verification. Keep B as a dated correction/hindsight vintage. No prospective outcome follows from a later commit timestamp. Ingestion in 2026 must remain distinct from historical public availability.

All metrics and both vintages are nested under a candidate and share its family split label. DeepSeek base/Instruct share an explicit hard-dependency label; Code Llama 70B variants share an ancestor label. This supplied grouping is conservative. It is not a runtime split implementation or proof of independent pretraining lineages.

The examples repeat the DeepSeek 6.7B estimate in J07/J08 with self-scoped dependency IDs. Their shared group prevents an immediate split discrepancy, but the production representation still needs one reusable estimate identity and explicit descendant references to implement rule G6 faithfully.

## Verification qualifications that must travel with the submission

1. Replace blanket “source audit independently complete” language with this scope-specific disposition. Native EvalPlus is reproduced; Epoch extent is prior-receipt corroborated; new primary-source facts remain pending.
2. Label the two embedded DeepSeek base-card strings as excerpts. Each has 3,834 supplied UTF-8 bytes, whereas document receipts claim 6,861 and 6,867 bytes. Their excerpt hashes cannot validate the declared full-document hashes. The 3,574-byte Instruct card is internally hash-complete, but was not independently re-fetched.
3. Treat `ready` descriptive status and `fresh_bytes_verified` in originals as the submitting session's assertions. They are not new capture timestamps or proof of this review's access to every full source body.
4. The schema/fixture tests are now executed locally; the eight submitted behavioral specifications remain unimplemented as a production adapter. Preserve that distinction.
5. The inspected repository context is historical pin `720ee3cb7107cc0cb9bca8b85983df7ee8db6ddc`, not freshly checked main. All ten cited repository bodies were matched locally to submitted Git blobs; nine match the retained preceding tree, and the changed preservation policy matches the published-candidate copy. The earlier publication receipt corroborates the merge/tree. No newer-main assertion is made.

## Proposed data-model limitations

Future partial admission needs metric-level assertion bindings: one candidate-level decision currently covers two snapshots and four metrics, while HumanEval and MBPP use distinct protocols. Resolving one HumanEval assertion must not admit all eight metric slots. Analytical views also need explicit selected feature/target IDs to exclude benchmark-imputed compute without excluding a separate independent replacement.

Execution identity and the proposed Epoch crosswalk relation should be separate dimensions. A verified Instruct run can use explicitly ancestral base compute without asserting that the Instruct endpoint equals the base row. The current `same_executed_model` implication is too coarse for that future use. These are design limits of a bounded, held proposal, not evidence that any currently included analytical row is wrong.

## Rights and release boundary

This review made zero new rights-document requests. Prior scoped records support the identified Epoch CSV under CC BY 4.0 and the dedicated historical EvalPlus result repository under Apache 2.0. They do not extend to linked model weights, corpora, generated outputs or papers. Keep original retention, analytical admission and redistribution as separate decisions; no new public-release permission or completed release is claimed. Any later packaging must retain the applicable attribution/notices and changes.

## Smallest missing artifact

A compact publisher-authored **aggregate-to-run manifest** remains the highest-value scientific next artifact, conditional on verifying the supplied pre-cutoff feature sources. First scope it to StarCoder2-3B, -7B and -15B, HumanEval/HumanEval+ in A/B: 12 scalar assertions. Then extend to DeepSeek-Coder-6.7B-base and -33B-base: eight more assertions. This is at most five candidate labels and 20 publication-metric assertions, not a promise of five independent runs or 20 usable training rows.

For each snapshot/key/metric, require the requested selector and served snapshot or loaded revision, complete weight/tokenizer/config manifest identity, output-set digest, generation interval, task/prompt identity, scorer/harness revision, actual denominator, A→B relationship and first-public evidence or explicit unknowns. Existing local evidence does not contain such a manifest. Its absence from all upstream locations has **not** been established. No maintainer contact, archive/output download or acquisition was performed.

Before moving these five candidates toward training, verify the historical feature sources and apply executable semantic gates. Even a complete run manifest would not fix unsupported current citations, benchmark-imputed compute circularity or Code Llama stage disagreements.

## Deliverables

- `offline-data-validation.json`: integrity, native-value comparisons, counts, local clocks, arithmetic, static migration and source limitations
- `evalplus-slot-changes.json`: all 161 independently reproduced native scalar changes
- `repository-evidence.json`: ten local Git-blob matches and historical pin context
- `schema-review/`: full independent schema and negative-mutation results
- `next-actions.json`: only unresolved work, bounded and gated
- `followup-prompt.txt`: one bundled follow-up prompt; not launched
- Reviewer-authored offline source checker: retained privately; not packaged because its inputs include separate retained source bodies

This directory is a review handoff, not an applied repository overlay or a claim of canonical integration.
