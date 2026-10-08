# Concentration and shared dependencies research

Sources reviewed 8 October 2026 against main `3a981281b59c91d29dd1b5157dfd90eac087c004`. Both [source priorities](../source_priorities.md) and the [64-family inventory](../../../data/evidence-program/source_inventory.json) were inspected at that revision. All five collections below are proposed new families relative to that register. CD IDs are provisional research identifiers; no inventory IDs, source admissions or frozen contracts change.

The [native catalog](../../../data/evidence-program/research/concentration-dependencies.json) contains five collections, 28 artifact references, 23 qualified findings, eight corrections, completed bounded work and seven focused follow-ups. The only new vendored source body is one 3,532-byte generated deps.dev graph, explicitly licensed CC BY 4.0 and isolated from `data/` and its CC0 dedication. Its fixed-fixture offline structure reader is implemented; ATRS semantic extraction remains an unimplemented proposal.

## Review outcome

Ranked by evidence utility: (1) UK ATRS for named deployment-role disclosures, (2) deps.dev for version-keyed resolved software structure, (3) Bank/FCA for concentration within defined provider-nomination responses. This ranking is not a risk ranking or a redistribution-readiness score. OMB product-use disclosures and FTC economic/contractual findings add complementary, separately qualified evidence.

## Relationship and inference boundaries

| Evidence class | What the source can support | What does not follow |
| --- | --- | --- |
| Ownership/economic rights | Explicit equity, profit or control disclosure | Investment amount alone is not an ownership percentage or operational dependence |
| Contractual access | Staff-qualified obligation or disclosed access arrangement | Access or spending commitments do not measure actual utilization |
| Disclosed operational use | Organization-reported deployment or product role | Publication is not verified present state, traffic share or criticality |
| Resolved software dependency | Package-version nodes and directed indexed requirement edges | Resolution is not installed production software or remote-service use |
| Survey concentration | Provider nominations within the stated survey/question | No workload, spend, compute or market share without that denominator |

Missing edges remain unknown. Several provider names do not prove independent failover. Source copies, joint publications and API/export representations share underlying evidence; repeated publication is not independent confirmation. No concentration-to-failure-probability or p(doom) conversion is supported.

GL003 remains the existing facility-level ownership/user enrichment target. GL014–GL016 entity matches do not subsume deployment or FTC study evidence. GL034 synthesis overlap requires evidence trace-back, not a second independent observation. No new inventory IDs allocated.

## CD001 UK Algorithmic Transparency Recording Standard deployment records

Named deployment-role disclosures with explicit phases, scoped supplier flags and consequential unknowns.

Coverage: First pilot reports published June 2022; official October 2022 RTAU blog confirms this. Current registry contains dated records but is not a complete historical panel.

Updates: Event-driven updates for substantive changes, including pilot-to-production; no fixed publication cadence verified.

Access/export: Public HTML inspected. Record-level JSON export unverified; no registry collector or automatic semantic extractor.

Rights: OGL v3.0 record text with exceptions; proprietary models, operational data and linked works excluded. Contains public sector information licensed under the Open Government Licence v3.0; cite each source record and responsible public body.

### Observed sample or schema

These are bounded research facts/schema examples, not admitted operational records.

[cd001_newcastle](https://www.gov.uk/algorithmic-transparency-records/newcastle-city-council-aws-contact-centre-services-amazon-q-and-contact-lens): Separate reported roles; no corporate ownership, conflict, current support or measured workload inference.

```json
{
  "from_publishers_raw": [
    "Cabinet Office",
    "Department for Science, Innovation and Technology",
    "Government Digital Service"
  ],
  "template_organization_raw": "Department for Science Innovation and Technology",
  "body_operational_owner_raw": "Newcastle City Council",
  "phase_raw": "Production",
  "atrs_version": "v4.0",
  "relationships": [
    {
      "dependency_name_raw": "Amazon Web Services",
      "role": "cloud_hosting_and_hosted_ai_service",
      "basis": "organizational_deployment_disclosure",
      "locator": "1.4.3 and 4.1.1"
    },
    {
      "dependency_name_raw": "PwC",
      "role": "implementation_support",
      "basis": "organizational_deployment_disclosure",
      "locator": "1.4.3",
      "temporal_qualifier": "supported design, configuration and initial implementation; current ongoing support not inferred"
    },
    {
      "dependency_name_raw": "Azure AD SSO",
      "role": "identity_service",
      "basis": "organizational_deployment_disclosure",
      "locator": "4.1.1"
    }
  ],
  "model_version_normalized": null,
  "model_version_missing_reason": "provider_managed_not_exposed_to_reporting_body"
}
```

[cd001_redbox](https://www.gov.uk/algorithmic-transparency-records/dsit-redbox): Mixed family/version-like product labels, not verified checkpoint identifiers. Do not normalize Gemini to a specific version or infer traffic per model. Retain fields with source-specific labels. Do not choose one, call either the deployment start, or infer an explanation for the difference.

```json
{
  "phase_raw": "Beta/Pilot",
  "supplier_involvement_raw": "No",
  "publication_fields": {
    "page_published": "28 April 2025",
    "body_date_published": "29 April 2025",
    "jsonld_datePublished": "2025-04-28T19:31:09+01:00",
    "jsonld_dateModified": "2025-04-28T19:31:09+01:00"
  },
  "model_labels_raw": "GPT-4o, GPT-4o-mini, Claude-3 Sonnet, Claude-3 Haiku, Gemini"
}
```

### Findings with evidence

- **CD001-F1** (disclosure): The collection displayed 152 records on 8 October 2026. No denominator for all deployments, organizations, spending or vendors is supplied. [cd001_collection](https://www.gov.uk/algorithmic-transparency-records)
- **CD001-F2** (disclosure): Newcastle discloses AWS hosting/AI services, PwC initial implementation support and Azure AD SSO, in a Production record published 13 August 2026. These are reported roles. PwC ongoing support, measured usage and deployment start are not inferred; unexposed provider-managed model versions remain null. [cd001_newcastle](https://www.gov.uk/algorithmic-transparency-records/newcastle-city-council-aws-contact-centre-services-amazon-q-and-contact-lens)
- **CD001-F3** (disclosure): Newcastle has publisher bodies, a top-level Organisation value and a body accountable-organization value that differ. Preserve all three raw fields and roles. Difference alone does not establish a same-concept contradiction, quality defect or corporate ownership. [cd001_newcastle](https://www.gov.uk/algorithmic-transparency-records/newcastle-city-council-aws-contact-centre-services-amazon-q-and-contact-lens)
- **CD001-F4** (disclosure): Redbox is Beta/Pilot and combines an external-supplier-involvement answer of No with AWS hosting, shared provider-account access and Google/Anthropic/OpenAI model access. The supplier field has its own scope. Model availability is not traffic allocation or verified independent failover; mixed family/version labels are not pinned checkpoints. [cd001_redbox](https://www.gov.uk/algorithmic-transparency-records/dsit-redbox)
- **CD001-F5** (disclosure): Redbox page Published is 28 April 2025, body Date published is 29 April 2025 and JSON-LD publication/modification dates are 28 April. Retain source labels without choosing a date or inventing a deployment-start date. The February 2025 user-count date applies only to that statement. [cd001_redbox](https://www.gov.uk/algorithmic-transparency-records/dsit-redbox)
- **CD001-F6** (documentation): First pilot reports published June 2022; official October 2022 RTAU blog confirms this. Current registry contains dated records but is not a complete historical panel. Event-driven updates for substantive changes, including pilot-to-production; no fixed publication cadence verified. This is a changing disclosure registry with variable scope/detail, not a complete historical deployment panel. [cd001_history](https://rtau.blog.gov.uk/2022/10/10/developing-the-algorithmic-transparency-standard-in-the-open/), [cd001_guidance](https://www.gov.uk/government/publications/guidance-for-organisations-using-the-algorithmic-transparency-recording-standard/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies)

### Artifact verification

| Artifact | Inspection/access | Rights status and scope |
| --- | --- | --- |
| [cd001_collection](https://www.gov.uk/algorithmic-transparency-records) | `primary_opened`. Collection displayed record count. Count inspected at review date; population denominator absent. | `unknown`; this_artifact_only_no_inheritance |
| [cd001_newcastle](https://www.gov.uk/algorithmic-transparency-records/newcastle-city-council-aws-contact-centre-services-amazon-q-and-contact-lens) | `primary_opened`. Tier 2 sections 1.1, 1.4.3, 4.1.1, 4.2.2 and page metadata. Public HTML and distinct role/date fields inspected. | `declared_license` (OGL-3.0); published_record_text_only_with_exceptions |
| [cd001_redbox](https://www.gov.uk/algorithmic-transparency-records/dsit-redbox) | `primary_opened`. Sections 1.4, 2.4, 3.3, 4.1.1, 4.2.7 and publication fields. Public HTML inspected; mixed model labels and multiple publication fields preserved. | `declared_license` (OGL-3.0); published_record_text_only_with_exceptions |
| [cd001_history](https://rtau.blog.gov.uk/2022/10/10/developing-the-algorithmic-transparency-standard-in-the-open/) | `primary_opened`. Pilot-history account. Official retrospective publication inspected. | `unknown`; this_artifact_only_no_inheritance |
| [cd001_guidance](https://www.gov.uk/government/publications/guidance-for-organisations-using-the-algorithmic-transparency-recording-standard/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies) | `primary_opened`. Update guidance and organizational scope. Event-driven update guidance inspected; no fixed census cadence established. | `unknown`; this_artifact_only_no_inheritance |
| [cd001_ogl](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | `primary_opened`. OGL v3.0 link in record footers. License pointer and record attribution requirement inspected. | `unknown`; this_artifact_only_no_inheritance |

Duplicate-evidence treatment: Multiple department relationships in one record share an origin. Copies/reposts are not independent confirmations. GL014–GL016 are entity-matching targets, not matching evidence families.

Remaining limits:
- Self-reported organizational disclosures; reporting scope and detail vary.
- Publication dates and record phases do not establish deployment start, current operational state at retrieval, or measured utilization.
- Operational/accountable organization is not a legal corporate-ownership relationship.

## CD002 Google Open Source Insights / deps.dev

Version-keyed resolved software structure, distinct from installed deployments or service dependencies.

Coverage: Historical package versions queryable. BigQuery documents SnapshotAt as row export time and Snapshots.Time for full snapshots. Earliest retained snapshot, retention and cadence unverified.

Updates: Official FAQ describes feeds and background scans; commonly used packages usually within roughly an hour, quieter packages can be stale. Not a guaranteed SLA.

Access/export: Anonymous individual JSON GET verified. BigQuery is documentation-only; no collector, installation or graph expansion.

Rights: Generated dependency data CC BY 4.0; package Apache-2.0 and upstream metadata rights are separate.

### Observed sample or schema

These are bounded research facts/schema examples, not admitted operational records.

[cd002_graph](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2:dependencies): The package release is 2024-10-07. The graph was retrieved in 2026; neither retrieval time nor HTTP Date proves the exact graph computation date. No reconstruction of what users installed in 2024.

```json
{
  "root": {
    "system": "PYPI",
    "name": "transformers",
    "version": "4.45.2"
  },
  "node_count_including_root": 18,
  "edge_count": 23,
  "selected_node_index": 6,
  "selected_node": {
    "versionKey": {
      "system": "PYPI",
      "name": "huggingface-hub",
      "version": "0.36.2"
    },
    "bundled": false,
    "relation": "DIRECT",
    "errors": []
  },
  "selected_edge": {
    "fromNode": 0,
    "toNode": 6,
    "requirement": "<1.0,>=0.23.2"
  },
  "graph_error": "",
  "retrieved_at": "2026-10-08T01:04:58.216305Z",
  "source_graph_resolved_at": null,
  "fixture_sha256": "9d11eaee99763097abb9bdc995fb03ad6e38d961c2110e711204ddd8cca32583",
  "fixture_byte_count": 3532
}
```

### Findings with evidence

- **CD002-F1** (resolved_graph): The exact fixture has 18 nodes including the root and 23 indexed directed edges. Node 6 is huggingface-hub 0.36.2 (DIRECT); edge 0 to 6 retains requirement <1.0,>=0.23.2. Graph was retrieved in 2026; selected fields match the earlier review example, but no original earlier-response hash exists for a byte-equality claim. [cd002_graph](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2:dependencies)
- **CD002-F2** (documentation): API documentation describes a clean generic 64-bit Linux resolution approximation, root as first node and directed requirement-resolution edges. DIRECT takes precedence for a node that is both direct and indirect; errors may signal incomplete or incorrect graph. Structure validity does not establish installability or production use. [cd002_docs](https://docs.deps.dev/api/v3/)
- **CD002-F3** (administrative_metadata): Companion metadata reports root publication at 2024-10-07T17:42:51Z, Apache-2.0 package licensing and a SOURCE_REPO association labeled UNVERIFIED_METADATA. Package publication differs from fixture retrieval; exact graph resolution time is unknown. Package license is not generated-data license, and repository association is not verified legal ownership. [cd002_version](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2), [cd002_graph](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2:dependencies)
- **CD002-F4** (documentation): Historical package versions queryable. BigQuery documents SnapshotAt as row export time and Snapshots.Time for full snapshots. Earliest retained snapshot, retention and cadence unverified. Official FAQ describes feeds and background scans; commonly used packages usually within roughly an hour, quieter packages can be stale. Not a guaranteed SLA. Snapshot/export times are not deployment-install dates. Historical earliest coverage, cadence and retention remain unverified; no BigQuery execution. [cd002_bigquery](https://docs.deps.dev/bigquery/v1/), [cd002_faq](https://docs.deps.dev/faq/)
- **CD002-F5** (access_or_rights_qualification): The official API Data section grants CC BY 4.0 to generated data including resolved dependencies; the Terms section permits caching. The one response is retained with source/attribution/change notice outside data/CC0. No blanket grant for companion aggregated metadata, package code or linked works. [cd002_docs](https://docs.deps.dev/api/v3/), [cd002_license](https://creativecommons.org/licenses/by/4.0/), [cd002_terms](https://developers.google.com/terms)

### Artifact verification

| Artifact | Inspection/access | Rights status and scope |
| --- | --- | --- |
| [cd002_docs](https://docs.deps.dev/api/v3/) | `primary_opened`. Data, Terms and GetDependencies sections. Official documentation read and bounded HTML capture verified; later direct retry timed out. | `unknown`; this_artifact_only_no_inheritance |
| [cd002_graph](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2:dependencies) | `pinned_bytes_verified`. Complete 18-node/23-edge generated JSON response. Only this original generated graph is vendored as a licensed fixture outside data/. | `declared_license` (CC-BY-4.0); generated_dependency_data_only |
| [cd002_version](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2) | `primary_opened`. Root package metadata: publishedAt, licenses and relatedProjects. Companion response inspected for qualified metadata; not vendored or relicensed by graph grant. | `unknown`; this_artifact_only_no_inheritance |
| [cd002_bigquery](https://docs.deps.dev/bigquery/v1/) | `documentation_only`. SnapshotAt and Snapshots schema. Documentation inspected; no account, query or export executed. | `unknown`; this_artifact_only_no_inheritance |
| [cd002_faq](https://docs.deps.dev/faq/) | `primary_opened`. Feeds and background scans. Published service-description freshness inspected; not a guaranteed SLA. | `unknown`; this_artifact_only_no_inheritance |
| [cd002_license](https://creativecommons.org/licenses/by/4.0/) | `primary_opened`. CC BY 4.0 pointer from API docs. Generated-data license reference verified. | `unknown`; this_artifact_only_no_inheritance |
| [cd002_terms](https://developers.google.com/terms) | `documentation_only`. API Terms reference. Terms reference verified; API docs expressly permit caching. | `unknown`; this_artifact_only_no_inheritance |

Duplicate-evidence treatment: API and BigQuery are representations of the same generated collection, not independent observations. Declared requirements may also appear in upstream registries/repositories.

Remaining limits:
- Clean generic 64-bit Linux resolution approximation; environment, features and changing releases affect results.
- Package nodes, packages, installed deployments, organizations, and providers are different units.
- UNVERIFIED_METADATA source-repository association does not establish verified provenance, legal ownership, or operational service use.
- Node or graph errors can make the graph incomplete/incorrect; a parser must preserve or fail review on these states.
- Empty edge requirement strings are observed and valid raw values; do not invent constraints.

## CD003 Bank of England / FCA AI surveys

Aggregate provider-nomination concentration within an explicitly bounded survey population.

Coverage: 2019, 2022, 2024 repeated editions; no fixed future schedule verified.

Updates: Periodic editions; no fixed future schedule verified.

Access/export: 2024 and 2019 reports read; 2022 targeted indexed primary text only, with full-artifact limitations. No respondent microdata/export acquired.

Rights: General terms permit download/display/print for personal or internal organizational noncommercial use. Further reuse requires authorization. The OGL clause covers the Bank Database; no evidence extends it to these report charts. Third-party material needs separate approval. Do not label this report OGL or approve publication of chart images/report content/derived extraction solely from Database licensing. Distinguish factual citation from clearance to redistribute a compiled dataset.

### Observed sample or schema

These are bounded research facts/schema examples, not admitted operational records.

[cd003_report2024](https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024): Provider-nomination concentration within survey responses; not spend, workload, compute, or whole-market share. Preserve published denominator wording. Raw category counts, treatment of missing responses, and coding/deduplication were not established.

```json
{
  "year": 2024,
  "responding_firms": 118,
  "top_three_share_percent": {
    "cloud": 73,
    "models": 44,
    "data": 33
  },
  "denominator_raw": "all named providers",
  "raw_category_counts": null
}
```

### Findings with evidence

- **CD003-F1** (survey_aggregate): The 2024 report has 118 responding firms and reports top-three provider shares of 73% cloud, 44% models and 33% data. Denominator is all named providers, after asking firms for their top three in each category. Raw counts/coding/missing responses are unknown; these are not spend, compute, workload or market shares. [cd003_report2024](https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024)
- **CD003-F2** (survey_aggregate): The 2019 report had 106 responses from almost 300 firms and expressly disclaims whole-system statistical representativeness. No matching 2019 top-three provider statistic was established; repeated editions are not a verified fixed-firm panel. [cd003_report2019](https://www.bankofengland.co.uk/report/2019/machine-learning-in-uk-financial-services)
- **CD003-F3** (survey_aggregate): Targeted 2022 indexed text reports 71 of 168 firms (42%) and a top-two cloud figure of 75%. Section 2.4 refers to firms using cloud services; Chart 9 refers to respondents. Full-artifact access remains incomplete. Preserve both denominator phrasings; top-two cloud and 2024 top-three named-provider figures are not silently comparable. Larger-firm skew and changing questions/composition persist. [cd003_report2022](https://www.bankofengland.co.uk/report/2022/machine-learning-in-uk-financial-services), [cd003_pdf2022](https://www.bankofengland.co.uk/-/media/boe/files/report/2022/machine-learning-in-uk-financial-services.pdf)
- **CD003-F4** (access_or_rights_qualification): General Bank terms restrict reuse, while a separate OGL clause covers its statistical Database. No evidence extends Database licensing to these report charts or a redistributed extraction; no microdata/CSV export is verified. Factual citation is distinct from clearance to redistribute report content or a compiled dataset. [cd003_legal](https://www.bankofengland.co.uk/legal), [cd003_report2024](https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024)

### Artifact verification

| Artifact | Inspection/access | Rights status and scope |
| --- | --- | --- |
| [cd003_collection](https://www.bankofengland.co.uk/research/fintech) | `primary_opened`. Research and survey index. Edition history inspected. | `unknown`; this_artifact_only_no_inheritance |
| [cd003_report2024](https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024) | `primary_opened`. Section 1.2 / Chart 1; section 2.8 / Chart 10. 2024 HTML and published aggregate figures inspected. | `restricted_use` (Bank-website-terms); report_material_not_statistical_database_ogl |
| [cd003_report2019](https://www.bankofengland.co.uk/report/2019/machine-learning-in-uk-financial-services) | `primary_opened`. Survey sample and nonrepresentativeness warning. Official report read. | `restricted_use` (Bank-website-terms); report_material_not_statistical_database_ogl |
| [cd003_report2022](https://www.bankofengland.co.uk/report/2022/machine-learning-in-uk-financial-services) | `indexed_excerpt_only`. Indexed official text: sample, section 2.4 and Chart 9. Targeted indexed primary text verified; full HTML exceeded tool-size limit. | `restricted_use` (Bank-website-terms); report_material_not_statistical_database_ogl |
| [cd003_pdf2022](https://www.bankofengland.co.uk/-/media/boe/files/report/2022/machine-learning-in-uk-financial-services.pdf) | `blocked`. Official full-report PDF pointer. PDF open gave unusable parsed text; direct bounded fetch returned 403. Full artifact not independently inspected; denied route not retried. | `restricted_use` (Bank-website-terms); report_material_not_statistical_database_ogl |
| [cd003_legal](https://www.bankofengland.co.uk/legal) | `primary_opened`. General terms and separate Database OGL clause. Terms inspected; report-specific redistribution permission unverified. | `unknown`; this_artifact_only_no_inheritance |

Duplicate-evidence treatment: Joint Bank/FCA edition is one survey. Secondary summaries and repeated charts are not independent observations. GL034 potential synthesis overlap is a trace-back question, not automatically a duplicate confirmed in this review.

Remaining limits:
- Repeated cross-sections, not a verified fixed-firm panel. Do not create a harmonized concentration time series before checking original questions, denominators, coding, and respondent composition. The 2024 report's own retrospective comparisons do not independently settle those details.
- Report publishes anonymized aggregates; no firm-provider microdata or reusable chart-data export verified.
- 2024 expanded generative-AI questions; earlier surveys focus on machine learning. Banking sectors are also split differently.
- Do not label this report OGL or approve publication of chart images/report content/derived extraction solely from Database licensing. Distinguish factual citation from clearance to redistribute a compiled dataset.

## CD004 OMB Federal Agency AI Use Case Inventory, 2025 COTS

Agency/use-category product disclosures with broad user bands and documented consolidation transformations.

Coverage: Consolidated COTS is described as a new reporting category in 2025; no comparable earlier COTS panel was verified.

Updates: Annual reporting; rolling repository updates

Access/export: Public HTTP 200 CSV; anonymously retrieved and parsed. No login, bulk harvesting, outreach, or repository mutation. Raw CSV is verification-only, not a redistributable fixture.

Rights: No license file in non-truncated pinned repository tree; no applicable CSV license found in root README or Data/README_datasets.md. Government publication/GitHub hosting are not treated as an artifact-specific grant.

### Observed sample or schema

These are bounded research facts/schema examples, not admitted operational records.

[cd004_csv](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Data/2025_consolidated_COTS_AI_use_cases.csv): Schema and bounded count observations only; no agency or participant rows. Flags include consolidation recoding; no workload, vendor allocation or population share.

```json
{
  "headers": [
    "Agency",
    "AI Use Case",
    "Agency Use (Y/N)?",
    "Name of Commercial Product or Service Used",
    "Estimated # of Licenses/Users"
  ],
  "row_count": 900,
  "distinct_agency_labels": 45,
  "readme_cots_submissions": 46,
  "reported_use_value_counts": {
    "N": 416,
    "Y": 468,
    "": 16
  },
  "reporting_year": 2025,
  "csv_sha256": "bd18984bdc41f8fc818c9d145de78ebe2563ee0ffab29fe7e96de4c223c8ba17"
}
```

### Findings with evidence

- **CD004-F1** (administrative_metadata): The pinned CSV contains five fields, 900 use-category rows and 45 distinct agency labels; the README states 46 COTS submissions. Counting units differ. Trim-only and NFKC/casefold/whitespace audits still give 45 labels; no missing agency, reporting error or deployment denominator is inferred. [cd004_csv](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Data/2025_consolidated_COTS_AI_use_cases.csv), [cd004_readme](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/README.md)
- **CD004-F2** (administrative_metadata): OMB consolidation records blank-use-flag recoding to N or Y. Every consolidated flag cannot be treated as an independently explicit verbatim agency response. Retain row-level normalization provenance in any future approved extraction. [cd004_normalization](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Validation/data_standardization_report_AI_COTS.md)
- **CD004-F3** (documentation): 2025 is the reporting year, the README summary is as of 13 April 2026 and the inspected 14 May 2026 commit changes only README. Consolidated COTS is new in 2025. Do not use commit time as a deployment or observation timestamp or claim a comparable earlier COTS panel. Shared product-text user bands cannot be divided among vendors or summed into unique users. [cd004_readme](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/README.md), [cd004_dataset_docs](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Data/README_datasets.md), [cd004_commit](https://api.github.com/repos/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/commits/06c7ebeef5b376524211042bd9673b2a7fefd3e3)
- **CD004-F4** (access_or_rights_qualification): No license file or applicable CSV grant was found in the pinned repository tree, root README or dataset README. Government publication or GitHub hosting does not establish artifact-specific reuse. The full CSV and agency row samples are not published in this catalog. [cd004_repository](https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/tree/06c7ebeef5b376524211042bd9673b2a7fefd3e3), [cd004_dataset_docs](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Data/README_datasets.md), [cd004_readme](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/README.md)

### Artifact verification

| Artifact | Inspection/access | Rights status and scope |
| --- | --- | --- |
| [cd004_repository](https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/tree/06c7ebeef5b376524211042bd9673b2a7fefd3e3) | `primary_opened`. Pinned inventory repository. 2025 reporting repository inspected at stated revision. | `unknown`; this_artifact_only_no_inheritance |
| [cd004_csv](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Data/2025_consolidated_COTS_AI_use_cases.csv) | `pinned_bytes_verified`. Five headers; 900 agency/use-category rows. Small public CSV was retrieved and parsed for verification; no CSV or raw rows are vendored. | `unknown`; this_artifact_only_no_inheritance |
| [cd004_readme](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/README.md) | `primary_opened`. COTS submissions and agency reporting table. 46-submission statement and 45 Y-marked agency-table rows inspected. | `unknown`; this_artifact_only_no_inheritance |
| [cd004_dataset_docs](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Data/README_datasets.md) | `primary_opened`. Consolidated dataset documentation. No applicable CSV redistribution license found. | `unknown`; this_artifact_only_no_inheritance |
| [cd004_normalization](https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/06c7ebeef5b376524211042bd9673b2a7fefd3e3/Validation/data_standardization_report_AI_COTS.md) | `primary_opened`. Consolidation flag-recoding provenance. Examples of blank-to-N and blank-to-Y standardization inspected. | `unknown`; this_artifact_only_no_inheritance |
| [cd004_commit](https://api.github.com/repos/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/commits/06c7ebeef5b376524211042bd9673b2a7fefd3e3) | `primary_opened`. Pinned commit metadata. 14 May 2026 revision affects README only, not a new reporting period. | `unknown`; this_artifact_only_no_inheritance |

Duplicate-evidence treatment: Consolidation reuses agency inventories, so original and consolidated rows share origin. Individual-use-case and COTS categories may overlap. GL023 Census BTOS is a different reporting population and does not subsume this family.

Remaining limits:
- A CSV row is an agency/use-category report, not a distinct production deployment.
- The 46-submission statement is distinct from 45 observed CSV agency labels; retain discrepancy.
- One shared licenses/users band applies to multi-product text; no per-product allocation.
- No model/provider graph, exclusivity, criticality, workload share, user uniqueness, or failure probability is established.
- Do not sum broad bands across repeated use categories.
- Artifact-specific CSV reuse and redistribution rights unresolved.
- 46 published COTS submissions versus 45 raw, trimmed, and normalized CSV labels remain unreconciled counting units; do not infer omission/error or calculate population-wide shares.
- Pinned COTS standardization report documents blank-to-N and blank-to-Y recodings; do not interpret every consolidated N as an independently explicit agency denial.

## CD005 FTC AI Partnerships and Investments 6(b) study

Historical regulator staff findings on economic and contractual relationships with anonymity preserved.

Coverage: One-off January 2025 publication; no recurring update schedule verified.

Updates: One-off January 2025 report; recurring update schedule unverified.

Access/export: Public redacted PDF and landing verified. No unredacted submissions or structured contract database verified.

Rights: Policy permits government-material reuse with feasible attribution. No implied FTC endorsement. FTC cannot grant rights to third-party copyrighted material, including unmarked material in filings or contractor-created content. Separate staff-authored findings from quoted company submissions, reproduced graphics, and linked third-party work; publication by FTC does not clear those materials. No unredacted submission export verified.

### Observed sample or schema

These are bounded research facts/schema examples, not admitted operational records.

[cd005_report](https://www.ftc.gov/system/files/ftc_gov/pdf/p246201_aipartnerships6breport_redacted_0.pdf): Retain the staff qualification; do not encode a directly inspected contractual clause or infer names from adjacent passages.

```json
{
  "relationship": "staff_characterized_model_release_parity",
  "partnership_count_lower_bound": 1,
  "cloud_partner": null,
  "model_developer": null,
  "identity_status": "anonymized",
  "evidence_origin": "staff_summary_of_respondent_document_submissions",
  "staff_qualification": "effectively required",
  "measured_workload_share": null
}
```

### Findings with evidence

- **CD005-F1** (regulator_staff_finding): Section 4.2, printed page 19 (PDF page 22), footnote 143 says at least one partnership effectively required model-release parity between partner cloud and first-party API. This is an anonymized staff characterization of respondent document submissions, not a directly inspected public contract clause. Cloud partner and developer remain null; adjacent names cannot fill the gap. [cd005_report](https://www.ftc.gov/system/files/ftc_gov/pdf/p246201_aipartnerships6breport_redacted_0.pdf)
- **CD005-F2** (regulator_staff_finding): The report separates equity/profit interests, access/control/consultation rights and cloud-spending commitments across three selected partnerships. Such rights or commitments do not measure actual utilization, workload share, operational criticality or ownership percentages. The three partnerships do not define the supplier population. [cd005_report](https://www.ftc.gov/system/files/ftc_gov/pdf/p246201_aipartnerships6breport_redacted_0.pdf), [cd005_landing](https://www.ftc.gov/reports/ftc-staff-report-ai-partnerships-investments-6b-study)
- **CD005-F3** (documentation): Respondent information runs through September 2024 and public information through January 2025. Appendix A requests certain management documents from January 2022 onward. Request scope is not complete historical coverage. The January 2025 study does not establish present relationships or a recurring schedule. [cd005_report](https://www.ftc.gov/system/files/ftc_gov/pdf/p246201_aipartnerships6breport_redacted_0.pdf)
- **CD005-F4** (access_or_rights_qualification): FTC policy generally permits reuse of government-authored material with attribution where feasible. FTC does not grant rights to company submissions, reproduced graphics, contractor work or other third-party content. Separate staff-authored findings from embedded copyrighted material; no implied endorsement. [cd005_policy](https://www.ftc.gov/policy-notices/website-policy)

### Artifact verification

| Artifact | Inspection/access | Rights status and scope |
| --- | --- | --- |
| [cd005_landing](https://www.ftc.gov/reports/ftc-staff-report-ai-partnerships-investments-6b-study) | `primary_opened`. Report landing page. One-off staff study and selected partnership scope inspected. | `government_material_policy` (US-government-material-policy); ftc_authored_material_only_excludes_third_party_content |
| [cd005_report](https://www.ftc.gov/system/files/ftc_gov/pdf/p246201_aipartnerships6breport_redacted_0.pdf) | `primary_opened`. Section 4.2, printed page 19; PDF page 22, zero-based index 21; footnote 143; scope statement and Appendix A. Public redacted PDF and parity page visually inspected; company submissions not separately inspected. | `government_material_policy` (US-government-material-policy); ftc_authored_material_only_excludes_third_party_content |
| [cd005_policy](https://www.ftc.gov/policy-notices/website-policy) | `primary_opened`. FTC website reuse policy. Government-material scope and third-party exceptions inspected. | `unknown`; this_artifact_only_no_inheritance |

Duplicate-evidence treatment: Compelled submissions and quoted public announcements need separate evidence-origin tags. FTC repetition of a public investment announcement is not a second investment observation. Company overlap with GL014–GL016 does not make this a system-card artifact.

Remaining limits:
- Equity/profit interests, consultation/control/access rights, and cloud-spending commitments are separate observations. None by itself supplies actual utilization, workload share, operational criticality, or ownership percentage.
- Three selected partnerships; redacted public report, not a public contract-level database or current complete supplier population.
- Separate staff-authored findings from quoted company submissions, reproduced graphics, and linked third-party work; publication by FTC does not clear those materials. No unredacted submission export verified.

## Implemented offline graph reader

[read_dependency_graph.py](../../../tools/evidence_program/read_dependency_graph.py) accepts one supplied local regular file that matches the exact fixture byte count and SHA-256. It never requests a URL, follows evidence links, resolves a package, installs code or imports a database. It emits JSON to stdout; it does not save or publish output.

Input identity: [original deps.dev response](https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2:dependencies), retrieved `2026-10-08T01:04:58.216305Z`; 3,532 bytes; SHA-256 `9d11eaee99763097abb9bdc995fb03ad6e38d961c2110e711204ddd8cca32583`. The response Date header is retained separately in the fixture manifest. Exact source graph-resolution time is unknown. Two bounded research reads yielded the same hash; no original earlier-review bytes exist to prove identity to that older response.

### Run locally

Use Python 3.12 in the supported POSIX environment. The new JSON reader uses only the standard library and adds no dependency. Existing aggregate schema/YAML dependencies remain in the unchanged [requirements](../../../tools/evidence_program/requirements-ci.txt).

```bash
python tools/evidence_program/read_dependency_graph.py \
  tools/evidence_program/tests/fixtures/concentration-dependencies/depsdev-transformers-4.45.2-dependencies.json

python -m unittest discover -s tools/evidence_program/tests -p "test_concentration*.py" -v
python tools/evidence_program/check.py
```

Output is `experimental_review_records_not_admitted`. It preserves original JSON, the complete parsed graph, unknown fields, errors, array/index identity and raw requirement strings. Explicit graph/node/edge review IDs are anchored to the fixed source SHA and source indices, with resolvable edge-to-node references. They are artifact-local review identities, not canonical entity identifiers, cross-snapshot package merges or independent-observation counts. Indexed nodes are not deduplicated by version key: a graph may repeat a package version in distinct nodes. Empty requirements, duplicate edges, cycles and relation-label inconsistencies are neither repaired nor turned into dependency-confidence claims. Graph structure validation does not certify resolution correctness, installability or actual production use.

Limits: 64 KiB input, depth 32, 8,192 lexical work units, 16 KiB decoded UTF-8 scalars, 128-character numeric tokens, 128 nodes and 512 edges. Strict JSON rejects duplicate keys, nonfinite values and invalid UTF-8. Indices must be integers rather than booleans and stay in range. Original JSON preserves numeric spelling even where the parsed representation uses standard JSON/Python numeric types. Source strings and URLs are inert.

The safe opener uses POSIX descriptor-relative traversal and rejects symlink files or ancestor components, nonregular files, FIFOs/devices, URI/stdin/UNC/device paths and parent traversal. It fails closed when required safe-open support is unavailable. The reader issues no network calls but cannot prove that the operating system has not mounted a remote filesystem behind an otherwise regular path. This is not a cross-platform general graph ingestion framework.

### Fixture rights and acquisition

The [fixture notice](../../../tools/evidence_program/tests/fixtures/concentration-dependencies/NOTICE.md) and [manifest](../../../tools/evidence_program/tests/fixtures/concentration-dependencies/manifest.json) retain Google Open Source Insights (deps.dev) attribution, the endpoint, hash, retrieval time, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and change notice. Original fixture bytes are unchanged; parser outputs are derived representations without implied endorsement. The local `.gitattributes` prevents text conversion for this exact JSON file.

The official [API Data section](https://docs.deps.dev/api/v3/#data) licenses generated data, including resolved dependencies, and its Terms section permits caching subject to API terms. This does not license package code, source-repository content, models or all aggregated upstream metadata. The companion version response and other inspected source bodies are not vendored under the generated-data grant. Other reviewed sources retain their access/rights holds.

### Acceptance coverage

1. One supplied local regular file, at most 65536 bytes, must match the exact 3532-byte SHA-256 fixture; no network, stdin or URI.
2. Reject malformed UTF-8/JSON, duplicate keys, nonfinite constants/numbers, wrong field types and booleans used as indices.
3. Bound nesting, lexical work, scalar and number sizes, node count and edge count before unbounded processing.
4. Reject negative or out-of-range edge indices; retain directed fromNode/toNode identity without deduplicating repeated version keys.
5. Preserve exact original JSON, all graph fields and unknown properties, source array order and empty requirement strings.
6. Preserve node errors and graph error without treating structure validation as correct resolution or installability.
7. Retain 18 nodes including root, 23 edges and the observed root-to-huggingface-hub 0.36.2 requirement unchanged.
8. Reject symlink components, nonregular files, FIFO/device/URI/UNC/parent-traversal paths; fail closed if safe-open support is unavailable.
9. Repeated reads have deterministic artifact-local graph/node/edge review IDs anchored to content hash and source indices; edge references resolve, while duplicate version keys remain separate nodes. Source strings/URLs are inert. IDs do not merge entities across snapshots or count independent evidence.
10. Keep retrieval time distinct from package release time and unknown graph-resolution/installation dates.
11. Retain CC BY 4.0 attribution for generated dependency data only, outside the data directory and its CC0 dedication.
12. Output experimental_review_records_not_admitted; no service use, ownership, market-share, concentration, failure probability or p(doom) inference.

The aggregate gate runs the real pinned graph and synthetic malformed/hostile cases separately from live-source verification. It also retains the previous two annotation fixtures and all frozen-contract checks. No live download, external API test, empirical failure study, language-accuracy evaluation or production import is part of deterministic CI. Passing metadata checks does not establish factual truth or legal permission.

## Separate ATRS mapping proposal

The earlier two-record ATRS proposal remains useful but unimplemented. The delivered JSON reader does not parse its HTML or extract semantic relationships. A future manually reviewed pilot is limited to the two identified records, at most 1 MiB per capture and 20 source-linked relationships. It requires scoped rights/attribution, durable hashes, heading/span evidence and a lossless reviewed field mapping. It need not trigger a canonical schema change.

Preserve the following field groups:

- Provenance: artifact URL, retrieval time, content hash, evidence group, heading and span
- Record roles: title, standard version, From publishers, template Organisation, body accountable organization and phase
- Time: each source publication/modification label, explicit statement-as-of and unknown effective start/end
- Relationships: raw names, role, basis, conditional/assertion strength and supplier-flag scope
- Versions and rights: raw mixed model labels, normalized value only when supported, missing reason and artifact-specific rights scope

Corrected acceptance requirements:

1. Exactly the two approved URLs; maximum 1 MiB each and no more than 20 manually reviewed relationships; no link following.
2. Keep AWS hosted service, historical PwC implementation support and Azure AD identity roles separate.
3. Keep missing Newcastle model version null with reason; preserve conditional architecture language.
4. Retain publishing bodies, organization metadata and body accountable organization as separate concepts, not automatic contradictory ownership.
5. Keep Redbox supplier flag No with its exact heading while retaining explicit AWS/model-access observations.
6. Retain Beta/Pilot, all differently labeled publication dates and mixed model-name specificity.
7. Every observation cites heading/span in a hashed artifact; copies do not multiply independent evidence.
8. Emit no inferred ownership percentages, per-provider use allocation, independent failover, market shares, failure probability or p(doom).

## Corrections and completed work

- **C01**: Replace alleged contradictory ownership/quality-defect framing with separately labeled publisher, organization-metadata and accountable-body values. Corporate ownership is not asserted.
- **C02**: Redbox has Published 28 April 2025, Date published 29 April 2025, and JSON-LD publication/modification 28 April. Preserve all with roles; no deployment-start inference.
- **C03**: The fresh sample matches, but say retrieved in 2026, not proven computed in 2026. Earlier review does not include original response bytes/hash. No drift observed in selected fields; future drift is not by itself an error.
- **C04**: 2022 targeted official indexed text is now verified, but full-artifact access/harmonization remains on hold. Its top-two cloud statistic has a different denominator from the 2024 top-three named-provider statistic.
- **C05**: README says 46 COTS submissions; CSV has 900 rows and 45 distinct raw labels; normalization variants also yield 45. These units differ. No missing agency or error inferred.
- **C06**: OMB standardization recodes some blank flags to N or Y. Do not treat every consolidated flag as a verbatim explicit agency response.
- **C07**: Pinned commit 06c7ebe... is a 14 May 2026 README-only update. Keep 2025 reporting, 13 April summary and commit date separate. Consolidated COTS category was new in 2025.
- **C08**: Parity is an anonymized staff characterization of respondent submissions, qualified as effectively required, not a directly inspected public contract clause. Keep both party fields null.

Completed: the five primary-source reviews, exact generated-graph acquisition/attribution and the bounded offline reader. Source admission and operational collection remain disabled; full registry extraction, historical harmonization, rights-held redistribution and canonical import remain outside this completion claim.

## Next actions

| Action | Status | Work and completion evidence |
| --- | --- | --- |
| CD-A1 (CD001, CD002, CD003, CD004, CD005) | `completed` | Verify the five primary collections, inventory relationship, measurement distinctions and artifact-scoped access/rights. Completion evidence: Current 64-source inventory inspected; five new-family candidates remain unadmitted. Eight corrections and source-specific limits are retained, including partial 2022 report access and unresolved rights. |
| CD-A2 (CD002) | `completed` | Acquire one explicitly licensed generated graph and implement the fixed-fixture offline structure reader. Completion evidence: Original 3,532-byte response is SHA-256 pinned with CC BY 4.0 attribution outside data/. Real-fixture and synthetic hostile-input tests run offline; no source expansion, package installation or operational admission. |
| CD-A3 (CD001) | `pending_contract_review` | Prepare a manually reviewed two-record ATRS mapping and durable scoped fixtures before any semantic extraction adapter. Completion evidence: At most two approved local HTML captures, each at most 1 MiB, no more than 20 relationships, explicit evidence spans/field roles/conditional language and lossless time/missingness mapping. No automatic contradiction or corporate ownership edge. |
| CD-A4 (CD002) | `open` | Establish documented earliest historical snapshots, retention and cadence without a paid query. Completion evidence: Primary public documentation identifies retained coverage and SnapshotAt/export versus graph-resolution time, or the unknowns remain explicit. |
| CD-A5 (CD003) | `blocked_access` | Resolve survey denominator/coding details and full 2022 source access before any cross-edition harmonization. Completion evidence: Original provider questions, raw category counts, missing-response/name coding and sample definitions support an explicit comparison, or remain unmatched; no respondent re-identification. |
| CD-A6 (CD003) | `pending_rights_review` | Establish artifact-specific permission for a report-derived dataset or chart redistribution. Completion evidence: An applicable primary grant covers the intended report/chart extraction separately from the statistical Database OGL, or the hold remains. |
| CD-A7 (CD004) | `pending_rights_review` | Resolve OMB CSV rights and definitions behind 46 submissions versus 45 agency labels. Completion evidence: Explicit CSV reuse basis and source count definitions are found, or both counting units remain unreconciled. Retain consolidation recoding evidence; do not silently normalize identities. |
| CD-A8 (CD005) | `pending_rights_review` | Scope rights for any intended FTC extract that includes third-party content. Completion evidence: Each selected passage is classified as staff-authored or third-party and has applicable reuse evidence; anonymous counterparty fields remain null. |
| CD-A9 (CD002) | `pending_contract_review` | Review a lossless canonical mapping before any future import or reader expansion. Completion evidence: Source nodes retain index identity even when version keys repeat; full raw graph/errors, exact fixture identity and separate dates/rights survive a reviewed mapping, or incompatibilities are explicit. |

## Focused follow-up prompts

These self-contained prompts target unresolved evidence/access/rights or mapping gaps. They are not permission for accounts, external outreach, operational collection, publication or production changes.

### CD-A3

The source format is prose-rich and roles/dates differ; a structural graph reader does not implement semantic ATRS extraction.

Review only https://www.gov.uk/algorithmic-transparency-records/newcastle-city-council-aws-contact-centre-services-amazon-q-and-contact-lens and https://www.gov.uk/algorithmic-transparency-records/dsit-redbox . Prepare a manually reviewed mapping for at most 20 relationship observations from these two records. Retain From publishers, template Organisation and body accountable organization as separate raw fields; preserve Newcastle AWS, historical PwC implementation and Azure AD identity roles, null provider-managed versions, conditional language, Redbox No supplier flag with its scope, Beta/Pilot phase, mixed model labels and distinct 28/29 April 2025 publication fields. Require OGL attribution, at most 1 MiB per capture, hashes and heading/span evidence before durable fixtures. Compare the mapping with the frozen pdoom-live contract at https://github.com/mishakgg/pdoom-live/blob/3a981281b59c91d29dd1b5157dfd90eac087c004/tools/evidence_program/contracts/dataset.schema.json without assuming a schema migration is necessary. Return only the reviewed mapping and unresolved gaps. No repository edits, registry sweep, model requests, login, automatic semantic extractor, production import or deployment.

### CD-A4

Queryable historical package versions do not establish a historical install graph or guaranteed snapshot history.

Read only https://docs.deps.dev/bigquery/v1/ and https://docs.deps.dev/faq/ plus a directly linked public documentation page if needed. Find explicit earliest retained full snapshot, retention policy and export cadence for deps.dev. Preserve package publication time, API retrieval time, SnapshotAt row-export time, full-snapshot time and unknown graph-resolution time separately. Report exact documented scope or retain unknowns. No accounts, BigQuery API enablement, queries, network collector, package installation, repository edits or ongoing monitoring.

### CD-A5

2022 full-artifact inspection is incomplete and top-two cloud and top-three named-provider statistics use different scopes.

Use official https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024 , https://www.bankofengland.co.uk/report/2022/machine-learning-in-uk-financial-services and https://www.bankofengland.co.uk/report/2019/machine-learning-in-uk-financial-services . Seek public original questionnaires/chart metadata for 2024 category denominator counts, missing responses and provider normalization, plus an accessible official complete 2022 artifact. Existing 2022 evidence is targeted official indexed text only; a direct PDF route returned 403, so do not retry that denied route or work around access restrictions. Compare only matching questions and population definitions; preserve section 2.4 versus Chart 9 denominator wording and changing sample/composition. Do not reconstruct respondents, infer market shares, harmonize unmatched figures, contact the Bank, log in, bulk-download or edit the repository.

### CD-A6

Published figures can be cited as facts, but this does not resolve report-content or compiled-extraction redistribution rights.

Review https://www.bankofengland.co.uk/legal and the reuse notices associated with https://www.bankofengland.co.uk/report/2024/artificial-intelligence-in-uk-financial-services-2024 . Seek artifact-specific permission for redistribution of a bounded provider-concentration extraction. Do not apply the Bank statistical Database OGL to report charts. State exactly which content and use are covered; if no grant is found, retain the hold and prepare the precise permission question without sending it. No outreach, login, report/chart mirroring, new dataset publication or repository edits.

### CD-A7

Repository hosting does not establish CSV licensing; submission and label counts are different units, and some flags were standardized.

At https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/tree/06c7ebeef5b376524211042bd9673b2a7fefd3e3 read README.md, Data/README_datasets.md and Validation/data_standardization_report_AI_COTS.md. Seek an applicable license for Data/2025_consolidated_COTS_AI_use_cases.csv and primary definitions/reconciliation of 46 COTS submissions versus 45 raw CSV labels (also 45 after trim-only and NFKC/casefold/whitespace normalization). Preserve 900 category rows, separate counting units, raw labels, blank-to-N/Y recoding provenance, reporting year 2025, summary date 13 April 2026 and README-only commit date 14 May 2026. Do not infer an omitted agency/error, upstream model provider, user-band allocation or deployment/market share. No agency outreach, login, bulk collection, full-CSV republication or repository mutation.

### CD-A8

The government-material policy does not license embedded company submissions or every graphic.

Inspect only https://www.ftc.gov/reports/ftc-staff-report-ai-partnerships-investments-6b-study , its public PDF https://www.ftc.gov/system/files/ftc_gov/pdf/p246201_aipartnerships6breport_redacted_0.pdf and https://www.ftc.gov/policy-notices/website-policy . For one proposed extract, identify whether it is staff-authored summary or third-party material and the applicable rights. For parity preserve section 4.2, printed page 19/PDF page 22, footnote 143, staff qualification effectively required, submission-summary origin and both anonymous party fields. Preserve September 2024 respondent and January 2025 public-information cutoffs. Do not infer parties from adjacent text, seek unredacted submissions, infer present relationships, create named contract edges, contact anyone or edit the repository.

### CD-A9

The delivered output is experimental review JSON, not an admitted canonical dependency dataset.

In https://github.com/mishakgg/pdoom-live read tools/evidence_program/read_dependency_graph.py and tools/evidence_program/contracts/dataset.schema.json at the delivered review revision; record that revision. Use only the delivered local fixture tools/evidence_program/tests/fixtures/concentration-dependencies/depsdev-transformers-4.45.2-dependencies.json (3532 bytes; SHA-256 9d11eaee99763097abb9bdc995fb03ad6e38d961c2110e711204ddd8cca32583). Compare a lossless mapping that keeps original JSON, indexed node identity, duplicate version keys, directed edges, empty constraints, raw errors/unknown fields, retrieval time 2026-10-08T01:04:58.216305Z and unknown resolution/installation times. If the reader or fixture is absent, report the exact missing input. Do not install packages, fetch graph extensions, infer remote-service use or deployment, modify schemas, collect operational data or import/publish output.

## Integration and limits

The [dated 26-session queue](research-session-review-queue.md) distinguishes review integration from source admission and implementation. The first four reviews are integrated at its snapshot; this fifth review is prepared. All prior catalog/guide source findings, the fixed annotation reader, frozen inventory/contracts, application runtime, migrations, collector configuration and production import/seed paths are unchanged. Deployment remains separate.

**Top additions:** UK ATRS deployment disclosures; deps.dev generated dependency graphs; Bank/FCA aggregates, subject to reuse and comparison holds.

**Strongest limitation:** These heterogeneous disclosures, resolutions and aggregates cannot reconstruct a complete current operational dependency graph or support a concentration-to-risk probability conversion.

**Smallest testable implementation:** Implemented fixed-fixture deps.dev offline JSON structure reader; ATRS semantic extraction and canonical mapping remain separate unimplemented/held work.
