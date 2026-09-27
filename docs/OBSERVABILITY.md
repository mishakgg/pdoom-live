# Operator observability

pdoom.live can return HTTP 200 while collection has stopped or the dataset has gone stale. This layer exists to make that difference visible. It is vendor-neutral: counters, a quality command, and a small alert document. It does not send email, Slack, or pages.

Checks report failures. They do not rewrite rows, merge people, or invent replacements.

## What to look at

| Question | Where |
| --- | --- |
| Can the app read the database? | `GET /api/health` returns `{ "ok": true }` only when `SELECT 1` succeeds. |
| Is the served dataset fresh? | `GET /api/status` returns `app` and `dataset` separately. `app: operational` with `dataset: stale` means the process is up and the data is not current. |
| Did integrity or collection actually fail? | `npm run quality:check` prints a summary and a JSON report. Exit code 1 means at least one hard error. |
| What should a scraper graph? | `GET /api/metrics`, disabled unless you turn it on. Prometheus text, bounded labels. |

A stale source does not mean the researcher is inactive. A collector failure is not evidence that the person said nothing.

Synthetic and fixture datasets are not on a live collection clock. Freshness problems there are informational. The same conditions are errors for `dataset_kind: live`.

## Commands

```bash
npm run quality:check
npm run quality:check -- --file data/fixtures/synthetic/dataset.json
npm run quality:check -- --baseline ops/baseline.json --guardrails ops/guardrails.json --as-of 2026-09-27T00:00:00Z
npm run quality:check -- --strict
PYTHONPATH=pipeline python -m pdoom_pipeline.observability check --snapshot snapshot.json
```

`--file` checks a canonical import document and does not need a database. Without `--file`, the command reads the current PostgreSQL dataset. `--strict` turns warnings into a non-zero exit. Growth does not fail the check.

Stdout is one JSON object. Stderr is the human summary. The JSON `findings` use `error`, `warning`, and `info`.

Pipeline collection records can be reduced to the same snapshot shape and checked with the Python command. The cohort quality report in `data/reports/` is a separate coverage write-up, not this check.

## Signals

Labels are a fixed set: source type, adapter, failure class, review state, statement type, route group, and status class. There is no series per person, URL, source item, or statement.

### Application

| Metric | Meaning |
| --- | --- |
| `pdoom_http_requests_total` | Instrumented API handlers (`health`, `status`, `metrics`, `api`). |
| `pdoom_http_errors_total` | Those responses with status 500–599. |
| `pdoom_http_request_duration_seconds` | Handler latency histogram. |
| `pdoom_db_queries_total` | Pool queries by `read` / `write` / `other` and `ok` / `error`. |
| `pdoom_db_query_failures_total` | Failures by `connection`, `timeout`, `constraint`, or `unknown`. |
| `pdoom_db_query_duration_seconds` | Query latency. Successes are counted, not logged. |
| `pdoom_readiness` | `1` when the database check is passing. |

Page navigations are not in the HTTP counters. Edge middleware only assigns a correlation id; it does not share memory with the Node metrics registry. API latency is the measured HTTP path.

### Collection

Counts of runs are limited to the configured window (default 168 hours). Current failing source items are included in the failure and rate-limit gauges even when the run is older.

| Metric | Meaning |
| --- | --- |
| `pdoom_sources_due` | Enabled rss/api/sitemap (and equivalent pipeline methods) past their cadence. |
| `pdoom_collection_attempted` / `_succeeded` / `_failed` | Runs in the window. |
| `pdoom_collection_unchanged` / `_changed` / `_new` | Item outcomes derived from run counters. |
| `pdoom_collection_runs` | The same runs by adapter and outcome. |
| `pdoom_collection_failures` | Failure class by adapter. Free-text error summaries are not labels; unknown text becomes `unclassified`. |
| `pdoom_collection_rate_limits` | Rate-limit failures. |
| `pdoom_sources_stale` | Enabled cohort sources whose last success is stale, by source type. |
| `pdoom_sources_never_successful` | Enabled cohort sources with no successful check, by source type. |

Cadence is 7 days for blogs, newsletters, repositories, and social posts; 30 days for papers, preprints, academic-works feeds, podcasts, and video; 14 days for other eligible methods. Fixture and manual sources are not on this clock.

### Extraction

| Metric | Meaning |
| --- | --- |
| `pdoom_extraction_items_processed` | Extraction runs started in the window. |
| `pdoom_extraction_failures` | Those runs that failed. |
| `pdoom_extraction_candidates` | Non-rejected statements by `explicit_numeric`, `explicit_qualitative`, or `model_inferred_signal`. |
| `pdoom_extraction_missing_horizon_ratio` | Share of non-rejected explicit numeric statements with no horizon text and no target date. |
| `pdoom_extraction_missing_definition_ratio` | Share with no definition text. |

### Data quality

| Metric | Meaning |
| --- | --- |
| `pdoom_cohort_size` | Members of the current dataset cohort. |
| `pdoom_people_with_non_academic_source` | Cohort members with a source other than paper, preprint, or academic works. |
| `pdoom_statement_bearing_people` | Cohort members with a non-rejected statement. |
| `pdoom_statements` | All stored statements by review state. |
| `pdoom_sources_freshness` | Cohort-scoped sources: `current` (≤14 days), `aging` (≤90 days), `stale`, `never_checked`. |
| `pdoom_integrity_violations` | Integrity counts below. Zero is healthy. |
| `pdoom_alert_firing` | `1` when that alert is firing. |

Cohort freshness follows the current dataset cohort, including sources with no owner. Integrity checks scan the whole database.

## Quality checks

Hard errors (exit 1):

- `database_unavailable` — the readiness query failed. Other dataset checks are skipped so an outage is not mistaken for an empty cohort.
- `cohort_empty` — a current dataset has no cohort members.
- `all_sources_stale` — every enabled cohort source is stale or never successful. Error for live data, info for synthetic.
- `collection_stopped` — live data has cadence-eligible sources and zero successful runs in the window.
- `duplicate_identity_ids` — the same namespace and external id appears twice.
- `multiple_current_versions` — more than one current row for a source item logical key.
- `human_verified_missing_evidence` — a human-verified statement has no evidence text.
- `numeric_without_numeric_evidence` — an explicit numeric statement has no numeric forecast value, or its evidence contains no digit.
- `impossible_probability` — a probability is outside 0–1, or its minimum is above its maximum.
- `public_statement_unavailable_source` — a human-verified or machine-validated statement points at a source item whose availability is `unknown` and whose collection status is not `collected` or `partial`.
- `canonical_validation_failed` — the import document did not validate. The report does not echo the document.
- `imports_repeatedly_fail` — three or more import failures in a row in this process.
- `public_verified_dataset_empty` — a baseline had public verified statements and the current count is zero.

Warnings:

- cohort, source, statement, or human-verified counts fell by more than the guardrail
- live stale-source ratio above 50%, or more than 20 percentage points above the baseline
- live freshness objectives missed
- extraction failure rate above 25% after at least 5 runs in the window
- missing horizon or definition rate above 50% among explicit numeric statements
- rate limiting on a live dataset

Info includes the freshness distribution, coverage counts, synthetic staleness, and growth relative to a baseline. Missing baseline means relative size checks were not applied; that is reported, not treated as a failure.

Default guardrails live in `packages/observability/catalog.json`. Override them with `--guardrails`. A drop equal to the ratio does not warn; the count must fall by more than the ratio. Increases never warn.

## Freshness objectives

Evaluated for live datasets only.

| Objective | Target |
| --- | --- |
| `enabled_sources_within_cadence` | At least 95% of cadence-eligible enabled sources succeeded within their source-type cadence. |
| `latest_successful_collection_age_hours` | Latest successful collection is at most 168 hours old. |
| `statement_bearing_sources_fresh` | At least 90% of cohort sources that carry a non-rejected statement are current or aging. |

A breach is a warning. `collection_stopped` is the hard alert when the window has no success at all. The statement-source objective does not judge whether a person has gone quiet.

## Alerts

Every report includes the same alert ids, each with `firing: true` or `false`:

| Id | Severity | Fires when |
| --- | --- | --- |
| `collection_stopped` | critical | Live collection window has no success. |
| `database_unavailable` | critical | Database readiness failed. |
| `imports_repeatedly_fail` | critical | Import failure streak reached the guardrail. |
| `stale_source_percentage_spike` | warning | Live sources are all stale, or the stale share exceeds the guardrail. |
| `extractor_failure_rate_spike` | warning | Extraction failure rate exceeds the guardrail. |
| `canonical_validation_failed` | critical | Canonical validation failed. |
| `public_verified_dataset_empty` | critical | Public verified statements fell to zero from a baseline. |

`pdoom_alert_firing{alert="..."}` is the same bit in Prometheus. Nothing in this repository posts the document to an external service. A later job can read the JSON or the gauge and forward it to email, Grafana, an uptime check, Slack, Discord, or a cloud monitor.

Suggested wiring:

- Uptime monitor on `GET /api/health` for process and database reachability.
- A second check on `GET /api/status` that fails when `dataset` is `stale` or `app` is `unavailable` for a live deployment. HTTP 200 on status only means the app could read the database.
- Prometheus scrape of `/api/metrics` from a private network, with alert rules on `pdoom_alert_firing == 1` and on `pdoom_readiness == 0`.
- `npm run quality:check -- --baseline ops/baseline.json` after each import. Store the baseline from a known-good import. Do not freeze today's absolute counts in CI; use the ratios.
- Optional `PDOOM_QUALITY_BASELINE` so `/api/status` and `/api/metrics` apply the same relative guardrails. The file is counts only.

## Status and metrics endpoints

`GET /api/status` is public and small:

- `app`: `operational` or `unavailable`
- `dataset`: `current`, `aging`, `stale`, `not_loaded`, or `unknown`
- `dataset_kind`
- `dataset_generated_at`
- `latest_successful_observation`
- `freshness` counts

It does not include adapter errors, SQL, hostnames, evidence, or review notes. Database unreadiness is HTTP 503. A stale live dataset stays HTTP 200 so a monitor that only checks the status code will miss it; read `dataset`.

`GET /api/metrics` is off unless `PDOOM_METRICS_ENABLED=1` (or `true`). Leave it off on the public hostname. Scrape it from an internal interface or an ingress allowlist. If `PDOOM_METRICS_TOKEN` is set, the request must send `Authorization: Bearer <token>`. That comparison is a deployment control, not an account system. Do not log the header. A wrong token is 403; a disabled endpoint is 404.

The metrics response is cached with the status snapshot for 15 seconds so a scrape does not rerun the aggregate queries on every poll. Successful reads on the public API do not build this snapshot.

## Logs and correlation

Important events are one JSON object per line on stderr:

`ts`, `level`, `operation`, `request_id`, `run_id`, `adapter`, `outcome`, `duration_ms`, `error_class`.

Operations include `db_query` (failures only), `import`, `quality_check`, `operational_snapshot`, and `baseline`. Successful queries are not logged.

Inbound `x-request-id` is kept when it is 8–64 characters of letters, digits, `_`, or `-`. Otherwise the server mints a new id and returns it on the response. Import and quality-check runs get their own id. These ids are for operators connecting a request, an import, and a collection or extraction run. They are not stored as analytics and they are not browser fingerprints.

Logs drop tokens, cookies, authorization headers, database URLs, SQL, evidence text, and raw bodies. Unknown fields are ignored. Values that do not match the stable token pattern are replaced.

## Performance

Recording one HTTP observation is an in-memory counter increment. The test suite fails if that average exceeds 0.2 ms over 20,000 calls. Successful database work adds the same kind of increment and does not format a log line. There is no distributed tracing stack.

## Diagnosing stale data

1. `GET /api/health`. If this is 503, the database is the problem. The quality report should show `database_unavailable` and should not also claim the cohort disappeared.
2. `GET /api/status`. If `app` is operational and `dataset` is stale, the site is up and the data is old. Read `latest_successful_observation` and `dataset_generated_at`.
3. `npm run quality:check`. Hard errors are integrity, an empty cohort, stopped live collection, or repeated import failure. Warnings are ratios and objectives.
4. If metrics are enabled, look at `pdoom_collection_succeeded`, `pdoom_sources_freshness`, `pdoom_sources_due`, `pdoom_collection_rate_limits`, and `pdoom_alert_firing`.
5. A high `never_checked` count means the source was registered and never collected. That is a pipeline gap, not a statement that the person is silent.
6. Rate limiting and other failure classes are operational. They are not quotes and they are not beliefs.

Keep the baseline file free of evidence text and notes. It only needs counts: `cohort_size`, `source_count`, `statement_count`, `human_verified_statements`, `machine_validated_statements`, and optional `stale_ratio`.
