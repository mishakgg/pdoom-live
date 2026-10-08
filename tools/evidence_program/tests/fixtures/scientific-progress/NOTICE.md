# Synthetic aggregate-ledger fixture

`synthetic-alab-ledger.json` is entirely self-authored test data. Its DOI
`10.0000/synthetic-alab-ledger`, reserved `example.invalid` URLs, identifiers,
locators and counts are fictional. It contains no source PDF, chemistry protocol,
structure, original experiment output or licensed third-party dataset. It is
not evidence for A-Lab or any real campaign.

The fictional historical target summary is 5/9. Its corrected target categories
are 3 successful, 1 inconclusive and 4 not obtained out of 8. The fictional
recipe summary is 9/24, a separate unit and denominator. Its remainder is not
classified. Elapsed duration is 6 days; dates and labor quantities are unknown
and remain null. These values deliberately differ from the manually curated
real review ledger.

## Offline contract and API

`validate_scientific_ledger.validate_ledger_bytes(raw)` validates UTF-8 JSON
bytes; `read_ledger(path)` opens a supplied bounded local regular file. Both
return review-only records. `LedgerInputError` is the rejection type. This is a
manually curated aggregate validator, not a PDF extraction adapter, collector,
canonical schema or admission mechanism. It does not establish source truth.

The input has exactly these top-level fields:

- `schema_version`: `alab-aggregate-ledger-v1`
- `input_kind`: `synthetic_fixture` or `manual_aggregate`
- `campaign`: one `doi`, `elapsed_days`, `start_date`, `end_date`,
  `researcher_hours`, `researcher_hours_saved`, `robot_active_hours`, `provenance`
- `records`: bounded observations of exactly three unique claims
- `corrections`: exactly one historical-to-corrected target edge

All five campaign date/labor fields are required nulls. Campaign elapsed days
measure duration, never researcher labor or savings. Each claim has `record_id`,
`observation_id`, `claim_kind`, `unit`, `status`, `counts`, and `provenance`.
Allowed claim kinds are `historical_target_summary` (targets, superseded),
`corrected_target_partition` (targets, current), and `recipe_summary` (recipes,
current). The first and last have `successful` and `denominator`; the corrected
target claim additionally has `inconclusive` and `not_obtained`. Only the target
partition must sum to its denominator. A correction has `from_record_id`,
`to_record_id`, `relation: "corrects"`, and `provenance`.

Each provenance list has 1–3 records with `source_url`, `source_doi`,
`claim_locator`, `capture_status`, and `artifact_sha256`. Source URLs match an
exact allowlist and source DOI. Synthetic records use `synthetic_fixture` capture
status. Real manual records preserve `text_observed_hash_unavailable` or
`indexed_primary_excerpt`. Hashes are required nulls: this contract does not
acquire or authenticate source artifact bytes. A hash of this ledger must never
be represented as a source artifact hash. A future bytes-backed capture contract
would need explicit review rather than inventing a digest here.

For real manual records the campaign DOI is fixed; each current claim requires
both the corrected primary PDF and the correction notice. The historical claim
requires the original primary PDF. Campaign duration requires the corrected PDF;
the correction edge requires the correction notice. Provenance strings are inert
untrusted text, retained for review and never executed or rendered as HTML.

The result has `campaign_count: 1`, a DOI `campaign_key`, normalized `records`,
and `current_records` sorted by `(unit, record_id)`. Equal repeated record and
observation identities collapse. Conflicting identity reuse is rejected, as is
an extra apparent version or any invalid correction chain. No extra arithmetic
explanation can become a fourth published claim. Reordering record observations
does not change the result.

The structural validator does not hard-code real counts. The separate scientific
catalog check must assert its reviewed real counts and locators without turning
those claims into synthetic fixture evidence. Output remains
`experimental_review_records_not_admitted` and explicitly labels producer
reanalysis, independent replication not established, novelty not necessarily
new to science, separate target/recipe denominators, and no recipe-remainder
inference. There is no novelty count, independent-replication count, labor-savings
claim, rate calculation or combined target/recipe success metric.

Limits: 64 KiB UTF-8 input, depth 12, 32 observation rows before deduplication,
3 provenance records per list, 2 KiB per decoded string, 80-character identifiers,
integer counts up to 1,000,000, duration 1–3,650 days. Unknown fields, duplicate
JSON keys, floating/nonfinite numbers, booleans as counts, invalid encodings,
unsafe URLs, symlinks and non-regular files fail closed. Filesystem mount locality
is not independently established; the validator itself performs no networking.

Run from the repository root:

    python -m unittest discover -s tools/evidence_program/tests -p test_scientific_ledger.py
    python tools/evidence_program/validate_scientific_ledger.py tools/evidence_program/tests/fixtures/scientific-progress/synthetic-alab-ledger.json
