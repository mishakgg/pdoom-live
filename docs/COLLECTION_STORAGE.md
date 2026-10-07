# Private bounded collection handoff

The local collection lease and Drive batch supervisor are separate from the public application. PostgreSQL remains the application database. This milestone does not configure OAuth, collect live sources, import data, create a schedule, or publish a dataset.

## Storage contract

`pdoom_pipeline.collection_storage.scratch.BoundedScratch` uses exactly `F:\CodexTaskScratch\pdoom-live\collection`. There is no supported alternate root or C: fallback. All collection state, downloads, staging copies, retries, temporary files, logs and caches must be under that root. Source checkout and test dependencies remain under the enclosing task tree, separately from the collection byte budget.

The maximum is **25,000,000,000 bytes**, decimal 25 GB. A configured lower limit is allowed; a higher limit is rejected. The default low-disk stop preserves 5,000,000,000 free bytes. Four MiB of the local budget is reserved for bounded journal/checkpoint writes. Both old target bytes and replacement `.writing` bytes count during atomic replacement. Downloads use bounded in-memory chunks and must persist through the gateway. Logs and caches cannot use an uncontrolled writer; environment routing alone does not enforce their byte limit.

`atomic_bytes(relative, chunks, max_bytes=...)` reserves the full new payload before opening a temporary file, checks actual whole-root usage and disk space on every chunk, fsyncs the temporary file and replaces the target. A failed or oversized stream preserves the previous target and removes only its own partial file. Chunks are at most one MiB. Paths reject alternate streams, traversal, hard links, symlinks and Windows reparse points. An OS-held writer lock is released on exit or process death; elapsed time never allows a second writer to steal a live lock. The root is a private task directory; unrelated files must never be placed there.

## Upload transaction

The supervisor accepts one admitted batch at a time, at most 128 MiB and 32 files. It does not queue a local archive. Each artifact carries an explicit admission decision, retention mode, rights basis and expected SHA-256; storage preserves this metadata and never decides source rights.

1. Read `about.get` and the pinned root before staging. Require the expected email and stable permission ID, an actual finite storage quota, enough free remote bytes, personal ownership, a writable folder, no shared-drive ID and owner-only permissions. Missing quota is a stop; claimed capacity is never assumed.
2. Stage one bounded batch and journal its descriptors. Assign each Drive-generated file ID and persist it **before** starting a remote mutation.
3. Use resumable uploads in one MiB chunks. On restart, query the server offset rather than trusting the local offset. An expired session restarts with the same file ID. A lost completion response reuses the complete remote file after readback. HTTP/network errors stop the attempt and preserve its journal; there is no infinite retry loop. Each resume has a finite chunk-request budget.
4. Check each remote file's exact byte count, MD5, available SHA-256, owner, private permissions, root parent and app idempotency marker. A mismatch stops without cleanup or checkpoint advancement.
5. Upload and verify a manifest containing all file IDs/hashes, unchanged rights decisions, cursor, account/root pin and previous manifest reference. Only then atomically commit the local checkpoint.
6. Remove precisely the verified batch files and explicitly tracked `runner/` inputs. Keep only a small current checkpoint and lock locally. Cleanup can resume after a crash. Unexpected files are left in place and stop cleanup; there is no recursive deletion.

Historical manifests are stored remotely, not appended to a growing local journal. The supported initial job is one pilot; starting a different pilot while one is pending is refused. A completed current batch can be resubmitted without another upload. Remote deletion, long-term retention expiry, multi-run restore and schedules remain separate operator decisions.

## Runner seam

The readiness owner adds `run_refresh(..., write_bytes=sink)`. The supervisor owns the lease and maps absolute targets beneath `collection/runner` into gateway-relative names. It splits serialized payloads into one MiB chunks. The hook must cover body/state/observation/staging/canonical writes, including replacements; between-source cancellation alone cannot enforce a disk cap. A source response is already bounded at six MB in memory. Pilot sources must be exactly the reviewed ID/URL/method/rights pins; no broader registry scan.

The initial pilot is metadata-only: `leads=[]`, `include_belief=False`, extraction and evidence disabled, `include_adapters=True`, at most eight sources. Current source policies do not admit a raw body archive. Private storage does not approve public statements. No `db:import` or publication command is part of this handoff.

## OAuth handoff and smoke gate

The code accepts a secure token provider; it never searches for credentials, starts consent, refreshes a grant, or uses application-default/service-account credentials. `UrllibTransport` requires the caller to attest the exact granted scope set `{https://www.googleapis.com/auth/drive.file}`. No full-Drive scope is requested. Tokens and resumable session URLs must not appear in logs, chat, Git, CLI arguments or manifests. Pending journal files contain sensitive upload session URLs and need current-user-only filesystem access.

At action time the operator confirms installed-app access using their existing desktop OAuth client and target personal account. The user supplies the client JSON directly to `F:\CodexTaskScratch\pdoom-live\collection\auth` through a secure handoff, never chat or the default C: Downloads directory. The credential provider and user-only ACL must be configured before launch. Any library cache or OAuth temporary file must also stay on F:. No paid API or personal MyDrive service-account ownership is used.

After consent, read API identity/quota, create app-owned private `pdoom-live-data`, pin its returned ID and owner permission ID, then run one synthetic file write/readback checksum transaction. Successful browser sign-in is not runner OAuth. A visual quota is supporting evidence, not the API quota admission gate. The central coordinator releases the one-time live pilot only after the combined runner hook, rights admission and smoke gates pass.

## Verification

From an F: checkout, route `TEMP`, `TMP`, `TMPDIR`, pip/npm caches and dependency paths to F:, set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, and disable pytest cache output. Use a fresh test directory inside the task tree:

```powershell
$env:PYTHONPATH = 'F:\CodexTaskScratch\pdoom-live\t06-runtime\deps;F:\CodexTaskScratch\pdoom-live\t06-storage\pipeline'
python -s -B -X utf8 -m pytest tests/test_collection_storage.py -p no:cacheprovider --basetemp F:\CodexTaskScratch\pdoom-live\t06-runtime\test-temp\focused
python -s -B -X utf8 -m pdoom_pipeline.collection_storage.readiness
```

Mocked tests exercise byte ceilings without allocating gigabytes, duplicate replacement bytes, low-disk stops, single-writer locking, path/reparse guards, scope/endpoint restrictions, account/quota/root failures, local and remote corruption, network interruption, lost responses, expired sessions, manifest failure, idempotent replay and cleanup after checkpoint crashes. No tests call live Drive or feeds.

Drive implementation follows the official [per-file scope guidance](https://developers.google.com/workspace/drive/api/guides/api-specific-auth), [resumable protocol](https://developers.google.com/workspace/drive/api/guides/manage-uploads), [pre-generated IDs](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/generateIds), and [account/quota fields](https://developers.google.com/workspace/drive/api/reference/rest/v3/about).
