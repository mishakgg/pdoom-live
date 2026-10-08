# Coverage assessment and next research sessions

Historical assessment prepared for the four prompts delivered on 8 October 2026 at 11:11 UTC. Current review/integration status is tracked in the [follow-up queue](../follow-up-queue.md) and [original-session queue](../../research-session-review-queue.md). No launch of these four sessions is confirmed.

Assessment date: 8 October 2026. Recommendation: four combined sessions, rather than another source-discovery batch. Each tackles three concrete unresolved branches and returns one typed evidence ledger plus a concise decision report. The point is to remove integration blockers, not increase the number of sources or documents.

## What was checked

- Recovered repository base: `6cf8c1c89a387a5b26022dd9ea0a216d45b2b629`. The inspected snapshot contained 205 Git-verified files at 10:54:43 UTC. This assessment did not independently re-query remote main or revisit the public source websites.
- Read `docs/evidence-program/source_priorities.md`, the dated review queue and coverage findings; inspected `data/evidence-program/source_inventory.json`; read the relevant catalog priorities, actions, holds, follow-up prompts and selected artifact/collection records across the 20 cataloged topics.
- Examined recovered source-21 mitigation, source-22 negative-results/replications and source-23 compute-supply-chain findings to check overlap. These are local reviewed materials, not proof of main integration. Latest task status supplied for this assessment: source 24 is source-review complete, source 25 benchmark drift is under review, and source 26 electricity/deployment remains queued. The source-21–23 batch is draft PR 329 in CI, with its catalogs not yet merged.
- Assessed the six received follow-up files after all six bodies had been read in full. The files form three output pairs, not six new original reports. Their public-source and closure claims remain supplied claims pending independent review.

The queue on the recovered base is explicitly a historical snapshot. Do not report its older status counts as the live state of main, or count reviewed catalogs as admitted evidence.

## Coverage is three different questions

### 1. Source coverage

The inventory contains 64 candidate source families, all marked `candidate_not_collected` (26 P0, 35 P1, 3 P2). The 20 research-topic catalogs add finer collection/artifact descriptions and overlap links; their rows are not all independent new sources. The supplied reviews extend coverage through mitigation, replication and compute supply chains, with the final three original topics still in progress or queued.

Original-language/local evidence remains thin for Africa, the Middle East, much of Latin America beyond Brazil, Central Asia and Pacific populations. That is a real scoped source-coverage limitation, not a license to add generic English summaries. It is lower priority for this batch than making already reviewed measurements interpretable. No new broad geographical source hunt is recommended now.

### 2. Operational ingestion

A reviewed catalog, acquisition URL, parser prototype or accepted PR is not a collected dataset. The evidence-program work retains source-admission and canonical-mapping holds, disabled operational collection and many unimplemented or intentionally bounded readers. Some offline readers and fixtures already exist; more external research cannot substitute for their lossless mapping, authorized fixture preparation, implementation, or integration verification.

The repository coverage audit also describes a materially older inspected commit. Its findings must stay date-scoped; a new whole-repository audit is not part of this follow-up pack.

### 3. Evidence comparability, rights and identity

This is the most consequential remaining research category: inconsistent statistics, unresolved measurement vintages and denominators, conflicting lifecycle assertions, and missing original evaluator/retest provenance. Artifact rights must be checked at the intended-use level, but repeated searches of the same exhausted terms pages are not useful work. An unresolved bounded rights review is a completed negative finding, not an invitation to keep searching unchanged pages.

## Recommended sessions, in priority order

### 1. Resolve labor measurement lineage

- Existing IDs: LM001, LM002, LM004; LM-A03/P01, LM-A04/P02, LM-A06/P04.
- Three branches: inspect the single still-unseen May 2025 BLS national statistical workbook; trace O*NET rating vintages and task/taxonomy changes; establish Indeed version/construct comparability.
- Why first: BLS and O*NET already have relatively clear scoped statistical/database reuse paths, while specific content/version questions remain untested. This can turn documentary coverage into a bounded, reviewable observation/mapping specification without waiting for access to private data.
- Required result: exact statistical fields and missingness, observation versus release clocks, dependence/republication edges, and tested mapping decisions. No causal AI employment series or exposure score.
- Excludes: Eurostat reconstruction, BTOS denied export routes, all forecast surveys and the returned three sessions.
- Prompt: `01-resolve-labor-measurement-lineage.txt`.

### 2. Reconcile experimental effects and uncertainty

- Existing IDs: AP002/AP-A03, overlapping NR007; SP001/SP-A03/SCI-H01; PI005/PI-A5/PI-H4.
- Three branches: METR HC3/nonrobust convention and early/late estimands; I4R SD/SE and output/input lineage; Costello editorial disposition and corrected cohort-specific aggregate effects.
- Why now: wrong uncertainty or a corrected sample attached to an old estimate can reverse the interpretation of evidence. These questions have concrete named primary targets and affect already curated aggregates.
- Required result: field-specific resolutions or holds, exact version/cohort identities and a demonstration that a mapping rejects incompatible combinations. No participant data or recomputation.
- Prior access restrictions remain in force. The blocked Science route is explicitly excluded; accessible deposit documentation and publisher-supplied notice metadata may still establish limited facts. If they cannot verify disposition, the concern stays active.
- Prompt: `02-reconcile-experimental-effects.txt`.

### 3. Resolve hosted-model and tariff events

- Existing IDs: MIR002, MIR004, IPP004; MIR-A02/P02, MIR-A04/P04, IPP-A04/P04; CN001/CN024/CN002.
- Three branches: Azure's two conflicting version/date pairs; DeepSeek-V3 promotional tariff boundary; the DeepSeek January 2025 R1/V3 alias conflict and shared tariff-event provenance.
- Why useful: it prevents mutable labels, translations and pricing notices from becoming false model identities or duplicate evidence. The genuinely external work is targeted history/conflict verification. Straightforward Google lifecycle mapping is excluded and belongs locally.
- Required result: source-assertion/event relationships and exact temporal precision, with unresolved actual serving/runtime links preserved. No inference calls, weight downloads or benchmark expansion.
- Prompt: `03-resolve-model-tariff-events.txt`.

### 4. Verify safeguard and evaluator lineage

- Existing IDs: recovered ME002, ME007; OS004/OS-A07; overlap ASI001.
- Three branches: CaMeL scoring-helper/paper/runtime linkage; AISI final-configuration remediation retest; identification and scope of the release-specific Apollo original for Astra.
- Why useful: a fix, a code concern and a published evaluator outcome are different evidence. These gaps can materially change whether an apparent mitigation result is usable.
- Required result: conservative evaluation/remediation chains, version-matched denominators and explicit uncertainty or missing-retest holds. The already verified AISI Astra original identification is excluded.
- If source-21 materials have not reached main, the supplied ME IDs and baseline assertions must be attributed as local-review context until verified. This research does not depend on treating them as merged or admitted.
- Prompt: `04-verify-safeguard-evaluator-lineage.txt`.

## Work identified at the delivery-time cutoff

1. Finish the original queue sequentially: complete the ongoing source-25 review, then review source 26 using its existing deliverable. Source 24 is source-review complete; keep its integration status separate. Track draft PR 329 for the source-21–23 batch through CI and integration without describing its catalogs as already merged. Do not commission replacement benchmark-drift or electricity/deployment research before these are assessed.
2. Independently review the six received follow-up outputs, preserving their supplied-versus-verified status. Reconcile their old `82fd46330539bd484c80190c69868d71b2052f6e` snapshot with current main and bind exact artifacts to IPP001/IPP002/IPP003. Do not create duplicate source families or misread historical missing-file claims as current absence.
3. Translate verified documentary advances into the existing catalogs, remaining-action statuses and acceptance cases. Keep completed-but-unresolved bounded checks complete. In particular, independently verify the claimed MLPerf publication/session link, ML.ENERGY v3 release date, PhAIL omission/migration history and Eurostat 2022 model period before adopting them.
4. Use existing evidence for lossless-mapping reviews that need no new public facts: StatCan AP001, the two Spanish INE ULR008 observations, the existing Google MIR001 lifecycle assertions, already-checked CRP correction/version relationships, and previously reviewed readers/manual ledgers. Separate fixture rights, source acceptance and future implementation approval. HAIP durable-source fixtures remain rights-dependent; its existing field mapping can be reviewed without recapturing source bodies.
5. Do not start a blanket adapter or validator expansion to make the research look complete. First establish the minimum fields that can survive the existing contracts, what is genuinely unsupported, and the positive/negative cases a later implementation would need.

## Delivery-time exclusions from the six returned files

- Rights/releases: ML.ENERGY compiled JSON, Common Crawl's two CSVs, DPI's two JSONs, FineWeb2 statistics CSV, Epoch/AA's three CSVs and a NanoGPT log. All ten raw-file grants remain supplied unknown/held. Covered actions include rights portions of TD-A03/A04/A06, AE-A04, IPP-A02/A03. Do not repeat the same terms-page searches without new applicability evidence or a genuinely different authorized intended-use question.
- Comparability: PhAIL partial cohort/migration history (RP-A6), RoboArena snapshot metadata (partial RP-A4), and MLPerf official listing plus claimed summary-to-session link (IPP-A01). Complete PhAIL membership/intervention bridges, RoboArena exclusions and MLPerf power-window/protocol/CUDA normalization remain held; these are not assigned again in this pack.
- Instruments: FS-A03/A04/A05 and partial LM-A05. The supplied LEAP weighting caption and Eurostat 2022→2021 model-period finding do not resolve weights/ESS/overlap or German administration. Do not restart failed ESPAI 2024, XPT Appendix 6 or Eurostat 2012 routes as if untried.
- Original-topic exclusions: source 24 Chinese governance is source-review complete, source 25 benchmark drift/contamination is under review, and source 26 electricity/deployment is queued. Source-23 compute capacity, fleet and power follow-ups should wait for the source-26 overlap decision. A limited overlap check of the source-25 report identifies METR time-horizon revision/fitting work, distinct from the AP002/NR007 developer-productivity trial in session 2; time-horizon work remains excluded.

## What counts as a good deep result

Each prompt asks for three related questions, not a source-count quota. Deliver only a typed evidence ledger and concise decision report. The ledger carries primary locators, event/version/measurement lineage, raw-versus-normalized fields, rights scope, exact conflict resolution or reason for a hold, cross-source duplicate links and mapping acceptance cases. Walk the cases through the mapping; distinguish manual checks from executed schema checks and unrun proposals.

Stop a branch after the exact evidence resolves it or a bounded primary-record/version check establishes why it cannot be resolved publicly within scope. A precise hold is valid. Private records, paid access, source execution, outreach, or more unrelated sources are not required substitutes. No session edits the repository, enables ingestion, runs models, creates a universal metric or converts observations to p(doom).

## Repository copy and status

The four neighboring TXT files are byte-identical copies of the delivered prompts. This assessment preserves the delivery-time recommendation and exclusions while removing private delivery metadata. Later original-review integration and accepted follow-up decisions are recorded in the linked queues; the historical status statements above are not a live main/CI report.
