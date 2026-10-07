# Evidence program data files

These are research-register metadata, audit findings, proposed analytical recipes and synthetic preparation examples. No collected source body or live production dataset is added here. Start with the [program index](../../docs/evidence-program/README.md).

- [source_inventory.json](source_inventory.json) combines all 64 source records, their coverage mappings and the audit baseline. [global_sources.json](global_sources.json) contains GL001–GL040; [chinese_sources.json](chinese_sources.json) contains CN001–CN024. These partitions agree exactly with the combined record list.
- [coverage_mapping.json](coverage_mapping.json) preserves independent stage flags and pinned evidence links for each source. [coverage_references.json](coverage_references.json) records audited link paths and Git blob identifiers for offline link-membership checks.
- [baseline_metrics.json](baseline_metrics.json) carries the 28 metrics with units, denominators, interpretation and audit limits. Historical `main_matches_baseline` is a recorded check at the stated time, not a continuously updated assertion about main.
- [source_inventory.csv](source_inventory.csv), [coverage_mapping.csv](coverage_mapping.csv) and [baseline_metrics.csv](baseline_metrics.csv) are deterministic inspection views of the JSON. Array/object cells use compact JSON; empty cells represent absent/null values. These CSVs must not be treated as new independent observations.
- [chinese/aliases.json](chinese/aliases.json) is a conservative lookup with automatic merging disabled. [chinese/query_lexicon.json](chinese/query_lexicon.json) contains unexecuted retrieval templates. [chinese/test_cases.json](chinese/test_cases.json) contains 25 wholly invented semantic test vectors with 41 partial contract fragments. [chinese/reference_manifest.json](chinese/reference_manifest.json) pins the schema, specification and inventory they reference.
- [analysis_recipes.json](analysis_recipes.json) is a proposed analysis checklist, not a production configuration. [methodology_example_checks.json](methodology_example_checks.json) is the reproducible 19-check synthetic arithmetic result.

Changes to source records or metrics must update the combined inventory and corresponding CSV views together. Keep source IDs stable; add explicit reviewable revisions rather than silently turning candidate sources into collected evidence. The [offline checker](../../tools/evidence_program/README.md) verifies that the redundant views agree.

Third-party source rights are not changed by the repository's [data license](../LICENSE). Follow each source record's artifact-specific rights notes before any acquisition, retention or publication.
