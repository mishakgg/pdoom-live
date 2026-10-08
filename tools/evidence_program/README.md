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

Research-catalog checks are offline metadata consistency checks. They do not refetch artifacts, establish legal rights, verify experiments or admit sources. The earlier Chinese-safety, adoption/productivity and organizational-safety readers remain proposals; their raw source files are not bundled. The open-model reader below and the dependency-graph reader are narrow implemented exceptions with two explicitly licensed annotation fixtures and one generated graph, distinct from operational collection.

[check_adoption_productivity.py](check_adoption_productivity.py) checks the adoption/productivity catalog, not live source payloads. Its focused regressions reject accidental admission, signed URLs, rights inheritance, measurement/estimand conflation, Census date-role collapse and adapter expansion. It does not implement the source adapter, package real-response fixtures, resolve source discrepancies or change frozen schemas.

[check_organizational_safety.py](check_organizational_safety.py) checks the [organizational-safety research catalog](../../data/evidence-program/research/organizational-safety.json) and [dated 26-session queue](../../docs/evidence-program/research/research-session-review-queue.md). Regressions keep declared powers, commitments, reported actions and external assessments distinct, reject premature admission or scoring, constrain the proposed HAIP scope, and preserve snapshot status. This is metadata consistency, not a report parser, rights approval, empirical safety evaluation or live queue monitor.

## Fixed two-revision annotation reader

[read_open_model_yaml.py](read_open_model_yaml.py) consumes only the supplied local before/after EU Open Source AI Index YAML files whose fixed hashes were verified in the [research guide](../../docs/evidence-program/research/open-model-diffusion.md). [Fixtures and license notice](tests/fixtures/open-model-yaml/NOTICE.md) sit outside `data/` and retain their separate CC BY 4.0 annotation license. The repository's data dedication and software license do not relicense them.

The reader emits experimental review records, full source fields and a deterministic criteria-set comparison. It preserves nulls, notes, unknown nested fields, month precision and raw assessments. It does not fetch evidence links, download models, infer practical usability or model-license changes, claim canonical-schema compatibility or perform production import. The output is not an admitted observation dataset. See the guide for the local command, exact pins, parser limits, acceptance tests and remaining mapping/rights/access work.

The aggregate check now runs the two real pinned fixtures plus synthetic parser/security tests. That reader's fixture acquisition is limited to the two public annotation files. The separate dependency-graph reader below adds one explicitly licensed generated JSON fixture. Historical bulk exports and operational ingestion remain outside both implementations.

## Fixed dependency-graph structure reader

[read_dependency_graph.py](read_dependency_graph.py) accepts one supplied local regular file matching the exact 3,532-byte deps.dev graph SHA-256 in the [research guide](../../docs/evidence-program/research/concentration-dependencies.md). The [fixture notice and attribution](tests/fixtures/concentration-dependencies/NOTICE.md) isolate generated dependency data under CC BY 4.0 from `data/`/CC0 and the repository software license. No companion package metadata or other source body is vendored under that license.

The standard-library reader preserves original JSON, indexed node/edge identity, unknown fields, errors and empty constraints. It rejects malformed, oversized, excessive-depth/work, duplicate-key, nonfinite and invalid-index inputs. POSIX descriptor-relative safe-open rejects symlink components and nonregular/network-style inputs; unsupported safe-open platforms fail closed. It makes no network or process calls. Parsed source strings are inert. The operating system may still mount a remote filesystem behind a regular path; filesystem locality cannot be guaranteed.

Output remains experimental review JSON, not an installed dependency inventory or canonical admitted dataset. Repeated version keys are retained as separate indexed nodes. Deterministic graph/node/edge IDs are artifact-local hash-and-index review references, not cross-snapshot entity identities or independent-observation counts; edge references resolve to those node IDs. No provider use, ownership, market share, common-mode failure probability or p(doom) is inferred. Source resolution time remains unknown. ATRS semantic extraction is unimplemented; a proposed manually reviewed two-record mapping remains separate.

[check_concentration_dependencies.py](check_concentration_dependencies.py) validates the additive [catalog](../../data/evidence-program/research/concentration-dependencies.json), five relationship classes, provenance/rights scope, critical qualifications, reader bounds and seven follow-ups. The aggregate gate runs the exact graph fixture plus synthetic malformed/hostile regressions. Metadata consistency and structure validation are not source truth, legal approval, deployment evidence or operational admission. [check_research_queue.py](check_research_queue.py) remains the generic dated sequential queue validator; its regression snapshots are independent of current review progress.

## Bounded offline historical-score reader

[read_wmt08_scores.py](read_wmt08_scores.py) reads one supplied local WMT08 gzip matching the fixed pin in the [historical research guide](../../docs/evidence-program/research/historical-capability-backfills.md). It bounds compressed/decompressed bytes, row and field work; validates one complete gzip member and six fields; and preserves exact decimal strings, original labels, source-specific directions and explicit unknowns. This is an experimental offline review helper with no network, operational admission or canonical import. Scores do not become independent experiments or a universal capability curve.

[The fixture notice](tests/fixtures/historical-backfills/NOTICE.md) explains synthetic-only CI. The real gzip has unresolved reuse rights and is not bundled, nor are full extracted results. Separate private local acceptance of the fixed 16,071-byte artifact is distinguished from CI; the ACL paper's license never licenses that file. Local filesystem mtime and gzip header mtime are not historical publication evidence.

[check_historical_backfills.py](check_historical_backfills.py) checks the five-family [catalog](../../data/evidence-program/research/historical-capability-backfills.json), guarded interpretations, artifact rights/date roles, inactive admission markers and focused follow-ups. The aggregate check runs these metadata checks and synthetic reader/security regressions only; it does not acquire or test the real WMT artifact in CI. Passing does not settle historical comparability, legal rights, missing-data interpretation or lossless production mapping.

## Scientific-progress catalog and manual aggregate ledger

The [guide](../../docs/evidence-program/research/scientific-progress.md) and [catalog](../../data/evidence-program/research/scientific-progress.json) retain five collections and compare every prior research catalog at exact baseline hashes. `check_scientific_progress.py` checks source-specific qualifications, aggregate values, rights/access boundaries, source references and the six-by-five duplicate-review matrix. These are documentary consistency checks, not empirical verification.

`validate_scientific_ledger.py` is an implemented local JSON validator, not a source extractor or collector. Its [manually curated ledger](../../data/evidence-program/research/alab-correction-ledger.json) preserves original/superseded 41/58 as an indexed-primary assertion, current targets 36/4/17 of 57 and recipes 105/353. It returns one DOI-keyed campaign and exactly two current records; correction is not a new experiment. Exact duplicate observation identities are idempotent and conflicting duplicates fail. Calendar/labor fields and unavailable source hashes remain null.

```bash
python tools/evidence_program/validate_scientific_ledger.py data/evidence-program/research/alab-correction-ledger.json
python -m unittest discover -s tools/evidence_program/tests -p 'test_scientific*.py'
python tools/evidence_program/check.py
```

The stdlib-only validator caps input at 64 KiB, nesting at 12, input records at 32 with exactly three unique claims, and provenance at three locators per record. It rejects unexpected fields, floats/nonfinite/boolean counts, duplicate JSON keys, invalid partitions/correction edges, URL deviations, symlink components, special files and parent traversal. The POSIX file reader fails closed when safe-open support is unavailable; filesystem mount locality is not established. Locators remain inert untrusted text. The contract is deliberately narrow, with fixed real and synthetic DOI/URL profiles, and checks structural consistency only.

Tests use an original [synthetic fixture](tests/fixtures/scientific-progress/synthetic-alab-ledger.json) with different counts and a reserved fictional DOI/URL; see [NOTICE](tests/fixtures/scientific-progress/NOTICE.md). Source-specific tests separately validate manually curated factual metadata without fetching source bytes. No participant/team records, chemical protocols, experimental data, sequences, coordinates, numerical certificate archives or source code are acquired or executed. The prior three offline readers, frozen schemas and 64-family inventory remain unchanged.

## Curated persuasion/information aggregate checks

`check.py` includes [catalog checks](check_persuasion_information.py), a small [in-memory ledger validator](validate_persuasion_ledger.py), and `test_persuasion*.py` regressions. The [research guide](../../docs/evidence-program/research/persuasion-information.md) distinguishes proposed versus implemented work. This adds no file-reader CLI or source parser. It validates one study, two current comparisons, three assertions and one same-estimand p-value correction; no participant CSV, model execution, statistical fitting or live fetch. Synthetic fixtures are self-authored; no source workbook/CSV is vendored. Exact p values, p-value operators, 95% intervals, conditioning and immediate outcome windows cannot cross comparison or version identities. Unknown publication byte hashes stay null.

Focused command: `python -m unittest discover -s tools/evidence_program/tests -p "test_persuasion*.py"`. Full evidence-program command: `python tools/evidence_program/check.py`. These consistency checks are not independent source-data reproduction or rights approval.

## Curated physical-robotics table checks

[check_robotics_physical.py](check_robotics_physical.py) validates the five-family [catalog](../../data/evidence-program/research/robotics-physical.json), source-qualified counts/rights, 40 prior-catalog overlap cells, corrections, holds and bounded follow-up prompts. [validate_barn_table.py](validate_barn_table.py) is a stdlib-only offline reader for a manually curated BARN 2024 Table II excerpt, not an HTML/PDF parser, collector or controller. The [fixture and CC BY 4.0 notice](tests/fixtures/robotics-physical/NOTICE.md) preserve the separate source license outside data/CC0. Full manuscript hashes remain null.

The reader emits 60 display-coordinate observations, 12 course summaries and four team summaries. X is a reported failure with null time/cause; credited aggregates and ambiguous tied row membership remain separate from all-attempt denominators. Input is bounded to 64 KiB/depth 12, regular POSIX no-symlink files; duplicate keys, nonfinite/boolean numeric fields, path traversal and special files fail. Exact duplicate coordinates are idempotent, conflicting duplicates fail, and unreviewed source versions are rejected. Display positions are not native cross-version run IDs. Source strings are inert, and filesystem mount locality is not established.

`python -m unittest discover -s tools/evidence_program/tests -p "test_robotics*.py"` runs focused tests; `python tools/evidence_program/check.py` includes catalog/fixture acceptance and all regressions. The [guide](../../docs/evidence-program/research/robotics-physical.md) documents commands, pins and bounds. No robot/harness/source execution, personal evaluators, raw trajectories, canonical import, scientific replication or universal capability score is implied by passing.

## Bounded offline training-data statistics

[read_common_crawl_statistics.py](read_common_crawl_statistics.py) accepts two already supplied local aggregate CSVs with exact full-byte pins and emits only three reviewed Common Crawl IDs. It makes no network calls and preserves native fields, separate revision/crawl identities, estimate flags, capture/release versus unknown publication dates and scoped rights. Unknown-language native URLs are a page-residual placeholder; normalized URL cardinality is null. Page sums reconcile; per-language URL totals need not equal monthly distinct URLs.

The [synthetic fixture notice](tests/fixtures/training-data/NOTICE.md) explains self-authored public CI inputs. Real statistics CSV rights remain unknown, so their private acceptance and 486 selected language observations are not vendored. Bounds: 1 MiB/64 KiB, 20000/256 rows, 128-byte fields, 1024-byte lines, 512 categories per crawl, count magnitude 10^12 and 0.00005-percentage-point rounding tolerance. POSIX safe-open rejects symlinks, traversal and nonregular files; mounted filesystem locality is not established.

[check_training_data_feedback.py](check_training_data_feedback.py) checks the five-source catalog, source-specific metadata fingerprints, 45 overlap cells across nine prior catalogs, rights/identity guards, completed work and remaining holds. Fingerprints protect reviewed documentary content from unnoticed changes; they do not establish truth or permission. No corpus, page content, source execution, model training, live collection, canonical admission or universal stock estimate is produced.

Commands: `python -m unittest discover -s tools/evidence_program/tests -p "test_training_data*.py"` and `python tools/evidence_program/check.py`. The [guide](../../docs/evidence-program/research/training-data-feedback.md) gives exact source pins, local/synthetic CLI commands and six bounded standalone follow-up prompts.
