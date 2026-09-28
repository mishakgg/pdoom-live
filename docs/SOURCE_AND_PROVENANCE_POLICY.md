# Source and provenance policy

## Goal

pdoom.live should be useful because users can verify where information came from.

Collection breadth is secondary to provenance quality.

## Source priority

Prefer sources in roughly this order for attribution:

1. the person's own public post, essay, site, newsletter, paper, talk, interview, podcast, testimony, repository, or model card;
2. official organization/lab publication directly attributable to the person;
3. primary audio/video/transcript published by a host;
4. reliable reporting containing an attributable direct statement;
5. secondary summaries for discovery only.

A secondary article saying that someone believes X is not equivalent to the person saying X.

## Initial source channels

High-value channels include:

- personal websites and RSS/Atom feeds;
- lab/research organization blogs and research pages;
- podcasts and podcast RSS metadata;
- YouTube talks, interviews, panels, and available captions/transcripts;
- arXiv and other paper/preprint metadata;
- OpenReview;
- GitHub;
- Hugging Face;
- Bluesky;
- Mastodon;
- X where collection is authorized and technically sustainable;
- conference sites and official talk archives;
- government testimony/hearing records;
- reputable interviews and press reports.

LinkedIn and other restrictive platforms may be useful for discovery, but the system must not depend on prohibited scraping.

## Collection rules

- Prefer official APIs, feeds, sitemaps, public datasets, and permitted page fetches.
- Respect authentication and access controls.
- Do not bypass paywalls, CAPTCHAs, anti-bot systems, robots restrictions that apply to the collector, or other technical controls.
- Record the collection method and source URL.
- Apply rate limits and backoff.
- Use a clear user agent where direct HTTP collection is appropriate.
- Bound response size, redirects, and processing time.

## Copyright / retention

The product should generally store only what it needs to identify, analyze, deduplicate, and evidence a statement.

Prefer storing:

- source metadata;
- canonical URL;
- hashes;
- timestamps;
- short necessary evidence excerpts;
- transcript timestamps;
- extracted structured facts;
- references to externally hosted material.

Do not build the product around republishing complete copyrighted articles, newsletters, podcast transcripts, or books.

If a source license explicitly permits broader retention, record the license/rights basis.

## Evidence

Each published statement should identify a verification target:

- a short text span and surrounding context;
- a transcript segment with timestamp;
- a page/section reference for a paper;
- or an equivalent stable reference.

Evidence should be attributable to the speaker/author. Content merely mentioning a person is not evidence of that person's view.

## Explicit numeric forecasts

An `explicit_numeric` record requires the source to contain the person's numerical value, range, odds, probability, date, quantity, or distribution.

Preserve:

- original wording;
- normalized number;
- units;
- definition/question;
- conditioning;
- horizon;
- evidence.

Examples that should remain different:

- probability of literal human extinction;
- probability of catastrophic harm;
- probability of permanent human disempowerment;
- probability conditional on AGI being built;
- chance of AGI by a specific year.

Do not aggregate them merely because they are all colloquially called p(doom).

## Qualitative statements

If someone says an outcome is “unlikely,” “plausible,” “a serious risk,” or similar without a number:

- store the statement as qualitative;
- preserve the wording/context;
- optionally attach a bounded taxonomy/category;
- do not fabricate a numerical equivalent.

## Model-inferred signals

Machine analysis can be useful for:

- topic classification;
- detecting potential view changes;
- finding candidate forecasts;
- summarizing source evidence;
- estimating whether two statements address comparable questions.

It must be clearly marked as inferred.

The system must not present inferred signals as direct quotes, explicit forecasts, or verified personal probabilities.

## Identity attribution

Accept strong evidence such as:

- a link from an official/personal profile to the account;
- consistent institutional identity;
- an ORCID/profile relation;
- verified platform identity;
- cross-links among known public profiles.

Name similarity alone is insufficient.

Ambiguous identities go to review.

## Duplicate handling

The same content may appear as:

- original post;
- syndicated copy;
- embedded video;
- podcast feed;
- transcript;
- press summary.

Prefer one canonical source item plus related-source links where possible.

Use upstream IDs, canonical URLs, media IDs, title/date/participant similarity, and content hashes. Deduplication decisions should be reversible.

## Corrections and deletions

If a source changes:

- observe the new content hash/version;
- preserve prior version metadata where appropriate;
- mark statements needing revalidation if their evidence changed.

If a source is removed:

- keep only what is lawful and necessary for audit;
- mark source availability;
- do not pretend the original remains currently accessible.

## Researcher inclusion

A tracked person needs an explicit inclusion reason.

Possible reasons:

- current/recent frontier-lab researcher or research leader;
- author of material frontier-model research;
- researcher focused on advanced-AI safety/evaluations;
- prominent academic/independent researcher whose work materially bears on frontier-AI forecasts;
- former frontier researcher with ongoing relevant public forecasting.

The cohort must be versioned so historical trends remain interpretable as membership changes.

## Trend eligibility

A statement should contribute to an aggregate only if:

- its source/provenance passes validation;
- its identity attribution passes validation;
- it matches the trend's declared question key, unit, and conditionality;
- its statement class is permitted by that metric;
- duplicates have been resolved;
- required units/horizon are available.

A trend must disclose the number of contributing people and statements.

## Source failures

Collectors will fail.

Distinguish:

- not found;
- temporarily unavailable;
- rate limited;
- unauthorized;
- blocked by source policy;
- parser unsupported;
- content too large;
- invalid content;
- collector bug.

Do not convert collection failure into “no statement exists.”
