# Complete source preservation and acquisition

This policy and the [machine-readable acquisition manifest](../../data/evidence-program/full-content-acquisition.json) distinguish source preservation, canonical interpretation and public publication. The selection review covers the existing [64-source inventory](../../data/evidence-program/source_inventory.json) and 26 research catalogs. Status below is verified through **8 October 2026, 22:44:41 UTC**; it does not imply a continuously refreshed collector.

## Preserve full useful content

Preserve complete useful permitted originals, meaningful historical versions, all native fields, uncertainty and provenance. Rights, legitimate access, integrity and bounded storage govern preservation. Unfinished semantic mapping, adapter acceptance tests or a p(doom) model do **not** prevent lawful raw preservation.

Metadata-only retention is a fallback for restricted or unresolved source bodies. The strict metadata queue remains a separate collection component, not the universal retention policy. Preserve source-specific holds rather than converting public availability into permission, or treating a software license as a blanket data grant.

There are three independent decisions:

1. **Preservation:** may this exact artifact be acquired and retained through a legitimate route, with its original bytes verified?
2. **Canonical mapping:** can its identities, units, versions, denominators and uncertainty be represented without distortion? Preserve original data while this remains unresolved.
3. **Publication:** do its rights and approved destination permit public redistribution? Eligibility under a license is distinct from permission to publish. Private archive completion does not imply public dataset publication.

## Storage placement and deduplication

Complete compact licensed CSV/JSON datasets may be reviewed for Git publication alongside normalized measurements, provenance and uncertainty. The data need not be reduced to metadata. Epoch hardware and the two EvalPlus result snapshots are useful examples; a current complete Epoch model CSV is also compact, although numerous historical copies would accumulate.

Keep bulky originals, binary/document archives and many historical vintages in the verified private archive, with content hashes and manifests referenced from Git. Preserve a publisher bundle as the original; extracted tables are linked derivatives. Do not count packaging, duplicate exports, mirrored copies or repeated unchanged versions as new source coverage.

Deduplicate physical blobs by complete SHA-256 and byte length, while retaining every source URL, version, retrieval time, license and supersession edge. Append new versions rather than overwriting by URL. Do not acquire unrelated model weights, training corpora or linked assets to increase byte totals.

This document enables no raw public release, public sharing, paid Git LFS, new credentials, production adapter or live collector.

## Initial substantive wave

Nine originals are selected. **Four originals totaling 7,488,579 source bytes are verified in the private archive. Five are prepared but not acquired.** The selected total of 25,454,290 bytes combines measured lengths and explicitly labelled HTTP-advertised lengths; it is not an acquired-corpus total.

- **GL001, Epoch AI models:** complete unchanged CSV archived; 6,826,880 bytes, 3,626 records, 57 fields. Original, attribution, manifest and commit record passed raw readback/checksum verification, checkpoint and tracked transfer-scratch cleanup. [Dataset-specific CC BY 4.0](https://epoch.ai/data/ai-models).
- **GL002, Epoch ML hardware:** complete CSV prepared, not archived; prior complete inspection measured 98,058 bytes, 178 records and 39 columns. Preserve precision-specific performance, dates, prices, missingness and references. [Dataset-specific CC BY 4.0](https://epoch.ai/data/machine-learning-hardware).
- **GL003, Epoch AI data centers:** complete publisher ZIP prepared, not acquired; HTTP advertises 114,113 bytes. The publisher documents six tables, and their separate CSV headers were observed. Actual ZIP members, CRCs and full-body checksum await capture verification. Preserve timelines, stages, IT/total power, compute/cost, chip quantities and sources. [Bundle and data-specific grant](https://epoch.ai/data/ai-data-centers).
- **BD001, two EvalPlus historical result JSONs:** both complete originals archived, 32,977 and 27,725 bytes, with 101 model objects each. Preserve all metric slots and nulls. Full Apache-2.0 LICENSE accompanies the files; both exact repository roots were checked and contain no NOTICE file. The grant belongs to the dedicated leaderboard repository at the specified commits, not separate evaluation software. See [benchmark drift research](research/benchmark-drift.md) and the exact pins in the manifest.
- **GL038 / FS003, LEAP Wave 12:** complete inert HTML archived, 600,997 bytes, including embedded published aggregates and exact question/condition wording. This is the known earlier full-body snapshot; fresh HEAD matched length only, not current content. Its [published report license](https://leap.forecastingresearch.org/reports/wave12) is CC BY 4.0. Unpublished respondent microdata and separately loaded assets remain outside this grant. See [forecast-survey research](research/forecast-surveys.md).
- **GL010 / FS001, ESPAI paper v1/v2/v3:** three complete versioned PDFs prepared, not acquired; advertised lengths are 5,925,368, 5,925,409 and 5,902,763 bytes. Each edition independently declares CC BY 4.0: [v1](https://arxiv.org/abs/2401.02843v1), [v2](https://arxiv.org/abs/2401.02843v2), [v3](https://arxiv.org/abs/2401.02843v3). Preserve every page and appendix. These are paper editions, not respondent datasets or new survey waves.

The EvalPlus pair and LEAP original were transferred together in a verified 96,127-byte ZIP containing three originals totaling 661,699 bytes plus supporting files. **The ZIP is transport packaging, not a fourth source.** The manifest records original hashes, measured/advertised extent and archive readiness separately. No canonical import, independent scientific replication or p(doom) conversion is claimed.

## Capacity and safe transfer extension

The scratch hard maximum remains **25,000,000,000 bytes**, with **5,000,000,000 bytes free-space reserve**. The presently tested per-artifact harness bound is **10 MiB**. This is an implementation boundary, not a permanent content-retention policy.

Two rights-clear originals need a reviewed transfer extension:

- **EDB004, EIA August 2026 generator workbook:** HTTP HEAD length 13,955,142 bytes. [Current workbook](https://www.eia.gov/electricity/data/eia860m/xls/august_generator2026.xlsx), [EIA data reuse policy](https://www.eia.gov/about/copyrights_reuse.php). The selected current path is allowed; historical archive paths and the linked codes workbook match observed robots disallow rules. Do not bypass those restrictions. This is generation-supply context, not an AI-load series.
- **EDB007, Queued Up 2026 workbook:** HTTP HEAD length 15,571,236 bytes. [Exact workbook](https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx), [data-file-specific CC BY 4.0](https://eta.lbl.gov/publications/queued-2026-edition-characteristics). The publisher describes full project-level data, a dictionary and 36 additional summary tabs. It excludes load-interconnection requests. See [electricity/deployment research](research/electricity-deployment.md).

Neither body has been acquired or its complete rows counted. Both advertise byte-range support; actual 206/Content-Range behavior is untested.

Before larger acquisition, review an artifact-specific total ceiling and a supported transfer/readback path. Reserve original, partial, reconstruction and raw-readback space within the unchanged scratch/free-space limits. Prefer a bounded whole-file transfer when supported. If chunking is necessary, require disjoint offsets, lengths and part hashes, immutable version/ETag consistency, verified range responses and final full-byte reassembly/hash. Stop if Range is ignored. Do not use chunks to silently bypass the whole-artifact guard or call a partial reconstruction a stored original.

The connected private archive route supports bounded transfers and raw readback, but direct quota, preallocated-ID and resumable controls and standalone backend credentials are not established. Do not substitute unauthorized credentials, paid infrastructure or an untested unattended runner.

For every transfer, stop on access/robots denial, unexpected redirects, changed identity or size, integrity failure, unsafe archive contents or insufficient capacity. Do not execute upstream scripts, macros or active document content. Reconcile uncertain uploads before retrying. Clean only tracked transfer scratch after expected files, full raw-byte readback hashes and checkpoint verification succeed. A rendered preview is not a raw-byte integrity check.

## Preserve unresolved evidence faithfully

Keep estimates, missing values, source confidence labels, units, construction stages, model/checkpoint identity, benchmark vintages, scenario wording and unresolved denominators intact. A paper revision is not a fresh elicitation; a corrected leaderboard is not automatically capability growth; respondent quartiles are not event-probability confidence intervals.

Next-in-line holds remain precise:

- **METR GL004:** three distinct historical JSONL blobs are identified, 52,136,242 Git-reported bytes after deduplication. Artifact-specific raw-data rights remain unresolved. Larger-file transport would also require review; unfinished horizon modeling is not the preservation blocker.
- **LiveBench GL005:** a visible judgment revision reports a 737,444-byte Parquet and 60,372 rows, versus 93,624 reported rows in its predecessor. Judgment-file license scope and an exact permitted immutable transfer remain unresolved; no body counts were independently verified.
- **MIT GL037:** dataset-specific CC BY 4.0 exists, but a legitimate complete export and version are not yet verified. This is an export/access hold, not denial of its data grant.
- **XPT GL011 and GL010 response/2024 attachments:** packaged/separately hosted data scope and/or access remain unresolved. The grant for a paper, software package or general research page does not automatically transfer.
- **Ten exact prior rights-release targets:** remain held as recorded in the manifest and [rights-release follow-up](research/followups/rights-release.md). Their holds do not override current GL001/GL002/GL003 dataset-specific grants.

Unknown rights/access stay held. Once a source-specific restriction is resolved, lawful full preservation can proceed without waiting for canonical modeling. Existing catalogs and their historical findings remain unchanged by these new policy/manifest files.
