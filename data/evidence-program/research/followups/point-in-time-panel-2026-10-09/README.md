# Point-in-time model-panel review, 9 October 2026

One research session, four supplied artifacts, twelve candidates, zero strict-ready candidates. This is an additive research package, not canonical training data, source admission or an enabled collector.

Start with [final disposition](final-disposition.json), [source corrections](source-corrections.json) and the [latest review](../../../../../docs/evidence-program/research/followups/point-in-time-panel-2026-10-09.md). Read [historical submitted files](submitted/README.md) separately from reviewer evidence in review/. The earlier offline review is retained as a historical stage; its source deferrals are superseded only where the latest review explicitly closes them.

## Package map

- submission-provenance.json: exact original and packaged hashes, sanitization, and issued-prompt identity limits
- submitted/: all four supplied artifacts, retaining the audit and schema JSON byte-for-byte; the examples contain eight explicitly documented locator redactions
- issued-assignment.txt: exact known issued prompt, not proof of executed input
- review/epoch-source-validation.json: archived 6,826,880-byte Epoch reparse, 3,626 rows, 57 fields, 192 raw-cell matches and 12 compute-note matches
- review/primary-source-evidence.json and primary-paper-verification.json: bounded 9/12 successful primary reads, three reader limitations, no execution binding
- review/offline-data-validation.json and evalplus-slot-changes.json: historical full native comparison, 24 selected objects/96 metric slots and all 161 changed slots
- review/validation-results.json, mutation-test-results.json and schema-review.md: shape checks and 41 negative probes, with 35 unsafe schema accepts
- review/replay_schema_checks.py: portable reviewer-authored offline replay; no source downloads or production admission
- next-actions.json and followup-prompt.txt: remaining evidence/design tasks only, not launched
- locator-redactions.json: affected field locations, reason and pre/post-copy hashes, without the original locator mapping
- NOTICE.md and licenses/: attribution and upstream-rights boundaries
- package-manifest.json: hashes for package files other than the manifest itself, including the linked review document

## Reproduce bounded schema findings

Run `python review/replay_schema_checks.py --output-dir /tmp/point-in-time-schema-replay` with Python and jsonschema installed, selecting a new output directory outside this package. The script parses supplied JSON as data, disables external reference resolution and leaves packaged inputs unchanged. It reproduces the 41 fixture-specific probes, not a complete domain validator, benchmark rerun or source-truth audit.

## Interpretation and rights

DeepSeek's 6ND values use disclosed 2T inputs with separate long-context accounting unresolved. StarCoder2 Table 6 already includes long-context. The scopes cannot be pooled as complete training totals. No aggregate row is bound to an executed model/service, output set, actual task/scorer manifest or denominator.

Raw publisher sidecars, private archive-transfer receipts and private locators are excluded. Unverified source-native Colab Drive links are replaced with stable SHA-256 locator tokens; locator-redactions.json records affected fields without publishing a URL mapping. Verified native-note comparisons refer to the private originals, not byte-identical public note text. Upstream rights and attribution remain scoped as documented in NOTICE.md; repository data licensing does not relicense third-party material.
