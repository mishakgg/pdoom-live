# Historical-backfill test input notice

The `synthetic-wmt08-scores.txt` file in this directory is self-authored test
input, not copied WMT data and not an observed benchmark result. Its deliberately
fictional system labels begin with `synthetic-`; its arbitrary decimal values do
not report WMT performance. Metric, language-pair and test-set strings exercise
the parser's historical-label preservation, not a new measurement or an identity
claim. Tests create gzip members from these bytes locally and do not fetch.

This directory contains no real WMT gzip, full extracted results, translations,
individual judgments, ACL paper, organizer page or other acquired source body.
The synthetic fixture is test software material under the repository software
license. It is outside `data/`; the repository's data dedication does not grant
rights to WMT sources.

Reuse and redistribution rights for the real WMT08 score gzip remain **unknown**.
Neither the ACL paper's license, repository software license, nor a data/CC0
dedication propagates to that gzip. Public availability is not permission to
redistribute it. Any separately supplied exact local artifact is only accepted
for experimental review, with no publication, canonical admission, production
import or claim of an independent experiment per score row.

The fixed reader pin identifies reviewed bytes, not a bundled fixture:

- Source: <https://www.statmt.org/wmt08/wmt08-human-and-automatic-ranks.gz>
- SHA-256: `f49c4f058173c45b0c3ff455be8024ed13d98656810127297d815a502587cbac`
- Compressed bytes: 16,071; decompressed bytes: 113,529; score rows: 2,584

Those are properties of the reviewed snapshot, not general WMT guarantees.
Real-file acceptance is a separate private local check and is not part of CI.
CI is wholly offline and synthetic. Explicit `--synthetic` output uses synthetic
artifact identities and null source URLs, historical dates and transport times;
it cannot establish observed WMT evidence or real-source rights.
