# Research session review queue

Status snapshot: 8 October 2026, 01:17 UTC. This is a pre-integration snapshot for session 5.

The 26 research sessions below are listed in arrival order. Review and integration proceed sequentially. Four reviews are integrated, one review is prepared for independent review and integration, and 21 remain queued. Session 5 is active; it is not yet merged at this snapshot.

Snapshot counts: 4 integrated; 1 prepared or awaiting CI; 21 queued.

## Status definitions

- **Review integrated:** Reviewed documentation is merged and post-merge checks passed. Source admission, adapter implementation and unresolved evidence holds are tracked separately.
- **Awaiting CI:** The reviewed changes are published in a pull request; integration is still pending.
- **Review prepared; integration pending:** Source findings and repository changes are prepared; independent review, publication and CI/integration remain pending. This is not a merged or admitted-source status.
- **Queued:** Substantive review has not started. Findings, rights, access and remaining actions have not been assessed.

## Arrival order

| Sequence | Research session | Review status | Repository references | Unresolved action status |
| ---: | --- | --- | --- | --- |
| 1 | Chinese safety evaluations | Review integrated | [Research guide](https://github.com/mishakgg/pdoom-live/blob/5f6ff0c15c0461f98dd059177384811bfa9eb839/docs/evidence-program/research/chinese-safety-evaluations.md) · [PR 312](https://github.com/mishakgg/pdoom-live/pull/312) | FLAMES adapter unimplemented; eight artifact holds; two focused follow-up prompts prepared |
| 2 | Real-world adoption and productivity | Review integrated | [Research guide](https://github.com/mishakgg/pdoom-live/blob/d35063f098be9dc59c386edd10f6088527156684/docs/evidence-program/research/adoption-productivity.md) · [PR 313](https://github.com/mishakgg/pdoom-live/pull/313) | StatCan adapter and executable fixtures unimplemented; five evidence holds; five focused follow-up prompts prepared |
| 3 | Organizational safety practices | Review integrated | [Research guide](organizational-safety.md) · [PR 314](https://github.com/mishakgg/pdoom-live/pull/314) | HAIP reader and durable fixtures unimplemented; rights review, Microsoft certificate/PDF and Apollo original-report holds; five bounded prompts |
| 4 | Open-model diffusion and accessibility | Review integrated | [Research guide](open-model-diffusion.md) · [PR 315](https://github.com/mishakgg/pdoom-live/pull/315) | Two-file offline reader implemented with separately licensed research fixtures; production mapping, broader histories, access and artifact rights remain held |
| 5 | Concentration and shared dependencies | Review prepared; integration pending | [Research guide](concentration-dependencies.md) · [Catalog](../../../data/evidence-program/research/concentration-dependencies.json) | One licensed fixed-graph offline reader implemented; ATRS semantic extraction, historical comparability, rights and canonical mapping remain held; seven focused prompts |
| 6 | Historical capability backfills | Queued | Pending review | Not yet assessed |
| 7 | AI-assisted scientific progress | Queued | Pending review | Not yet assessed |
| 8 | Persuasion and information ecosystems | Queued | Pending review | Not yet assessed |
| 9 | Robotics and physical-world capability | Queued | Pending review | Not yet assessed |
| 10 | Training-data availability and feedback loops | Queued | Pending review | Not yet assessed |
| 11 | Human reliance and decision quality | Queued | Pending review | Not yet assessed |
| 12 | Algorithmic efficiency and scaling | Queued | Pending review | Not yet assessed |
| 13 | Agent autonomy/security evaluations and incidents/near-misses | Queued | Pending review | Not yet assessed |
| 14 | Labor-market effects and skill demand | Queued | Pending review | Not yet assessed |
| 15 | Forecast and survey reconstruction | Queued | Pending review | Not yet assessed |
| 16 | Incidents and near-misses | Queued | Pending review | Not yet assessed |
| 17 | Inference cost and price–performance | Queued | Pending review | Not yet assessed |
| 18 | Claim-to-result provenance | Queued | Pending review | Not yet assessed |
| 19 | Model identity and retirement histories | Queued | Pending review | Not yet assessed |
| 20 | Undercovered languages and regions | Queued | Pending review | Not yet assessed |
| 21 | Mitigation effectiveness | Queued | Pending review | Not yet assessed |
| 22 | Negative results and replications | Queued | Pending review | Not yet assessed |
| 23 | Compute supply-chain bottlenecks | Queued | Pending review | Not yet assessed |
| 24 | Chinese governance in practice | Queued | Pending review | Not yet assessed |
| 25 | Benchmark drift and contamination | Queued | Pending review | Not yet assessed |
| 26 | Electricity and deployment bottlenecks | Queued | Pending review | Not yet assessed |

## Open actions for reviewed sessions

### Session 1 Chinese safety evaluations

[PR 312](https://github.com/mishakgg/pdoom-live/pull/312) is merged. All four post-merge checks were observed green by 23:20 UTC on 7 October 2026.

- Implement and test the proposed bounded offline FLAMES parser before claiming adapter completion.
- Retain all eight artifact-specific holds covering FLAMES, Chinese SafetyQA, JADE, LiveSecBench, CHiSafetyBench, SuperCLUE-Safety, M³-SafetyBench and C-SEM. Research integration did not clear these holds.
- Use the two focused M³ methods/reuse and LiveSec historical-provenance prompts in the [research guide](https://github.com/mishakgg/pdoom-live/blob/5f6ff0c15c0461f98dd059177384811bfa9eb839/docs/evidence-program/research/chinese-safety-evaluations.md).

### Session 2 Real world adoption and productivity

[PR 313](https://github.com/mishakgg/pdoom-live/pull/313) is merged. All four post-merge checks were observed green by 23:50 UTC on 7 October 2026.

- Finish lossless native provenance/date/flag mapping and durable bounded fixtures before implementing the proposed three-point StatCan adapter. The existing schema provides a mapping candidate; a schema change has not been established as necessary.
- Retain the five evidence holds for METR data/code rights and uncertainty conventions; QJE final methods and replication manifest/terms; Cui package rights and version/date identity; Census workbook evidence; and SDTIU full methods and rights.
- The [research guide](https://github.com/mishakgg/pdoom-live/blob/d35063f098be9dc59c386edd10f6088527156684/docs/evidence-program/research/adoption-productivity.md) contains the five focused follow-up prompts and detailed completion conditions.

### Session 3 Organizational safety practices

The [source review](organizational-safety.md) was merged in [PR 314](https://github.com/mishakgg/pdoom-live/pull/314) at [4ecece6](https://github.com/mishakgg/pdoom-live/commit/4ecece6abd322932f70f121aef2e99fc3be467bb). Four post-merge checks passed. All five collections remain unadmitted.

- Completed bounded checks: current access to both Fujitsu PDFs; both METR-anticipated textual edits; original AISI paper/version/license and evolving-protocol relationship; source-family comparison. None establishes safety effectiveness.
- Prepare the two-report/five-question/up-to-six-clause HAIP reader only after durable fixtures and lossless compatibility mapping are reviewed. The source reader is unimplemented.
- Retain artifact-specific rights holds, Microsoft underlying certificate and 2026 PDF access gaps, and the targeted Apollo original-report gap.
- Five self-contained prompts and eight action entries are in the guide and catalog; three entries are completed bounded work, five are open or held.

### Session 4 Open-model diffusion and accessibility

The [source review](open-model-diffusion.md) and offline two-revision reader were merged in [PR 315](https://github.com/mishakgg/pdoom-live/pull/315) at [3a98128](https://github.com/mishakgg/pdoom-live/commit/3a981281b59c91d29dd1b5157dfd90eac087c004). All four post-merge checks were observed green by 01:01 UTC on 8 October 2026. Two exact annotation YAMLs are acquired as separately licensed research test fixtures. Operational collection and source admission remain disabled.

- Implemented bounded reader: 14 parent and 12 child criteria, one criteria-set change removing `api` and `package`, and zero inferred model-access or model-license events. No evidence links or model files are fetched.
- Preserve open weights, open source, practical access and successful reproduction as different concepts; model licenses do not inherit annotation rights.
- Remaining actions and focused prompts are in the guide and catalog. Historical Hub export contents/rights, Epoch date and category mapping, OLMo reproduction evidence and PeaTMOSS dataset access/rights are separately qualified.

### Session 5 Concentration and shared dependencies

The [source review](concentration-dependencies.md) is prepared with five unadmitted collections, 28 artifact references, 23 qualified findings and eight corrections. Independent integration review, publication and CI/merge remain pending at this snapshot.

- Completed bounded reader: one 3,532-byte deps.dev generated graph, 18 indexed nodes and 23 edges, licensed CC BY 4.0 with separate attribution outside `data/`. Structure validation does not establish installed deployment, service use or concentration risk.
- Preserve five evidence bases: ownership/economic rights, contractual access, disclosed operational use, resolved software dependencies and survey concentration. Unknown denominators, parties, dates and rights remain explicit.
- ATRS role labels and publication dates stay separate; OMB's 46 submissions/45 labels are different units and some flags reflect consolidation recoding; FTC parity remains anonymous, staff-qualified and historical.
- Two actions are completed; seven follow-ups cover manual ATRS mapping, deps.dev snapshot history, Bank comparability/access and reuse, OMB count definitions/rights, FTC third-party rights and lossless canonical mapping. No general semantic extractor or operational collector is enabled.

## Scope

This index records review progress and links to repository-native research guides. Integrated research catalogs remain unadmitted candidate evidence. The first three reviews retain their unimplemented source-reader proposals. Session 4 implements a fixed two-file annotation reader, and session 5 a fixed one-file graph structure reader; no operational collector is enabled. Refresh status and unresolved actions when later reviewed changes are merged.

## Snapshot maintenance

This file records status at its stated time, not live main/CI state. After independent review, merge and post-merge checks, a later authorized update may record a new dated snapshot with verified PR/commit evidence. Until then, session 5 remains prepared in this historical snapshot even if this document itself is subsequently merged. Do not promote queued sessions, source admission, adapter implementation or unresolved evidence holds merely because a research-review PR merges.
