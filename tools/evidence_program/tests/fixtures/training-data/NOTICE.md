# Synthetic Common Crawl CSV contract fixtures

These two small CSVs are self-authored fictional examples, not copies of Common
Crawl statistics or estimates of real crawl sizes. Their schema, native crawl-ID
labels and `<unknown>` sentinel exercise the bounded reader. All counts and
percentages are invented. The historical row checks filtering; one selected
crawl's rounded percentages sum to 99.9999; estimated digest cardinalities may
exceed page captures; URL cardinalities need not add across language buckets.
The native unknown-language `urls` field mirrors a page residual rather than an
independently measured URL cardinality; its normalized cardinality stays null.

Run with the explicit `--synthetic-fixture` flag. Output has `synthetic: true`,
separate synthetic observation identities, null source-byte hashes, and unknown
capture/release dates. Expected real source pins are metadata only in this mode.

No full source CSV is vendored. The default reader requires the two independently
verified full-byte SHA-256 pins at commit
`1053c982a91ba0bb4323c5f00ec3230d9cd54e4b` of
<https://github.com/commoncrawl/cc-crawl-statistics>. CSV-specific and underlying
web-page redistribution rights remain unknown. The source repository's Apache
2.0 code license is not inherited by these source datasets or web pages.
