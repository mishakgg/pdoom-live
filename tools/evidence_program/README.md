# Evidence program checks and frozen contract

This isolated toolset connects the [research program](../../docs/evidence-program/README.md) to deterministic repository checks. The frozen proposed dataset contract is v0.1.0 and is not the application's canonical import format. Nothing here starts operational collection, imports production records, runs a model or enables scoring.

## Run

Use Python 3.12 (CI-tested) with `jsonschema`/`referencing` and pinned `PyYAML` for the bounded offline annotation reader. The pinned dependency set requires Python 3.11+; the frozen validator itself retains its original Python 3.10+ minimum. Exact tested versions and their transitive dependencies are in [requirements-ci.txt](requirements-ci.txt). The GitHub workflow installs them only in its disposable CI job. Local checks use already available dependencies and never install them automatically.

From the repository root:

```bash
python tools/evidence_program/check.py
python tools/evidence_program/validate_dataset.py tools/evidence_program/examples/synthetic_dataset.json
python -m unittest discover -s tools/evidence_program/tests -p test_contract.py -v
python tools/evidence_program/check_methodology_examples.py
```

The aggregate check exits nonzero on any failed gate. It does not fetch endpoints; source URL checks establish syntax, while coverage links must match the pinned audit references. Broken relative documentation paths fail; remote availability and Markdown section-anchor validity are not checked. `--base-tree <GitHub-tree.json>` is available only for local overlay review without a checkout; CI checks the actual checkout with no override.

## What is checked

- Exactly 64 unique stable source IDs, URL syntax, required fields, rights/verification vocabulary and candidate-not-collected state
- Complete 64-source coverage mapping, consistent source names, audit commit and pinned link references; baseline denominators and JSON/CSV agreement
- [Frozen contract manifest](frozen_contract_manifest.json), 14 schemas, 21 synthetic linked records and all 71 positive/negative contract regression tests
- 25 Chinese immutable original strings and exact zero-based, half-open Unicode code-point spans; all 41 partial fragments resolved through their actual frozen schema field paths
- 23 alias entries, review requirements, disabled automatic merging and valid Chinese inventory references
- 30 lexicon concepts and 14 query templates; these remain unexecuted retrieval aids
- Reproducible 19-check methodology arithmetic result and known record-type references in proposed recipes
- [Implementation task pack](../../data/evidence-program/implementation_tasks.json): unique task IDs, known source/recipe references, acyclic resolved dependencies, safe existing/proposed paths, nonempty acceptance evidence, unexecuted statuses and matching Markdown task IDs/titles
- [Chinese safety research catalog](../../data/evidence-program/research/chinese-safety-evaluations.json): separate candidate IDs, frozen-inventory identity, scoped artifact/rights references, inactive admission markers, index-only qualification, and bounded proposed-only FLAMES specification
- [Adoption/productivity research catalog](../../data/evidence-program/research/adoption-productivity.json): inactive collection markers, separate survey/study identities, scoped provenance and rights, interpretation/date guards, and a bounded proposed-only StatCan specification
- [Open-model diffusion catalog](../../data/evidence-program/research/open-model-diffusion.json): unadmitted family identities, artifact-scoped rights, exact fixture pins and interpretation guards; the real fixed-hash annotation pair and synthetic hostile-input regressions run offline
- Local documentation links (including nested research guides) and negative tests for the integration gates

## Frozen contract contents

- [Dataset schema](contracts/dataset.schema.json) is self-contained Draft 2020-12 with all 13 proposed record types.
- The 13 per-record schemas under [contracts/](contracts/) resolve locally through the validator; `.invalid` IDs are offline namespaces.
- [Field dictionary](contracts/field_dictionary.json) and [unit registry](contracts/unit_registry.json) explain field shape and units.
- [Synthetic bundle](examples/synthetic_dataset.json), [JSONL view](examples/synthetic_records.jsonl) and [builder](examples/build_examples.py) are wholly fictional, closed examples.
- [Validator](validate_dataset.py) checks shape and selected cross-record semantics, including provenance references, exact decimals, translation lineage, synthetic isolation and snapshot hashes.
- [Contract tests](tests/test_contract.py) are the unchanged 71-case suite. [Integration tests](tests/test_integration.py) cover the repository wrapper's failure cases.

The frozen schemas, validator, example builder, fixtures and contract tests are byte-preserved from the reviewed Step 3 artifact. Intentional contract evolution needs a separately reviewed version and fingerprint update. Documentation links and run commands have been adapted for their native repository paths.

## Limits and isolation

Passing is not evidence of truth, identity approval, source permissions, translation quality, scientific comparability, statistical validity, calibration or production publication. A shape-valid Chinese fragment is not a complete record. Synthetic examples cannot establish real extractor performance. The recipes are proposed methodology, not implemented analytics. The task pack is an unexecuted plan and grants no operational permissions. Proposed paths describe the audited historical baseline; checks do not require those paths to remain absent after later authorized implementation.

No app runtime, database schema, production import/seed path or collector configuration depends on this directory. Existing database and pipeline suites remain separate. This check does not replace them or claim they ran.

Research-catalog checks are offline metadata consistency checks. They do not refetch artifacts, establish legal rights, verify experiments or admit sources. The earlier Chinese-safety, adoption/productivity and organizational-safety readers remain proposals; their raw source files are not bundled. The open-model reader below is a narrow implemented exception with two explicitly licensed annotation fixtures, distinct from operational collection.

[check_adoption_productivity.py](check_adoption_productivity.py) checks the adoption/productivity catalog, not live source payloads. Its focused regressions reject accidental admission, signed URLs, rights inheritance, measurement/estimand conflation, Census date-role collapse and adapter expansion. It does not implement the source adapter, package real-response fixtures, resolve source discrepancies or change frozen schemas.

[check_organizational_safety.py](check_organizational_safety.py) checks the [organizational-safety research catalog](../../data/evidence-program/research/organizational-safety.json) and [dated 26-session queue](../../docs/evidence-program/research/research-session-review-queue.md). Regressions keep declared powers, commitments, reported actions and external assessments distinct, reject premature admission or scoring, constrain the proposed HAIP scope, and preserve snapshot status. This is metadata consistency, not a report parser, rights approval, empirical safety evaluation or live queue monitor.

## Fixed two-revision annotation reader

[read_open_model_yaml.py](read_open_model_yaml.py) consumes only the supplied local before/after EU Open Source AI Index YAML files whose fixed hashes were verified in the [research guide](../../docs/evidence-program/research/open-model-diffusion.md). [Fixtures and license notice](tests/fixtures/open-model-yaml/NOTICE.md) sit outside `data/` and retain their separate CC BY 4.0 annotation license. The repository's data dedication and software license do not relicense them.

The reader emits experimental review records, full source fields and a deterministic criteria-set comparison. It preserves nulls, notes, unknown nested fields, month precision and raw assessments. It does not fetch evidence links, download models, infer practical usability or model-license changes, claim canonical-schema compatibility or perform production import. The output is not an admitted observation dataset. See the guide for the local command, exact pins, parser limits, acceptance tests and remaining mapping/rights/access work.

The aggregate check now runs the two real pinned fixtures plus synthetic parser/security tests. Fixture acquisition is limited to these two public annotation files. Other source bytes, historical bulk exports and operational ingestion remain outside this implementation.
