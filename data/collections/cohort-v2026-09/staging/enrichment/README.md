# Enrichment staging

Identity and coverage jobs write source rows here as `sources.jsonl`.

Belief refresh does not write this directory. When a canonical document is assembled, enrichment rows are added only when their slug and canonical URL are not already present. A belief file name must not collide with a file in this directory.
