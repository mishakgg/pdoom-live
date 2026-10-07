# Public visibility regression fixture

All names, identities, excerpts, URLs, and organizations are fictional. Load only into a database whose name contains `test`.

`test/public-visibility.test.tsx` loads this canonical fixture and restores the standard synthetic fixture afterward. It covers all five review states on sources, identities, affiliations, statements, forecasts, and relationships; public statements attached to independently nonpublic forecasts; mixed public/private evidence and participants; an explicitly rejected source containing a machine-validated statement; and an unreviewed container with one independently public audit item.

The historical removed item remains visible for audit. Its newer version is unreviewed, so the audit metadata must not link to that hidden version. Raw staging metadata contains a marker that must never appear in application responses or SSR.

Before the real staging/review tests add rows, the website has 11 public statements and 11 audit items, with 3 source containers in its source lists. Research exports have 9 statements and 9 items, with 2 source containers: they omit needs-review content and the unreviewed-container audit exception. Research statements and relationships must retain source, item, and endpoint records in the same export.
