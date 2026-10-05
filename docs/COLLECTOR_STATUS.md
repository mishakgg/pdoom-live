# Collector status

Belief collection calls RssCollector only.

`collect_beliefs` in `pipeline/pdoom_pipeline/belief/collect.py` imports `RssCollector` from `pipeline/pdoom_pipeline/collectors/rss.py` and calls `RssCollector().parse` on feed payloads. No other collector class is imported or called from that function.

These collector modules exist under `pipeline/pdoom_pipeline/collectors/` and are not wired into collect_beliefs:

- `arxiv` (`ArxivCollector`)
- `bluesky` (`BlueskyCollector`)
- `crossref` (`CrossrefCollector`)
- `forum_magnum` (`ForumMagnumCollector`)
- `github` (`GitHubCollector`)
- `huggingface` (`HuggingFaceCollector`)
- `openalex_works` (`OpenAlexWorksCollector`)
- `openreview` (`OpenReviewCollector`)
- `semantic_scholar` (`SemanticScholarCollector`)
- `youtube_metadata` (`YouTubeMetadataCollector`)

`base.py` in that directory is a package marker. It does not define a collector.

ForumMagnum and Bluesky stay unwired.

The tracked set is a defined cohort, not all AI researchers. Counts and freshness for that cohort are what the dataset can support. This note does not treat the cohort as a stand-in for the field.
