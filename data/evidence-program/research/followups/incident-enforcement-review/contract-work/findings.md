# Batch G native-contract review

## Result

This is a research mapping, not an adapter or native admission. The immutable ledger's 20 artifact entries (18 inspected, 2 failed retrievals), 43 attributed assertions and 7 source chains are covered. No source-native record was converted, imported, or admitted.

The current repository snapshot is `mishakgg/pdoom-live@aff815147b12235177da9f66f4c09c2c1508f3eb`. Ten narrowly required files were fetched through the GitHub connector and verified against their returned Git blob SHA. Their byte lengths and SHA-256 hashes are in [repository-file-manifest.json](repository-file-manifest.json).

## Material contract boundaries

- The repository contains two distinct layers. Proposed pdataset 0.1.0 supports source artifacts, organizational actors, attributed statements, incidents and resource observations. It is explicitly a design/validation prototype, not the production importer.
- Current production `statementSchema` requires `person_slug`. Its organization-capable participant record does not remove that requirement. OPC, FTC, CAC, court and respondent institutional assertions cannot be imported directly by inventing a person.
- A source artifact, a source assertion, a harmful event, a legal instrument, a remedy requirement, an operator compliance claim and an independently assessed outcome are different units. Document count is not event count; official hosting is not independent verification.
- Proposal incident fields require deliberate event taxonomy, curated deduplication, verification, causation and severity-rubric choices. Empty subject references are permitted, but they do not make anonymous events resolved. Resource observations require a measured subject; the regulator must not be inserted simply to satisfy that field.
- An `other` resource category and generic measurement shape do not justify treating enforcement activity as resource or incident incidence. Native metric/scope prose can retain context, but there are no typed numerator-denominator or cohort-link objects.
- The input supplies retrieval calendar dates, not verified capture instants for every artifact. Required system UTC timestamps cannot be fabricated from midnight or publication. Signature, filing, issuance, effective, completion, listing, retrospective coverage and technical packaging dates cannot be losslessly compressed into one event time.
- Native statement relationships and evidence relations are small enums. Legal supersession, republishing, compliance-with, source-local case identity, unresolved conflicts, indexing candidates and cohort overlap need preserved research sidecars. Legal supersession is not a record revision link.
- Rights remain scoped by artifact and component. The submitted session did not inspect OPC's linked licence version; the current INM003 catalog independently retains its scoped CC-BY-3.0-NZ declaration, which this review does not downgrade. Third-party material remains excluded. FTC policy does not clear respondent filings or an entire mixed court package. Chinese publisher copyright and source credit establish no affirmative reuse grant. Source-text inspection is neither named-human review nor publication clearance.

[contract-mapping.json](contract-mapping.json) contains 19 field groups, per-artifact and per-assertion dispositions, actor boundaries, all seven chain reviews and eight explicit semantic-gap categories. It retains source-native dates, legal authority, qualifiers, units, unknowns, provenance, rights and dependence without claiming lossless automatic conversion.

## Separate offline probes

[synthetic-probe-input.json](synthetic-probe-input.json) contains 32 wholly invented fixtures, separate from every original acceptance case and research assertion. The local runner used installed jsonschema 4.26.0, Draft 2020-12, FormatChecker and an offline registry against the pinned main schema plus five type wrappers.

[schema-probe-results.json](schema-probe-results.json): 16 shapes accepted, 16 rejected, all 32 expectations matched. No external schema resolution or network request occurred during the probes.

This is structural-only evidence. Deliberately misleading fictional confirmation, causality and order-to-completion claims can pass shape validation. Unknown rights with eligible publication, missing human reviewers, wrong reference targets, cross-record supersession and reversed ranges also demonstrate that the standalone schema is not the full validator.

The repository validator was read, not imported or executed. Its additional rights, reviewer, reference, revision, temporal, unit and translation checks are static code-inspection findings documented in [validator-inspection.json](validator-inspection.json). The production TypeScript validator and its helpers were not executed.

All original 20 acceptance cases remain `not_executed`, with null runtime results. [original-acceptance-preservation.json](original-acceptance-preservation.json) records that unchanged state. No assertion of runtime acceptance, legal correctness, fact verification, causal validity, completed remediation or native readiness follows from these probes.

## Deliverables

- [Contract mapping](contract-mapping.json)
- [Probe inputs](synthetic-probe-input.json), [probe results](schema-probe-results.json); the offline runner remains local reviewer support
- [Pinned repository file manifest](repository-file-manifest.json)
- [Static validator inspection](validator-inspection.json)
- [Original acceptance preservation](original-acceptance-preservation.json)
- The parent publication manifest binds the public files; staging integrity and pinned source copies remain local reviewer support.
