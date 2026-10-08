# Private bounded collection handoff and portable paths

The collection lease and Drive batch supervisor are separate from the public application. PostgreSQL remains the application database. This milestone does not configure OAuth, collect live sources, import data, create a schedule, or publish a dataset.

## Storage contract

`pdoom_pipeline.collection_storage.scratch.BoundedScratch` defaults to explicit legacy `ScratchPaths(mode="windows")`, using exactly `F:\CodexTaskScratch\pdoom-live\collection`. Windows mode accepts no root overrides and has no C: fallback. There is no automatic host detection or default POSIX destination. On a POSIX host, the unconfigured Windows default fails closed rather than creating a relative directory named like an F: path.

POSIX callers must provide `ScratchPaths(mode="posix", workspace_base=..., collection_root=..., seed_root=...)`. All three values must be absolute, link-free paths. The trusted workspace, collection parent and seed directory must already exist. Collection and seed roots must be separate strict descendants of that workspace; neither can contain the other. The caller must choose a dedicated collection directory, never the checkout, home, filesystem root or an unrelated shared directory. The base is a trusted operator/runtime choice, not a path supplied by ingested content. Seed files are read-only inputs; collection cleanup never targets them.

Existing workspace/seed ancestry below the trusted base must belong to the current user and must not be group/world writable. Existing scratch nodes must additionally have no group/world permission bits. Directories must also permit the required owner access, and failed directory scans stop byte accounting rather than silently skipping unreadable contents. Unsafe existing permissions stop the operation; they are never silently changed. New scratch directories use mode `0700`; lock and gateway files use `0600` and no-follow/exclusive creation. Seed validation rejects links, hard links and special files before a fresh pilot. Windows ACL provisioning remains an external prerequisite. This private directory and one cooperating writer are the trust boundary; the gateway is not a sandbox for hostile same-user processes that can rename files concurrently.

All collection state, downloads, staging copies, retries, temporary files, logs and caches must stay under the selected collection root. Source checkout, seed inputs and test dependencies remain under the workspace, separately from the collection byte budget. Their disk use is still seen by the filesystem free-space check. A temporary cloud workspace is disposable, and a portable path does not implement remote restoration or continuous collection.

The maximum is **25,000,000,000 bytes**, decimal 25 GB. A configured lower limit is allowed; a higher limit is rejected. The default low-disk stop preserves 5,000,000,000 free bytes. Four MiB of the local budget is reserved for bounded journal/checkpoint writes. Both old target bytes and replacement `.writing` bytes count during atomic replacement. Downloads use bounded in-memory chunks and must persist through the gateway. Logs and caches cannot use an uncontrolled writer; environment routing alone does not enforce their byte limit.

`atomic_bytes(relative, chunks, max_bytes=...)` reserves the full new payload before opening a temporary file, checks actual whole-root usage and disk space on every chunk, fsyncs the temporary file and replaces the target. A failed or oversized stream preserves the previous target and removes only its own partial file while the writer lease remains live. Chunks are at most one MiB. Paths reject alternate streams, traversal, hard links, symlinks and Windows reparse points. An OS-held writer lock is released on exit or process death; elapsed time never allows a second writer to steal a live lock. The root is a private task directory; unrelated files must never be placed there. The same conservative relative-name rules apply in both modes, so artifacts remain portable back to Windows.

Atomic byte/JSON writes and directory creation require a live lease in the current process before any filesystem mutation. Constructed, exited, closed-handle or inherited-process leases cannot create parents or remove another writer's `.writing` file. If a stream releases its lease, replacement and partial cleanup stop; a subsequent legitimate lease can recover the retained partial. Reentering an active lease object is refused without losing its original lock. Mutation targets are validated and normalized before reserving `writer.lock`, `writer.lock.writing` and their descendant namespaces, including native Windows case aliases. These lock paths cannot be payload destinations or temporary targets; the locked inode stays stable for the lease. Read-only path and JSON inspection remain available without a lease. Supervisor recovery already checks the lease before its public cleanup paths; its transaction and cleanup ordering are unchanged.

## Upload transaction

The supervisor accepts one admitted batch at a time, at most 128 MiB and 32 files. It does not queue a local archive. Each artifact carries an explicit admission decision, retention mode, rights basis and expected SHA-256; storage preserves this metadata and never decides source rights.

1. Read `about.get` and the pinned root before staging. Require the expected email and stable permission ID, an actual finite storage quota, enough free remote bytes, personal ownership, a writable folder, no shared-drive ID and owner-only permissions. Missing quota is a stop; claimed capacity is never assumed.
2. Stage one bounded batch and journal its descriptors. Assign each Drive-generated file ID and persist it **before** starting a remote mutation.
3. Use resumable uploads in one MiB chunks. On restart, query the server offset rather than trusting the local offset. An expired session restarts with the same file ID. A lost completion response reuses the complete remote file after readback. HTTP/network errors stop the attempt and preserve its journal; there is no infinite retry loop. Each resume has a finite chunk-request budget.
4. Check each remote file's exact byte count, MD5, available SHA-256, owner, private permissions, root parent and app idempotency marker. A mismatch stops without cleanup or checkpoint advancement.
5. Upload and verify a manifest containing all file IDs/hashes, unchanged rights decisions, cursor, account/root pin and previous manifest reference. Only then atomically commit the local checkpoint.
6. Remove precisely the verified batch files and explicitly tracked `runner/` inputs. Keep only a small current checkpoint and lock locally. Cleanup can resume after a crash, including when Drive quota is full. Recovery revalidates account/root privacy, excludes already verified remote files from the new quota reservation, and reserves incomplete files plus the manifest; committed cleanup requires zero new remote bytes. Incomplete resumable files conservatively reserve their full size because quota accounting may occur only at completion. Unexpected files are left in place and stop cleanup; there is no recursive deletion.

Historical manifests are stored remotely, not appended to a growing local journal. The supported initial job is one pilot; starting a different pilot while one is pending is refused. A completed current batch can be resubmitted without another upload. Remote deletion, long-term retention expiry, multi-run restore and schedules remain separate operator decisions.

## Runner seam

The readiness owner supplies `run_refresh(..., write_bytes=sink)` in PR #294. Actual-runner integration tests require that hook and fail if it is absent. That dependency is merged into main, and CI exercises the combined implementation. The supervisor owns the lease and maps absolute targets beneath `collection/runner` into gateway-relative names. It splits serialized payloads into one MiB chunks. The hook must cover body/state/observation/staging/canonical writes, including replacements; between-source cancellation alone cannot enforce a disk cap. A source response is already bounded at six MB in memory. Pilot sources must be exactly the reviewed ID/URL/method/rights pins; no broader registry scan. A newly added structured collection policy or broader redirect-origin policy stops for a new reviewed pin; the wrapper cannot override a revocation or expand source access.

The initial pilot is metadata-only: `leads=[]`, `include_belief=False`, extraction and evidence disabled, `include_adapters=True`, at most eight sources. Current source policies do not admit a raw body archive. The checkpoint and remote manifest preserve the runner's actual policy decisions and its explicit `imported=false, public_revocations_applied=false` result. This private handoff does not remove previously published database rows; public revocation remains a separate database-owner operation. Private storage does not approve public statements. No `db:import` or publication command is part of this handoff.

## OAuth handoff and smoke gate

The code accepts a secure token provider; it never searches for credentials, starts consent, refreshes a grant, or uses application-default/service-account credentials. `UrllibTransport` requires the caller to attest the exact granted scope set `{https://www.googleapis.com/auth/drive.file}`. No full-Drive scope is requested. Tokens and resumable session URLs must not appear in logs, chat, Git, CLI arguments or manifests. Pending journal files contain sensitive upload session URLs and need current-user-only filesystem access.

The original Windows deployment procedure requires action-time confirmation of installed-app access using the operator's existing desktop OAuth client and target personal account. The user supplies the client JSON directly to `F:\CodexTaskScratch\pdoom-live\collection\auth` through a secure handoff, never chat or the default C: Downloads directory. The credential provider and user-only ACL must be configured before launch. Any library cache or OAuth temporary file must also stay on F:. No paid API or personal MyDrive service-account ownership is used. This historical Windows credential procedure does not authorize a cloud credential transfer or a new cloud OAuth flow. The portability patch provides no POSIX credential provider, grants, credential files, or live upload setup; a separately reviewed secure flow and target account verification are required before any cloud first write.

After consent, read API identity/quota, create app-owned private `pdoom-live-data`, pin its returned ID and owner permission ID, then run one synthetic file write/readback checksum transaction. Successful browser sign-in is not runner OAuth. A visual quota is supporting evidence, not the API quota admission gate. The central coordinator releases the one-time live pilot only after the combined runner hook, rights admission and smoke gates pass.

## Read-only POSIX configuration check

The Python API can inventory an explicitly chosen layout without creating a directory, taking a writer lease, authenticating, uploading, or fetching any source:

```python
from pathlib import Path
from pdoom_pipeline.collection_storage.scratch import ScratchPaths
from pdoom_pipeline.collection_storage.readiness import report

paths = ScratchPaths(
    mode="posix",
    workspace_base=Path("/workspace/project"),
    collection_root=Path("/workspace/project/collection"),
    seed_root=Path("/workspace/project/checkout/data/seed/cohort/v2026-09"),
)
readiness = report(paths)
```

The example paths are placeholders; the workspace, collection parent and seed root must actually exist and pass ownership checks. `report(paths)` reports real free bytes, configured path mode, 25 GB hard maximum, 5 GB free reserve, 128 MiB/32-file batch maximum and the runner write-hook presence. Its status remains `blocked_for_live_pilot`, and continuous collection, scheduling and public import remain false. The existing module command without arguments remains the Windows readiness check. No path or environment value selects a real Drive account.

For temporary cloud execution, use a verified workspace disk, not an assumed `/tmp` capacity. A filesystem with about 31.65 GB available can accommodate the 25 GB hard maximum plus the 5 GB reserve only while other workspace use stays small. Per-write checks are decisive; that snapshot is not a capacity guarantee. Do not increase the maximum to consume spare disk.

## Verification

From an F: checkout, route `TEMP`, `TMP`, `TMPDIR`, pip/npm caches and dependency paths to F:, set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, and disable pytest cache output. Use a fresh test directory inside the task tree:

```powershell
$env:PYTHONPATH = 'F:\CodexTaskScratch\pdoom-live\t06-runtime\deps;F:\CodexTaskScratch\pdoom-live\t06-storage\pipeline'
python -s -B -X utf8 -m pytest tests/test_collection_storage.py -p no:cacheprovider --basetemp F:\CodexTaskScratch\pdoom-live\t06-runtime\test-temp\focused
python -s -B -X utf8 -m pdoom_pipeline.collection_storage.readiness
```

Mocked tests exercise byte ceilings without allocating gigabytes, duplicate replacement bytes, low-disk stops, single-writer locking, path/reparse guards, scope/endpoint restrictions, account/quota/root failures, local and remote corruption, network interruption, lost responses, expired sessions, manifest failure, idempotent replay and cleanup after checkpoint crashes. No tests call live Drive or feeds.

Drive implementation follows the official [per-file scope guidance](https://developers.google.com/workspace/drive/api/guides/api-specific-auth), [resumable protocol](https://developers.google.com/workspace/drive/api/guides/manage-uploads), [pre-generated IDs](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/generateIds), and [account/quota fields](https://developers.google.com/workspace/drive/api/reference/rest/v3/about).

On POSIX, run the three storage suites from a trusted checkout with dependencies installed separately and test files confined to a dedicated workspace directory:

```sh
PYTHONPATH=pipeline python -s -B -m pytest tests/test_collection_storage.py tests/test_collection_storage_runner.py tests/test_collection_storage_portable.py -p no:cacheprovider --basetemp /workspace/project/test-temp/storage
```

The portable suite uses only synthetic Drive/feed responses and small local files. It exercises configured POSIX paths against the actual runner and verifies restart after failed manifest upload, checkpoint-before-cleanup, cleanup at full remote quota, seed mismatch, private permissions, owner/link guards, disk reserve on every write, duplicate-copy accounting and one-shot replay. Existing Windows validation and host-mapped regression tests remain in place; POSIX test success is not a native Windows ACL/locking verification or live cloud authorization.

## Conditional pilot readiness checkpoint (historical Windows evidence)

The deterministic storage/bootstrap/pilot suite and seven tests against the readiness owner's actual refresh runner passed together: **69 passed**, with synthetic feed responses and fake Drive only. They also cover Windows device/alias filenames, redacted credential-provider failures, increasing remote quota usage, full-quota committed cleanup/replay, manifest-only reservations and lost manifest completion responses. The actual pilot entrypoint validates account/root with zero upload reservation before completed/pending recovery; only a fresh collection reserves a new batch. Actual-runner tests cover full-quota committed cleanup/replay, manifest-only pending recovery without refetching, and fresh full-quota refusal before any fetch. The real-process crash test resolves inherited `PYTHONPATH` entries before changing the child working directory, and passes with the CI-style relative `PYTHONPATH=pipeline` invocation. They verify all eight original feeds, zero persisted raw-body sentinel/evidence/statements/forecasts, manifest-before-cleanup ordering, an actual state-write quota stop preserving the smoke checkpoint, and a failed feed remaining a truthful partial result. The write-hook/rights/Windows-lock dependency is [PR #294](https://github.com/mishakgg/pdoom-live/pull/294), tested at `f6a4c65c8a9a020b244e17c7678d1828b5fc20d0`.

Read-only desktop evidence on 2026-10-07 established that the target account is signed into the Codex browser, Drive displays 408.2 GB of 5 TB used, and its existing Cloud project has a desktop client named `pdoom-client-1` and the Drive API enabled. No client secret, OAuth grant, credential, root folder, live corpus, or schedule was created by this work. API quota and runner credentials remain unproven until the post-consent smoke.

The remaining first-write gates are action-time user consent for that existing client with `drive.file` only, a secure F:-only credential provider and current-user-only ACLs, API account/permission ID and quota verification, app-owned private root creation/readback/pin, and synthetic checksum smoke. A live metadata-only pilot additionally requires current URL/rights readiness and the parent's one-time release after independent review. Public semantic release work is separate from the private metadata pilot.


## Cloud release boundary

The eight original source pins and exact-eight check remain unchanged. A historical five-source pilot approval is not a substitute for this executable eight-source contract. Any five-source profile must be an explicit later reviewed release/profile decision, including its exact source IDs, URLs, rights, exclusions and authorization; do not trim the registry silently or infer approval for all eight. Current source readiness still needs verification before a live release.

This patch implements configuration portability only. It does not implement continual uploads, high/low watermarks, multi-run remote checkpoint restoration, deduplication across workspace resets, or streaming corpus shards. The concrete follow-on plan and release gates are in [Continuous collection design](./COLLECTION_CONTINUOUS_DESIGN.md). The current pilot remains one bounded invocation, with account/quota/private-root pins and synthetic smoke required before a separately released live run.
