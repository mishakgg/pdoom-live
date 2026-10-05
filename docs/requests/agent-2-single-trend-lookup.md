# Interface request for Agent 2

Owner of this request: public read performance (Agent 6). `packages/db/src/trend-query.ts` is not edited on this branch.

## Current cost

`getTrend(slug)` calls `listComputedTrends()` and then keeps one slug. `listComputedTrends` loads the current cohort once and then computes every prepared and discovered method.

Callers that need one slug:

- `getPublicTrend` in `packages/db/src/public-read.ts` (public API and export)
- `loadTrend` in `apps/web/lib/loaders.ts`
- `apps/web/app/api/trends/[slug]/route.ts`
- `getOverview` in `packages/db/src/queries.ts` still needs the full list

The scale fixture now inserts the extra people into the current cohort, with numeric forecasts, ranges, revisions, and review exclusions. One run on Node v22.22.2 and PostgreSQL 16.15, pool max 5, recorded:

- fixture: 400 people (20 with status `review`), 1,200 sources, 3,000 statements, 420 forecasts, 400 cohort memberships, cohort size 408
- `getTrend("extinction-by-2070-distribution")`: 6 queries on both runs, 60.2 ms and 87.6 ms cold, 37.0 ms and 51.5 ms repeated, 78,362 byte payload. Contributing statements 12. Conditional, GDP, and revision trends also contributed (9, 8, and 9)
- `getOverview`, which calls `listComputedTrends` after coverage: 26 queries, 133.2 ms and 559.1 ms cold, 129.4 ms and 515.9 ms repeated, 257,594 bytes. The slower run was the first after PostgreSQL started
- `getPerson("scale-person-1")`: 9 queries, 7.5 ms and 8.2 ms cold

Those are observations from that environment, not a target percentage. A single-slug path still computes every method today; the 6 queries are the shared input load plus the volume query, and the other methods run in process. Skipping them will not remove the input load. `getOverview` is the larger measured cost because coverage reads the enlarged source set and then computes every method again.

## Requested change

Add a single-method path on `getTrend` that:

1. Accepts `pg.Pool | pg.PoolClient` and uses only `.query` on that object, so a caller can pass the public snapshot client. The cast in `getPublicTrend` can then go away.
2. Loads cohort inputs once.
3. Computes the requested prepared method only. Discover other methods only when the slug is not one of the prepared slugs.
4. Leaves eligibility, exclusion reasons, units, horizons, conditionality, and the numeric summaries unchanged.

`listComputedTrends` should keep computing every method for the trends index and for `getOverview`.

Do not drop cohort rows, skip review checks, or change forecast mathematics to make the scale timing smaller.

## Published head checked

Agent 2 published `cursor/forecast-comparability-1787` at `b959a47f88f2c3d6c948072e038a082847aa666f` (pull request 26) after this request was drafted. On that head, `getTrend` still calls `listComputedTrends` and keeps one slug. `loadTrendInputs` is now exported, which is a useful seam for a single-method path, but the public single-slug callers still pay for every method.

That head also edits `packages/db/src/public-read.ts` and `packages/db/src/queries.ts`. The public-read change filters `qualitative` and `inspection` rows in `presentTrend` before the revision fallback. This branch wraps the same readers in one repeatable-read snapshot and still falls through to `presentRevision` for any kind other than volume, distribution, timeline, and quantity. A merge has to keep both the snapshot wrapper and those two kind branches. This branch does not apply that change.
