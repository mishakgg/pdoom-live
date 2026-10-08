# AI evidence program

The source research, repository audit, proposed dataset contract, Chinese preparation, modelling methodology and implementation plan are integrated here as readable documentation, native JSON/CSV and executable offline checks. They extend the project's research and design surface; they are not imported production evidence.

## Sequential deliverables

| Step | Status | Readable result | Native companions |
| --- | --- | --- | --- |
| 1. Prioritize global and Chinese sources | Complete | [Source priorities](source_priorities.md) | [64-source inventory](../../data/evidence-program/source_inventory.json), [CSV](../../data/evidence-program/source_inventory.csv) |
| 2. Audit existing coverage | Complete | [Coverage findings](coverage_findings.md) | [64 source mappings](../../data/evidence-program/coverage_mapping.json), [28 baseline metrics](../../data/evidence-program/baseline_metrics.json) |
| 3. Specify the proposed dataset | Complete, frozen v0.1.0 | [Dataset specification](dataset_spec.md) | [14 schemas and field dictionary](../../tools/evidence_program/contracts/), [validator and 71 regression tests](../../tools/evidence_program/README.md) |
| 4. Prepare Chinese evidence handling | Complete, preparation only | [Chinese guide](chinese_guide.md) | [23 alias entries](../../data/evidence-program/chinese/aliases.json), [query lexicon](../../data/evidence-program/chinese/query_lexicon.json), [25 synthetic cases](../../data/evidence-program/chinese/test_cases.json) |
| 5. Describe modelling methodology | Complete, proposed methodology | [Modelling methodology](modelling_methodology.md) | [Analysis recipes](../../data/evidence-program/analysis_recipes.json), [19 synthetic arithmetic checks](../../data/evidence-program/methodology_example_checks.json) |
| 6. Break implementation into tasks | Complete, proposed and unexecuted | [27 bounded tasks](implementation_tasks.md) | [Task pack and dependencies](../../data/evidence-program/implementation_tasks.json) |

The source IDs GL001–GL040 and CN001–CN024 are stable research-register identifiers, not production source-artifact revision IDs. All 64 families remain `candidate_not_collected`. The source inventory records availability and rights findings dated 7 October 2026; it is neither a census nor legal clearance to ingest source content.

The coverage baseline is pinned to repository commit `f5274396885dbb654fc2861a78fa5be8f42fad38`. It describes inspected checked-in artifacts, not the current production database. Catalogs, adapters, source configurations, saved observations, extracted candidates and approved public evidence are separate stages. In particular, no finding here turns catalog metadata into collected quantitative data.

## Run the integrated checks

From the repository root, use Python 3.12 (CI-tested) with the dependencies in [requirements-ci.txt](../../tools/evidence_program/requirements-ci.txt) available. The pinned dependency set requires Python 3.11+:

```bash
python tools/evidence_program/check.py
```

The [scoped GitHub workflow](../../.github/workflows/evidence-program.yml) installs pinned testing dependencies in its disposable CI environment and then runs the same offline entry point. The check itself does not install software, fetch sources, use credentials, write to a database or start a collector. It validates source and coverage references, JSON/CSV agreement, frozen contract fingerprints, the 71 contract tests, Chinese code-point spans and 41 schema fragments, methodology arithmetic, and local documentation links.

Passing is evidence of reproducible file consistency and synthetic regression behavior. It is not proof of factual accuracy, rights clearance, Chinese-language extraction quality, benchmark comparability, forecast calibration or a successful production import. See [checks and limitations](../../tools/evidence_program/README.md).

## Relationship to the existing product

The production [ingestion contract](../INGESTION_CONTRACT.md), [data model](../DATA_MODEL.md), [public API](../PUBLIC_API.md) and [trend methodology](../TREND_METHODOLOGY.md) remain authoritative for the running application. The proposed 13-type evidence contract lives under `tools/evidence_program/contracts/` rather than replacing `packages/contracts/` or creating a migration. A future compatibility adapter must preserve identities, revisions, exact decimals, review state and provenance and reject lossy conversions.

Synthetic examples live only under [the isolated tooling directory](../../tools/evidence_program/examples/). Chinese semantic cases also carry explicit synthetic/preparation markers and are partial fragments, not production records. Neither location is read by the application's database seed or import commands. No live collector, public scoring route or deployment is enabled by this integration.

Collection remains a separate authorized operational step. Preserve the [collection storage controls](../COLLECTION_STORAGE.md), including the configured Windows F:-only scratch boundary and hard 25,000,000,000-byte cap, and verified private handoff before cleanup. The collection workflow has not started. Website deployment is separate from local collector storage.

## Data and reuse

See the [data directory guide](../../data/evidence-program/README.md) for JSON/CSV roles. The repository's data dedication covers original inventory metadata and synthetic fixtures only to the extent permitted by its existing [data license](../../data/LICENSE). It does not license third-party articles, benchmark tasks, transcripts, model weights or underlying datasets linked by this inventory. Their artifact-specific rights remain in each record and require separate review.


## Implementation handoff

The [Step 6 plan](implementation_tasks.md) builds on merged protections and keeps source integration, operational authorization, scientific validation and publication separate. Execute one assigned ticket at a time in dependency order. All implementation tickets remain unexecuted; the optional PR 32 UI port is deferred. Deployment remains on hold. The [machine-readable pack](../../data/evidence-program/implementation_tasks.json) is a planning artifact, not an executable configuration or permission grant.

## Additive research reviews

[Chinese safety-evaluation research](research/chinese-safety-evaluations.md) records eight provisional candidates, artifact-specific access and rights, corrected historical-version comparisons, and an unimplemented bounded FLAMES adapter specification. It enriches discovery without changing the frozen 64-source inventory or admitting operational collection. The [JSON catalog](../../data/evidence-program/research/chinese-safety-evaluations.json) retains source pins and explicit unresolved limitations.

[Real-world adoption and productivity](research/adoption-productivity.md) separately reviews five collections, retaining reported adoption, administrative outcomes and causal estimands. It records corrected dates/version identities, access and rights holds, conditional next actions and a proposed three-point StatCan adapter. The [JSON catalog](../../data/evidence-program/research/adoption-productivity.json) is additive; the frozen inventory and contract remain unchanged.

[Organizational safety practices](research/organizational-safety.md) reviews two proposed new families and GL014/GL015/GL016 governance enrichments. Declared authority, commitments, reported actions and external assessments remain distinct, with explicit access/rights holds and a proposed two-report HAIP reader. The [JSON catalog](../../data/evidence-program/research/organizational-safety.json) includes bounded next actions. The [dated 26-session review queue](research/research-session-review-queue.md) preserves arrival order and preparation/integration status at its stated snapshot; it is not a live completion claim.

[Open-model diffusion and accessibility](research/open-model-diffusion.md) reviews Hub histories, the EU Open Source AI Index, Epoch accessibility fields, OLMo materials and PeaTMOSS reuse evidence. The [catalog](../../data/evidence-program/research/open-model-diffusion.json) qualifies artifact-specific access/rights and deduplication. A fixed two-file offline YAML reader is implemented and tested against separately licensed annotation fixtures; it returns experimental review records only. The dated queue records the first three reviews as integrated and this fourth review as prepared at its stated snapshot.
