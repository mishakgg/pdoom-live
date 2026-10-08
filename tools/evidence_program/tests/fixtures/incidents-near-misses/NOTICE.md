# NHTSA publication-correction manual ledger

This fixed, manually curated JSON ledger records exactly two agency-authored publication-correction facts from the National Highway Traffic Safety Administration (NHTSA) Standing General Order 2021-01 data dictionary. It is not source PDF bytes, crash-report CSV data, a PDF parser fixture or an independent new evidence collection.

## Attribution and provenance

Source: https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/SGO-2021-01_Data_Element_Definitions.pdf

The inspected PDF contains 33 physical pages. Its edition date, printed on page 1, is September 15, 2026. Both correction facts are in Table 1 on physical page 4:

- August 27, 2026: correction of a wrongly associated narrative for report 34952-11803, version 1, caused by internal processing. No before or after narrative is included.
- June 15, 2026: restoration of reports received on or before April 15 that processing had omitted from the May 15 publication. The June 15 row references the update in the May 15 row. This is a publication-completeness correction; it does not add crash records.

The full PDF was separately acquired for private verification on 2026-10-08T08:24:05.902306+00:00. Its original 529128 bytes have SHA-256 c92e1bec238e757867d67ea5bf0b26f4a3e9223d0b92a9a7ce76d446518f4fa4. The HTTP Last-Modified timestamp was 2026-09-15T12:30:24Z. None of these clocks is the correction date. The source PDF is not redistributed here. The manifest's fixture hash instead hashes this manually curated JSON ledger.

Both claims already appear in the repository's ASI005-F04 finding, using artifact asi005_dictionary in source family nhtsa-automated-driving and chain ASI-R02. The two more granular assertion IDs preserve that link. They add zero independent evidence and zero events.

## Rights and privacy

This ledger retains factual identifiers and manually normalized facts from agency-authored documentation. The government-work scope of 17 U.S.C. §105 is the stated basis: https://www.govinfo.gov/content/pkg/USCODE-2024-title17/html/USCODE-2024-title17-chap1-sec105.htm . Agency hosting alone does not give a reuse grant for manufacturer-authored submissions, narratives or attachments. Such a grant was not established. The repository's software or data license is not substituted for source-material rights.

No manufacturer narrative bodies, names, VINs, addresses, contacts, clinical details, injury quantities, inferred engagement, causal conclusions or rates are retained. Prior corrected content was not captured and remains unavailable. Its text is never reconstructed.

## Reader and tests

Run from the repository root:

- python tools/evidence_program/read_nhtsa_corrections.py tools/evidence_program/tests/fixtures/incidents-near-misses/nhtsa-publication-corrections.manual.json
- python -m unittest discover -s tools/evidence_program/tests -p test_incident_corrections.py -v

The reader is offline, read-only and limited to these two correction identities in May–September 2026. It validates a manual JSON structure, not the original PDF, landing page or arbitrary source documents. Maximums are 64 KiB per ledger, eight snapshots, JSON depth eight, 512 nodes and 512 UTF-8 bytes per string. Exactly two correction records are required in each snapshot; unsupported input produces an explicit error rather than silently filtered output.

Replay preserves supplied earlier assertion revisions and their captured-content availability, even under an unchanged report ID/version. Equal bytes are idempotent. A supplied changed source hash creates a different artifact revision; unknown hashes remain null, and metadata fingerprints must not be read as evidence that source bytes changed. New retrieval clocks alone do not create new assertion revisions. Non-fixture source metadata is caller supplied and unverified. No input is operationally admitted, and the reader never writes canonical data.

The fixed curated acceptance tests are separate from synthetic/adversarial mutation tests. Invented hash changes and private-capture metadata used by mutation tests are not claims that those historical artifacts exist. Directory-local .gitattributes forces LF for the byte-pinned fixture. A regression test performs an actual local git index checkout with core.autocrlf=true and verifies the hashes afterward. Tests never fetch the PDF or run source instructions.
