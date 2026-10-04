# Coverage funnel, before and after cohort 2026.10.0

Counts are unique people. A registered feed, an academic identifier, a source item, and a usable statement are separate stages.

organization_hq_country is a property of the current organization. It is not a person's nationality.

collection_score is a fetch budget. It is not a ranking of people.

| Stage | Before | After |
| --- | ---: | ---: |
| Tracked person | 323 | 328 |
| Verified external identity | 246 | 246 |
| High-confidence external identity | 137 | 137 |
| Accessible source, including academic feeds | 250 | 250 |
| Accessible non-academic source | 24 | 24 |
| Observed item | 59 | 63 |
| Attributable evidence | 59 | 63 |
| Usable evidence | 15 | 22 |
| Statement candidate | 15 | 15 |
| Public or review-eligible statement | 12 | 12 |
| Research-export-eligible statement | 2 | 2 |

## Primary gap

| Gap | Before | After |
| --- | ---: | ---: |
| academic_source_only | 181 | 181 |
| awaiting_review | 13 | 13 |
| failed_collection | 4 | 3 |
| no_attributable_statement_found | 22 | 25 |
| no_known_source | 67 | 69 |
| not_attempted | 8 | 9 |
| research_export_eligible | 2 | 2 |
| unsupported_parser | 26 | 26 |

## Quality

- Ambiguous records: 71 before, 74 after.
- Duplicate external-id groups: 0 before, 0 after.
- Duplicate observation URL count: 0 before, 1 after.
- Duplicate observation rate: 0.0 before, 0.003 after.
- Collector failure rate: None before, 0.1111 after.
- Freshness before: {'observations_with_published_at': 225, 'observations_missing_published_at': 9, 'newest_published_at': '2026-09-23T19:00:00Z', 'oldest_published_at': '2017-06-05T23:56:05Z'}
- Freshness after: {'observations_with_published_at': 324, 'observations_missing_published_at': 9, 'newest_published_at': '2026-10-03T17:36:19Z', 'oldest_published_at': '2017-06-05T23:56:05Z'}

## Collection cost

The stored staging directory is the second bounded live run on 2026-10-04. Fixture tests do not call these hosts. No paid API was used.

- Runtime: 5.43 seconds.
- HTTP requests: 13.
- Staging collector runs: 9. Failures: 1. Failure rate: 1/9.
- Failure: `parser_unsupported` for `https://sethlazar.substack.com/feed` because the response content type was `text/html`.
- Observations: 99. Candidates: 1, review state `needs_review`.
- Historical belief-collection failures, joined by URL and not replayed here: 51 events over 129 runs in `data/reports/cohort-v2026-09-quality.json` (48 `speaker_labels_absent`, 2 `rate_limited`, 1 `invalid_content`).

People who gained usable evidence in this pass: Andrew Critch, Eliezer Yudkowsky, Lilian Weng, Nathan Lambert, Sung Nako, Victoria Krakovna, and Yoo Kang-min. Usable evidence here is an attributable excerpt or a candidate with evidence text. It is not yet a research-export forecast. The statement extractor emitted one new candidate, from Paul Christiano's LessWrong post, and left the other excerpts without a forecast candidate.

Adapters remain unwired. `runner_wired` is false.

## Why some stages did not move

Verified identities stayed at 246. The new Bluesky and Semantic Scholar ids belong to people who already had an external id. The five new people have no external id. Ambiguous unresolved people stayed at 71. The three new ambiguity rows are recorded non-merges, so the ambiguity file grew from 71 to 74 without a new identity merge. Duplicate external-id groups stayed at 0.

Accessible sources stayed at 250, and accessible non-academic sources stayed at 24. The new ForumMagnum and Bluesky feeds belong to people who already had a non-academic source. Neil Zeghidour and Alexandre Défossez have no known personal source. Yan Junjie's Chinese management page is an institution-level reference, not a collectible personal feed. Sung Nako and Yoo Kang-min share one press-release URL. The duplicate observation URL count of 1 is that shared URL.

`no_known_source` rose from 67 to 69 because the two Kyutai researchers were added without a personal feed. `not_attempted` rose from 8 to 9 because Yan Junjie has a reference page and no collection attempt. `failed_collection` fell from 4 to 3 because Seth Lazar's new HTML response is `parser_unsupported`, so his primary gap is now `unsupported_parser`. Eliezer Yudkowsky moved out of `unsupported_parser` because a LessWrong excerpt is now stored, which kept that gap's person count at 26.
