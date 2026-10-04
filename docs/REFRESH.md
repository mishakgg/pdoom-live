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
| `data/collections/cohort-v2026-09/state/bodies/` | Last fetched body, keyed by URL |
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
- A run with both progress and a failure is `partial`. A run whose selected sources all fail, with nothing retained, is `failed`. Neither status is counted as a full success.

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

The lock file is created exclusively. A second run exits while the recorded process is alive. A dead process id, or a lock older than six hours, is reclaimed on the next run. If a host rebooted and the lock remains, confirm no refresh is running and delete `data/collections/cohort-v2026-09/state/refresh.lock`. The next `--once` resumes from the saved cursor. Completed sources are not imported twice; publication is a separate upsert.

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
