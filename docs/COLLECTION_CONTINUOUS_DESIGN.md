# Continuous private collection: follow-on design, not implemented

## Status and boundaries

The portable path foundation changes where an explicitly configured collector may write. The existing implementation still has one writer, one pending batch (at most 128 MiB / 32 files), one MiB disk-write and HTTP chunks, and a one-shot metadata pilot. Its completed pilot checkpoint intentionally returns without another fetch. Repeatedly calling that entrypoint is not continuous collection.

No cloud credentials, OAuth grants, schedules, live collection or Drive mutations are part of the portability work. Account email, permission ID and folder pin belong in private runtime configuration; examples must use synthetic identities such as `collector@example.org`. The target account, finite API quota, owner-only app-owned root and synthetic write/readback smoke must all be verified through the eventual authorized runtime. A connected document plugin alone does not provide a runner token.

Keep the exact eight-source pin registry unchanged until a separate release/profile decision reconciles any historical five-source approval. A source profile needs a stable ID/version and exact reviewed identities, URLs, collection methods, rights and allowed origins; profile changes require review. No source expansion, evidence extraction or public import follows from selecting POSIX paths.

## One accounting coordinator

One coordinator must own the complete scratch budget, durable state and upload transaction. Producers may fetch/parse in bounded memory, but they cannot write directly or each claim their own 25 GB allowance. A producer obtains a reservation from the coordinator, streams bounded writes through it and releases unused capacity. Limit the number and aggregate bytes of in-flight producers as well as their individual response sizes.

The coordinator accounts for active shards, sealed shards, retries, temporary copies, upload staging, state, caches and logs. Copy-on-replacement counts both old and new bytes. Preserve the 25,000,000,000-byte maximum, 5,000,000,000-byte filesystem free reserve, four MiB metadata reserve and final check before every physical write. Reserve headroom for in-flight response completion and transaction metadata before admitting more work.

The current OS lock coordinates processes on one scratch root. It is not a cross-machine lease. A restart/migration must establish that no earlier cloud coordinator can still mutate the same remote stream. Do not run overlapping cloud sessions against one stream. A fencing/lease protocol and conflict tests are required before multi-host execution; local lease expiry must never be inferred merely from elapsed time.

## Bounded sealed shards

Replace the whole-corpus rewrite path before enabling sustained operation. `ObservationStore.save`, refresh state and canonical export currently serialize growing aggregate structures and reconstruct whole output files. The gateway bounds disk writes, but it does not make these Python objects, serializations or rewrites streaming. A larger disk cap or a loop around `run_refresh` does not solve this limitation.

Introduce versioned append-only, size-bounded shard records for normalized metadata and state deltas. Seal a shard at a record boundary, include a bounded record count, payload bytes, SHA-256, source/profile version and cursor range, and never modify sealed bytes. An individual record needs its own maximum and an explicit oversized-record failure. JSONL or another auditable streaming format can be used after a separate schema decision. Preserve source provenance, rights decisions and metadata-only retention.

Proposed starting settings, subject to measurement and release review:

- Seal/upload when a batch reaches 64 MiB or its oldest admitted record reaches five minutes, whichever comes first. The timer starts with the first record; it is not a schedule that invents empty batches.
- Keep the existing 128 MiB / 32-file supervisor ceiling and one pending remote transaction until stronger bounded-queue tests justify any change.
- Pause new fetch admission at 20,000,000,000 accounted bytes; resume only below 12,500,000,000 bytes after verified cleanup and fresh free-space/quota checks. Include outstanding reservations, not just bytes already written.
- Retain per-write hard-cap and 5 GB free-space checks even below the high watermark. An account/privacy/quota/rights error always pauses admission regardless of occupancy. Already admitted data remains local until safely committed; never delete it just to cross the low watermark.

These watermarks and the 64 MiB/five-minute trigger are proposals, not settings implemented by the portability patch. Use hysteresis to avoid repeated pause/resume at the boundary, and test the worst-case staged copy plus reserved producer bytes. On a roughly 31.65 GB-free workspace the margin above a 25 GB corpus plus 5 GB reserve is small; dependencies and other workloads consume that margin.

## Durable remote state and reset recovery

Each committed manifest should carry a stream ID, monotonic generation, profile hash, preceding manifest ID/hash, file IDs/hashes, actual source outcomes and cursor-after state. It must also identify a bounded versioned state snapshot plus subsequent deltas sufficient to restore source cursors, conditional request validators, source bindings, logical item keys, content versions and deduplication decisions. Do not treat the last run's result summary as a complete restorable corpus state.

The current backend has no general remote manifest discovery/download or latest-head restoration protocol. Add and test those read operations separately within the same app-owned files and account/root constraints. Determine how a fresh workspace securely learns the stream/root/head pin, and use an explicitly reviewed head-selection/conflict protocol. Stop on a forked chain, missing snapshot/delta, profile mismatch, unexpected owner/root or failed hash. Do not assume the newest filename or timestamp is a trustworthy checkpoint.

Restore only verified state needed for the next bounded slice. Partition or compact the dedup index under the same disk/memory budgets; do not download an unbounded historical corpus to reconstruct it. Restore stable source identities, upstream IDs/canonical URLs plus content hashes, content-version counters and conditional headers. A repeated source response after a reset must neither duplicate an existing item/version nor suppress a genuinely changed item. Source rebindings, rights revocations and changed profiles must still stop for the appropriate review.

Remote state publication must complete before a generation is advertised as committed. Losing the local filesystem after remote commit should allow reconstruction without refetching committed items. Losing it before manifest commit must not advance the source cursor. Interrupted remote files may need operator-visible orphan accounting and an explicit retention/deletion policy; this design does not authorize remote deletion.

## Transaction and restart state machine

Use explicit, durable transitions rather than an unbounded retry loop:

1. `RESTORING`: authenticate via the approved provider, validate account/root/quota, establish sole coordinator ownership and verify the selected remote state chain. Do not admit producers yet.
2. `COLLECTING`: admit only the released profile and bounded reservations; write open shards through the coordinator. A cancellation or source failure produces a truthful partial/error outcome.
3. `SEALED`: persist immutable shard descriptors and hashes. Assign stable batch identity and remote file IDs durably before mutations.
4. `UPLOADING`: retain the pending journal, query the server offset on resume, reuse IDs across expired sessions/lost replies and bound requests/retries per attempt. Paused network attempts retain local bytes.
5. `VERIFYING`: read back size/checksums, private ownership, root parent and idempotency markers for every payload and manifest/state object. Any mismatch prevents checkpoint advancement and cleanup.
6. `COMMITTED`: after the remote manifest/state is verified, atomically advance the local checkpoint. Publish the remote head only through the reviewed conflict-safe protocol. A failed head publication must be recoverable by verified generation identity.
7. `CLEANING`: delete only the explicit, verified generation inputs, never the seed tree or untracked files. A restart can finish committed cleanup at zero new upload reservation, including when quota is full.
8. `PAUSED`: reject new admission on capacity, rights, auth, ownership, checksum or cancellation conditions. Resume only after the relevant condition is explicitly revalidated; use the low watermark for capacity recovery.

Do not assume a local OS lock, cursor-after alone or a successful upload request makes a generation durable. Preserve the existing manifest-before-cleanup rule and remote hash/ownership verification.

## Performance measurements and release gates

Benchmark HTTP upload chunk sizing independently from disk-write units. They both currently use the one MiB constant; a future transport experiment must introduce a separate reviewed HTTP setting, preserve resumable-protocol alignment and finite request budgets, and test offset probes, partial acceptance, retries and memory limits. Keep physical gateway writes bounded and checked even if an HTTP request aggregates several units. Do not infer throughput from synthetic tests or change both sizes together without measurements.

Before any continuous release, deterministic tests must establish:

- Multiple bounded generations, pause/resume hysteresis and no aggregate reservation overshoot across producers.
- Crash/restart at every state transition, lost upload/manifest/head responses, partial offsets, expired sessions and full-quota committed cleanup.
- Empty/new cloud workspace restoration, manifest-chain corruption/forks, wrong account/root/profile and missing state objects.
- Dedup across repeated responses and resets, unchanged/changed versions, conditional requests and revoked source admission.
- Disk and memory plateau over many generations; no growing monolithic local state or whole-corpus rewrite.
- Truthful partial outcomes and no public import, disallowed raw content or expanded source/profile scope.

Only after independent code review, CI, secure runtime authorization, actual account/quota/private-root verification and synthetic smoke should a separately approved bounded live profile run. Continuous operation needs its own release and operational stopping conditions; configuration portability is not that release.
