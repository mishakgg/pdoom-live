# Recurring refresh

A refresh checks a bounded slice of admitted sources, keeps the last good observation when a source fails, and writes one canonical document. It does not import that document and it does not enable a schedule.

## Command

From the repository root:

```bash
scripts/refresh/run-once.sh --max-sources 40 --max-seconds 900
```

The same entry point is:

```bash
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.refresh --once --max-sources 40 --max-seconds 900
```

`--once` is required. Without it the process exits and does not fetch. `collect_beliefs --live` uses this same bounded path.

Defaults are 40 sources and 900 seconds. The fetcher waits 0.25 seconds between requests to the same host, times out a request at 20 seconds, and retries a timeout, HTTP 429, or HTTP 5xx at most three times. Retry-After is honored and capped at 60 seconds. HTTP 304 with a stored body is a successful unchanged check. HTTP 304 without a stored body is fetched once without conditional headers.

## What one run writes

State stays in files next to the collection. There is no second database and no queue.

| Path | Role |
| --- | --- |
| `data/collections/cohort-v2026-09/state/collection_state.json` | Per-source identity, conditional-request validators, cursor, content hashes, last attempt, last success, retry time, and at most eight errors |
| `data/collections/cohort-v2026-09/state/observations.json` | Retained observation versions |
| `data/collections/cohort-v2026-09/state/bodies/` | Licensed, unexpired last validated body, keyed by the exact primary fetch URL; absent by default |
| `data/collections/cohort-v2026-09/state/refresh.lock` | Overlap lock |
| `data/collections/cohort-v2026-09/staging/belief/` | Belief observations and statements |
| `data/collections/cohort-v2026-09/staging/enrichment/` | Enrichment source rows, written only by enrichment jobs |
| `data/collections/cohort-v2026-09/canonical-live.json` | Assembled canonical document |

Belief staging and enrichment staging are different directories. The assembler adds an enrichment source only when its slug and canonical URL are absent. It then adds retained adapter versions from the observation store. The checked-in canonical file is replaced only when an operator runs this command.

## Outcomes

Each selected source ends as new, changed, unchanged, skipped, or failed.

- Unchanged means the stored hash matched, or the server returned 304.
- Changed means a new hash was stored and the previous hash was kept as an older source-item version.
- Skipped means the source is inside its retry window and was not requested.
- Failed means this attempt did not succeed. A previous good observation stays in the document.
- A run with both progress and a failure is `partial`. A run with no successful source check is `failed`, even when earlier observations are retained. Cancellation before any successful check, or a slice entirely inside retry windows, cannot claim success. Neither status is counted as a full success.

`scripts/deploy/publish-dataset.sh` refuses a document whose latest belief or refresh run is `failed`. A `partial` document can be imported, and the publication record says `publish_partial`. An import that errors rolls back the transaction. The pre-import backup is left in place.

## Identity and review

Statement and evidence slugs are hashes of the claim and the evidence span. They do not use collection order. Reordering sources or inserting another item does not rename an unchanged claim.

Version 1 source-item slugs stay `item-` plus the first 20 hex characters of the SHA-256 of the canonical URL. That is the slug shape already published by this pipeline. A later content hash gets a different slug so the first row remains addressable. Import does not delete rows that are absent from a later file, so an older public slug still resolves after a refresh.

The review candidate key is the curation hash in `packages/contracts/src/curation.ts`: person, source hash, evidence hash, extractor, statement type, question, horizon, unit, and numeric values. It is not a collection index. Review decisions are append-only. Import does not rewrite `statement_extractions` or `review_decisions`.

When the incoming extraction matches the reviewed candidate key, import keeps the stored review state and any corrected text, statement type, evidence span, and forecast fields. When the source hash, evidence hash, or content version no longer matches the latest approval, the stored `human_verified` value remains and public reads report `needs_review`. A rejection stays rejected. Restoring the reviewed bytes makes that approval apply again.

## Schedule

The timer is not enabled. Until an operator enables it outside this repository's release script, the dataset updates only after a manual `run-once` and a later `publish-dataset.sh`. That is the expected latency today.

`deploy/refresh/pdoom-refresh.service` and `pdoom-refresh.timer` are a single-host systemd skeleton for a daily 06:00 UTC pass. `release.sh` does not install or start them. A daily pass of 40 sources, with about a quarter-second between requests to one host, finishes well inside the 900 second bound when sources answer. The public freshness window treats a success within 14 days as current. About 250 continuously collectible registry sources would take several daily passes to cycle, so a source can be up to about a week old and still inside that window once the timer is actually enabled. Do not enable the timer as part of a deploy.

## Lock recovery

The lock file is created exclusively. A second run exits while the recorded process is alive. A confirmed dead process id is reclaimed on the next run. A live or unknown process keeps its lock regardless of age. An incomplete or unreadable lock requires explicit recovery. Windows uses a read-only process handle and a zero-time wait to check liveness; it never sends a signal to probe a process. If a host rebooted and the lock remains, confirm no refresh is running and delete `data/collections/cohort-v2026-09/state/refresh.lock`. The next `--once` resumes from the saved cursor. Completed sources are not imported twice; publication is a separate upsert.

Keep `collection_state.json` and `observations.json` with the database. Those files are how a later run knows which hash is version 1. Deleting them and fetching the current page again writes that page as version 1 under the original public item slug. If Postgres already stored those bytes as a later version, import stops on the source-item uniqueness check instead of creating a second row. Restore the state files from backup, or restore the database to the matching export, before the next publish.

SIGTERM and SIGINT stop the slice between sources. The last completed source stays in the checkpoint.

## Admitted adapters

RSS, arXiv, GitHub, and OpenAlex works are called through `pdoom_pipeline.refresh.runtime`. Other registry methods stay in the seed export and are not fetched by this command. A feed URL that is also a belief lead is collected once, on the belief path.

## Dependencies

The refresh uses the existing Python pipeline, its HTTP fetcher, and JSON files on the collection disk. Publication uses the existing Postgres import. No Redis, worker fleet, or paid queue is required.

## Times

These stay separate:

- `published_at` is the source's publication time.
- `observed_at` is when this pipeline observed the item.
- extraction run `started_at` / `completed_at` is when the extractor ran.
- `generated_at` is when the canonical document was assembled.
- `imported_at` is when Postgres committed the import.
- `last_checked_at` is the last attempt. `last_success_at` is the last attempt that succeeded. Freshness uses `last_success_at`. A check that fails does not erase a previous success.

## Admission and retention controls

Only curator-supplied registry and lead configuration grants admission. Existing explicitly enabled registry rows with nonempty `rights_notes`, and executable belief leads with a nonempty `basis`, preserve their metadata/excerpt behavior. Missing admission, a disabled registry row, duplicate identities/URLs, or conflicting admission is a policy failure before fetching. A belief lead cannot bypass a disabled or narrower matching registry policy. `needs_review` identity metadata is not an approved personal belief.

An optional `collection_policy` object overrides legacy rights decisions:

```json
{
  "admitted": true,
  "rights_basis": "Reviewed permission reference and scope",
  "evidence": true,
  "extraction": false,
  "raw_retention": {
    "license": "CC-BY-4.0",
    "expires_at": "2026-10-08T00:00:00Z"
  }
}
```

This is an example of the format, not a grant for any current source. `admitted` and a nonempty rights basis are required for structured policy. Evidence and extraction default to true only within admission; `evidence: false` also disables extraction. Raw persistence is off unless a recognized copying license and an explicit zoned expiry are supplied. Unchanged-only copying licenses govern the unchanged raw bytes, not a grant to redistribute derived text. Public availability, open-access labels, source text, and free-text notes do not grant raw retention. Existing checked-in sources have no structured raw permission.

Fetched bytes stay in bounded memory until the entire selected source finishes successfully. Only its exact primary fetch response may enter the raw cache; robots, transcripts and ancillary URLs do not inherit that permission. Cache reads require a recorded, unexpired permission. At each run, revoked, expired and legacy ungoverned cache bodies are removed from the URL-hashed body directory. Permission changes never silently extend an existing cache expiry. Normalized adapter metadata drops full feed bodies (`upstream_version`); retained excerpts remain bounded. Revoked admission suppresses retained observations from the next artifact, and narrower evidence/extraction flags remove cached evidence and statement candidates before staging/export. The return value includes `policy_decisions`, and successful source checkpoints record the applied policy for a private manifest.

**Revocation applies to the new collection artifacts only.** The result explicitly reports `publication.imported=false` and `publication.public_revocations_applied=false`. Public database import currently retains records absent from later documents. Revoking a source in a new collection artifact does not delete or retract already published database records; any public revocation requires a separate reviewed product/DB workflow.

## Source identity and truthful checks

GitHub source URLs must be exact HTTPS profile URLs on `github.com`, with a valid login agreeing with `external_id` when present. OpenAlex sources must be the official works endpoint with exactly one author filter agreeing with the external identity. HTTP validators and freshness use the actual generated API fetch URL. Other admitted collectors retain their existing interfaces.

A source ID is durably bound to its URL, collection method, external identity and owner. Changing that binding requires explicit admission review and state reconciliation; it cannot silently retarget retained items. Legacy URL-keyed checkpoints are adopted only when the admitted URL/owner still agrees. Platform URL canonicalization cannot rewrite a foreign host merely because its path mentions a platform.

Outbound fetches, redirected requests and feed-supplied transcript targets default to the admitted origin. A curator can supply `allowed_fetch_origins` as an explicit list of HTTP(S) origins for reviewed cross-origin redirects or transcripts. The list does not bypass SSRF, response-size, deadline or parser checks. Sources requiring unreviewed redirects fail truthfully until their additional origin is reviewed.

A 304 is successful only with retained validated bytes that parse successfully, or a successful unconditional recovery fetch. An unsupported/malformed feed, robots refusal, unresolved page attribution, transcript failure, or collector bug fails the selected source. It preserves the previous successful timestamp, validators, source cursor and observation version. Last-attempt time and bounded error history still record the failure. The scheduling cursor advances only after a successful source check. Retained items do not turn an all-failed pass into success. Valid empty feeds are successful checks.

## Bounded storage integration

`run_refresh(write_bytes=sink)` routes state JSON, observation versions, licensed bodies, every belief staging output and canonical JSON through one `sink(absolute_path, bytes)` callback. The sink owns atomic replacement and must reserve the full new payload in addition to existing target bytes before opening its temporary file. The refresh response-memory bound remains six million bytes. Sink failures propagate, preserving the prior persisted target; they cannot return a successful run. Observation versions are persisted before their successful state checkpoint (timestamps, validators and cursor), both during the source loop and final assembly. Quota refusal or a process crash before the checkpoint preserves the previous success; data written first can be replayed idempotently after restart. Source outputs completed before a later refusal may already be checkpointed, which is ordinary resumable progress.

The storage supervisor holds its exclusive lease and adapts this hook to `BoundedScratch.atomic_bytes` beneath the fixed F: collection root. Its temporary bytes, caches, logs and lock also belong inside that counted root. The default local writer preserves ordinary standalone refresh behavior and has no 25 GB guarantee. Never release a Windows collection pilot through the default writer. All remote uploads require size/checksum readback and a verified private manifest before tracked local cleanup.

A once-only metadata/staging pilot may proceed only after the combined gateway, source pins, quota and private Drive verification pass and the coordinator authorizes release. Use the exact eight reviewed feed descriptors, `leads=[]`, `include_belief=False`, `max_sources=8`, and explicit evidence/extraction false in their policy copies. No current source admits a full raw-response archive. T11–T14 remain required before publishing semantic claims or aggregates: attribution from author/guest metadata, numeric definitions/conditionality/horizons, duplicate/version normalization, and extraction/review eligibility need independent validation. Candidate collection is not evidence of a person's belief or population consensus. No schedule or public import is enabled by these guards.
