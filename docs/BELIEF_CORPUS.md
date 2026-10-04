# Belief and forecast corpus

This layer collects public writing and appearances for people already in cohort `2026.09.0`. It does not add people. A name that shows up only as a guest, coauthor, or mention stays out of the cohort. Unknown handles stay unknown.

Collection priority in `collection_priority.jsonl` is a fetch budget. It is not a ranking of researchers and it is not a measure of importance.

## What is collected

Owned feeds are public RSS or Atom feeds tied to one person by the feed's author field, or by the full name on an owned site when the author field is empty. A feed is not assigned to someone because a URL used to belong to them. `bounded-regret.ghost.io` is an author-matched feed: each item follows the current author field.

Show feeds are official podcast RSS feeds. The show source has no person owner. A guest is recorded only when exactly one high-distinctiveness cohort display name appears in the episode title. A low-distinctiveness name in a title is not enough. Two cohort names in one title are left unresolved. Statements are taken only from transcript turns labeled with that person's name. Show notes and unlabeled transcripts are not the guest's words.

X, Bluesky, and Mastodon are not searched by name. The `2026.09.0` corpus pass does not collect them.

Cohort `2026.10.0` stages a Bluesky author feed and a LessWrong user-post feed for accounts that were already linked to a tracked person. Those adapters are not part of `collect_beliefs`, and they do not write `canonical-live.json`. See [channel integration](./CHANNEL_INTEGRATION_2026_10.md).

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
- `remote_work_automation` — full automation of remote work, as the speaker worded it. Not an AGI date and not a job-displacement share.
- `coding_automation` — coding or software-engineering automation.
- `job_displacement` — jobs, workers, or unemployment. Not a task share. The unit records whether the speaker stated a geography.
- `task_automation` — tasks automated or affected. Not an unemployment or job share.
- `wage_effect` — a direct wage forecast.
- `productivity_growth` — productivity, GDP, or growth. Not a job share.
- `capability_milestone` — a capability threshold that is not one of the timeline keys.
- `compute_scaling` — compute, scaling, or energy.
## Extraction

`rule-extract-0.4.0` copies numbers, ranges, odds, years, and percentages that the source states. A probability of arrival by a year stays a probability. A date forecast stays a timeline. "Before 2035", "within five years", "two to three years", "in the early 2030s", and "this decade" keep the source's horizon wording. "This decade" has no invented calendar year. Qualitative words such as "unlikely" do not become percentages. A task share is not stored as a job or unemployment share.

A number and its definition may come from adjacent sentences in the same source item when one sentence has the probability and the next begins with an anaphoric phrase such as "by that I mean". A horizon or condition in the immediately previous sentence can attach to a numeric sentence that already names the outcome. A bullet that says only "35% probability by 2050" can use the outcome from the immediately previous sentence when that sentence says "probability of" a named outcome. The number stays the bullet's number. A previous sentence that merely mentions an outcome, without that probability wording, does not lend it. The evidence text keeps both sentences. These candidates are `needs_review` and carry `multi_sentence_evidence`. The window does not cross a `<<<SPEAKER_GAP>>>` marker, a different speaker label, or a question. An unrelated nearby percent, such as a benchmark score, does not become a probability. "Disempowered" stays `disempowerment` and is not stored as extinction. "What humans do" stays a task share. "Jobs" stay a job share. "Over the next decade" is kept as horizon wording. A median stated as "my own median timelines of N years until full automation of remote work" stays that question. A sentence that names another person as the one who thinks or estimates the figure is not extracted.

Podcast and talk transcripts are split into consecutive turns by the tracked speaker. A label may include a timestamp, as in `Dario Amodei (00:01:02):`. An intervening speaker starts a new block, so the next turn is not treated as adjacent. Unlabeled transcript text is not extracted. When a show episode has no separate transcript URL, the collector reads the official episode page and keeps only turns labeled with the guest's name. A sentence that says "I'll give a probability of N% for that" can use the outcome named in the immediately previous sentence. A sentence that says other people interpreted a number, or that names nuclear war as the cause, is not extracted. A curated official single-speaker talk page can be extracted when the page names the person and has no competing speaker labels. The person does not own the event.

Sentences that report someone else's number, a hypothetical scenario, or a present-tense statistic are not emitted. A bare mention of AGI or alignment is not a model signal. A signal requires stance language as well as a topic, and it stays `model_inferred_signal` with no numeric value.

Pipeline review flags such as `missing_horizon`, `ambiguous_definition`, `multi_sentence_evidence`, `range_value`, and `possible_duplicate` stay on the candidate JSONL. They are not public labels and they do not promote a row.

A qualitative sentence with no comparable question is exported as a statement without a forecast. The live forecast object requires a non-empty `question_key`, so the exporter does not fill `unspecified`. No new comparison bucket is created.

Owned essays are single public HTML pages, or a public markdown API when the HTML host blocks the collector. `html_page` maps to the canonical collection method `manual`, with adapter `html_page`, because the live import enum has no separate HTML method. The tracked person's name has to be on the page, in a platform byline handle that contains their name tokens, or in a hostname that contains both their given and family name on a page curated as their site. Comments after a configured cut marker are not extracted. Podcast shows are still not owned by the guest.

Evidence keeps the sentence plus one neighboring sentence on each side. Speaker-labeled transcripts can carry a timestamp when the line has one. Conditions introduced by "if", "unless", "given", or "assuming" stay on the forecast. Missing horizons or ambiguous definitions stay `needs_review`. Nothing is marked `human_verified`.

A later statement becomes an `updates` candidate only when its own text says the view was revised and the number or year changed for the same question key and horizon. The same number restated later for that same question and horizon can be `repeats`. "To clarify" with the same number can be `clarifies`. "I retract" or "I was wrong" can be `retracts`. A different number, or a different horizon, without revision language does not become a changed belief. These relationships stay `unreviewed`.

Pages that were considered and not admitted are written to `source_leads.jsonl`. That file is not part of the canonical import. A lead records the person, URL, source type, why it was left out, and whether a later pass should retry it.

## Canonical export

`pdoom_pipeline.export.corpus.export_corpus` maps these rows into the live import document from `docs/INGESTION_CONTRACT.md`. Collector observations stay excerpts. The command is:

```bash
PYTHONPATH=pipeline python -m pdoom_pipeline.jobs.collect_beliefs --live
```

The canonical file is `data/collections/cohort-v2026-09/canonical-live.json`.
