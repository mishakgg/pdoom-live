# Offline schema and semantic review

## Decision

The submitted proposal is structurally valid and internally conservative, but it is not an implemented analytical-admission gate. The Draft 2020-12 metaschema and examples both validate successfully. All 12 supplied candidates remain excluded from every strict analytical view. This supports retaining the bounded proposal for further work, not admitting any candidate into a training panel.

A reviewer-authored offline harness exercised all eight proposed acceptance specifications with **41 negative mutations**. The submitted schema rejects 6 and accepts 35 unsafe mutations. The bounded reviewer checks reject all 41. These are executed data/schema tests, not adapter, ingestion, production, model-execution, or upstream-source tests. The proposal already explicitly says its domain cases were not implemented, so the accepted mutations identify required work rather than refuting a claim of production enforcement.

## Scope and reproducibility

- Inputs: exact prompt byte range and all four originals named in the session-02 intake manifest. All four file sizes and SHA-256 digests match the manifest, and remain unchanged after testing. JSON duplicate keys were also checked; none found.
- Runtime: installed Python and `jsonschema 4.26.0`, `Draft202012Validator`, explicit `FormatChecker`. Schema references are all local; external resolution is disabled.
- Metaschema: pass. Examples without format assertions: pass. Examples with format checking: pass. Baseline bounded semantic checks: no errors.
- No uploaded code was executed. Only newly authored reviewer code ran. No network, provider, Drive, source retrieval, repository integration, original edits, or canonical schema changes occurred.
- Cross-file native-value checks use the audit's embedded extracts as their oracle. They establish agreement among supplied files only. They do not verify the Epoch CSV, EvalPlus upstream bodies, source dates, rights claims, or the claimed repository commit. The parent review may independently establish additional evidence; it is not included in this harness's claims.

Repository replay adaptation:

`python review/replay_schema_checks.py --output-dir /tmp/point-in-time-schema-replay` (from this package directory; choose a new output directory outside the checkout)

The JSON outputs include every mutation as explicit JSON Pointer replacements, schema errors, and reviewer check diagnostics. Synthetic IDs/timestamps in negative fixtures are not recovered facts.

## Baseline facts independently counted within the supplied examples

- 12 candidates in 4 families
- 24 snapshot objects and 96 metric slots: 76 numeric, 20 null
- 106 feature records; 19 flagged included by cutoff
- 0 strict-view inclusions; 0 executed checkpoint/service IDs; 0 known snapshot run IDs
- All 24 embedded native snapshot objects agree with the corresponding audit extracts, including four metric values, `link`, `open-data`, `prompted`, and `size`
- Current Epoch feature raw values agree with the six corresponding audit extract fields checked; native blank numeric fields stay null in their numeric interpretation
- Included feature clocks pass cutoff ordering under the declared source-value versus reconstructed-input interpretation
- The three DeepSeek 6ND calculations equal their referenced parameter/token values; referenced feature assertions resolve within the file
- Native nulls have missingness explanations; candidate, artifact, protocol, feature, and snapshot keys are distinct in the baseline
- The four conservative family blocks are retained. Baseline measurements are not relabeled as new inference or output reuse.

No actionable contradictory baseline scalar, null, cutoff inclusion, or strict-readiness result was found in these bounded checks. External evidence gaps remain.

## Eight-case results

| Submitted case | Executed negative tests | Schema rejects | Schema accepts unsafe | Finding |
|---|---:|---:|---:|---|
| PIT-01: alias/executed model | 3 | 1 | 2 | Unresolved identity blocks a strict flag, but executed IDs can be assigned while status remains alias-only; promotion of status/relationship/ID admits a strict view with null run/protocol evidence. |
| PIT-02: base/specialized/instruct | 3 | 0 | 3 | Rejected ancestry can become equivalence; base compute can become descendant total or ancestral scope can be relabeled total. |
| PIT-03: revision identity | 1 | 0 | 1 | A documentary ID and future inspected revision can be labeled exact historical execution without a run manifest. |
| PIT-04: corrections/runs/protocol | 5 | 0 | 5 | New-inference and regrade labels, documented-run status, and actual denominators can be asserted with null execution evidence. Zero denominators and unrelated metric keys are accepted. |
| PIT-05: null/blank/uncertainty | 8 | 2 | 6 | Required metric slots and 0–100 ranges work; native null preservation, blank handling, missing-reason consistency, and uncertainty provenance do not. Empty-string raw values can satisfy the included-value gate. |
| PIT-06: time/information sets | 10 | 2 | 8 | A missing required availability string is rejected, but future availability, reversed intervals, historical-as-prospective flags, broken dependency references, and incorrect 6ND arithmetic pass. |
| PIT-07: benchmark-imputed compute | 1 | 0 | 1 | An independent-compute view can be ready with only benchmark-imputed eligible compute, after synthetic identity/timing promotion. |
| PIT-08: duplication/dependence | 10 | 1 | 9 | Identical whole snapshots are rejected, but duplicate logical keys, nonidentical duplicate slots, artifact reimports, missing protocol links, repeated decisions, and broken family grouping pass. |

The tests are deliberately selected counterexamples. The acceptance rate is not a coverage or quality percentage.

## Actionable enforcement gaps

### 1. Analytical readiness is a label gate, not an execution-evidence gate

Pointers: `/$defs/candidate/allOf`, `/$defs/candidate/properties/identity`, `/$defs/snapshot`, `/$defs/protocol`.

Tests 01b, 01c and 03a show that the schema does not constrain non-exact identities to a null executed ID. Its strict inclusion implication checks only identity status, relationship, nonempty ID, and an evidence array of at least one string. It does not require run, output, execution time, actual protocol, complete loaded-artifact identity, or evidence that binds those fields. Test 04d permits `actual_run_documented` with every actual-run field null.

**Fix before analytical admission:** separate documentary identity from verified execution assertions; have a semantic gate resolve evidence to the selected run/output/protocol and loaded artifact or served API snapshot. Add schema implications for easy consistency requirements, including contradictory identity status and documented-run/null combinations. Do not invent evidence simply to satisfy fields.

### 2. Cutoff claims need cross-field temporal checks

Pointers: `/$defs/time`, `/$defs/feature/allOf`, `/$defs/snapshot/allOf`.

Format assertions test date syntax, not ordering. Tests 06a–06d admit 2026 citation/feature/input availability under a 2024 cutoff, and `earliest > latest`. Test 06e permits A's `repository_chronology_only` label to be prospective; 06f permits B to be labeled proven while result availability remains unknown. Tests 06i–06j leave nonempty but nonexistent input references or a wrong computed result.

**Fix:** validate bounds, clock selection, input reference resolution, derivation arithmetic and chronology externally. Require known cutoff provenance for a proven label, preserve the repository-chronology assumption explicitly, and select historical versus hindsight assertions per analysis. Format checking must be explicitly enabled in the chosen validation runtime.

### 3. Actual denominators and revision mechanisms are freely assignable

Pointers: `/$defs/protocol/properties/actual_run_binding`, `/$defs/protocol/properties/evidence_status`, `/$defs/snapshot/properties/revision_relationship`.

Tests 04a–04e permit new inference without run/output/time, regrading without output identity, copied nominal 399-task counts as actual denominators, zero denominators, and an unrelated metric key. Merely requiring a positive integer still would not establish a real denominator.

**Fix:** require per-assertion or per-run task-manifest/scorer evidence and constrain denominator metric keys. Regrading needs documented reused outputs; new inference needs an execution record. Preserve unknown values rather than filling them from the benchmark declaration.

### 4. Native preservation and uncertainty need immutable-source comparisons

Pointers: `/$defs/snapshot/properties/source_pass_at_1_percent`, `/$defs/snapshot/properties/missing_reasons`, `/$defs/quantity`, `/$defs/feature/allOf`.

Tests 05a–05e accept null-to-zero, forward-fill, notes-to-native-cell replacement, unsupported numeric confidence, and missing null explanations. Test 05h exposes a local shape loophole: `raw: ""` passes the included-feature gate's non-null check even though point/bounds are null.

**Fix:** compare native slots/raw cells with retained exact-source data; keep explicit derived assertions separate. Enforce value/reason consistency, nonempty admitted strings, coherent uncertainty fields and ordered bounds. Do not derive a statistical interval from a qualitative label.

### 5. Independent-compute eligibility has no feature-selection link

Pointers: `/$defs/candidate/properties/decisions`, `/$defs/feature/properties/provenance`.

Test 07a makes an independent-compute decision ready while its only admitted compute is explicitly `benchmark_imputation`. Its synthetic pre-cutoff date demonstrates that temporal availability does not eliminate circularity. The current model contains no per-view selected-feature IDs, so it cannot state which compute assertion is actually used.

**Fix:** make each analytical view select explicit feature/target assertion IDs and apply provenance and scope rules to those selected assertions. A candidate-level block on any preserved imputed feature would be too broad if an independently evidenced replacement also exists. Preserve both, select only the independently valid one.

### 6. Logical uniqueness, references, and dependence require a real key model

Pointers: candidate `snapshots`, `features`, `decisions`, `dependencies`; top-level `artifact_records` and `protocol_records`.

`uniqueItems` rejects identical snapshot objects, not repeated `(candidate, artifact, metric)` slots with a changed field. Other arrays also lack key uniqueness. Tests 08a–08j demonstrate these distinctions. Family grouping is stored as unconstrained strings, not enforced against known ancestry components.

**Fix:** validate unique logical keys and foreign keys; deduplicate content identity while retaining receipt/location provenance; form connected dependency components before splitting. Use explicit assertion/run keys without treating an unknown run ID as a common run.

## Modeling limitations to address next

1. **Shared estimate representation:** J07 and J08 each carry the same 8.04e22 6ND estimate with their own self-scoped input dependency IDs. Their common `shared-base-pretraining:deepseek-coder-6.7b` hard group and family group preserve grouping, so this is not demonstrated split leakage. It does not yet implement rule G6's “represent reused compute once” literally. Introduce a shared estimate assertion ID with base/pretraining scope and let the descendant reference it as ancestral compute.
2. **Candidate versus view/metric granularity:** one candidate-level decision covers two snapshots with four metrics each, while a snapshot has a single nullable `evaluation_spec_id` although HumanEval and MBPP have separate declared protocols. The present held examples are valid, but partial future admission needs per-metric assertion bindings and explicit selections. Do not require or silently imply that resolving one StarCoder2 HumanEval assertion validates all eight slots.
3. **Execution versus crosswalk relation:** every strict view currently requires `identity.relationship == same_executed_model`. This combines verified execution identity with the relationship to the Epoch row. A genuinely executed instruct model could use explicitly ancestral base compute without claiming endpoint equivalence. Resolve these as separate dimensions before admitting legitimate ancestry-scoped features.
4. **Bounded proposal, not reusable production schema:** the fixed cutoff/commit and four family enum are appropriate for this example packet, but no general adapter contract or production enforcement is supplied.

## Smallest safe next implementation step

Under separate engineering authorization, implement a noncanonical assertion-level adapter and semantic validator over retained immutable sources, with these negative fixtures as regression tests. Keep all current strict views held. The publisher aggregate-to-run manifest proposed by the research remains the smallest evidence artifact likely to unlock selected base-model assertions; a stronger schema cannot manufacture that missing provenance.

## Files

- `validate_offline.py`: new reviewer-authored harness
- `validation-results.json`: baseline, hashes, counts, runtime, case summary, and evidence boundary
- `mutation-test-results.json`: all 41 explicit patches and observed validator results
- `SCHEMA-REVIEW.md`: this review
