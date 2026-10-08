# Bounded repeated-cycle metadata queue

## Status

`collection_storage.continuous.ContinuousQueue` implements a separately released, single-host queue over the existing strict Drive `Supervisor`. It does not call `run_metadata_pilot` or repeatedly rewrite the observation corpus. `continuous_feed.MetadataFeedProducer` is an optional RSS-only producer. No source schedule, credential provider, OAuth grant, remote root, public import, or background service is created by either module.

The historical exact-eight pilot and its pin file are unchanged. A `ReviewedProfile` must explicitly identify a versioned subset of those exact original pins and a per-source item limit. Changing a URL, identity, rights decision, allowed origin, structured collection policy, profile or configured limit stops the existing stream. A profile object is a review artifact, not authorization to collect: each `run_cycle` also requires an explicit release.

This is a bounded implementation milestone, not unattended production readiness. The ordinary connected document plugin cannot be adapted by inventing API quota, preallocated IDs, or resumable sessions. A small connector-assisted file transfer is a separate test; it does not verify this coordinator end to end.

## State and bounds

One `BoundedScratch` lease owns collection, state, staging, retries, temporary files, caches and logs. All queue file writes use its guarded streaming or atomic metadata methods. The existing maximum remains 25,000,000,000 bytes; this queue additionally rejects a free-space reserve below 5,000,000,000 bytes. No change is made to the existing 128 MiB/32-file Supervisor batch limit or one-MiB write/upload chunks.

Defaults:

- Metadata shard: at most 64 MiB, 4,096 new records, 16 KiB per record
- Seal at the first record boundary after five minutes from the first new record, or earlier on size, record count, cancellation, or the end of the bounded source slice
- One producer at a time; at most eight reviewed sources and 500 records examined per source
- Pause admission at 20 GB of actual scratch bytes plus outstanding reservation; resume only below 12.5 GB after fresh account, root, disk and quota checks
- Reserve two payload copies, three state copies and four MiB of transaction metadata before admitting a slice
- Dedup snapshot: at most 65,536 item/content-version pairs and 16 MiB; exceeding either stops without eviction, cursor reset or assumed success
- At most six upload attempts per sealed generation, with durable two-to-60-second exponential backoff; no automatic sleep or infinite retry

Lower bounds can be configured for tests. Increasing the stated maxima is rejected. Producers must themselves honor the provided item bound and stop callback before allocating/fetching. The optional feed producer has a one-MB response/parser bound, ten-second per-request timeout, and at most five redirects. It performs one request attempt per cycle; the queue owns persisted retry timing. This is a cooperative bounded-producer API, not a sandbox for arbitrary Python producers.

A payload contains only source identity/URL, logical item identity, title, upstream ID, declared author, publication/observation times, metadata-content hash, content-version number and profile hash. The whitelist rejects body, summary, evidence, segment, statement and forecast fields. Hashing covers the retained metadata, not a copyrighted body. Raw feeds are transient bounded parser input and are never persisted or uploaded. A changed body with unchanged retained metadata does not produce a new metadata version.

The disk dedup index is scanned as bounded JSONL, and a bounded delta is held only for the current shard. State snapshots contain the complete capped dedup index and source cursors/conditional validators. They are streamed through a one-MiB maximum chunk coalescer, not serialized as an ever-growing corpus object. This avoids a filesystem accounting scan for every tiny index row while preserving the final guard before each physical write. The snapshot is rewritten and uploaded once per generation; that cost is bounded by the explicit 16-MiB/65,536-entry ceiling. Snapshot validation uses bounded sets/maps up to that same entry limit. This deliberately favors a simple, auditable first slice over an indefinitely growing index or a new database. Sustained operation past that limit requires a separately reviewed partition/compaction design.

## Transaction and recovery

1. Validate the held local lease, exact profile, account/root and finite quota. A new stream requires the existing verified synthetic smoke checkpoint.
2. Recover a sealed/uploading/cleaning/restoring generation before admitting any new source fetch. A pending transaction owned by another stream stops admission.
3. Stream one immutable metadata payload and complete bounded state snapshot. Cursors and conditional validators advance only when that source slice was completely consumed. Interrupted or failed sources retain their earlier cursor; individual successfully observed metadata records may still be committed with a truthful partial outcome.
4. Persist a sealed journal containing stable descriptors, rights, generation, stream/profile and preceding manifest reference.
5. Submit through the unchanged Supervisor. It persists preallocated IDs before mutation, probes offsets, verifies remote receipts, writes the manifest, commits its checkpoint and performs its own tracked staging cleanup.
6. Independently read the manifest bytes back through the narrow bounded reader, verify the batch identity and preceding head, then install the verified state snapshot. Atomically commit the queue head before deleting only the two fixed queue input files.
7. Recover cleanup without a new upload reservation, even at full remote quota. Unknown remote outcomes retain the same durable IDs and stop/reconcile; there is no blind duplicate upload.

Crashes before sealing do not advance a cursor/index and are refetched from the last committed state. Crashes after sealing resume the same transaction. Crashes after the Supervisor checkpoint do not resubmit data. Failures to verify the extra manifest byte read preserve the local payload/snapshot even if the Supervisor checkpoint already exists.

The local OS lock prevents two processes using the same scratch root. It is not a cross-host lease. Operators must never overlap cloud executors for one stream. No elapsed-time rule permits stealing a writer. A future remote compare-and-swap/fencing and trustworthy automatic latest-head protocol remain release blockers for multi-host/unattended use.

## Explicit reset restoration

`restore(RecoveryPin(manifest_id, manifest_sha256, generation), sole_coordinator_confirmed=True)` restores a fresh local queue from an externally verified exact head. It validates account/root, manifest SHA-256/MD5, batch identity, source/profile/limits, all current remote payload receipts, the complete state snapshot checksum, bounded rows and source-state schema, and matching preceding-head references. Duplicate old versions remain duplicates after reset; genuinely changed metadata receives the next version.

There is no filename/timestamp-based head discovery or unbounded history walk. The externally pinned manifest hash is the trust anchor. Selecting the correct current head and ensuring that no prior executor can still write are operator responsibilities. A stale but otherwise valid explicit head cannot independently be identified as stale without the future shared-head protocol. Missing, corrupt or ambiguous state is a stop, never permission to recreate an empty dedup index.

Restore writes a recoverable journal before installing its checkpoint/index. It does not delete orphaned remote objects or modify historical manifests. Remote retention and orphan accounting remain operator-owned.

## Transport and source-policy seams

The injected backend must implement the exact existing `DriveBackend` contract plus:

`download_chunks(file_id, *, chunk_bytes, max_bytes) -> Iterable[bytes]`

The queue checks every yielded chunk, advertised byte count and final hashes. Authentication stays in the approved caller/provider; neither module reads tokens from environment variables, browsers, personal vaults or plugin internals.

`DriveHTTP.download_chunks` implements this read seam using original blob bytes from `files/{id}?alt=media` and bounded HTTP Range requests through the existing `Transport.send` authentication path. It does not use document exports, parsed previews, download links, or a separate credential provider. Google documents blob media and Range support in its [download guide](https://developers.google.com/workspace/drive/api/guides/manage-downloads#partial_download).

Each requested chunk is at most one MiB; a read admits at most 128 MiB and 128 requests (`max_bytes <= chunk_bytes * 128`). The queue's smaller manifest and snapshot limits still apply. The production `UrllibTransport` bounds each body read to the requested range length plus one overflow-detection byte, rejects an oversized declared response before reading it, and does not read error, redirect or ignored-range response bodies. It retains the existing no-redirect handler, 30-second request timeout, exact `drive.file` scope and bounded metadata/upload responses. Responses are closed before yielding a chunk. Cancellation is checked before advancing the read iterator and after each response.

Only HTTP 206 with an exact contiguous Content-Range, stable bounded total, matching byte count, and identity content encoding is accepted. Multi-range reads require a strong ETag on the first response, send it in If-Match on later requests, and require the same ETag in every response. Missing/changed validators, range/length disagreement, ignored ranges, and interrupted reads stop without a fallback or automatic retry. This conservative HTTP contract is fail-closed; deterministic mocks establish implementation compatibility, not that an approved live runner/provider has passed it. Final pinned size/SHA-256/MD5 and account/root checks remain mandatory in the queue. A readback failure preserves queue inputs and the existing transaction for reconciliation.

The optional RSS producer requires `robots_allowed(source, stop)` to return the result of a current reviewed robots/policy check. Its factory supplies a real `SafeFetcher` with the bounded supported transport. The existing URL scope and SSRF-safe request path remain active. A runtime requiring a proxy must establish a supported safe transport; success through ordinary urllib is not evidence that the direct IP-pinned SafeFetcher path works there. No proxy or security control is disabled by this module.

Conditional 304 responses are handled without a raw body cache. They require previously completed conditional validators, unchanged cursor and zero records. A feed larger than the per-cycle item bound is explicitly partial: its cursor stores the exact response SHA-256 and next entry offset, and no whole-feed ETag/Last-Modified is saved yet. The next cycle unconditionally re-fetches the bounded response and continues only if its hash matches; a changed response restarts traversal with committed dedup intact. The final page can save the whole-feed validators. At most 10,000 entries and one MB are parsed per response. Timer/record/byte interruption does not advance that page's cursor.

The producer filters items against the explicit pinned exact author name for Holden Karnofsky, Jack Clark, Nathan Lambert, Yoshua Bengio, Jan Leike and Paul Christiano. The coordinator independently checks this author metadata before retention. Lilian Weng keeps the existing name-confirmed-page rule. Victoria Krakovna's pin additionally requires a statement candidate, so the metadata-only queue rejects a profile containing it before fetching. The legacy exact-eight pilot is unchanged; this new path does not silently relax its conditional pin. Guest-author exclusions can produce a completed page with zero retained records; that means the feed was checked, not that a public statement was found.

RSS items need an explicit GUID or a valid individual item URL. The legacy parser's positional feed_url#index fallback is not admitted here. Without a GUID, the canonical item URL is the stable key. Ambiguous items fail the source slice without advancing its continuation or validators.

The producer projects only metadata directly from safe XML, with explicit namespace handling and inspection of every RSS/DC/Atom author declaration. Conflicting or empty author declarations cannot satisfy an exact-author rule. Person constructs reject mixed text/tails, foreign or unsupported children, nested markup and missing names; plain standard Atom name/email/uri fields remain supported; ambiguous IDs or canonical links are rejected. It does not invoke the legacy first-author/body-extracting observation helper. Titles remain untrusted metadata, not extracted claims. Error prose and transport URLs are not put into queue diagnostics. Its default User-Agent names the verified repository and does not advertise an unverified mailbox.

## Deterministic validation

From the checkout, with pytest and defusedxml in an authorized dependency directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline:/path/to/test-deps \
  python -B -m pytest tests/test_collection_storage*.py -p no:cacheprovider \
  --basetemp /trusted/workspace/dedicated-tests
```

The focused suites cover repeated generations, old/changed version dedup, explicit subset boundaries, rights revocation, raw-field rejection, finite index limits, every queue transition, lost upload replies, expired sessions, retry backoff, remote account/root/hash failures, full quota, partial outcomes, timer/cancellation/deadline seals, capacity hysteresis, missing local state, explicit remote restoration, and robots/304 metadata-only producer behavior. `test_collection_storage_drive_readback.py` also instantiates the real DriveHTTP and UrllibTransport against mocked HTTP for complete smoke/queue/restore cycles, bounded original-byte ranges, ETag/total changes, interrupted response reads, cancellation between chunks, and retained-input recovery after readback failure. All remote and source responses are synthetic. Existing Supervisor, runner and portable filesystem suites remain required regression gates.

## Safety review revisions

The first frozen candidate passed its original 212-test gate but independent adversarial probes found five gaps: post-commit cleanup rollback, premature whole-feed ETag advancement, inconsistent 304 records, missing author-policy enforcement, and positional fallback item IDs. That candidate is retained as superseded evidence. Revisions preserve each frozen predecessor. The current revision also covers repeated/conflicting author fields, namespaced Atom identity and authors, and missing/ambiguous identity fields. It adds explicit regressions for each, hash-bound bounded RSS continuation, coordinator-level author checks, and a metadata-only rejection for the statement-candidate pin. A cleanup failure preserves the installed cleaning journal, and cleanup rechecks the exact durable head and installed index before deleting inputs.
