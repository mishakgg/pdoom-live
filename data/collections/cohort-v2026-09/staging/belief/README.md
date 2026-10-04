# Belief staging

`jobs.refresh` and `jobs.collect_beliefs` write observations, statements, runs, and a summary here.

Enrichment jobs must not write this directory. The refresh assembles `canonical-live.json` from this staging area plus the seed registry and any enrichment source rows.
