# Interface request for Agent 2

Owner of this request: public read performance (Agent 6). `packages/db/src/trend-query.ts` is not edited on this branch.

## Current cost

`getTrend(slug)` calls `listComputedTrends()` and then keeps one slug. `listComputedTrends` loads the current cohort once and then computes every prepared and discovered method.

Callers that need one slug:

- `getPublicTrend` in `packages/db/src/public-read.ts` (public API and export)
- `loadTrend` in `apps/web/lib/loaders.ts`
- `apps/web/app/api/trends/[slug]/route.ts`
- `getOverview` in `packages/db/src/queries.ts` still needs the full list

The scale fixture now inserts the extra people into the current cohort, with numeric forecasts, ranges, revisions, and review exclusions. Measured cold and repeated `getTrend("extinction-by-2070-distribution")` numbers are recorded in the PR after `test/scale.test.ts` writes `/tmp/pdoom-public-read-scale.json`. Those numbers are observations, not a target percentage.

## Requested change

Add a single-method path on `getTrend` that:

1. Accepts `pg.Pool | pg.PoolClient` and uses only `.query` on that object, so a caller can pass the public snapshot client. The cast in `getPublicTrend` can then go away.
2. Loads cohort inputs once.
3. Computes the requested prepared method only. Discover other methods only when the slug is not one of the prepared slugs.
4. Leaves eligibility, exclusion reasons, units, horizons, conditionality, and the numeric summaries unchanged.

`listComputedTrends` should keep computing every method for the trends index and for `getOverview`.

Do not drop cohort rows, skip review checks, or change forecast mathematics to make the scale timing smaller.
