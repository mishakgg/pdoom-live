# Frontend handoff

## Identity

- Branch: `cursor/frontend-observatory-redesign-6a22`
- Pull request: https://github.com/mishakgg/pdoom-live/pull/32
- Suite head: `b8509ddb6d6efc831e21c249a8b38b5d2c8b4875` (production build, Vitest, and Playwright).
- Published head: the pull request head. Commits after the suite only add this handoff and the trend-library column note. `/trends` was rendered after that note and shows “Dataset read” and the contributing definition.
- Base: `cursor/partial-integration-refresh-a32e` at `b4cf2307cb6e40240d5824131996ace942051f83` (pull request #31)
- `origin/main`: `d13c8ab9bc2d643e28b7f52daf1a4c15724e77d7`

The branch was rebased onto the six-workstream candidate so the pull request contains only the interface. Included heads, already in `b4cf230`: #21 navigation (`af6ec9b`), #22 coverage (`6c23609`), #25 public reads (`8c36cc1`), #26 comparability (`b959a47`), #27 refresh (`85ec81d`), #29 review staging (`bfe99a8`). Do not merge this pull request together with those pull requests, and do not merge or deploy it.

Coordination notes on `cursor/integration-coordination-a32e` are a different owner. They are not part of this diff.

## Design

Research ledger, recorded in `docs/DESIGN.md`. Public Sans at 16px, cool gray canvas, white surfaces, teal for links and numeric estimates, amber for qualitative views and the synthetic banner, slate for model-inferred signals. Newsreader remains the wordmark only. Monospace is limited to hashes and stored keys.

## Owned files

```
apps/web/app/curation/[slug]/page.tsx
apps/web/app/curation/page.tsx
apps/web/app/data/page.tsx
apps/web/app/global-error.tsx
apps/web/app/globals.css
apps/web/app/layout.tsx
apps/web/app/page.tsx
apps/web/app/source-items/[slug]/page.tsx
apps/web/app/sources/[slug]/page.tsx
apps/web/app/topics/[slug]/page.tsx
apps/web/app/trends/[slug]/page.tsx
apps/web/app/trends/page.tsx
apps/web/components/breadcrumb.tsx
apps/web/components/choice-field.tsx
apps/web/components/dataset-notice.tsx
apps/web/components/person-profile.tsx
apps/web/components/review-form.tsx
apps/web/components/search-results.tsx
apps/web/components/site-nav.tsx
apps/web/components/statement-audit.tsx
apps/web/components/trend-view.tsx
apps/web/components/trends.module.css
apps/web/components/trends.tsx
apps/web/lib/format.ts
apps/web/lib/presentation.ts
apps/web/next.config.ts
docs/DESIGN.md
test/presentation.test.ts
```

`apps/web/next.config.ts` sets `devIndicators: false`. No dependency was added. Forecast mathematics, ingestion, storage, identity data, and review permissions were not changed.

## Curator contract preserved from #29

The queue and record pages still call `curationEnabled()` and return not found otherwise. The record form keeps `submitReview`, the existing field names, and the explicit-numeric confirmation checkboxes. No bulk or automatic approval was added.

The pages now show stored state versus effective state, the machine recommendation as not human verification, participant role and value label, attribution participants, evidence locator, review flags, question-registry membership, duplicates, operator relationships versus machine suggestions, original machine extraction, and each warning’s required action. Rejection reasons stay a searchable choice; the action text is the hint for the selected reason.

## Refinement passes

1. First rendered pass. The trend chart sat below a repeated title and a long introduction. The duplicate panel heading was collapsed to a one-pixel accessible heading, the method and cohort moved behind the table, and the homepage status became a compact ledger so the first statements enter the desktop view.
2. Second rendered pass. Chart links no longer repeat the estimate’s accessible name. Each exclusion row carries its reason. Mobile data tables no longer force the last column onto one line. Chart groups use `role="group"` so links inside them are not nested interactive controls.
3. After the rebase onto `b4cf230`. Review fields from #29 were placed in the ledger layout. A later inspection found the narrow filter grid splitting its note beside the first field, a repeated numeric reading, and a cohort version printed as a bare number after a slug that already contained one. Those three were corrected. Collection states use a full-width ledger row.
4. An independent screenshot critique. The data-page cohort line it flagged had already been changed to “version”. The trend library’s “Contributing” and time columns were undefined, so the library now says that contributing counts people with an included record and that the time is a read of stored data. A raw `needs_review` token inside Jonah Hale’s stored sentence is fixture text, not the review label. The question reference is a closed disclosure. The people-page Apply control continues below the first mobile screen.

## Verification

Commands, from the repository root, with empty `OPENAI_API_KEY`, `YOUTUBE_API_KEY`, `GITHUB_TOKEN`, and `HUGGINGFACE_TOKEN` unset:

```
NODE_ENV=production npm run build
NODE_ENV=test DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pdoom_live_test npx vitest run
npx playwright test
```

Fixture for the dev server and the visual pass: `data/fixtures/synthetic/dataset.json` in `pdoom_live`, with `PDOOM_CURATION_MODE=local`. Playwright uses `pdoom_e2e_test` and `pdoom_e2e_empty_test`.

Results on `b8509dd`:

- Production build succeeded.
- Vitest: 214 passed, 2 failed. Both failures are `spawnSync python ENOENT` in `test/canonical-import.test.ts`. Python is not installed in this environment. The other 27 files passed, including UI, presentation, review, staging review, and runtime.
- Playwright: 135 passed, 2 skipped. That includes axe on the public templates, keyboard search, 200% zoom navigation, response and script budgets, empty-live, and database-down. Chromium only.

Visual inspection on the dev server covered homepage, people, topics, statements, statement audit, sources, search, trends, trend detail, data, methodology, the missing-record page, the review queue, and a record review. Widths included 390, 768, 1280, and 1440. Measured horizontal overflow was 0. On the 1280×800 extinction trend, the question, scope, contributing count, and chart sit inside the first viewport. The first queue row is inside that viewport. Chart-point navigation, the exclusion disclosure, search suggestions, and the unsaved-decision status were exercised.

## Limitations

- Inspected in Chromium through Playwright and the dev server. Firefox, Safari, and a deployed environment were not inspected.
- No pre-redesign page-weight number was captured on this machine. The existing production budget suite passed after the redesign. That is not a numeric before/after delta.
- Public exclusion rows do not include an event time. A row is identified by its preserved value or a readable slug, plus the person and the full reason.
- Production Playwright does not enable local curation. The curator pages were checked on the dev server, and the review unit tests passed.
- `next dev` can still mount a development portal. `next start` does not. The accessibility run used `next start`.
