# Open-model diffusion and accessibility research

Sources reviewed 8 October 2026 against main `4ecece6abd322932f70f121aef2e99fc3be467bb`. Both [source priorities](../source_priorities.md) and the [64-family inventory](../../../data/evidence-program/source_inventory.json) were read at that revision. This adds **four proposed new families and an accessibility enrichment of GL001**, with no inventory or frozen-contract change. OM identifiers are provisional research IDs.

The [machine-readable catalog](../../../data/evidence-program/research/open-model-diffusion.json) preserves artifact-specific access/rights, 29 qualified findings, duplicate-evidence rules, next actions and focused follow-up prompts. **All five families remain operationally unadmitted.** Two exact, openly licensed annotation files have been acquired and vendored solely for research regression tests outside `data/`; their separate CC BY 4.0 license is retained. The two-file offline reader is implemented. It is not a general collector, a canonical dataset importer or a model-usability test.

## Review outcome

Ranked for source utility: (1) Hugging Face Hub metadata history, (2) European Open Source AI Index, (3) Epoch accessibility enrichment. OLMo and PeaTMOSS provide complementary reproduction-support and static-reuse evidence. None supplies a representative denominator of successful practical use.

The smallest implementation is complete within this review: the reader handles 3,648-byte parent and 3,398-byte child annotation files, preserves 14 and 12 criteria, and reports one criteria-set change removing `api` and `package`. All surviving values and system/organization fields are unchanged. It emits zero inferred model-access revocations or model-license changes.

## Interpretation boundaries

- Keep open weights, open source and practical accessibility separate. Listed weights, a license label, a complete training recipe and a successful local run support different claims.
- Preserve source-reported assessments as assessments; do not convert `partial`/`closed` into our own certification or a formal-definition verdict.
- Keep release, repository revision, archive label, collection, observation and explicit assessment times separate. Unknown times remain unknown.
- Keep annotation/database/code/model/component rights distinct. A source declaration is scoped to its artifact and cannot clear every linked work.
- Downloads, forks and citations are imperfect activity/attention proxies. Static model-loading dependencies do not establish executed, sustained or business use.
- A changed tag or removed assessment criterion is not evidence of relicensing or revoked access. A license-change event requires linked before/after evidence for the relevant model artifact.
- No automatic identity merge, ecosystem-wide denominator, independent reproduction claim, API-alias/retirement registry, operational admission or p(doom) conversion is implemented.

## OM001 Hugging Face Hub metadata history

Broad historical repository metadata with overlapping daily/weekly evidence, incomplete access fields and activity proxies.

Inventory treatment: `new_relative_to_frozen_inventory`; no new inventory ID allocated.

Coverage: Observed model partitions begin 2024-07-24; pinned adding commit documents a 2026-09-30 model partition. This is not proof of gap-free coverage.

Cadence: Upstream states daily; archive uses weekly labels. Completeness and distinct observations are not established.

Access/export: Public viewers, file tree and Git/LFS pointer metadata; historical Parquet row extraction not attempted.

Rights: Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision.

### Observed sample/schema

These are source observations or documentation examples at the stated scope, not operational records.

OM001-F1: Current model schema only; do not apply the dataset-subset example to models or historical snapshots. [om001_artifact_02](https://huggingface.co/datasets/cfahlgren1/hub-stats/viewer/models/train)

```json
{
  "fields": [
    "id",
    "createdAt",
    "lastModified",
    "cardData",
    "downloads",
    "downloadsAllTime",
    "baseModels",
    "siblings",
    "config",
    "safetensors",
    "gguf"
  ],
  "missing_top_level_fields": [
    "gated",
    "private",
    "sha"
  ],
  "cardData": "JSON-formatted string",
  "baseModels": "structured relation",
  "siblings": "filename list"
}
```

OM001-F2: Publisher-declared hash and size only; payload not downloaded or independently hashed. [om001_artifact_07](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/commit/f148d7443c2514f7b4be9ec1cd281deadae9895e)

```json
{
  "path": "models/2026-09-30/models.parquet",
  "bytes": 1572863800,
  "declared_lfs_sha256": "9831c3066e56afb09e23166c85963e9ad94b626b1d02cc4d8f9c44e16d08b7b1"
}
```

OM001-F3: The code permits stale commit reuse and uses local-time datetime conversions. Labels, upstream commit time, archive commit time and observation time must stay separate. [om001_artifact_09](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/main/hub_download.py)

```json
{
  "source": "cfahlgren1/hub-stats",
  "cutoff": "timestamp < next_date_timestamp",
  "folder": "current_date"
}
```

OM001-F4: Do not invent changelog years or assume schema stability. [om001_artifact_03](https://huggingface.co/datasets/cfahlgren1/hub-stats/blob/main/README.md)

```json
{
  "lineage_heading": "July 25th, year omitted",
  "outage_heading": "July 9th, year omitted",
  "counters_heading": "Feb 27th, year omitted"
}
```

### Verified findings and qualifications

- **OM001-F1** (`source_reported_metadata`): The current models viewer exposes model metadata; it does not expose top-level gated/private/sha. Current model schema only; do not apply the dataset-subset example to models or historical snapshots. [om001_artifact_02](https://huggingface.co/datasets/cfahlgren1/hub-stats/viewer/models/train)
- **OM001-F2** (`access_or_rights_qualification`): Pinned 2026-09-30 model artifact is a large LFS payload pointer. Publisher-declared hash and size only; payload not downloaded or independently hashed. [om001_artifact_07](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/commit/f148d7443c2514f7b4be9ec1cd281deadae9895e)
- **OM001-F3** (`documentation`): Archive code labels the start of each weekly interval and selects the latest upstream file-affecting commit before the next interval. The code permits stale commit reuse and uses local-time datetime conversions. Labels, upstream commit time, archive commit time and observation time must stay separate. [om001_artifact_09](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/main/hub_download.py)
- **OM001-F4** (`documentation`): Daily-updated source documents added lineage/counter fields and a gguf integer-overflow import outage lasting several weeks. Do not invent changelog years or assume schema stability. [om001_artifact_03](https://huggingface.co/datasets/cfahlgren1/hub-stats/blob/main/README.md)
- **OM001-F5** (`documentation`): Eligible GET and HEAD requests to query files are counted; GGUF files can each count when cloning a repository. Not unique users, complete weight transfers or deployments. Never sum overlapping rolling windows. [om001_artifact_10](https://huggingface.co/docs/hub/models-download-stats)
- **OM001-F6** (`source_reported_metadata`): Repository presence, listed files, declared lineage and license tags support different metadata claims. A missing gating field is unknown. Listed weights do not demonstrate successful access; changed license tags do not alone prove relicensing. [om001_artifact_02](https://huggingface.co/datasets/cfahlgren1/hub-stats/viewer/models/train)

### Source and artifact locators

| Artifact | Access and locator | Rights scope |
| --- | --- | --- |
| [om001_artifact_01](https://huggingface.co/datasets/cfahlgren1/hub-stats) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_02](https://huggingface.co/datasets/cfahlgren1/hub-stats/viewer/models/train) | `primary_opened`. Model viewer header, line 31; hf_presence_boundary Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_03](https://huggingface.co/datasets/cfahlgren1/hub-stats/blob/main/README.md) | `primary_opened`. Changelog lines 127–154 Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_04](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / ODbL. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_05](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/main/README.md) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / ODbL. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_06](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/tree/main/models) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / ODbL. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_07](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/commit/f148d7443c2514f7b4be9ec1cd281deadae9895e) | `pointer_only`. LFS pointer diff, lines 108–110 LFS pointer declares 1,572,863,800 bytes and SHA-256 9831c3066e56afb09e23166c85963e9ad94b626b1d02cc4d8f9c44e16d08b7b1; payload bytes were not acquired or independently hashed. | `declared_license` / ODbL. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_08](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/f148d7443c2514f7b4be9ec1cd281deadae9895e/models/2026-09-30/models.parquet) | `pointer_only`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. LFS pointer declares 1,572,863,800 bytes and SHA-256 9831c3066e56afb09e23166c85963e9ad94b626b1d02cc4d8f9c44e16d08b7b1; payload bytes were not acquired or independently hashed. | `declared_license` / ODbL. source_declared_dataset_scope_excludes_models_and_embedded_third_party_works. Daily dataset card declares Apache-2.0; weekly archive card declares ODbL. Neither licenses models, weights or all embedded third-party card prose. ODbL derivative-export obligations need a scoped decision. |
| [om001_artifact_09](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/main/hub_download.py) | `primary_opened`. Code lines 140–180 and 187–190 Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om001_artifact_10](https://huggingface.co/docs/hub/models-download-stats) | `primary_opened`. How downloads are counted and GGUF handling Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |

Evidence overlap: Daily and weekly Hub collections share upstream records and are not independent corroboration. Model identities can overlap GL001, CN002, CN003 and developer artifacts; identity overlap is not an extra independent release.

Limitations:
- No historical Parquet payload read, full-file hash computation, selective extraction, transfer or model execution tested.
- License declarations do not clear embedded third-party card text, weights or linked code. ODbL downstream obligations require a scoped export decision.
- Schema history and collection outages need pinned per-snapshot inspection.
- Upstream commit and collection timestamps for the selected historical file remain unresolved; directory date is not a measurement timestamp.

## OM002 European Open Source AI Index

Component-level source assessments with explicit annotation reuse rights and version-sensitive criteria.

Inventory treatment: `new_relative_to_frozen_inventory`; no new inventory ID allocated.

Coverage: Predecessor launched July 2023; successor announced 2025-02-24. Site reports database generated 2026-08-27. Git history gives record states, not retroactive assessment dates.

Cadence: Periodic research-team/community updates; no fixed cadence promised.

Access/export: Public small YAML files at immutable Git commits, retrieved via GitHub base64 connector.

Rights: The exact two annotation YAML headers declare CC BY 4.0 with index-site and 2024 paper attribution. The later README also requests the index DOI. This licenses annotations only, not Llama or linked evidence.

### Observed sample/schema

These are source observations or documentation examples at the stated scope, not operational records.

OM002-F1: Only these two annotation fixtures are acquisition-ready for the bounded reader. [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)

```json
{
  "files": [
    {
      "label": "before",
      "commit": "e39b4edd41811e975f9262d77ee286796d7792e5",
      "git_blob_sha1": "ce4e77557ac41d97ec59d872a2d6b7f19229ecdb",
      "bytes": 3648,
      "sha256": "89d1f517d5171d832c59359e83d6c7b7577aaf0c14f8a06c08b01adbbcdfcc17",
      "criterion_count": 14
    },
    {
      "label": "after",
      "commit": "ff85b6ff442035e41c9492cefa54f78be0b827fc",
      "git_blob_sha1": "855671b61e19ccdefa95879c0d85a4c5eb77dc5f",
      "bytes": 3398,
      "sha256": "cc93e48df6a72c3e15d05ae2a056fcf775d4ccf7c590bc26c13ebbdb9fea6ec8",
      "criterion_count": 12
    }
  ]
}
```

OM002-F2: Criterion removal is a schema change, not model-access revocation or license change. [om002_artifact_07](https://api.github.com/repos/Language-Technology-Assessment/main-database/git/commits/ff85b6ff442035e41c9492cefa54f78be0b827fc), [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)

```json
{
  "parent_child_relationship_verified": true,
  "after_parent_commit": "e39b4edd41811e975f9262d77ee286796d7792e5",
  "git_metadata_url": "https://api.github.com/repos/Language-Technology-Assessment/main-database/git/commits/ff85b6ff442035e41c9492cefa54f78be0b827fc",
  "commit_message": "Remove package and api fields",
  "removed_criteria": [
    "api",
    "package"
  ],
  "added_criteria": [],
  "changed_surviving_keys": [],
  "byte_identical_after_removing_package_api_blocks": true,
  "observations_total": 26,
  "inferred_model_access_revocations": 0,
  "inferred_model_license_changes": 0,
  "nested_extra_property": {
    "path": "api.metaprompt",
    "value": "closed"
  },
  "raw_model_license_label": "Llama 3.3 Community License Agreement"
}
```

OM002-F3: Do not promote nested properties into separate criteria or turn missing schema criteria into closed. [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)

```json
{
  "null_links": [
    "datasources_basemodel",
    "datasources_endmodel",
    "weights_basemodel",
    "paper",
    "datasheet"
  ],
  "nested_extra_property": "api.metaprompt"
}
```

OM002-F4: Commit timestamps are not explicit assessment dates; no invented December 1 date. [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml), [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml)

```json
{
  "name": "Llama 3.3",
  "base": "Llama-3.3-70B",
  "end": "Llama-3.3-70B-Instruct",
  "release_date": "2024-12",
  "release_precision": "month",
  "assessment_timestamp": null,
  "raw_model_license": "Llama 3.3 Community License Agreement"
}
```

OM002-F5: Preserve as source assessments; note inference-only code explanation without independently reclassifying it. [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)

```json
{
  "weights_basemodel": "closed",
  "weights_endmodel": "partial",
  "trainingcode": "partial",
  "licenses": "closed"
}
```

OM002-F6: Preserve actual criterion-set fingerprint instead of inventing a formal schema version. [om002_artifact_02](https://github.com/Language-Technology-Assessment/main-database/blob/83011c306a1565ee1a6ecf4c881f09caa118d7e9/readme.md)

```json
{
  "empty_class": "NA",
  "intro_dimension_count": 14,
  "actual_post_change_criteria_count": 12
}
```

OM002-F7: Retain all applicable attribution; does not license assessed models or evidence links. [om002_artifact_02](https://github.com/Language-Technology-Assessment/main-database/blob/83011c306a1565ee1a6ecf4c881f09caa118d7e9/readme.md), [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)

```json
{
  "fixture_notice": "site + Liesenfeld and Dingemanse 2024 paper",
  "readme_notice": "index DOI 10.5281/zenodo.15386042"
}
```

### Verified findings and qualifications

- **OM002-F1** (`byte_verified_diff`): Both exact fixture byte streams were retrieved and their Git blob SHA-1 values independently recomputed. Only these two annotation fixtures are acquisition-ready for the bounded reader. [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)
- **OM002-F2** (`byte_verified_diff`): After is the immediate Git child of before; deleting package and api blocks from before reproduces after byte-for-byte. Criterion removal is a schema change, not model-access revocation or license change. [om002_artifact_07](https://api.github.com/repos/Language-Technology-Assessment/main-database/git/commits/ff85b6ff442035e41c9492cefa54f78be0b827fc), [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)
- **OM002-F3** (`byte_verified_diff`): Five explicit null evidence links per revision remain distinguishable from missing criteria; before contains nested api.metaprompt=closed. Do not promote nested properties into separate criteria or turn missing schema criteria into closed. [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)
- **OM002-F4** (`assessor_annotation`): Llama 3.3 record preserves base/end identities and a month-precision release date. Commit timestamps are not explicit assessment dates; no invented December 1 date. [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml), [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml)
- **OM002-F5** (`assessor_annotation`): The index reports closed base weights, partial end weights, partial training code and closed licenses. Preserve as source assessments; note inference-only code explanation without independently reclassifying it. [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)
- **OM002-F6** (`documentation`): Selection targets generative models marketed as open; generally latest version/largest family member, with possible multi-modality overlap. Preserve actual criterion-set fingerprint instead of inventing a formal schema version. [om002_artifact_02](https://github.com/Language-Technology-Assessment/main-database/blob/83011c306a1565ee1a6ecf4c881f09caa118d7e9/readme.md)
- **OM002-F7** (`access_or_rights_qualification`): Exact YAML headers specify CC BY 4.0 annotation reuse with index link and 2024 paper attribution; later README additionally requests index DOI citation. Retain all applicable attribution; does not license assessed models or evidence links. [om002_artifact_02](https://github.com/Language-Technology-Assessment/main-database/blob/83011c306a1565ee1a6ecf4c881f09caa118d7e9/readme.md), [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml), [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml)

### Source and artifact locators

| Artifact | Access and locator | Rights scope |
| --- | --- | --- |
| [om002_artifact_01](https://osai-index.eu/) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om002_artifact_02](https://github.com/Language-Technology-Assessment/main-database/blob/83011c306a1565ee1a6ecf4c881f09caa118d7e9/readme.md) | `primary_opened`. eu_methodology; eu_attribution Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml) | `pinned_bytes_verified`. eu_fixture_bytes; eu_nested_schema Entire small annotation YAML decoded losslessly from GitHub base64; SHA-256 and Git blob SHA-1 independently recomputed. Original bytes retained as a separately licensed research fixture. | `declared_license` / CC-BY-4.0. annotation_data_only_excludes_models_and_linked_works. The exact two annotation YAML headers declare CC BY 4.0 with index-site and 2024 paper attribution. The later README also requests the index DOI. This licenses annotations only, not Llama or linked evidence. |
| [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml) | `pinned_bytes_verified`. eu_identity_time; eu_reported_classes Entire small annotation YAML decoded losslessly from GitHub base64; SHA-256 and Git blob SHA-1 independently recomputed. Original bytes retained as a separately licensed research fixture. | `declared_license` / CC-BY-4.0. annotation_data_only_excludes_models_and_linked_works. The exact two annotation YAML headers declare CC BY 4.0 with index-site and 2024 paper attribution. The later README also requests the index DOI. This licenses annotations only, not Llama or linked evidence. |
| [om002_artifact_05](https://osai-index.eu/news/introducing-eu-osai-index/) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om002_artifact_06](https://doi.org/10.5281/zenodo.15386042) | `documentation_only`. Index DOI citation requested in the pinned source README. Attribution DOI verified as a source-supplied reference; no DOI deposit payload acquired. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om002_artifact_07](https://api.github.com/repos/Language-Technology-Assessment/main-database/git/commits/ff85b6ff442035e41c9492cefa54f78be0b827fc) | `primary_opened`. eu_exact_diff Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |

Evidence overlap: Opening up ChatGPT is predecessor lineage, not an independent copy of successor assessments. Website tables, YAML, paper tables and releases may reproduce the same annotations. An openness assessment is distinct evidence about a shared release, not a second model-release event.

Limitations:
- Do not present source classes as formal OSI certification or our own execution tests.
- Current family selection and largest-model practice exclude a representative all-release denominator.
- No model-weight, linked license assent, download or execution attempt.

## OM003 Epoch AI accessibility enrichment

Accessibility enrichment of the existing GL001 model-table artifact; current categories do not date original availability.

Inventory treatment: `existing_family_enrichment`; inventory ID: `GL001`.

Coverage: Publisher says 1950 to present; all-model CSV update listed 2026-10-05. Current categories cannot establish historical accessibility at release.

Cadence: CSV documentation states daily; major additions generally within two weeks, other literature-review additions periodic.

Access/export: Publisher-linked public CSV; populated field documentation observed, complete CSV not downloaded.

Rights: Epoch declares CC BY 4.0 for its dataset with source/author attribution; referenced model artifacts and source documents have separate rights.

### Observed sample/schema

These are source observations or documentation examples at the stated scope, not operational records.

OM003-F1: A documentation example, not a row retrieved from the CSV. [om003_artifact_03](https://epoch.ai/data/ai-models-documentation/records)

```json
{
  "model": "Llama-2 70B",
  "publication_date": "2023-07-18",
  "model_accessibility": "Open weights (restricted use)",
  "training_code_accessibility": "Unreleased"
}
```

OM003-F4: Does not clear model weights or references. [om003_artifact_01](https://epoch.ai/data/ai-models)

```json
{
  "download_url": "https://epoch.ai/data/all_ai_models.csv",
  "listed_updated": "2026-10-05",
  "license": "CC-BY-4.0"
}
```

### Verified findings and qualifications

- **OM003-F1** (`source_reported_metadata`): Documentation sample is Llama-2 70B with differing weight and training-code availability. A documentation example, not a row retrieved from the CSV. [om003_artifact_03](https://epoch.ai/data/ai-models-documentation/records)
- **OM003-F2** (`documentation`): Training-code field explanation repeats model-access categories and examples. Preserve raw fields; do not silently repair publisher definitions. [om003_artifact_03](https://epoch.ai/data/ai-models-documentation/records)
- **OM003-F3** (`documentation`): Known month/unknown day is encoded as YYYY-MM-15; known year/unknown month-day as YYYY-07-01. An observed date landing on those days is not itself evidence of imputation. [om003_artifact_03](https://epoch.ai/data/ai-models-documentation/records)
- **OM003-F4** (`access_or_rights_qualification`): Publisher links all_ai_models.csv and licenses Epoch data under attribution terms linking CC BY 4.0. Does not clear model weights or references. [om003_artifact_01](https://epoch.ai/data/ai-models)
- **OM003-F5** (`documentation`): Notability depends on selected benchmark, citation, usage and historical-significance criteria. Current classifications are not license-change events or a representative denominator of all models. [om003_artifact_01](https://epoch.ai/data/ai-models)

### Source and artifact locators

| Artifact | Access and locator | Rights scope |
| --- | --- | --- |
| [om003_artifact_01](https://epoch.ai/data/ai-models) | `primary_opened`. Downloads, Citations, Python Import and licensing FAQ; epoch_selection Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om003_artifact_02](https://epoch.ai/data/all_ai_models.csv) | `pointer_only`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Official linked CSV endpoint verified through publisher documentation; full CSV bytes not downloaded. | `declared_license` / CC-BY-4.0. epoch_dataset_only_excludes_references_and_models. Epoch declares CC BY 4.0 for its dataset with source/author attribution; referenced model artifacts and source documents have separate rights. |
| [om003_artifact_03](https://epoch.ai/data/ai-models-documentation/records) | `primary_opened`. Records table, model name and accessibility rows; Training code accessibility row, lines 202–203; Publication date row Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om003_artifact_04](https://epoch.ai/data/ai-models-documentation/downloads) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om003_artifact_05](https://epoch.ai/data/ai-models-documentation) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |

Evidence overlap: Keep GL001, do not register a duplicate model-table family. GL034 AI Index can synthesize Epoch evidence and should retain upstream dependency.

Limitations:
- Resolve training-code definition inconsistency before automatic cross-source mapping.
- Need a dated CSV snapshot and per-record evidence before any accessibility timeline.
- Purposive subset and possible date placeholders prevent naïve ecosystem percentages or exact-date claims.

## OM004 Ai2 OLMo reproducibility artifacts

Release-specific materials supporting reuse/reproduction, with component-specific rights and checkpoint-format constraints.

Inventory treatment: `new_relative_to_frozen_inventory`; no new inventory ID allocated.

Coverage: Initial OLMo announcement 2024-02-01; OLMo 2 announcement 2024-11-26. No claim of complete later-family coverage.

Cadence: Release-driven, irregular.

Access/export: Public small manifest, documentation, model card and file listing; no binary transfer.

Rights: Pinned repository/model-code declarations are Apache-2.0. The olmo-mix-1124 dataset instead declares ODC-By 1.0 plus Common Crawl terms and differing constituent terms. No blanket linked-artifact clearance.

### Observed sample/schema

These are source observations or documentation examples at the stated scope, not operational records.

OM004-F1: Training checkpoint entries, not 36 public releases or adopters. [om004_artifact_05](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/configs/official-1124/OLMo-2-1124-7B-stage2.csv)

```json
{
  "blob_sha1": "3ab613d11b9879c96e5a1d64d43d0369c90fa2d8",
  "fields": [
    "Ingredient",
    "Step",
    "Checkpoint Directory"
  ],
  "first": {
    "Ingredient": "1",
    "Step": "1000",
    "Checkpoint Directory": "https://olmo-checkpoints.org/ai2-llm/peteish7/stage2/olmo-7b-1124_stage2_ingredient1/step1000-unsharded/"
  },
  "rows": 36,
  "ingredients": 3
}
```

OM004-F2: Documentation inspected, no conversion or training executed. [om004_artifact_06](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/docs/Checkpoints.md)

```json
{
  "blob_sha1": "ad65c1a214229d71d22b2cd449b8ac3b57bb7488",
  "native_members": [
    "config.yaml",
    "model.safetensors",
    "optim.safetensors",
    "train.pt"
  ]
}
```

OM004-F4: Storage volume, not measured runtime memory or affordability. [om004_artifact_04](https://huggingface.co/allenai/OLMo-2-1124-7B/tree/main)

```json
{
  "displayed_storage": "29.2 GB"
}
```

### Verified findings and qualifications

- **OM004-F1** (`source_reported_metadata`): Pinned stage-two CSV has 36 data rows across three ingredients. Training checkpoint entries, not 36 public releases or adopters. [om004_artifact_05](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/configs/official-1124/OLMo-2-1124-7B-stage2.csv)
- **OM004-F2** (`documentation`): Native checkpoints include model/optimizer/training state; Transformers and HF OLMo checkpoints cannot feed native training script directly. Documentation inspected, no conversion or training executed. [om004_artifact_06](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/docs/Checkpoints.md)
- **OM004-F3** (`access_or_rights_qualification`): Documentation says checkpoint directories are not directly browsable while member files are public. No member-file download was tested; do not infer absent weights from directory HTTP failure. [om004_artifact_06](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/docs/Checkpoints.md)
- **OM004-F4** (`source_reported_metadata`): Selected model file listing reports 29.2 GB stored files. Storage volume, not measured runtime memory or affordability. [om004_artifact_04](https://huggingface.co/allenai/OLMo-2-1124-7B/tree/main)
- **OM004-F5** (`source_reported_metadata`): Selected model card describes logs as coming soon. Keep promised and delivered artifacts separate; no exhaustive search for later logs was made. [om004_artifact_03](https://huggingface.co/allenai/OLMo-2-1124-7B)
- **OM004-F6** (`access_or_rights_qualification`): olmo-mix-1124 declares ODC-By 1.0 and Common Crawl terms, distinct from the model/code Apache declaration. Do not flatten training-data rights into a model license. [om004_artifact_08](https://huggingface.co/datasets/allenai/olmo-mix-1124)

### Source and artifact locators

| Artifact | Access and locator | Rights scope |
| --- | --- | --- |
| [om004_artifact_01](https://allenai.org/blog/olmo2) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om004_artifact_02](https://allenai.org/blog/olmo-open-language-model-87ccfc95f580) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om004_artifact_03](https://huggingface.co/allenai/OLMo-2-1124-7B) | `primary_opened`. olmo_pending_logs Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. The card declares model/code Apache-2.0; this is not automatically a license for the page prose or all linked data. |
| [om004_artifact_04](https://huggingface.co/allenai/OLMo-2-1124-7B/tree/main) | `primary_opened`. olmo_storage Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om004_artifact_05](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/configs/official-1124/OLMo-2-1124-7B-stage2.csv) | `primary_opened`. olmo_manifest Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. pinned_repository_material_only_excludes_linked_components. Pinned root repository license inspected. Linked weights/data/third-party components require their own rights evidence. |
| [om004_artifact_06](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/docs/Checkpoints.md) | `primary_opened`. olmo_checkpoint_formats; olmo_directory_access Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. pinned_repository_material_only_excludes_linked_components. Pinned root repository license inspected. Linked weights/data/third-party components require their own rights evidence. |
| [om004_artifact_07](https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/LICENSE) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. pinned_repository_material_only_excludes_linked_components. Pinned root repository license inspected. Linked weights/data/third-party components require their own rights evidence. |
| [om004_artifact_08](https://huggingface.co/datasets/allenai/olmo-mix-1124) | `primary_opened`. Dataset license paragraph and constituent table Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / ODC-By-1.0. declared_dataset_license_subject_to_common_crawl_and_constituent_terms. Pinned repository/model-code declarations are Apache-2.0. The olmo-mix-1124 dataset instead declares ODC-By 1.0 plus Common Crawl terms and differing constituent terms. No blanket linked-artifact clearance. |

Evidence overlap: An OLMo release may share identity with Hub/Epoch/openness-index entries; checkpoint, announcement and assessment claims differ. One producer does not represent ecosystem-wide access.

Limitations:
- Reproducibility support is not successful independent reproduction.
- Model card says logs coming soon; this cannot establish log delivery.
- Other linked dataset/code artifact rights require individual review.
- Checkpoint directory listing failure is not proof of inaccessible member files.

## OM005 PeaTMOSS model-to-software reuse

Historical static model-to-software dependency evidence, distinct from downloads or measured deployment.

Inventory treatment: `new_relative_to_frozen_inventory`; no new inventory ID allocated.

Coverage: Primarily July–August 2023, with retained histories. Later repository commits do not refresh underlying observations.

Cadence: Historical collection; no verified recurring refresh.

Access/export: Public SQL schema, scripts and sample ZIP metadata; full material is directed to Globus with account/setup instructions.

Rights: Root code license is Apache-2.0; nested license-analysis code is BSD-3-Clause. Harvested metadata, sample SQLite contents and full snapshot redistribution rights remain unverified.

### Observed sample/schema

These are source observations or documentation examples at the stated scope, not operational records.

OM005-F1: Observed schema, not an invented concrete dependency edge. [om005_artifact_03](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/PeaTMOSS.sql)

```json
{
  "blob_sha1": "fde81ecf47acb10b5f9ea36a9e2c224732031d7c",
  "bytes": 16807,
  "table": "model_to_reuse_repository",
  "columns": [
    "model_id",
    "reuse_repository_id"
  ],
  "related": [
    "reuse_file.path",
    "hf_commit",
    "model_to_license",
    "reuse_repository"
  ]
}
```

OM005-F2: Metadata only; bytes and internal contents were not retrieved. [om005_artifact_04](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/PeaTMOSS_SAMPLE.db.zip)

```json
{
  "filename": "PeaTMOSS_SAMPLE.db.zip",
  "bytes": 14255498,
  "git_blob_sha1": "855c4ba6352c598141eff7d079c3396c13527cc6"
}
```

OM005-F3: Author-reported historical counts; mapped subset differs from broader cohort. [om005_artifact_01](https://arxiv.org/html/2402.00699v1)

```json
{
  "links": 44337,
  "mapped_models": 2530,
  "mapped_downstream_repositories": 15129,
  "broader_downstream_cohort": 28575
}
```

OM005-F5: Public documentation does not establish anonymous or authorized bulk access. [om005_artifact_05](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/README.md)

```json
{
  "metadata_size_reported": "8.32 GB including enhanced metadata",
  "full_size_reported": "48.2 TB"
}
```

### Verified findings and qualifications

- **OM005-F1** (`source_reported_metadata`): SQL defines model_to_reuse_repository with model_id and reuse_repository_id as the composite primary key. Observed schema, not an invented concrete dependency edge. [om005_artifact_03](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/PeaTMOSS.sql)
- **OM005-F2** (`source_reported_metadata`): Pinned sample archive is listed with exact metadata. Metadata only; bytes and internal contents were not retrieved. [om005_artifact_04](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/PeaTMOSS_SAMPLE.db.zip)
- **OM005-F3** (`study_reported_measurement`): Paper reports 44,337 mapped links between 2,530 models and 15,129 downstream repositories. Author-reported historical counts; mapped subset differs from broader cohort. [om005_artifact_01](https://arxiv.org/html/2402.00699v1)
- **OM005-F4** (`documentation`): Method searched public non-fork non-archived Sourcegraph-indexed repositories with at least five stars using Python loading signatures and static analysis. Private use, unsupported loaders and dynamic loading are omitted; enhanced LLM-extracted metadata needs separate provenance. [om005_artifact_01](https://arxiv.org/html/2402.00699v1)
- **OM005-F5** (`access_or_rights_qualification`): README directs full database and snapshots to Globus and explains account/setup steps. Public documentation does not establish anonymous or authorized bulk access. [om005_artifact_05](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/README.md)

### Source and artifact locators

| Artifact | Access and locator | Rights scope |
| --- | --- | --- |
| [om005_artifact_01](https://arxiv.org/html/2402.00699v1) | `primary_opened`. Abstract and section 4.2.2; Sections 4.2.2 and 5 Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om005_artifact_02](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. No artifact-specific redistribution grant established for this page/body. Public accessibility alone is not permission. |
| [om005_artifact_03](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/PeaTMOSS.sql) | `primary_opened`. peat_schema Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. repository_code_and_documentation_only_excludes_harvested_data. Root code license is Apache-2.0; nested license-analysis code is BSD-3-Clause. Harvested metadata, sample SQLite contents and full snapshot redistribution rights remain unverified. |
| [om005_artifact_04](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/PeaTMOSS_SAMPLE.db.zip) | `pointer_only`. peat_sample_metadata Sample archive listing only: 14,255,498 bytes and Git blob SHA 855c4ba6352c598141eff7d079c3396c13527cc6. Archive and SQLite contents not acquired. | `unknown`. this_artifact_only_no_inheritance_to_linked_material. Harvested sample data rights unknown; root code license does not automatically apply to SQLite contents. |
| [om005_artifact_05](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/README.md) | `primary_opened`. peat_access Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. repository_code_and_documentation_only_excludes_harvested_data. Root code license is Apache-2.0; nested license-analysis code is BSD-3-Clause. Harvested metadata, sample SQLite contents and full snapshot redistribution rights remain unverified. |
| [om005_artifact_06](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/LICENSE) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / Apache-2.0. repository_code_and_documentation_only_excludes_harvested_data. Root code license is Apache-2.0; nested license-analysis code is BSD-3-Clause. Harvested metadata, sample SQLite contents and full snapshot redistribution rights remain unverified. |
| [om005_artifact_07](https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/License-Analysis/LICENSE) | `primary_opened`. Publisher page, file-tree entry or source-linked attribution reference inspected in bounded review. Public primary metadata/documentation inspected; not proof of successful model/data payload transfer. | `declared_license` / BSD-3-Clause. repository_code_and_documentation_only_excludes_harvested_data. Root code license is Apache-2.0; nested license-analysis code is BSD-3-Clause. Harvested metadata, sample SQLite contents and full snapshot redistribution rights remain unverified. |

Evidence overlap: GL040 is a discovery route for the paper, not a registration of this dataset. Hub model attributes duplicate upstream evidence; dependency edges and preserved source-file/commit evidence are distinct.

Limitations:
- Full anonymous access unverified; no login, installation, transfer, sample archive or full database download.
- Dataset and snapshot redistribution rights unresolved independently of code licenses.
- Static dependency evidence is not production execution, sustained use or business adoption.

## Completed offline reader

[read_open_model_yaml.py](../../../tools/evidence_program/read_open_model_yaml.py) is deliberately restricted to this one reviewed parent/child pair. The supplied local files must match both fixed SHA-256 and Git blob pins and exact source byte counts. It reads at most 64 KiB per file and accepts no URLs or standard-input stream. No source, model or evidence URL is opened. Explicit UNC/device/network path prefixes are rejected before opening; ordinary drive-letter paths remain supported. The reader issues no network requests, but cannot prove that the operating system has not mounted a remote filesystem behind a supplied regular-file path.

### Exact pinned inputs

| Revision | Commit | Git blob | SHA-256 | Bytes |
| --- | --- | --- | --- | --- |
| [eu_before](https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml) | `e39b4edd41811e975f9262d77ee286796d7792e5` | `ce4e77557ac41d97ec59d872a2d6b7f19229ecdb` | `89d1f517d5171d832c59359e83d6c7b7577aaf0c14f8a06c08b01adbbcdfcc17` | 3648 |
| [eu_after](https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml) | `ff85b6ff442035e41c9492cefa54f78be0b827fc` | `855671b61e19ccdefa95879c0d85a4c5eb77dc5f` | `cc93e48df6a72c3e15d05ae2a056fcf775d4ccf7c590bc26c13ebbdb9fea6ec8` | 3398 |

The child is the immediate Git child of the parent. Parent commit time is `2026-03-12T13:10:33Z`; child time is `2026-03-13T14:41:47Z`. Neither is an explicit assessment timestamp. Deleting the parent’s `api` and `package` blocks yields the child byte-for-byte. The base/end model identifiers and raw `Llama 3.3 Community License Agreement` label are unchanged.

### Run locally

Use Python 3.12 and the reviewed, pinned [requirements](../../../tools/evidence_program/requirements-ci.txt). PyYAML 6.0.3 is used for bounded syntax events, never Python-object construction. Dependencies are installed only through the existing explicit CI requirement-install step or by the operator; the reader never installs software.

```bash
python tools/evidence_program/read_open_model_yaml.py \
  tools/evidence_program/tests/fixtures/open-model-yaml/before-llama-3.3.yaml \
  tools/evidence_program/tests/fixtures/open-model-yaml/after-llama-3.3.yaml

python tools/evidence_program/check.py
python -m unittest discover -s tools/evidence_program/tests -p "test_open_model*.py" -v
```

JSON is written to stdout; the reader does not persist, import or publish output. For this pair it retains exact raw YAML, complete source field documents and 26 criterion review records with deterministic identities and derived criterion-set fingerprints. A derived fingerprint is not an official source schema-version number. Full 14-criterion alignment marks removed child criteria `absent_from_schema`, never recoded as `closed`. Provenance retains the original fixture acquisition time `2026-10-08T00:20:44Z`, separately from current execution time and unknown assessment time.

Every non-null YAML scalar stays text, including dates, numbers and booleans. This avoids silent date/numeric coercion and is an explicit preservation representation, not a general YAML-native type model. YAML nulls remain null; exact original bytes remain in `original_yaml` so spelling/comments/quotes are auditable. Unknown nested properties and source notes survive, including `api.metaprompt=closed` and five explicit null criterion links in each revision.

The syntax-event parser rejects tags, anchors, aliases, duplicate keys, multiple documents and malformed structures. Limits are 4,096 parser events, nesting depth 32 and 16 KiB per scalar, in addition to the 64 KiB file bound. Local non-regular files and, where supported, symlinks are rejected. The public entry point has no custom hash allowlist or permissive parsing switch. Synthetic tests exercise internal parser behavior without weakening the fixed-hash public entry point.

### Rights and attribution

The two unchanged fixtures are retained under [tools/evidence_program/tests/fixtures/open-model-yaml](../../../tools/evidence_program/tests/fixtures/open-model-yaml/NOTICE.md), outside `data/` and its CC0 dedication. Original source comments remain intact. The software license does not relicense these annotations. A fixture-local `.gitattributes` forces LF endings for only these two YAML files so a Windows checkout with automatic CRLF conversion retains the pinned bytes. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) applies only to the annotation data; no assessed model, weights or linked evidence is licensed by that grant.

Attribution: [European Open Source AI Index](https://osai-index.eu/); Liesenfeld, A. and Dingemanse, M. (2024), “Rethinking open source generative AI: open-washing and the EU AI Act,” Proceedings of the 2024 ACM Conference on Fairness, Accountability, and Transparency, pp. 1774–1787. The later source README additionally requests the [index-files DOI](https://doi.org/10.5281/zenodo.15386042). The fixtures are unmodified; parsed JSON and comparison reports are transformed annotations and derived comparisons, without implied licensor endorsement.

### Acceptance tests

1. Exactly two supplied local regular files, each at most 65536 bytes, and fixed before/after hash allowlist; no network.
2. Reject wrong hash, reversed inputs, oversize, malformed YAML, duplicate keys, tags, anchors, aliases and bounded-work violations.
3. Emit 14 parent and 12 child criterion review records, with no system/org pseudo-criteria.
4. Emit one criteria-set change removing api and package; all 12 surviving criteria are identical.
5. Emit zero inferred model-access revocation or model-license change events.
6. Retain 2024-12 as a month string and leave explicit assessment timestamp null; source commit time is separate.
7. Preserve source raw YAML, complete nested fields and unknown properties, including api.metaprompt=closed.
8. Preserve source null links, notes and raw class labels; a missing criterion is absent_from_schema rather than closed.
9. Keep annotation CC BY 4.0 attribution separate from raw Llama 3.3 Community License Agreement label.
10. Repeated reads yield deterministic identifiers and output; revision/hash provenance is attached.
11. Vendored real fixtures retain exact original bytes and scoped notices outside data/; synthetic cases are labeled as such.
12. Output is experimental_review_records_not_admitted and makes no canonical-schema, runtime-usability, adoption or p(doom) claim.

The aggregate check runs the real pinned files and synthetic hostile/preservation cases as well as existing contract/integration checks. Catalog validation is metadata consistency, not an independent model-property test or legal approval. No live source download is part of deterministic CI. Actual fixture checks are distinguished from synthetic tests; no model-runtime, hardware-affordability, full-source historical extraction or production import test is claimed.

## Corrections and completed bounded work

- **baseline_refresh** (`context_updated`): Earlier review baseline 6c2a4aa531cd5b8e5411c25ee08569d707a682b1 is historical. This pass reads both requested files at 4ecece6abd322932f70f121aef2e99fc3be467bb; frozen inventory remains version 1.1 with 64 records.
- **rights_attribution_expand** (`clarified`): Retain exact fixture site/paper attribution and add later README index-files DOI citation; annotation CC BY 4.0 never covers the assessed Llama artifacts.
- **hf_observation_clock** (`strengthened`): Weekly script uses local-time datetime conversions and a next-interval cutoff. Do not equate week labels with collection times, claim unique weekly observations, or assume timezone-independent cutoff behavior.
- **peat_sample_size** (`precision_added`): Verified sample filename is PeaTMOSS_SAMPLE.db.zip, 14,255,498 bytes. Approximate 14.3 MB claim is supported; payload remains uninspected.
- **no_false_access_events** (`supported_restraint`): Exact before/after index files support one criterion-set change and zero supported access-revocation/license-change events.
- Exact fixture rights, raw bytes, immediate-parent relation, month precision and nested/null preservation are verified. The formerly proposed bounded reader is now implemented and tested; production mapping and broader source collection remain separate.

## Next actions

| Action | Status | Work and completion evidence |
| --- | --- | --- |
| OM-A1 (OM002) | `completed` | Verify the exact parent/child annotation bytes, immediate-parent relation, source dates and per-file annotation rights. Completion: Both Git blob hashes and SHA-256 digests recomputed; parent/child metadata and the CC BY 4.0 annotation header inspected. Two untouched files retained only as separately licensed research fixtures, with attribution and rights exclusion notices. |
| OM-A2 (OM002) | `completed` | Implement and test the fixed-hash offline two-file reader. Completion: Deterministic real-fixture regression returns 14 and 12 criteria, one criteria-set change removing api/package, unchanged surviving values and zero inferred model-access/license events; hostile/malformed/oversize/hash tests run in the aggregate gate. |
| OM-A3 (OM001) | `pending_rights_review` | Establish bounded historical Hub-row access, schema continuity and artifact-specific rights before any snapshot materialization. Completion: A small, approved, immutable row sample with provenance, selected upstream commit times, missingness/schema mapping and separately supported card/annotation rights; no full Parquet download required. Apache-2.0 and ODbL dataset-card labels alone do not clear all embedded third-party card prose. |
| OM-A4 (OM003) | `open` | Resolve the training-code field-definition inconsistency and date-precision mapping for an accessibility enrichment of GL001. Completion: Primary publisher clarification or internally consistent raw documentation examples retained with uncertainty; one immutable bounded export sample only after its intended scope is reviewed. No new inventory ID, assumed license-change event or release-day imputation. |
| OM-A5 (OM004) | `open` | Verify the selected OLMo release's delivered reproducibility materials and component-specific terms. Completion: Version-pinned links and access state for logs/recipe/config/training-data components; distinguish a promised item from delivered material and reproduction support from an independently executed reproduction. No weights downloaded or model run. |
| OM-A6 (OM005) | `blocked_access` | Resolve PeaTMOSS harvested-data/sample/full-snapshot reuse terms and bounded access conditions. Completion: Explicit applicable data rights and an author-supported bounded export path, separate from root Apache/BSD code licenses; Globus authentication remains a separate approval/access step. Do not treat archive listing as inspected SQLite contents. |
| OM-A7 (OM002) | `pending_contract_review` | Review a lossless mapping before any future operational import or expansion beyond the exact two fixtures. Completion: Separate reviewed mapping preserves raw YAML/nested source fields, assessment/version dates, criterion-set identity and annotation/model-license separation. Current output remains experimental and unadmitted; no canonical-contract change is established as necessary. |

## Focused follow-up prompts

These prompts address the remaining bounded gaps. They do not authorize operational collection, accounts, outreach or publication.

### OM-A3

Historical partition labels and declared metadata licenses do not establish row-level time identity or third-party text reuse.

Verified entry points: https://huggingface.co/datasets/cfahlgren1/hub-stats/blob/main/README.md ; https://huggingface.co/datasets/cfahlgren1/hub-stats/viewer/models/train ; https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/main/README.md ; https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/main/hub_download.py ; immutable pointer https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots/blob/f148d7443c2514f7b4be9ec1cd281deadae9895e/models/2026-09-30/models.parquet . This last payload is 1,572,863,800 bytes and must not be downloaded for this check. Main-branch documentation is mutable; record the revision you inspect. Review only the Hugging Face cfahlgren1/hub-stats and hfmlsoc/hub_weekly_snapshots primary documentation, script and immutable metadata. Establish how a weekly label selects an upstream revision and can repeat stale data. Identify a supported bounded export of at most 20 model metadata rows, but do not download it until artifact-specific reuse of intended fields and byte bounds are clear. Separate daily Apache-2.0 and weekly ODbL dataset-card declarations from linked models and embedded third-party model-card prose. Return exact revision/path/selected-commit time, observed schema, missingness and rights holds. No login, bulk Parquet, model download, repository edits or ongoing collection.

### OM-A4

Epoch is already GL001; field-definition ambiguity and placeholder dates can create false availability histories.

Read Epoch AI model records and downloads documentation at https://epoch.ai/data/ai-models-documentation/records and https://epoch.ai/data/ai-models-documentation/downloads. Resolve the training-code accessibility definition that appears to repeat model-access categories, retaining the Llama-2 70B example and raw labels. Explain explicit date-precision evidence versus placeholder-day coincidence. Return one bounded mapping proposal with provenance and unresolved questions, keeping present-day category separate from original-release access. No full CSV, license-change inference, new source ID, repository edits or external outreach.

### OM-A5

OLMo materials and listings document support for reproduction, not successful independent reproduction.

Exact starting points: https://huggingface.co/allenai/OLMo-2-1124-7B ; https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/docs/Checkpoints.md ; https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/configs/official-1124/OLMo-2-1124-7B-stage2.csv ; https://github.com/allenai/OLMo/blob/090253dac6688f2532509daa7aa2eb5fae50e956/LICENSE ; https://huggingface.co/datasets/allenai/olmo-mix-1124 . Restrict this pass to those metadata/documents and at most one source-linked logs pointer. Inspect only official Ai2 OLMo 2 cards, pinned checkpoint documentation and metadata for the OLMo-2-1124-7B release. Determine whether the card's promised logs have a delivered, versioned public artifact, retaining exact provenance. Distinguish native and Transformers checkpoint usability, the 36 stage-two training checkpoints from releases/adopters, and model/code Apache-2.0 from ODC-By-1.0/Common-Crawl/constituent dataset terms. Return accessible pointers, dated limitations and any unresolved rights. No weights, runtime tests, full training data, login, bulk download or repository edits.

### OM-A6

Public scripts/schema do not clear harvested snapshots; a login-gated distribution route is not verified anonymous export.

Exact starting points: https://arxiv.org/html/2402.00699v1 ; https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/README.md ; https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/LICENSE ; https://github.com/PurdueDualityLab/PeaTMOSS-Artifact/blob/c4b75d45302bfb046e0dae2ce0a43aac637ec487/License-Analysis/LICENSE . The sample PeaTMOSS_SAMPLE.db.zip is 14,255,498 bytes; listing metadata is verified but its bytes/SQLite contents were not acquired. Restrict the pass to public notices and access instructions. Inspect public author-controlled PeaTMOSS documentation, paper and license statements for PurdueDualityLab/PeaTMOSS-Artifact. Seek an explicit statement covering harvested metadata, the SQLite sample and full repository snapshots separately from Apache-2.0/BSD-3-Clause code. Identify whether a small author-supported export can be obtained without authentication; report exact login/permission or missing-license blocker if not. Preserve the July–August 2023 collection period and mapped-edge cohort rather than the January 2025 repository revision. Do not log in, fetch sample ZIP/full corpus, contact authors or edit the repository.

### OM-A7

An offline review result is not a source admission or production-schema guarantee.

Repository: https://github.com/mishakgg/pdoom-live . Frozen baseline: 4ecece6abd322932f70f121aef2e99fc3be467bb. Read https://github.com/mishakgg/pdoom-live/blob/4ecece6abd322932f70f121aef2e99fc3be467bb/tools/evidence_program/contracts/field_dictionary.json and https://github.com/mishakgg/pdoom-live/blob/4ecece6abd322932f70f121aef2e99fc3be467bb/tools/evidence_program/contracts/dataset.schema.json . Exact source annotations: https://github.com/Language-Technology-Assessment/main-database/blob/e39b4edd41811e975f9262d77ee286796d7792e5/llama-3.3.yaml (3,648 bytes, SHA-256 89d1f517d5171d832c59359e83d6c7b7577aaf0c14f8a06c08b01adbbcdfcc17) and https://github.com/Language-Technology-Assessment/main-database/blob/ff85b6ff442035e41c9492cefa54f78be0b827fc/llama-3.3.yaml (3,398 bytes, SHA-256 cc93e48df6a72c3e15d05ae2a056fcf775d4ccf7c590bc26c13ebbdb9fea6ec8). Use the delivered two-file reader and these exact local fixtures only, 64 KiB maximum per file. Read the existing frozen evidence-program contract and the implemented tools/evidence_program/read_open_model_yaml.py, without changing either. Propose a lossless mapping for the two pinned EU Open Source AI Index revisions, retaining nested fields including api.metaprompt, null links, month precision, raw judgments, source commit versus unknown assessment time, criterion-set change and distinct annotation/model licenses. Identify any real incompatibility with evidence; do not assume a schema migration is required. Return mapping and acceptance tests only. Read-only retrieval of the listed reference pages is allowed; the reader itself must execute only on supplied local files, without following evidence or model links. If the delivered reader source or local fixtures are absent, report the exact missing input rather than guessing its behavior. No source admission, operational collection, production import, model execution or schema edits.

## Status and limits

Review preparation and repository integration are separate from source admission and reader implementation. See the [dated 26-session queue](research-session-review-queue.md). This review preserves the frozen 64-source inventory, frozen contract and prior three research catalogs. No application runtime, database migration, production import/seed path or collector configuration changes.

**Top additions:** HF Hub metadata history, European Open Source AI Index, and existing GL001 accessibility enrichment.

**Strongest limitation:** None provides a representative denominator of successful practical use. Metadata, assessor classes, artifact listings and static dependencies each establish narrower evidence.

**Smallest testable implementation:** Implemented offline reader over two pinned annotation files: 26 criterion review records, one criteria-set change and zero inferred model-access/license events.
