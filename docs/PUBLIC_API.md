# Public API and dataset export

The public research surface is separate from the canonical import document in `docs/INGESTION_CONTRACT.md`. The import document is an internal ingestion contract. It includes extraction runs, curator review states, and operational fields. Clients should use this export instead.

## Versioning

`/api/v1/...` is the stable read API. The export document version is `export_schema_version` `1.0.0`. That number is not the canonical import `schema_version`.

Responses are JSON. There is no content negotiation. A breaking change to a response field gets a new path prefix (`/api/v2`) or a new export schema version.

Unversioned routes such as `/api/statements`, `/api/overview`, and `/api/health` remain the application query API. They are not a stability promise. They can include `needs_review` statements that the website shows as unsettled. They do not include `unreviewed` or `rejected` records. New consumers should call `/api/v1`.

Application statement pagination keeps the requested date order on every page, with unknown dates first in ascending order and last in descending order. Previous cursors return the immediately preceding page, including across unknown-date boundaries; people pages keep name/UUID order in both traversal directions. Application and `/api/v1` cursor version 1 remain compatible; newly issued date cursors retain database microseconds while older millisecond cursors remain accepted. Display timestamps are unchanged. Malformed cursor timestamps, UUIDs, and empty name keys return `400 invalid_cursor`.

The API is read-only. There is no authentication, account, or write endpoint.

## Review states

| State | Research export and `/api/v1` | Label |
| --- | --- | --- |
| `human_verified` | included | `verified: true`, `machine_labeled: false` |
| `machine_validated` | included | `verified: false`, `machine_labeled: true` |
| `needs_review` | omitted | website may still show it as unsettled |
| `unreviewed` | omitted | hidden on the website as well |
| `rejected` | omitted | hidden on the website as well |

`machine_validated` is not human verification. Asking `/api/v1` for `rejected`, `unreviewed`, or `needs_review` is an invalid query.

Affiliations, external identities, sources, forecasts, and relationships use the same filter. A forecast whose own review state is not public is omitted even if the statement is public, so a non-public number is not attached to a public statement.

A statement also requires a source in an included review state, so every exported statement, source item, and relationship retains its public source and endpoint links. The website's exact audit exception for an unreviewed source container does not apply to `/api/v1` or research exports. An explicitly rejected source cannot expose its statements through either surface. A removed original can retain its public audit record; availability is distinct from review rejection.

Referenced evidence must belong to the statement's declared source item, because its locator and content hash accompany that evidence in the public representation. Cross-item evidence references are omitted, including when the foreign item is otherwise public; the stored rows remain available for internal review.

Trend reads also remove hidden statement content and independently nonpublic forecast values/metadata before aggregation. Exclusions for a public statement can report a missing usable forecast but cannot preserve its hidden number, range, distribution, definition, or horizon. Unreviewed/rejected statements are absent from named exclusions and inspection rows. Redacted website-visible needs-review candidates may still contribute only to aggregate omission counts in research output. Removing hidden input rows can reduce exclusion counts without changing the cohort denominator or calculation method.

People with status `active` or `historical` are included. A person with status `review` is included only when they are the speaker of a public statement, so that statement still has a person record. `in_current_cohort` says whether they belong to the loaded cohort.

## Endpoints

| Method and path | Query |
| --- | --- |
| `GET /api/v1/dataset` | none |
| `GET /api/v1/people` | `cursor`, `limit`, `q`, `organization`, `status` (`active` or `historical`) |
| `GET /api/v1/people/{slug}` | none |
| `GET /api/v1/statements` | `cursor`, `limit`, `q`, `person`, `organization`, `source`, `topic`, `statement_type`, `review_state`, `from`, `to`, `sort` |
| `GET /api/v1/statements/{slug}` | none |
| `GET /api/v1/topics` | none |
| `GET /api/v1/topics/{slug}` | none |
| `GET /api/v1/sources` | `cursor`, `limit` |
| `GET /api/v1/sources/{slug}` | none |
| `GET /api/v1/source-items/{slug}` | none |
| `GET /api/v1/trends` | none |
| `GET /api/v1/trends/{slug}` | none |
| `GET /api/v1/search` | `q` required |
| `GET /api/v1/openapi.json` | none |

The OpenAPI document is `packages/contracts/openapi/public-v1.openapi.json`.

### Pagination

List routes return:

```json
{
  "api_version": "v1",
  "export_schema_version": "1.0.0",
  "data": [],
  "page": { "limit": 20, "total": 0, "next_cursor": null, "prev_cursor": null }
}
```

`limit` is an integer from 1 to 50. The default is 20. Cursors are opaque. Pass `page.next_cursor` or `page.prev_cursor` back as `cursor`. A cursor is bound to the sort it was issued for.

People are ordered by display name, then slug. Sources are ordered by name, then slug. Statements default to `event_time_desc` with slug as a tie-break. Null event times sort last in that order.

Topic and trend collections are returned in full, with topics capped at 500.

Trend observations use the same methods as the public trend pages. Numeric trends include effective `human_verified` estimates only. Volume counts include `human_verified` and `machine_validated`. A `needs_review`, `unreviewed`, `rejected`, or stale `human_verified` record is omitted from the observation. Comparability exclusions for records that remain in this export are listed by statement. Exclusions for records outside this export are counted and not named.

### Statement classes

`statement_type` is one of:

- `explicit_numeric` — the person supplied a number, range, or distribution
- `explicit_qualitative` — the person expressed a view without a number
- `model_inferred_signal` — machine classification or synthesis

Numeric fields are present only on explicit numeric forecasts. A qualitative or inferred statement does not carry `value_numeric`. When a number is present, the same object includes `question_key`, `question_text`, `definition_text`, `condition_text`, `horizon_text`, `unit`, and the target dates. A null horizon means the source did not state one.

### Provenance

A statement points at a person, a source, a source item, and the source item's canonical URL. List rows include an evidence reference: slug, kind, character or millisecond span, and segment hash. Detail rows and `statements.json` add the short excerpt. Excerpts are capped at 2,000 characters of text and 800 characters of context.

Detail rows also include `content_hash`, `content_reference`, availability, and public relationships (`updates`, `clarifies`, `retracts`, `contradicts`, `repeats`).

Timestamps are UTC ISO-8601. `event_time` is when the statement applies. `published_at` is the source item's publication time. `observed_at` is when the item was observed. `from` and `to` filter `event_time` as inclusive UTC dates.

Source objects include `last_checked_at` and `last_success_at`. Freshness uses `last_success_at`. The dataset object keeps `source_generated_at` (when the canonical file was assembled) separate from `imported_at` (when this database imported it). The catalog also reports `latest_source_checked_at` and `latest_source_success_at`. A failed check does not erase `last_success_at`.

### Errors

```json
{ "error": { "code": "invalid_query", "message": "Query parameters are invalid." } }
```

| HTTP | `code` | When |
| --- | --- | --- |
| 400 | `invalid_query` | Bad parameters, unknown parameters, duplicate parameters, inverted dates, query string over 2,048 characters, search text outside 2–120 characters or over 8 terms |
| 400 | `invalid_cursor` | Cursor cannot be read |
| 400 | `query_too_expensive` | Search exceeded its statement timeout |
| 404 | `not_found` | No public record for that slug |
| 405 | `method_not_allowed` | Any method other than GET |
| 429 | `rate_limited` | Process limit, or too many snapshot reads. `Retry-After` is set |
| 500 | `query_failed` | The query could not be completed |
| 503 | `query_failed` | A statement timeout on a non-search read |

Error responses use `Cache-Control: no-store`.

## Caching

Successful `/api/v1` responses send:

- `Cache-Control: public, max-age=60, stale-while-revalidate=300`
- `ETag` — strong SHA-256 of the response body

`Last-Modified` is not sent. Dataset import time does not change when a curator correction, review decision, or source-version mismatch changes a public payload, and HTTP-date cannot distinguish two changes in the same second. `If-Modified-Since` is ignored. A request that sends both `If-None-Match` and `If-Modified-Since` is decided only by the ETag: a match is 304, and a mismatch is 200.

`If-None-Match: *` matches when a representation exists. Weak validators (`W/"..."`) are compared as their opaque value.

These headers describe public dataset reads. They are not used for curator queues, and the website's server rendering does not go through this HTTP layer.

`/api/v1/dataset` and trend observations use the import time as `as_of` / `calculated_at`. That field is not a validator. A repeated read is a 304 only when the body bytes are unchanged.

The process keeps a bounded in-memory copy of recent representations, keyed by path and query. A conditional repeat is served from that copy when a content revision still matches, so the heavy read is skipped. The revision is one query over dataset import, review decisions, statement and forecast rows, source content hashes and versions, evidence hashes, people, cohort membership, and published trend definitions. It changes when any of those change, including two reviews that share a timestamp second, because the decision count and key are part of the fingerprint. Large tables contribute a count and a 64-bit xor, so a hash collision can hide a change until the 60-second entry lifetime. The copy is also dropped after 60 seconds, after 48 entries, or after about 2 MB.

Public source freshness is computed from the dataset import time, not the wall clock, so a public payload does not change merely because time passed. `/api/status` is different: its snapshot is cached for 15 seconds and classifies freshness at the `as_of` captured when that entry was built.

One response reads its dataset stamp, rows, counts, and trends in a single `REPEATABLE READ` `READ ONLY` transaction, so a commit that lands mid-request cannot mix two snapshots. The transaction is capped by a 15-second statement timeout, a 2-second lock timeout, and a 15-second idle timeout. Building a representation takes one of three snapshot slots so probes can still get a connection. A request that cannot enter returns 429 with `Retry-After`. A cache hit does not take a slot; it reads the shared revision and returns the stored body. Concurrent misses for the same URL share one load, and a rejected load is not stored. Search runs inside that snapshot with a 2-second statement timeout and returns `query_too_expensive` if the database cancels it. `/api/live`, `/api/ready`, and `/api/health` do not take a snapshot slot.

## Rate limits

The process keeps a fixed window in memory. The default is 600 requests per minute per client key and 3,000 per minute for the whole process. The client key is `direct` unless `PDOOM_TRUSTED_PROXY_HOPS` is a positive integer. That number is how many reverse proxies append the peer they observed to `X-Forwarded-For`. The client address is that many places from the right. A leftmost value supplied by the caller is not treated as identity. If the header is missing, shorter than the hop count, or not a list of IP addresses, the request stays in the shared `direct` bucket. Client keys are capped at 1,024; further keys share an `overflow` bucket. The process ceiling remains the backstop.

Configure `PDOOM_PUBLIC_RATE_LIMIT`, `PDOOM_PUBLIC_RATE_WINDOW_MS`, `PDOOM_PUBLIC_PROCESS_RATE_LIMIT`, and `PDOOM_TRUSTED_PROXY_HOPS`. Do not add Redis for this.

Expensive public reads also fail fast when three are already running. That 429 uses the same `Retry-After` error shape. `/api/live`, `/api/ready`, and `/api/health` do not take a public-read slot.

Put the real per-visitor limit on the reverse proxy or CDN. This in-process limiter does not run for server-rendered pages, which call the database helpers directly.

Search and list bounds are part of the same control: page size, query length, search-term count, and a cap of 50 source items on a source detail response.

## Snapshot command

```bash
npm run data:export -- --out data/exports/public --generated-at 2026-09-27T00:00:00.000Z
```

`--generated-at` is optional. When it is set, two runs against the same imported rows write the same bytes. Output defaults to `data/exports/public`. The command refuses to write into fixtures, seeds, raw collections, reports, or application source. `data/exports/` is gitignored.

`manifest.json` records:

- `export_schema_version` and `generated_at`
- dataset id, kind, import schema version, and import time
- cohort slug, version, name, and definition
- methodology document version `2026.09.0`, provenance policy path, trend method versions, and topic versions
- record counts
- license status and note
- SHA-256, byte length, and record count for each data file
- `snapshot_id`

`snapshot_id` is the SHA-256 of a canonical list of the other files' hashes plus export schema version, `generated_at`, import time, and dataset id. It does not include `manifest.json`, because the manifest contains the id.

### Files

JSON files are the structured export, with stable key order. CSV files are RFC 4180 tables for people, statements, and forecasts. Nested entities are not flattened into one CSV. Topic slugs in `statements.csv` are joined with `|`.

A forecast row repeats the question, definition, condition, horizon, and unit beside any numeric value.

## License

Synthetic fixture exports cite CC0 1.0, matching `data/LICENSE`. They are not statements by real researchers.

Live exports set license status `pending`. Short excerpts may remain under the original source's copyright. The export is not permission to republish full articles, transcripts, or books. The website software remains under PolyForm Shield 1.0.0 and is not part of the data export.

## Citation

```text
pdoom.live public dataset <dataset_id>, cohort <cohort_slug> <cohort_version>, API v1, export schema 1.0.0. <imported_at>. https://pdoom.live/data
```

Name the dataset id, cohort version, and import or snapshot time. A chart is not a citation.

## What is omitted

Operational extraction fields, prompt identifiers, model names, verification and attribution notes, collection adapter names, rights notes, ingestion errors, logical keys, and unpublished source bodies are omitted. Evidence is a short excerpt plus a hash and a URL.
