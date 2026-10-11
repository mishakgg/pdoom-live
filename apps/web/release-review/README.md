# Local fixture release review

Reviewed on 12 October 2026 (Europe/Istanbul), starting from `75641fc777cb3af2d21258128d28c93deb4314d3`, in a separate Git worktree on `codex/web-release-review-20261012`.

**Result: ready for a local release review using synthetic fixtures. No remaining blocker was found within that scope.** This is not a production deployment or a verification of a live researcher dataset.

## Changes

- Every public page now identifies the synthetic dataset, including direct researcher, statement, and source-item URLs. The notice explicitly says that people, organizations, statements, and evidence are fictional. Live and unloaded datasets are not mislabeled synthetic. A failed dataset-context read is disclosed without replacing the page's error boundary.
- Header search suggestions now show both the statement class and the review state before navigation. A model-inferred signal cannot appear in that surface as an unlabeled direct statement.
- Media evidence locators display a usable timestamp while preserving the exact stored offsets: `31:00–31:25 (1860000–1885000 ms)` for the fixture podcast.
- Pagination tests use explicit UTC instants and check legacy cursors with both UTC and America/New_York database timezones. The original date-only fixtures caused an incorrect failure on a non-UTC server; cursor implementations and contracts are unchanged.
- CLI process tests launch Node with `--import tsx`, exercising the actual CLI's shutdown and export behavior without the tsx command wrapper's Unix socket.
- Added regression tests for the disclosures, search labels, timestamps, and complete fixture-to-evidence journey. Existing accessibility checks also require the fixture notice on all 20 public routes.

Only web application code, tests, and this review evidence were changed. Shared contracts, SQL schemas/migrations, ingestion code, researcher registries, and fixture data were not changed. The F: archive was not accessed. Nothing was deployed.

## Validation

Final checks ran on Node **22.23.3**, PostgreSQL **16.15**, and Playwright **1.63.0** with its pinned Chromium **153.0.8010.12**. The same final implementation also passed on the session's initial Node 24.19.0 runtime.

| Check | Result |
| --- | --- |
| `npm ci` | Passed on the initial Node 24 runtime; lockfile unchanged |
| `npm run lint` | Passed: zero errors, six existing API-anchor warnings |
| `npm run typecheck` | Passed for all workspaces and E2E tests |
| `npm test` | **493 passed**, 57 files, zero failures |
| `npm run build` | Passed; production Next.js build |
| `CI=1 npm run test:e2e` | **166 passed**, two intentional viewport-specific skips, zero failures |
| `git diff --check` | Passed |

The two Playwright skips are the desktop-only intermediate-width/zoom test in the mobile project and the mobile-only masthead test in the desktop project. Each runs in its intended project.

Lint's existing warnings concern native links to `/api/v1` resources on the Public data page. The page deliberately uses anchors to avoid Next.js prefetch query parameters that the API rejects. They are not lint errors and were not replaced with client navigation.

The baseline had 479 passing and three failing unit tests; all three failures were resolved without changing runtime database or public cursor behavior. Its 161 browser tests already passed. The final suite adds fixture-disclosure, suggestion-label, timestamp, timezone, and journey coverage.

### Isolation and reproduction

All checkout files, dependencies, browser caches, and PostgreSQL data were kept in this session's Linux workspace; neither Windows C: nor F: was used. The environment exposes a single mapped Unix uid, so a temporary uid/owner compatibility shim was used only to launch the disposable PostgreSQL server. It is not part of the repository or application. PostgreSQL listened only on loopback, with Unix sockets disabled.

Databases were separate:

- `pdoom_release_unit_test`: unit/database tests; migrated and reset through the existing test setup.
- `pdoom_release_fixture_test`: existing synthetic dataset plus the existing browser-only adversarial overlay.
- `pdoom_release_empty_test`: existing empty-dataset test fixture.
- The outage server used the existing deliberately refused database port.

On a normal machine with Node 22 and PostgreSQL 16, the repository's documented commands reproduce the review:

```bash
npm ci
npm run lint
npm run typecheck
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/pdoom_release_unit_test npm test
npm run build
npx playwright install chromium
E2E_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/pdoom_release_fixture_test \
E2E_EMPTY_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/pdoom_release_empty_test \
CI=1 npm run test:e2e
```

Create the unit database first. The existing E2E setup creates and seeds its own databases using `E2E_ADMIN_DATABASE_URL`; the default is the local `postgres` database. Use only isolated databases whose names contain `test`.

The CDN's download alias returned HTML in this environment. The exact pinned Chromium headless-shell archive was obtained from its official Chrome-for-Testing storage URL; no browser version or application configuration was substituted.

## Browser findings

| Review area | Verified behavior |
| --- | --- |
| Main journey | Homepage → Ada Quill → 2025 statement → original evidence → stored source-item audit, on desktop and mobile |
| Evidence | Exact stored excerpt, surrounding context, canonical URL, source publication/observation times, readable media span, safe new-tab link |
| Statement classes | Explicit numeric estimates retain their stated values; qualitative views have no invented probability; inferred signals are labeled as model output, separately from human verification |
| Synthetic data | Notice present on all 20 audited public routes and direct links; absent on the empty live dataset |
| Mobile | 390×844 touch viewport, wrapping evidence/URLs, usable navigation and suggestion popup, no horizontal overflow |
| Keyboard | Skip link, visible focus rings, Tab/Enter navigation, arrow-key suggestions, Escape dismissal, stable-id person selection |
| Search and filters | Similar names remain distinct; stale requests stay dismissed; filters and pagination survive history; invalid/stale cursors offer recovery without dropping valid filters |
| Empty/error states | Empty live dataset, zero matching statements, invalid filters, unknown slugs, unavailable evidence, absent dates/horizons, and refused database all remain explicit |
| Accessibility | Axe checks across 20 public routes on desktop/mobile; headings, landmarks, focus and 200% zoom checks pass |
| Security and performance | Hostile evidence remains text; private/unreviewed/rejected markers stay out of public views; browser request, response-time, and script budgets pass |

The browser tests guard console errors, uncaught exceptions, dialogs, unintended external requests, and repeated API requests. Expected outage responses are allowed only by their dedicated tests. No guard or performance budget was weakened.

## Screenshots

These are actual full-page Chromium screenshots from the passing Node 22 fixture run. Mobile captures use device scale factor 2; the layout viewport is 390×844.

| Surface | Desktop | Mobile |
| --- | --- | --- |
| Homepage | [Open](screenshots/home-desktop.png) | [Open](screenshots/home-mobile.png) |
| Researcher and all three classes | [Open](screenshots/researcher-desktop.png) | [Open](screenshots/researcher-mobile.png) |
| Numeric statement and evidence | [Open](screenshots/statement-desktop.png) | [Open](screenshots/statement-mobile.png) |
| Stored original evidence | [Open](screenshots/source-evidence-desktop.png) | [Open](screenshots/source-evidence-mobile.png) |
| Inferred signal in search | [Open](screenshots/inferred-search-desktop.png) | [Open](screenshots/inferred-search-mobile.png) |

![Researcher statements with explicit, qualitative and inferred labels](screenshots/researcher-desktop.png)

## Remaining blockers and limits

**Local fixture release review: none found.** Remote CI should be checked before merging the draft PR.

Synthetic originals use the reserved `synthetic.pdoom.example` host. The journey verifies stored evidence and the outbound URL, target and link protection. One outbound navigation is intercepted with a clearly marked fixture response to test opening the original URL without a live request. This does not verify the existence or content of a real publication.

The browser review covers Chromium and mobile emulation, not physical devices or Firefox/WebKit. Live ingestion, real researcher coverage, public deployment, and the Windows/F: environment were outside this review. A public launch still needs its separate live-data and operational review.
