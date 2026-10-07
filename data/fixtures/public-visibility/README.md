# Public visibility regression fixture

All names, identities, excerpts, URLs, and organizations are fictional. Load only into a database whose name contains `test`.

`test/public-visibility.test.tsx` loads this canonical fixture and restores the standard synthetic fixture afterward. It covers all five review states on sources, identities, affiliations, statements, forecasts, and relationships; public statements attached to independently nonpublic forecasts; mixed public/private evidence and participants; an explicitly rejected source containing a machine-validated statement; and an unreviewed container with one independently public audit item.

The historical removed item remains visible for audit. Its newer version is unreviewed, so the audit metadata must not link to that hidden version. Raw staging metadata contains a marker that must never appear in application responses or SSR.

Three machine-validated statements reference evidence on a different item: an item in a rejected source, one in an unreviewed source, and an otherwise public item. Canonical import accepts these independent references; all public reads must fail closed on the mismatch, and a relationship to a mismatched statement must be omitted. Same-item historical/removed audit evidence stays public.

Hidden forecasts have distinct ranges, distribution quantiles, and metadata markers to catch leaks through trend exclusions and serialized output. A verified public distribution with an unregistered question exercises the unpooled inspection view positively. The audit container has staged ownership pointing at the private-attribution person; item search must use its public speaker instead and must not match hidden-only participants or staged ownership.

Before the real staging/review tests add rows, the website has 11 public statements and 11 audit items, with 3 source containers in its source lists. Research exports have 9 statements and 9 items, with 2 source containers: they omit needs-review content and the unreviewed-container audit exception. Research statements and relationships must retain source, item, and endpoint records in the same export.
