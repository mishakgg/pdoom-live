# Full-content intake review: 9 October 2026

## Decision

Accept this one-session submission as qualified research only. The sanitized candidate is not published or operationally approved. It does not establish acquisition readiness. All eight proposed acquisition cases remain unexecuted. The companion schema passes structural checks but accepts twelve unsafe semantic mutations, so it must not serve as a production admission gate.

The existing ESPAI v3 PDF identity was separately reconciled against its retained copy: 5,902,763 bytes, SHA-256 `8a440d9f5c24e3627b2887c4b654f8b98253706a92e8e4ece266f8c2fe9903a7`. This is archive identity reconciliation only. No new source manuscript was acquired, present arXiv byte equality was not established, and no additional independent-study credit follows.

## Package and provenance

The companion [data package](../../../../data/evidence-program/research/followups/full-content-intake-2026-10-09) accounts for all eight supplied artifacts: narrative, specification, schema, ledger, cases, metadata body, metadata receipt and submitted validation summary. Originals remain preserved separately; public copies disclose sanitization and retain original/candidate hashes. The known issued assignment is not proof of the exact launched session input. The referenced ZIP and separate README were not supplied.

Submitted artifacts are historical claims. The final disposition and review addenda take precedence for interpretation without rewriting the submission. The original 26-session queue and older three-followup bundle counts are unchanged. This is one additional separate research session.

## Verified source findings

### FCI-SV01: Exact ESPAI v1 and v3 rights and links

Both exact-version pages link CC BY 4.0, their matching vN PDF and matching vN source. Submission times are 2024-01-05T14:53:09Z and 2025-10-08T18:38:53Z. No manuscript or source package was requested. [FCI-P01](https://arxiv.org/abs/2401.02843v1), [FCI-P02](https://arxiv.org/abs/2401.02843v3)

Review action: Retain exact edition identifiers and rights evidence. Keep source-package transport and member-level exceptions unresolved; do not extend paper rights to separately linked assets.

### FCI-SV02: Generic citation metadata loses exact version

All three checked version pages expose an unversioned citation_pdf_url, while visible PDF and source hrefs retain the requested vN. [FCI-P01](https://arxiv.org/abs/2401.02843v1), [FCI-P02](https://arxiv.org/abs/2401.02843v3), [FCI-P03](https://arxiv.org/abs/2310.19852v1)

Review action: Use the exact-version href. Add a rejection test for silent latest-version substitution; a versioned landing URL alone does not pin the generic metadata URL.

### FCI-SV03: CN017 v1 has a different rights basis

2310.19852v1 links arXiv nonexclusive-distribution 1.0, not CC BY. Its later v2-v6 history does not establish those versions’ rights. [FCI-P03](https://arxiv.org/abs/2310.19852v1)

Review action: Preserve the exact v1 rights classification. Research-private storage relies separately on the parent-verified arXiv terms; public serving remains uncleared.

### FCI-SV04: Uploaded OpenAlex response independently reproduced

The preprint-DOI GET returned W4414876758 with canonical JAIR DOI 10.1613/jair.1.19087. The new 18,977-byte response matches the uploaded SHA-256 exactly and still lists three locations plus PDF/TEI cache flags. [FCI-P11](https://api.openalex.org/works/https://doi.org/10.48550/arXiv.2401.02843)

Review action: Keep both observation receipts and their separate timestamps. Count this as one research metadata read, no new lineage, manuscript acquisition or corpus admission.

### FCI-SV05: A Work record does not bind a cached edition

OpenAlex selects the published DOI and ranks OA locations; Work updated_date includes metadata changes such as citation counts. Its fulltext documentation explicitly disallows archive-object matching via locations[].pdf_url. PDF and TEI use distinct UUIDs. [FCI-P04](https://help.openalex.org/access/fulltext/), [FCI-P05](https://help.openalex.org/data/works/attributes/), [FCI-P11](https://api.openalex.org/works/https://doi.org/10.48550/arXiv.2401.02843)

Review action: Keep cached PDF, TEI, JAIR copy and exact arXiv editions distinct. Require actual object/version/rights binding before content admission; Work-level cc-by metadata is insufficient for exact-edition attribution.

### FCI-SV06: Cache availability and access remain separate

Current docs require an API key for per-file content; complete archive sync is a paid service. OpenAlex adds no content rights. Its daily content manifest maps Work IDs to separate object UUIDs, but no manifest row or cached body was inspected. [FCI-P04](https://help.openalex.org/access/fulltext/), [FCI-P07](https://help.openalex.org/access/snapshot/)

Review action: Keep cached objects held. No credentials, content endpoint, paid access or sync was attempted. TEI remains a derived representation and is not proof of complete original text.

### FCI-SV07: Metadata grant and lifecycle are distinct from original retention

OpenAlex metadata is CC0. The public metadata snapshot overwrites previous state; the works deletion ledger is replaced rather than append-only. The same Sync page both permits rare restoration and describes deletion as final. [FCI-P06](https://help.openalex.org/access/sync/)

Review action: Keep source statements and uncertainty together. Track metadata merges/removals without treating them as manuscript withdrawal, copyright revocation or a destruction instruction. Do not propagate mirror-delete instructions to the original archive.

### FCI-SV08: Published aggregate counts are unsuitable denominators

Snapshot documentation gives September examples of about 327M default and 476M all works; the October quick reference gives about 324M core plus 193M expansion. Neither is a measured relevant-work population or inspected manifest. [FCI-P07](https://help.openalex.org/access/snapshot/), [FCI-P08](https://help.openalex.org/api/llm-quick-reference/)

Review action: Preserve dated examples without reconciling them by arithmetic. Freeze selection-specific IDs, corpus, filters and observation interval before completeness claims.

### FCI-SV09: Cursor documentation gap narrowed

Official paging documentation is now inspected: per_page supports 1-100; 200 is deprecated legacy behavior. Basic page×per_page cannot exceed 10,000. Cursor traversal starts with * and follows next_cursor until null with empty results; whole-corpus cursor harvesting is discouraged. [FCI-P12](https://help.openalex.org/api/paging/)

Review action: Replace “cursor documentation uninspected” with “documentation verified, bounded paginator and completeness behavior unexecuted.” No live paging sequence was run.

### FCI-SV10: MIT data-specific grant and publisher links

The official risks page expressly grants CC BY 4.0 for MIT AI Risk Initiative data, and still advertises the same Google Sheets copy and OneDrive full-database links. The page describes source metadata, quotation/page evidence and taxonomy mappings. [FCI-P09](https://airisk.mit.edu/risks)

Review action: Attach the grant to initiative/database data. Do not extend it to complete cited papers. Keep publisher-advertised location separate from successfully retrieved workbook.

### FCI-SV11: MIT complete native export remains unverified

Neither linked workbook was retried. Uploaded MIT-E03/E04 report tool-side authentication redirects; they establish neither origin HTTP 500 nor universal anonymous-access failure. Current landing-page access succeeds, but native bytes, media type, sheet coverage, revision and mirror equivalence remain unknown. [FCI-P09](https://airisk.mit.edu/risks)

Review action: Retain the native-export hold. Preserve historical access observations with their original dates and null origin HTTP status; do not convert a tool error into a server-status claim.

### FCI-SV12: MIT release announcement does not pin the live workbook

Version 4 is announced on 2025-12-04. The current risks page advertises 1700+/74 while its FAQ and the release page retain 1600+/65 context. These are inconsistent population labels, not verified export counts. [FCI-P09](https://airisk.mit.edu/risks), [FCI-P10](https://airisk.mit.edu/blog/repository-update-december-2025)

Review action: Record the release announcement separately from native workbook identity. Do not assign version 4 or a complete row denominator to a mutable linked workbook without binding evidence.

### FCI-SV13: ESPAI v3 retained-copy reconciliation is now satisfied

The parent’s separate 16:04:12 readback report verifies the existing v3 original at 5,902,763 bytes with historical SHA-256 8a440d9f5c24e3627b2887c4b654f8b98253706a92e8e4ece266f8c2fe9903a7. It reports unchanged original metadata/revision and no source-dataset request.

Review action: Narrow the proposed retained-tranche follow-up: v3 re-download/reconciliation is unnecessary for identity. This is retained-copy reuse, not a newly acquired source body or proof of present arXiv PDF-byte equality.

### FCI-SV14: Companion schema remains research-only

The separate offline review passes the supplied ledger and schema checks but demonstrates twelve semantic enforcement gaps. All eight submitted acquisition acceptance cases remain unexecuted.

Review action: Admit the schema/specification/cases only as proposed research artifacts. Runtime admission must wait for invariant hardening and executed positive/negative tests; do not present standards compliance as production readiness.

## Operational blockers

1. P0: Separate proposed retention eligibility from completed source acquisition, destination commit/readback, analytical inclusion and publication.
2. P0: Bind each affirmative rights decision to an applicable object/edition/use grant and resolving evidence. Private research permission is not public redistribution permission.
3. P1: Enforce content-state, representation and coverage transitions. Historical, partial, blocked and newly observed bytes must remain distinct.
4. P1: Require unique IDs, closed references, derived counts, canonical study mapping, exact version/URL binding and evidence chronology.
5. P1: Pin working format validation and build executable fixtures. A nominal FormatChecker did not provide optional URI/date-time checking in the reviewed runtime; explicit tested checks supplied those checks.

The offline review ran 28 supplied-data check groups and 18 synthetic schema probes: six unsafe controls were rejected and twelve semantic mutations were accepted. These probes do not execute ACQ-01–ACQ-08, nor establish that the populated submission itself makes the mutated false claims. All eight case expected outcomes were statically reviewed; no definite contradiction was found. ACQ-05/06 need explicit lawful-access, object-grant, transfer and destination commit/readback preconditions before operational use.

## Remaining route holds

- OpenAlex: bounded selected-population enumeration is unexecuted; cached object UUID, edition, applicable grant and access remain unresolved.
- arXiv: native-source transport, container membership, member-level exceptions and all-version manifest coverage remain unresolved. Exact-page rights do not remove an access restriction.
- MIT: no native workbook bytes, media type, row/sheet/notes coverage, immutable revision or mirror equivalence were verified. Page-level data rights do not grant rights in cited full papers.

## Bounded next steps

The four prompts in followup-prompts.json cover offline invariant hardening, finite OpenAlex enumeration, newly evidenced permitted native routes, and sequential additive repository integration. Each has an activation gate and stopping condition. Do not repeat completed archive-identity, exact landing-rights, singleton metadata, MIT grant or paging-documentation checks simply because the original intake listed them as open.

## Integration boundary

Only new research documentation/data paths are proposed. Current main, collector state, canonical contracts, external storage and publication are unchanged. A later single authorized writer must recheck the current base, apply the additive package, update the current index/queue without count inflation, run repository aggregate checks and obtain independent integration review. Sanitized packaging is not proof of live integration compatibility.
