# Belief and forecast corpus

This layer collects public writing and appearances for people already in cohort `2026.09.0`. It does not add people. A name that shows up only as a guest, coauthor, or mention stays out of the cohort. Unknown handles stay unknown.

Collection priority in `collection_priority.jsonl` is a fetch budget. It is not a ranking of researchers and it is not a measure of importance.

## What is collected

Owned feeds are public RSS or Atom feeds tied to one person by the feed's author field, or by the full name on an owned site when the author field is empty. A feed is not assigned to someone because a URL used to belong to them. `bounded-regret.ghost.io` is an author-matched feed: each item follows the current author field.

Show feeds are official podcast RSS feeds. The show source has no person owner. A guest is recorded only when exactly one high-distinctiveness cohort display name appears in the episode title. A low-distinctiveness name in a title is not enough. Two cohort names in one title are left unresolved. Statements are taken only from transcript turns labeled with that person's name. Show notes and unlabeled transcripts are not the guest's words.

X, Bluesky, and Mastodon are not searched by name. This pass does not collect them.

## Question keys

Records share a `question_key` only when they could sit in one comparison. The definitions live in `pipeline/pdoom_pipeline/belief/taxonomy.py`.

- `extinction_unconditional` — AI-caused human extinction, not conditioned on AGI or ASI.
- `extinction_conditional_agi` — extinction conditional on AGI or ASI.
- `catastrophe_broad` — a broader catastrophic outcome.
- `disempowerment` — permanent disempowerment or loss of control.
- `ai_takeover` — the speaker's wording was AI takeover. Not pooled with extinction or with generic disempowerment.
- `mass_human_death` — most humans die. Not pooled with extinction.
- `ambiguous_doom` — doom, p(doom), existential risk, or an irreversible-future figure whose definition was not one of the more specific keys. These stay `needs_review`.
- `agi_timeline` — the speaker's AGI date. Not the same as human-level or transformative AI.
- `asi_timeline` — ASI or superintelligence.
- `transformative_ai_timeline` — transformative AI.
- `human_level_ai_timeline` — human-level AI.
- `agi_by_year_probability`, `asi_by_year_probability`, `transformative_ai_by_year_probability`, `human_level_ai_by_year_probability` — a probability of arrival by a stated horizon. The value is a probability, not a year, so these are not the timeline keys.
- `coding_automation` — coding or software-engineering automation.
- `job_displacement` — jobs or tasks. The unit records whether the speaker stated a geography.
- `productivity_growth` — productivity, GDP, or growth. Not a job share.
- `capability_milestone` — a capability threshold that is not one of the timeline keys.
- `compute_scaling` — compute, scaling, or energy.
- `unspecified` — export placeholder only. The live forecast schema requires a non-empty `question_key`. The extractor uses it when a qualitative sentence has no comparable question. It is not a statistical comparison bucket.

## Extraction

`rule-extract-0.3.0` copies numbers, ranges, odds, years, and percentages that are in the sentence. A probability of arrival by a year stays a probability. A date forecast stays a timeline. Qualitative words such as "unlikely" do not become percentages. Sentences that report someone else's number, a hypothetical scenario, or a present-tense statistic are not emitted. A bare mention of AGI or alignment is not a model signal. A signal requires stance language as well as a topic, and it stays `model_inferred_signal` with no numeric value.

Owned essays are single public HTML pages, or a public markdown API when the HTML host blocks the collector. `html_page` maps to the canonical collection method `manual`, with adapter `html_page`, because the live import enum has no separate HTML method. The tracked person's name has to be on the page, in a platform byline handle that contains their name tokens, or in a hostname that contains both their given and family name on a page curated as their site. Comments after a configured cut marker are not extracted. Podcast shows are still not owned by the guest.

Evidence keeps the sentence plus one neighboring sentence on each side. Speaker-labeled transcripts can carry a timestamp when the line has one. Conditions introduced by "if", "unless", "given", or "assuming" stay on the forecast. Missing horizons or ambiguous definitions stay `needs_review`. Nothing is marked `human_verified`.

A later statement becomes an `updates` candidate only when its own text says the view was revised and the number or year changed for the same question key. Two different extracts without that language do not become a changed belief.

## Canonical export

`pdoom_pipeline.export.corpus.export_corpus` maps these rows into the live import document from `docs/INGESTION_CONTRACT.md`. Collector observations stay excerpts. The command is:

```bash
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.collect_beliefs --live
```

The canonical file is `data/collections/cohort-v2026-09/canonical-live.json`.
