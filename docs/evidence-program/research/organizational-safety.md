# Organizational safety-practices research catalog

Sources reviewed 7 October 2026 against main `72436af9c44e7da2fae70e87c3573f65d60860a7`. Integration prepared 8 October 2026. This is an additive research review: **two proposed new families and three governance enrichments** of GL015, GL014 and GL016. All five remain `candidate_not_collected` and unadmitted. The [64-family inventory](../../../data/evidence-program/source_inventory.json), frozen contracts and prior research remain unchanged.

The [machine-readable catalog](../../../data/evidence-program/research/organizational-safety.json) records source URLs, locators, access and rights qualifications, sample summaries, evidence classes, next actions and bounded follow-up prompts. OS identifiers are provisional research IDs, not allocated inventory IDs. Source review does not establish source admission, independent assurance, causal effectiveness or permission to republish source documents.

## Review outcome

The best three additions for **source utility, not company safety performance**, are OECD HAIP, Anthropic governance/review records and Microsoft annual reports. Selective organizational disclosure is the strongest limitation: public records rarely expose every rejected release, disagreement, failed test or remediation outcome.

Useful bounded checks were completed rather than deferred: both Fujitsu PDFs now open; both textual edits anticipated by METR are present in the current February report; an original AISI Astra paper, its paper-only license and its evolving evaluation protocol are identified; and all source-family relationships were checked against the frozen inventory. These closures do not establish effectiveness or complete historical coverage.

## Interpretation boundaries

- Keep declared authority, formal commitments, reported completed actions/current practices/release decisions and external assessments distinct.
- Record a separate support class: organization-reported, external-assessor-reported or official document metadata. A policy provision is evidence of a declared mandate, not its exercise.
- Keep publication, effective, reporting-period, coverage-cutoff, review and decision dates separate; preserve unknowns and date precision.
- An external review is scoped evidence, not an automatic audit pass. Retain contractual publication constraints and evaluator/tested-checkpoint limitations.
- Missing disclosure does not establish missing practice, noncompliance or zero safety. Staff counts, report lengths and case counts do not become safety scores.
- No organizational ranking, personal profiling, completed-incident invention or p(doom) conversion is supported.
- Findings below are limited analyst summaries and citations; no raw source bodies, full evidence excerpts or internal intake records are published.

## OS001 OECD Hiroshima AI Process organizational reports

New source family at the known OECD publisher; voluntary organizational disclosures with dated instruments and role distinctions.

Inventory disposition: `new_relative_to_frozen_inventory`. Operational admission: none.

Coverage: The selected Fujitsu pair is Q2 2025 and Q3 2026, published 22 April 2025 and 2 October 2026. This is inspected sample coverage, not the earliest/complete collection extent.

Cadence: Rolling submissions; active recognition expects at least annual resubmission. Reporting-quarter labels do not establish quarterly submission cadence.

Access: Public HTML and both official PDFs opened. Report 36 has 17 physical pages; report 204 has 24. Bulk CSV control exists but was not invoked; endpoint, schema and completeness remain unverified.

Rights: Artifact-specific rights for Fujitsu-authored submissions are unknown. OECD-owned-material terms and post-July-2024 CC BY policy do not automatically clear third-party submissions.

### Observed sample

This is an analyst summary of inspected material, not a native export schema or an admitted event record.

- report id: 204
- organization: Fujitsu
- country: Japan
- published at: 2026-10-02T07:34:00Z
- timestamp precision: minute
- reporting period raw: Q3 2026
- locator: Section 4 Q21
- advisory body: AI Integrity Center
- decision body: relevant business divisions
- final accountability: relevant business divisions
- effective date: unknown / not established
- framework version: unknown / not established
- statement kind: reported_current_practice
- support kind: organization_reported

### Verified findings and qualifications

- **OS001-F1** (document_metadata; official_document_metadata): Report 36 displays 22 April 2025, 20:45 GMT+0 and Q2 2025; report 204 displays 2 October 2026, 07:34 GMT+0 and Q3 2026. Preserve minute precision; neither timestamp dates introduction of the practices. [haip_36_html](https://oecd.ai/en/transparency/reports/36), [haip_204_html](https://oecd.ai/en/transparency/reports/204)
- **OS001-F2** (reported_current_practice; organization_reported): Report 204 Q21 distinguishes AI Integrity Center advice from relevant business divisions’ decisions and final accountability. No effective date or individual release approval is supplied. [haip_204_html](https://oecd.ai/en/transparency/reports/204), [haip_204_pdf](https://api.oecdai.org/transparency-reports/204/view-pdf)
- **OS001-F3** (reported_current_practice; organization_reported): Report 36 Section 4(d) concerns CQO-led IT-system quality governance including AI. The later AI-risk question is differently scoped and more role-specific; this pair does not establish transfer of authority. [haip_36_html](https://oecd.ai/en/transparency/reports/36), [haip_36_pdf](https://api.oecdai.org/transparency-reports/36/view-pdf), [haip_204_html](https://oecd.ai/en/transparency/reports/204)
- **OS001-F4** (formal_commitment; organization_reported): Report 204 Q8.A describes planned preparation of red-teaming options for higher-risk projects according to need. It is neither completed/scheduled testing nor a promise to test every qualifying project. [haip_204_html](https://oecd.ai/en/transparency/reports/204), [haip_204_pdf](https://api.oecdai.org/transparency-reports/204/view-pdf)
- **OS001-F5** (reported_current_practice; organization_reported): Report 204 Q23 describes central incident recordkeeping with conditional external reporting. It supplies no identified incident, completed remediation or halted release. [haip_204_html](https://oecd.ai/en/transparency/reports/204), [haip_204_pdf](https://api.oecdai.org/transparency-reports/204/view-pdf)
- **OS001-F6** (document_metadata; official_document_metadata): OECD announced instrument v2.0 on 28 May 2026. Neither sampled report header supplies an explicit version field. Keep it unknown unless independently mapped and marked as an inference; lettered and numbered questions cannot be joined by position. [haip_revision](https://www.oecd.org/en/about/news/press-releases/2026/05/oecd-launches-streamlined-hiroshima-ai-process-reporting-framework-to-help-small-and-medium-sized-enterprises-participate.html), [haip_36_html](https://oecd.ai/en/transparency/reports/36), [haip_204_html](https://oecd.ai/en/transparency/reports/204)
- **OS001-F7** (document_metadata; official_document_metadata): OECD checks eligibility, completeness and link accessibility, not substantive accuracy; recognition is neither endorsement nor compliance certification. Participation is voluntary and eligibility-limited; catalog countries are not a representative global census. [haip_catalog](https://oecd.ai/en/transparency/reports), [haip_faq](https://oecd.ai/en/transparency/faq)
- **OS001-F8** (document_metadata; official_document_metadata): Both official PDFs opened in this review. The earlier report-36 rate-limit result is a historical retrieval failure, not the current access state. CSV export remains uninspected. [haip_36_pdf](https://api.oecdai.org/transparency-reports/36/view-pdf), [haip_204_pdf](https://api.oecdai.org/transparency-reports/204/view-pdf), [haip_catalog](https://oecd.ai/en/transparency/reports)

### Source and artifact locators

| Artifact | Inspected location and access |
| --- | --- |
| [haip_catalog](https://oecd.ai/en/transparency/reports) | Disclaimer; Export all reports to CSV control; visible organization/country rows. `primary_opened`; Official public primary material inspected in bounded review. |
| [haip_faq](https://oecd.ai/en/transparency/faq) | Eligibility; processing; recognition; delisting. `primary_opened`; Official public primary material inspected in bounded review. |
| [haip_36_html](https://oecd.ai/en/transparency/reports/36) | Header; Section 4(a); Section 4(d). `primary_opened`; Official public primary material inspected in bounded review. |
| [haip_204_html](https://oecd.ai/en/transparency/reports/204) | Header; Q21; Q23; Q8.A. `primary_opened`; Official public primary material inspected in bounded review. |
| [haip_36_pdf](https://api.oecdai.org/transparency-reports/36/view-pdf) | 17 physical pages; Section 4(a) p9; Section 4(d) p10. `primary_opened`; Official public primary material inspected in bounded review. |
| [haip_204_pdf](https://api.oecdai.org/transparency-reports/204/view-pdf) | 24 physical pages; Q21 p14; Q23 p15; Q8.A p8. `primary_opened`; Official public primary material inspected in bounded review. |
| [haip_revision](https://www.oecd.org/en/about/news/press-releases/2026/05/oecd-launches-streamlined-hiroshima-ai-process-reporting-framework-to-help-small-and-medium-sized-enterprises-participate.html) | 28 May 2026 date and opening paragraph. `primary_opened`; Official public primary material inspected in bounded review. |
| [oecd_terms](https://www.oecd.org/en/about/terms-conditions.html) | Ownership introduction; Written Content 1.1; Data third-party caveat. `primary_opened`; Official public primary material inspected in bounded review. |

Evidence overlap: HTML/PDF share the report identity. Successive disclosures retain historical value without becoming independent proof of repeated action/effectiveness. Preserve links to cited cards/reports instead of double-counting underlying evidence.

Limitations:
- Self-selected organizational reporting; no complete decision or incident denominator.
- Unspecified event/effective dates and partial crosswalk cannot establish a governance transition.
- Global catalog coverage is not population representativeness; country coverage and disclosure quality differ.
- Rights and CSV output remain separate holds.

## OS002 Anthropic RSP, risk reports and external reviews

GL015 governance enrichment: policy-defined authority, conditional commitments, reported implementation and scoped external criticism remain different evidence classes.

Inventory disposition: `existing_family_enrichment`. Operational admission: none.

Coverage: Policy archive v1.0 effective 19 September 2023 through v3.4 effective 8 July 2026; index updated 14 August 2026. Selected implementation reporting covers through 15 July 2026 with some later mitigation updates.

Cadence: Event-driven policy revisions. RSP v3.4 promises risk reports every 3–6 months; roughly annual procedural-compliance review is a distinct commitment, not observed compliance.

Access: Official index, v3.2/v3.4 PDFs, August risk report alias, ASL-3 announcement and METR HTML plus original/updated review PDFs inspected. No structured organizational-event export verified. Mutable aliases lack retained content pins. A bounded follow-up inspected only the relevant February report passages and changelog; both anticipated textual edits are now present.

Rights: No artifact-specific open redistribution license established for the selected Anthropic or METR review PDFs. METR HTML reserves rights; policy publication is not a reuse grant.

### Observed sample

This is an analyst summary of inspected material, not a native export schema or an admitted event record.

- organization: Anthropic
- policy version: 3.2
- effective date: 2026-04-29
- body: Long-Term Benefit Trust
- authority scope: Request public/private external report or section review; approve reviewer selection; receive regular briefings
- statement kind: declared_authority
- support kind: organization_reported
- exercise of power: unknown / not established

### Verified findings and qualifications

- **OS002-F1** (declared_authority; organization_reported): RSP v3.2 is effective 29 April 2026. It provides for LTBT-requested review, LTBT approval of reviewer selection and regular briefings. These provisions do not prove exercise or general final release authority. Ordinary determinations involve CEO/RSO; Board/LTBT approval is additionally required when marginal-risk analysis is a major basis for proceeding. [anthropic_rsp_v3_2](https://www-cdn.anthropic.com/files/4zrzovbb/website/28c6241900d90410628a8a2003a5572faae4365a.pdf)
- **OS002-F2** (formal_commitment; organization_reported): RSP v3.4 is effective 8 July 2026. It commits to risk reports every 3–6 months. Mandatory full external review depends on both specified highly-capable-model and significant-redaction conditions; LTBT may separately request review. Future procedural-compliance review is not completed substantive assurance. [anthropic_rsp_v3_4](https://www-cdn.anthropic.com/files/4zrzovbb/website/0bacdc8440ea96e62a8766d99ebe1d4eea6d5f3a.pdf)
- **OS002-F3** (reported_current_practice; organization_reported): The August report, published 14 August per the index, covers 24 February–15 July 2026 with some later mitigation updates. It says LTBT had not requested, and the RSP had not required, an external review since the authority change; pilot reviews continued. This is time-bounded organizational reporting, not proof of noncompliance or absence of all external review. [anthropic_august_risk_report](https://anthropic.com/aug-2026-risk-report), [anthropic_rsp_index](https://www.anthropic.com/responsible-scaling-policy)
- **OS002-F4** (reported_completed_action; organization_reported): The 22 May 2025 announcement reports precautionary, provisional ASL-3 Deployment and Security Standards activation for Claude Opus 4. It does not establish definitive capability-threshold attainment. [anthropic_asl3_activation](https://www.anthropic.com/news/activating-asl3-protections)
- **OS002-F5** (external_assessment; external_assessor_reported): METR’s 8 May 2026 review targets only the automated-R&D section. It challenges the original analytical support and a missing survey response counted as negative; its low-risk bottom line also uses additional evidence. This is a scoped external assessment with substantive reservations, not an organization-wide audit or unqualified endorsement. [metr_review_publication](https://metr.org/blog/2026-05-08-rd-section-anthropic-risk-report-feb-2026-review/), [metr_original_review](https://metr.org/assets/Original%20Review%20of%20%22Risks%20from%20automated%20R&D%22%20section%20in%20the%20Anthropic%20Risk%20Report%20-%20February%202026.pdf)
- **OS002-F6** (external_assessment; external_assessor_reported): The pilot review appendix discloses NDA/publication review and Anthropic’s general publication veto; no actual redactions occurred. Preserve these publication-control constraints without inferring a violation of later mandatory-review provisions. [metr_original_review](https://metr.org/assets/Original%20Review%20of%20%22Risks%20from%20automated%20R&D%22%20section%20in%20the%20Anthropic%20Risk%20Report%20-%20February%202026.pdf)
- **OS002-F7** (document_metadata; official_document_metadata): The updated METR review anticipated two report amendments. A separate current-text check now verifies both: the February report survey row includes the missing-response caveat and modest scaffolding/tooling qualifier. Its changelog attributes these textual edits to METR feedback on 26 May, with editorial cleanup on 8 July. This establishes current textual presence, not historical first public availability, effectiveness or resolution of other criticisms. [metr_updated_review](https://metr.org/assets/Updated%20Review%20of%20%22Risks%20from%20automated%20R&D%22%20section%20in%20the%20Anthropic%20Risk%20Report%20-%20February%202026.pdf), [anthropic_february_risk_report_current](https://anthropic.com/feb-2026-risk-report)

### Source and artifact locators

| Artifact | Inspected location and access |
| --- | --- |
| [anthropic_rsp_index](https://www.anthropic.com/responsible-scaling-policy) | Current and Prior Versions; April 29, 2026; July 8, 2026; August 14, 2026. `primary_opened`; Public HTML, no login; linked current-version alias resolves to v3.4. |
| [anthropic_rsp_v3_2](https://www-cdn.anthropic.com/files/4zrzovbb/website/28c6241900d90410628a8a2003a5572faae4365a.pdf) | PDF page 1: cover; PDF page 14: section 3.6, final paragraph; PDF page 15: section 3.6.1, final sentence; PDF page 16: section 4, item 2; PDF page 20: April 29, 2026 changelog. `primary_opened`; Public PDF, 20 physical pages |
| [anthropic_rsp_v3_4](https://www-cdn.anthropic.com/files/4zrzovbb/website/0bacdc8440ea96e62a8766d99ebe1d4eea6d5f3a.pdf) | PDF page 1: cover; PDF page 11: section 3.1 Timing; PDF pages 14–15: sections 3.6–3.6.2; PDF page 16: Public comments; section 4 item 7. `primary_opened`; Public PDF, 21 physical pages |
| [anthropic_august_risk_report](https://anthropic.com/aug-2026-risk-report) | PDF page 14: section 1.3.3 Coverage dates of risk reports; PDF page 15: section 1.3.5 Governance and review changes around Risk Reports. `primary_opened`; Public PDF alias, 186 physical pages; content-addressed target/hash not established |
| [anthropic_asl3_activation](https://www.anthropic.com/news/activating-asl3-protections) | Dated header; Opening four paragraphs. `primary_opened`; Public HTML |
| [metr_review_publication](https://metr.org/blog/2026-05-08-rd-section-anthropic-risk-report-feb-2026-review/) | Date: May 8, 2026; Executive summary; Footnote 1; Footer. `primary_opened`; Public HTML linking original and updated PDFs |
| [metr_original_review](https://metr.org/assets/Original%20Review%20of%20%22Risks%20from%20automated%20R&D%22%20section%20in%20the%20Anthropic%20Risk%20Report%20-%20February%202026.pdf) | PDF pages 12–13: Appendices, Detail on our review process; PDF pages 13–14: Differences between original and updated review. `primary_opened`; Public PDF, 14 physical pages |
| [metr_updated_review](https://metr.org/assets/Updated%20Review%20of%20%22Risks%20from%20automated%20R&D%22%20section%20in%20the%20Anthropic%20Risk%20Report%20-%20February%202026.pdf) | PDF page 12: Detail on our review process; PDF pages 12–13: Differences between original and updated review. `primary_opened`; Public PDF, 13 physical pages |
| [anthropic_february_risk_report_current](https://anthropic.com/feb-2026-risk-report) | PDF page 2: Change log, May 26 and July 8, 2026 entries; PDF page 62: section 3.4, Internal model use survey row; PDF page 32: section 2.4.4.2, annotated system-card excerpt. `primary_opened`; Public PDF, 106 physical pages; same alias linked by METR and Anthropic. |

Evidence overlap: Policy versions, implementation reports and reviews are related artifacts, not repeated independent measurements. METR original/updated reviews concern one underlying automated-R&D assessment. Preserve aliases as representations and review expectations separately from observed later textual corrections and unmeasured effectiveness.

Limitations:
- Published governance powers differ from their exercise.
- External publication constraints and reviewed-section scope limit assurance interpretation.
- Coverage cutoff, publication, effective dates and later updates are distinct.
- Mutable aliases are not immutable source pins; no complete corpus or decision census verified.

## OS003 Microsoft Responsible AI Transparency Reports

New source family of annual corporate reporting with selected deployment-review case studies; no complete review ledger or organization-wide assurance claim.

Inventory disposition: `new_relative_to_frozen_inventory`. Operational admission: none.

Coverage: Public annual editions verified for 2024, 2025 and 2026, announced 1 May 2024, 20 June 2025 and 1 September 2026. The sampled 2025 Voice case concerns an October 2024 release.

Cadence: Annual report editions, with case-specific retrospective periods and event dates rather than uniform report-year timestamps.

Access: Report hub, three announcements, 2024 and 2025 PDFs, and 2026 HTML opened. Full 2026 PDF link returned tool errors. Certification footnote returned no readable body; no underlying certificate or audit report inspected.

Rights: Report-specific open grant unknown; verified general website terms reserve rights and restrict copying/redistribution absent another applicable license. Public reports are not an open document corpus.

### Observed sample

This is an analyst summary of inspected material, not a native export schema or an admitted event record.

- report edition: 2025
- publication date: 2025-06-20
- product: Copilot Voice
- model: GPT-4o
- release month: 2024-10
- review unit: Sensitive Uses and Emerging Technologies team
- review date: unknown / not established
- final approver: unknown / not established
- named external evaluator: unknown / not established
- measured risk reduction: unknown / not established
- statement kind: reported_completed_action
- support kind: organization_reported
- artifact id: microsoft_2025_pdf
- locator: Physical PDF p19 / printed pp34–35

### Verified findings and qualifications

- **OS003-F1** (document_metadata; official_document_metadata): The three editions were announced on 1 May 2024, 20 June 2025 and 1 September 2026. Edition dates do not replace review/release dates of their cases. [microsoft_2024_announcement](https://blogs.microsoft.com/on-the-issues/2024/05/01/responsible-ai-transparency-report-2024/), [microsoft_2025_announcement](https://blogs.microsoft.com/on-the-issues/2025/06/20/our-2025-responsible-ai-transparency-report/), [microsoft_2026_announcement](https://blogs.microsoft.com/on-the-issues/2026/09/01/responsible-ai-in-2026-how-we-are-adapting-for-whats-ahead/)
- **OS003-F2** (reported_completed_action; organization_reported): The 2025 PDF’s Voice case reports predeployment Sensitive Uses review, internal/external red-teaming coordination, additional evaluations and a voice-output restriction for the October 2024 Copilot Voice release using GPT-4o. Exact review date, named external evaluator, final approver and measured benefit remain unknown. [microsoft_2025_pdf](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2025-Responsible-AI-Transparency-Report.pdf)
- **OS003-F3** (reported_completed_action; organization_reported): The 2025 report attributes early-2025 ISO/IEC 42001:2023 certification to M365 Copilot and M365 Copilot Chat. Neither underlying certificate nor audit report was inspected. This does not establish that the transparency report was independently audited. [microsoft_2025_pdf](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2025-Responsible-AI-Transparency-Report.pdf)
- **OS003-F4** (document_metadata; official_document_metadata): Full 2026 report PDF access was not verified after Read the report tool errors; public HTML and announcement were inspected. This failure does not establish a login requirement or general unavailability. [microsoft_2026_html](https://www.microsoft.com/en-us/corporate-responsibility/topics/responsible-ai/reports/transparency-report/), [microsoft_2026_announcement](https://blogs.microsoft.com/on-the-issues/2026/09/01/responsible-ai-in-2026-how-we-are-adapting-for-whats-ahead/)
- **OS003-F5** (document_metadata; official_document_metadata): The report landing page links restrictive general Terms of Use; no report-specific open-license override was found in this bounded review. Artifact-specific reuse and public factual-summary treatment require separate rights determination. [microsoft_terms](https://www.microsoft.com/en-us/legal/terms-of-use), [microsoft_2026_html](https://www.microsoft.com/en-us/corporate-responsibility/topics/responsible-ai/reports/transparency-report/)

### Source and artifact locators

| Artifact | Inspected location and access |
| --- | --- |
| [microsoft_index](https://www.microsoft.com/en-us/corporate-responsibility/reports-hub) | Archived trusted technology reports; Responsible AI Transparency Report. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_2024_announcement](https://blogs.microsoft.com/on-the-issues/2024/05/01/responsible-ai-transparency-report-2024/) | 1 May 2024 date and inaugural-edition opening. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_2024_pdf](https://aka.ms/RAITransparencyReport2024PDF) | Official PDF alias opened, 40 physical pages. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_2025_announcement](https://blogs.microsoft.com/on-the-issues/2025/06/20/our-2025-responsible-ai-transparency-report/) | 20 June 2025 date and second-annual opening. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_2025_pdf](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2025-Responsible-AI-Transparency-Report.pdf) | Physical p19, printed pp34–35 Voice case; physical p18, printed pp32–33 certification; footnote 54 physical p34. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_2026_announcement](https://blogs.microsoft.com/on-the-issues/2026/09/01/responsible-ai-in-2026-how-we-are-adapting-for-whats-ahead/) | 1 September 2026 date and third-annual opening. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_2026_html](https://www.microsoft.com/en-us/corporate-responsibility/topics/responsible-ai/reports/transparency-report/) | Third-annual report heading; Read the report link; footer Terms of Use. `primary_opened`; Official public primary material inspected in bounded review. |
| [microsoft_certification_footnote](https://techcommunity.microsoft.com/blog/microsoft365copilotblog/microsoft-365-copilot-achieves-isoiec-420012023-certification/4397144) | 2025 report footnote 54; redirected Community Hub target returned no readable body. `access_blocked`; Redirect reached Community Hub without readable article body; underlying certificate and audit report not inspected. |
| [microsoft_terms](https://www.microsoft.com/en-us/legal/terms-of-use) | Personal and Non-Commercial Use Limitation; Content; Documents. `primary_opened`; Official public primary material inspected in bounded review. |

Evidence overlap: Preserve report editions and cases separately; Microsoft application review may use OpenAI models. Same model does not itself prove duplicated or independent evaluation. Identify actual reused results before relating to GL014.

Limitations:
- Curated corporate case studies omit a complete denominator of approved, delayed, rejected or abandoned releases.
- Staff totals, report length and case counts cannot measure safety effectiveness.
- Product-scoped certification claims do not imply report assurance or organization-wide audited safety.
- PDF and certificate access limitations remain explicit; no access bypass or guessed artifact URL.

## OS004 OpenAI governance and deployment records

GL014 governance enrichment with distinct advisory roles, declared decision authority, reported review actions and release-specific determinations.

Inventory disposition: `existing_family_enrichment`. Operational admission: none.

Coverage: Selected organizational documents from 28 May 2024 to the hub update displayed 7 October 2026. Astra first publication is 3 September 2026; current HTML separately lists 9 and 22 September revisions.

Cadence: Event-driven announcements, policy versions, cards and addenda. No complete internal decision history or release census established.

Access: Public official HTML, Preparedness v2 PDF and Frontier Governance Framework PDF inspected. Astra HTML sections support selected claims; its View PDF click failed with no usable direct PDF URL. No decision-log export established. AISI official pages, arXiv metadata and a 33-page v1 paper were inspected; a dedicated Apollo Astra original was not located in a bounded search.

Rights: No artifact-specific report/cards/announcement redistribution grant established; user Input/Output provisions do not license corporate-report text. A separately identified original AISI paper v1 declares CC BY 4.0; that paper-only grant does not clear any OpenAI artifact.

### Observed sample

This is an analyst summary of inspected material, not a native export schema or an admitted event record.

- organization: OpenAI
- model: GPT-6 Astra
- artifact id: openai_astra
- published at: 2026-09-03
- event date: unknown / not established
- decision body: OpenAI leadership
- advisory body: Safety Advisory Group
- decision summary: Reported launch safeguards determination
- support kind: organization_reported
- internal minutes or full report available: false (scoped to the stated source/claim)

### Verified findings and qualifications

- **OS004-F1** (declared_authority; organization_reported): The 28 May 2024 SSC formation announcement defines recommendations to the full Board; the page’s 18 June membership update is a separate timestamp. [openai_ssc_formation](https://openai.com/index/openai-board-forms-safety-and-security-committee/)
- **OS004-F2** (declared_authority; organization_reported): The 16 September 2024 update announces independent Board oversight and authority to delay releases; it does not provide the exact effective date of that structure. A stated power does not prove exercise. [openai_ssc_update](https://openai.com/index/update-on-safety-and-security-practices/)
- **OS004-F3** (reported_completed_action; organization_reported): The same September update separately reports SSC and Board review of the o1 assessment; exact review date is not supplied. [openai_ssc_update](https://openai.com/index/update-on-safety-and-security-practices/)
- **OS004-F4** (declared_authority; organization_reported): Preparedness v2 Appendix B gives CEO or designee final go/no-go authority, permits leadership action without SAG participation, preserves SSC oversight access and permits Board reversal. These are defined powers, not evidence an override occurred. The document was last updated 15 April 2025; no separate effective date is established. [openai_pf_v2](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf), [openai_pf_v2_announcement](https://openai.com/index/updating-our-preparedness-framework/)
- **OS004-F5** (formal_commitment; organization_reported): The Frontier Governance Framework announcement is dated 28 May 2026. It and the PDF describe a complementary relationship with Preparedness; no repeal or effective date should be inferred from the announcement. [openai_fgf_announcement](https://openai.com/index/openai-frontier-governance-framework/), [openai_fgf](https://cdn.openai.com/pdf/e37d949b-8c9f-4d76-b99e-4272f4631a7e/openai-frontier-governance-framework.pdf)
- **OS004-F6** (reported_release_decision; organization_reported): The Astra safeguards section reports leadership’s public-launch safeguards determination informed by SAG advice and an internal report. That internal report and exact decision date are not available in the passage; 3 September is original publication, not approval time. [openai_astra](https://deploymentsafety.openai.com/gpt-6-astra), [openai_astra_safeguards](https://deploymentsafety.openai.com/gpt-6-astra/safeguards)
- **OS004-F7** (document_metadata; official_document_metadata): Astra’s current HTML lists 9 and 22 September revisions; the hub separately shows an October 7 update for Sol/Luna. Keep these artifact-specific timestamps apart. [openai_astra_changelog](https://deploymentsafety.openai.com/gpt-6-astra/change-log), [openai_hub](https://deploymentsafety.openai.com/)
- **OS004-F8** (reported_completed_action; organization_reported): Astra contains developer-published summaries of AISI and Apollo work. Apollo used a near-final representative checkpoint; AISI alignment evaluations were in simulated environments. These sections are not independent assurance of the organization’s decision process. [openai_astra_aisi](https://deploymentsafety.openai.com/gpt-6-astra/external-evaluations-for-alignment-uk-aisi), [openai_astra_apollo](https://deploymentsafety.openai.com/gpt-6-astra/external-evaluations-for-alignment---apollo-research)
- **OS004-F9** (document_metadata; official_document_metadata): A bounded follow-up identified an original AISI Astra paper. Official index entry is dated 28 September 2026, while arXiv v1 submission is 29 September, 19:09:55 UTC; preserve distinct publication events. [aisi_research_index](https://www.aisi.gov.uk/research), [aisi_astra_arxiv_v1](https://arxiv.org/abs/2609.38415v1)
- **OS004-F10** (external_assessment; external_assessor_reported): AISI section 3.1 identifies earlier evaluation versions underlying the Astra card and later improvements to realism. Link an evolving assessment protocol; neither force identical-result deduplication nor treat the related work as fully independent corroboration. [aisi_astra_pdf](https://arxiv.org/pdf/2609.38415)
- **OS004-F11** (external_assessment; external_assessor_reported): The AISI study reports simulated tests with cyber classifiers disabled and unresolved simulation-awareness limitations. This scoped model-behavior study does not independently assure governance or production safeguards. [aisi_astra_original_landing](https://www.aisi.gov.uk/research/evaluating-whether-gpt-6-astra-performs-unsanctioned-supply-chain-attacks), [aisi_astra_blog](https://www.aisi.gov.uk/blog/gpt-6-astra-performs-unsanctioned-supply-chain-attacks-in-simulations), [aisi_astra_pdf](https://arxiv.org/pdf/2609.38415)
- **OS004-F12** (document_metadata; official_document_metadata): The arXiv v1 license link establishes CC BY 4.0 for this paper only. It does not license OpenAI cards, the whole AISI site, transcripts or separately linked data. [aisi_astra_arxiv_v1](https://arxiv.org/abs/2609.38415v1), [cc_by_4](https://creativecommons.org/licenses/by/4.0/)
- **OS004-F13** (document_metadata; official_document_metadata): No dedicated Apollo Astra original report was located in one targeted official-domain search and the current science index. This limited negative result is not proof that no public report exists; developer-card attribution remains distinct. [apollo_science_index](https://www.apolloresearch.ai/science)

### Source and artifact locators

| Artifact | Inspected location and access |
| --- | --- |
| [openai_hub](https://deploymentsafety.openai.com/) | Updates list; Oct 07 GPT-6 Sol and GPT-6 Luna. `primary_opened`; public_html_opened |
| [openai_ssc_formation](https://openai.com/index/openai-board-forms-safety-and-security-committee/) | Body paragraphs 1–3. `primary_opened`; public_html_opened |
| [openai_ssc_update](https://openai.com/index/update-on-safety-and-security-practices/) | Introduction and section 1. `primary_opened`; public_html_opened |
| [openai_pf_v2_announcement](https://openai.com/index/updating-our-preparedness-framework/) | Clarified capability levels and Defined Safeguards Reports bullets. `primary_opened`; public_html_opened |
| [openai_pf_v2](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf) | Cover and Appendix B, printed p15 / one-based PDF p16. `primary_opened`; public_pdf_text_opened |
| [openai_fgf_announcement](https://openai.com/index/openai-frontier-governance-framework/) | Publication date and first two body paragraphs. `primary_opened`; public_html_opened |
| [openai_fgf](https://cdn.openai.com/pdf/e37d949b-8c9f-4d76-b99e-4272f4631a7e/openai-frontier-governance-framework.pdf) | Introduction printed pp1–2; section6 printed p18; section7 printed pp19–20. `primary_opened`; public_pdf_text_opened |
| [openai_astra](https://deploymentsafety.openai.com/gpt-6-astra) | Publication header; Change log; section10.2 Safeguards; sections8.8 and8.8.1. `primary_opened`; public_html_opened |
| [openai_astra_safeguards](https://deploymentsafety.openai.com/gpt-6-astra/safeguards) | 10.2 Safeguards; final introductory paragraph. `primary_opened`; public_html_opened |
| [openai_astra_changelog](https://deploymentsafety.openai.com/gpt-6-astra/change-log) | Change log. `primary_opened`; public_html_opened |
| [openai_astra_aisi](https://deploymentsafety.openai.com/gpt-6-astra/external-evaluations-for-alignment-uk-aisi) | 8.8 External Evaluations for Alignment – UK AISI. `primary_opened`; public_html_opened |
| [openai_astra_apollo](https://deploymentsafety.openai.com/gpt-6-astra/external-evaluations-for-alignment---apollo-research) | 8.8.1 External Evaluations for Alignment – Apollo Research. `primary_opened`; public_html_opened |
| [openai_terms](https://openai.com/policies/terms-of-use/) | Content and Our IP rights; no artifact-specific report reuse license identified. `primary_opened`; public_html_opened |
| [aisi_research_index](https://www.aisi.gov.uk/research) | GPT-6 Astra evaluation entry dated September 28, 2026. `primary_opened`; public_html_opened |
| [aisi_astra_original_landing](https://www.aisi.gov.uk/research/evaluating-whether-gpt-6-astra-performs-unsanctioned-supply-chain-attacks) | Abstract and full paper link. `primary_opened`; public_html_opened |
| [aisi_astra_blog](https://www.aisi.gov.uk/blog/gpt-6-astra-performs-unsanctioned-supply-chain-attacks-in-simulations) | Opening paragraphs, Simulation Awareness Limitations and full report link. `primary_opened`; public_html_opened |
| [aisi_astra_arxiv_v1](https://arxiv.org/abs/2609.38415v1) | Submission history and view license. `metadata_only`; Unversioned arXiv metadata page opened and v1 explicitly listed; canonical version-specific citation retained. |
| [aisi_astra_pdf](https://arxiv.org/pdf/2609.38415) | Title page; section 3.1, printed page9 / physical PDF page9; section 3.3, printed page10. `primary_opened`; Public unversioned PDF text opened; v1 matched inspected arXiv history. No byte hash retained; URL may change on future revisions. |
| [cc_by_4](https://creativecommons.org/licenses/by/4.0/) | Attribution, sharing/adaptation and notices. `primary_opened`; public_license_deed_opened |
| [apollo_science_index](https://www.apolloresearch.ai/science) | Bounded full-index text search for Astra returned no match. `primary_opened`; public_html_opened |

Evidence overlap: A card’s summaries of external work are externally attributed developer disclosures. Link a specific original evaluator assessment/checkpoint before assigning independence or duplicate identity; retain policy, report and card relationships. The original AISI paper explicitly identifies earlier card evaluations and later improved protocols: preserve an evolving-assessment relationship rather than identical-row duplication.

Limitations:
- Selected public summaries do not reveal full deliberations, complete sign-offs or internal disagreement.
- Declared veto/override powers do not prove an actual override.
- A revised card must not be treated as its immutable first-publication text.
- Underlying evaluator relationships need exact assessment and checkpoint identities.

## OS005 Google DeepMind FSF and implementation reports

GL016 enrichment connecting versioned governance specifications to model-release assessments, while preserving unknown approving bodies and checkpoint identities.

Inventory disposition: `existing_family_enrichment`. Operational admission: none.

Coverage: Official FSF archive lists 17 May 2024, 4 February 2025, 22 September 2025 and 17 April 2026 versions. Sampled Gemini 3 Pro report is November 2025 and explicitly applies FSF v3.

Cadence: Policy and model-release updates are event-driven. FSF v3.1 commits to at least annual review, not annual publication of a new framework.

Access: Official index and the selected v2/v3.1 framework PDFs plus Gemini 3 Pro report opened. No structured organizational-event export or full approval ledger verified.

Rights: No artifact-specific reuse grant established for framework and implementation-report PDFs. Model-weight or software licenses cannot clear these documents.

### Observed sample

This is an analyst summary of inspected material, not a native export schema or an admitted event record.

- model: Gemini 3 Pro
- report month: 2025-11
- framework version applied: 3
- cyber alert threshold reached: true (scoped to the stated source/claim)
- cyber ccl reached: false (scoped to the stated source/claim)
- decision: acceptable_for_deployment
- decision basis: organization_reported
- final approving body: unknown / not established
- approval date: unknown / not established
- external tested version raw: similar earlier version
- external tested checkpoint id: unknown / not established

### Verified findings and qualifications

- **OS005-F1** (declared_authority; organization_reported): FSF v2’s governance section names the AGI Safety Council, Responsibility and Safety Council and Google Trust & Compliance Council as examples of appropriate response-plan bodies. The policy does not identify a particular model’s final approver. [deepmind_fsf_v2](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/updating-the-frontier-safety-framework/Frontier%20Safety%20Framework%202.0.pdf)
- **OS005-F2** (declared_authority; organization_reported): FSF v3.1 describes legal, compliance and safety review with escalation and generic governance functions. Reduced naming specificity compared with v2 does not establish council abolition, transfer or loss of powers. [deepmind_fsf_v2](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/updating-the-frontier-safety-framework/Frontier%20Safety%20Framework%202.0.pdf), [deepmind_fsf_v3_1](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/strengthening-our-frontier-safety-framework/frontier-safety-framework_3-1.pdf)
- **OS005-F3** (formal_commitment; organization_reported): Version 3.1, published 17 April 2026, promises at least annual framework review, with more frequent review under stated concerns. It does not guarantee annual publication. [deepmind_frontier_index](https://deepmind.google/frontier-safety/), [deepmind_fsf_v3_1](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/strengthening-our-frontier-safety-framework/frontier-safety-framework_3-1.pdf)
- **OS005-F4** (reported_release_decision; organization_reported): The November 2025 Gemini 3 Pro implementation report explicitly uses FSF v3. It reports a reached cyber alert threshold but no relevant CCL attainment; the safety summary reports deployment acceptability and internal launch approval. The final approving body and approval date remain unknown. [deepmind_gemini3pro_report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf)
- **OS005-F5** (reported_completed_action; organization_reported): External tests used a similar earlier version. Google reports no material capability change in the final version; the passage provides no unique earlier-checkpoint ID. Keep the raw description and unknown ID rather than claim a pinned tested checkpoint. [deepmind_gemini3pro_report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf)
- **OS005-F6** (document_metadata; official_document_metadata): The official index links implementation reports and model-card summaries. These representations need shared-evidence links; external model testing does not independently assure the organizational approval process. [deepmind_frontier_index](https://deepmind.google/frontier-safety/), [deepmind_gemini3pro_report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf)

### Source and artifact locators

| Artifact | Inspected location and access |
| --- | --- |
| [deepmind_frontier_index](https://deepmind.google/frontier-safety/) | The Frontier Safety Framework version cards; Model evaluations and safeguards. `primary_opened`; Public HTML; framework and Gemini report links opened successfully |
| [deepmind_fsf_v2](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/updating-the-frontier-safety-framework/Frontier%20Safety%20Framework%202.0.pdf) | PDF page 1: date/version; PDF page 7: Governance. `primary_opened`; Public PDF, 9 physical pages |
| [deepmind_fsf_v3_1](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/strengthening-our-frontier-safety-framework/frontier-safety-framework_3-1.pdf) | PDF page 1: cover; PDF page 10: section 2.1.2 pre-deployment review; PDF page 14: section 3.1.2 pre-deployment review; PDF page 16: section 4.1; PDF page 17: sections 5.1 and 5.3. `primary_opened`; Public PDF, 20 physical pages |
| [deepmind_gemini3pro_report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf) | PDF page 1: publication month; PDF page 2: Risk assessment process; PDF page 6: summary table and External Safety Testing; PDF page 9: Cybersecurity; PDF page 23: Safety Summary. `primary_opened`; Public PDF, 26 physical pages; metadata title includes v2 |

Evidence overlap: Model-card summaries and implementation reports can describe the same underlying work. Keep applied policy version distinct from later frameworks. An acknowledged evaluator is not release-specific corroboration until a matching report is identified.

Limitations:
- Public specification wording cannot establish unannounced internal authority changes.
- Alert thresholds and CCLs must not be conflated.
- No unique earlier checkpoint, exact approval date or final approving body verified.
- No complete release census, independent governance assurance or causal mitigation benefit established.

## Proposed bounded HAIP source reader

**Proposal only, not implemented.** Two Fujitsu report metadata summaries, five question locations, at most six manually reviewed clause summaries. Use [report 36](https://oecd.ai/en/transparency/reports/36) Section 4(a)/4(d) and [report 204](https://oecd.ai/en/transparency/reports/204) Q21/Q23/Q8.A. Q21 may split advice and decision/accountability. No bulk export, additional organizations or recurring collection.

Reviewed source readings have not become durable source-body fixtures. The catalog checker below does not parse those reports. The proposed fields describe a research mapping, not a new canonical schema: a lossless compatibility review is required before source-reader implementation or canonical output.

Expected document metadata:

- Report 36: 2025-04-22 20:45 UTC, minute precision; Q2 2025
- Report 204: 2026-10-02 07:34 UTC, minute precision; Q3 2026
- Event/effective dates and artifact-declared framework versions remain unknown

Field groups:
- source family key; no newly allocated GL ID
- organization and report identity
- requested/resolved URL; retrieval time; content hash
- section/question and bounded source locator
- publication timestamp and precision; reporting-period text
- event/effective date and date basis; unknown remains null
- instrument version and evidence/inference basis; observed question signature
- statement kind and separate support kind
- actor body/role; authority scope; conditions
- representation/revision/shared underlying-evidence relationship
- artifact rights and review status

### Acceptance tests

1. Accept exactly reports 36 and 204 and five allowlisted question locations; exactly two document metadata summaries, at most six clause summaries. No bulk export, enumeration, schedule or extra organizations.
2. Match reviewed minute-precision publication timestamps and report quarters. Never substitute them for event, effective or decision dates.
3. Leave instrument version unknown without explicit artifact evidence. Observed structure or inferred mapping uses its own basis and manual review.
4. Do not positional-join lettered and numbered questions. Preserve partial crosswalk status where scope or requested detail changed.
5. Keep CQO IT-quality governance distinct from later AI-risk advice and final accountability. Do not infer authority-transfer events.
6. Keep Q8.A conditional preparation as a plan, not completed/scheduled testing or universal testing coverage.
7. Keep Q23 as an attributed incident-recordkeeping process. Do not emit fictional incidents, remediation or stopped releases.
8. Keep missing answers, effective dates and approvers unknown. Missing disclosure is not evidence of no practice, failed compliance or zero performance.
9. HTML/PDF of one report share a document identity. Repeated reports preserve history without multiplying independent evidence of effectiveness.
10. Identical fixture bytes and reviewed question maps produce stable identities; changed bytes or question structure require a reviewable revision, not overwrite.
11. Require artifact-specific rights and source locators; do not inherit OECD licenses for third-party reports. Raw source bodies stay outside the public catalog.
12. Separate declared authority, formal commitments, reported actions and external assessments. No staffing safety score, company ranking or p(doom) conversion.
13. Review a lossless mapping separately before any canonical output. The current catalog validator tests metadata consistency, not this unimplemented source reader.

## Next-action log

These are research follow-through states, separate from repository merge/CI state. Nothing here authorizes operational acquisition, production publication, a collector or deployment. The [dated 26-session queue snapshot](research-session-review-queue.md) tracks sequential review preparation and integration separately.

### OS-A01 · completed

Scope: OS001, OS002, OS003, OS004, OS005. Work type: `completed_bounded_work`.

Complete bounded primary-source verification, artifact-specific corrections, role/date separation, duplicate-evidence analysis and local catalog consistency checks.

Completion evidence: Five research collections with source locators and explicit limitations; local regressions and frozen-file comparison. Research preparation does not establish merged status, source admission, parser completion or rights clearance.

### OS-A02 · pending_contract_review

Scope: OS001. Work type: `offline_implementation_design`.

Design durable bounded HAIP fixtures and a lossless compatibility mapping before implementing the proposed two-report source reader.

Completion evidence: Two reviewed input fixture hashes and five question mappings; up to six attributed clauses; explicit version/date/rights handling; executable acceptance tests only after separately assigned implementation.

### OS-A03 · pending_rights_review

Scope: OS001, OS002, OS003, OS004, OS005. Work type: `rights_hold`.

Resolve artifact-specific retention/redistribution scope before acquiring reusable source bodies or publishing extracted source text.

Completion evidence: Applicable grant/terms scoped to each artifact and intended use, or a retained hold; Microsoft restrictive defaults and OECD third-party exceptions preserved. No blanket inheritance from report hosts, software, model or repository licenses.

### OS-A04 · completed

Scope: OS002. Work type: `completed_bounded_work`.

Check only the two textual edits anticipated by the updated METR review in the current February risk report.

Completion evidence: Both are present at physical p62 section 3.4, with May 26 textual-change and July 8 editorial entries at p2. Current-text check closed; immutable bytes, first public availability and effectiveness remain unverified.

### OS-A05 · blocked_access

Scope: OS003. Work type: `access_dependent`.

If certification evidence is used, inspect one public underlying certificate reached from the report footnote.

Completion evidence: Issuer, exact product/management-system scope, issue/expiry dates and exclusions; distinguish certificate from audit report and transparency-report assurance. Stop at login or unavailable evidence.

### OS-A06 · blocked_access

Scope: OS003. Work type: `access_dependent`.

Resolve the single official 2026 Read the report PDF link only if full-report evidence is needed.

Completion evidence: Verified final artifact URL and page count, or time-scoped tool failure; no guessed filenames or report-wide completeness claim from HTML.

### OS-A07 · open

Scope: OS004. Work type: `targeted_source_gap`.

Retain the targeted Apollo original-report identification gap; AISI original identification, scoped license and evolving-protocol relationship are already verified.

Completion evidence: A public release-specific Apollo original and checkpoint/date/scope correspondence, or a retained bounded-search hold. No repeated broad AISI search or numerical crosswalk is needed.

### OS-A08 · completed

Scope: OS004. Work type: `completed_bounded_work`.

Identify one original AISI Astra assessment and inspect its version, license and relationship to the system-card evaluation.

Completion evidence: Official AISI entry and arXiv v1, paper-only CC BY 4.0, section 3.1 evolving-protocol qualification and simulation limits verified. No numeric-result extraction or complete evaluator-corpus claim.

## Bounded follow-up prompts

Each prompt addresses an actual remaining gap. Completed METR textual-presence and AISI original-identification checks are not assigned again. Source-body fixtures, canonical mapping and operational collection remain separate work.

### OS-A02

Why needed: Reviewed pages have not become durable source fixtures or a reviewed canonical mapping.

Prepare only an offline research-fixture and lossless-mapping design for https://oecd.ai/en/transparency/reports/36 and https://oecd.ai/en/transparency/reports/204. Restrict to 36 Section 4(a), 4(d), and 204 Q21, Q23, Q8.A: two metadata summaries and at most six attributed clauses. Assess compatibility against the frozen v0.1.0 references at https://github.com/mishakgg/pdoom-live/blob/72436af9c44e7da2fae70e87c3573f65d60860a7/tools/evidence_program/contracts/field_dictionary.json, https://github.com/mishakgg/pdoom-live/blob/72436af9c44e7da2fae70e87c3573f65d60860a7/tools/evidence_program/contracts/source_artifact.schema.json, https://github.com/mishakgg/pdoom-live/blob/72436af9c44e7da2fae70e87c3573f65d60860a7/tools/evidence_program/contracts/statement.schema.json and https://github.com/mishakgg/pdoom-live/blob/72436af9c44e7da2fae70e87c3573f65d60860a7/tools/evidence_program/contracts/actor.schema.json. Preserve minute timestamps, unknown effective/instrument dates, partial question crosswalk, conditional plans and distinct CQO versus AI-risk roles. Return an explicit field-by-field lossless mapping or documented unsupported fields and an executable-test plan. Do not add a schema, retain raw source bodies, use bulk export, implement a collector, admit evidence or enable scoring. Source capture or implementation needs its own assigned scope.

### OS-A03

Why needed: The bounded review already established OECD third-party exceptions and restrictive Microsoft defaults. It did not establish a grant for the proposed retention or summary use; investigate only a finite first slice of that unresolved question.

Assess public artifact-specific rights evidence only for this first slice: Fujitsu HAIP report 36 https://oecd.ai/en/transparency/reports/36, report 204 https://oecd.ai/en/transparency/reports/204, and Microsoft 2025 report https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2025-Responsible-AI-Transparency-Report.pdf. Hard cap: these three source artifacts, the already verified terms at https://www.oecd.org/en/about/terms-conditions.html and https://www.microsoft.com/en-us/legal/terms-of-use, and at most one explicitly linked artifact-specific copyright/license notice per source artifact. Existing findings are that OECD-owned-material licensing does not automatically cover Fujitsu submissions and Microsoft general terms restrict copying/redistribution absent another applicable license. Do not repeat broad rights discovery. Determine whether a specific notice or applicable exception explicitly addresses the intended metadata, brief analyst-summary and source-body retention uses, keeping those uses separate; report evidence and unresolved intended-use questions rather than declaring legal clearance. Return a per-artifact hold where no sufficient basis is public. No contacting rights holders, login, source-body mirroring or inheritance from software/model/repository licenses. Other catalog artifacts remain on hold outside this three-artifact slice.

### OS-A05

Why needed: The Microsoft report contains a product-scoped certification claim, but certificate and audit report were not inspected.

Follow only the 2025 Microsoft Responsible AI Transparency Report footnote 54 at https://techcommunity.microsoft.com/blog/microsoft365copilotblog/microsoft-365-copilot-achieves-isoiec-420012023-certification/4397144 to a public certificate if available. Verify issuer, exact organizational/product scope, standard, issue/expiry dates and exclusions. Distinguish certificate, underlying audit report and assurance of the transparency report. Stop at authentication or unreadable content; no outreach or guessed URLs. Return a bounded verified result or retain the hold.

### OS-A06

Why needed: Official HTML opened but its full-report link failed; HTML does not establish the PDF contents.

Resolve only the official Read the report link at https://www.microsoft.com/en-us/corporate-responsibility/topics/responsible-ai/reports/transparency-report/ and its public redirect target. Record final URL, declared edition and page count if readable; otherwise record the exact tool-level access limit. No guessed filenames, login, bulk download, repeated retries or full-text redistribution.

### OS-A07

Why needed: A bounded official search did not identify a dedicated Apollo Astra original; AISI original verification is already complete.

Check only the public Apollo links in https://deploymentsafety.openai.com/gpt-6-astra/external-evaluations-for-alignment---apollo-research and the official https://www.apolloresearch.ai/science index for an explicitly linked release-specific original report. If found, record tested checkpoint, dates and scope relative to the card; otherwise retain unknown availability without inferring absence. AISI original-paper identification and protocol/license checks are already complete. No repeated broad search, scores, governance-audit claim, archive crawl, login or outreach.

## Verification limits

- Primary-source verification is a dated bounded reading, not empirical replication, independent audit or legal clearance.
- No source-body fixture bytes or verified content hashes were retained. Policy effective dates, dated changelogs and arXiv version metadata are explicit provenance, but mutable page/PDF aliases still require byte/version pinning before future acquisition.
- Offline tests validate catalog consistency and selected negative cases, not organizational truth, effectiveness, source-reader behavior or active compliance.
- The frozen 64-family inventory, canonical contracts, earlier research catalogs, collection settings and production surfaces remain untouched.

The [offline checker](../../../tools/evidence_program/README.md) exercises admission, provenance, rights, date/role interpretation guards, bounded proposal limits and the dated queue. Passing tests prove catalog consistency and negative regression behavior only; the source-reader acceptance tests above remain unexecuted.

## Top additions

OECD HAIP, Anthropic governance/review records and Microsoft annual reports, ranked only by evidence utility.

## Strongest limitation

Selective organizational disclosure does not establish complete conduct, safety effectiveness or independent assurance.

## Smallest testable implementation

Two Fujitsu metadata summaries, five questions and at most six reviewed clauses, with separate dates, roles, evidence support and rights. Still proposal-only.
