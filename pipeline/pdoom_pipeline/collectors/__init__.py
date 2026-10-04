"""Source collectors. Each one emits SourceObservation records."""

from pdoom_pipeline.collectors.arxiv import ArxivCollector
from pdoom_pipeline.collectors.bluesky import BlueskyCollector
from pdoom_pipeline.collectors.forum_magnum import ForumMagnumCollector
from pdoom_pipeline.collectors.github import GitHubCollector
from pdoom_pipeline.collectors.openalex_works import OpenAlexWorksCollector
from pdoom_pipeline.collectors.rss import RssCollector

__all__ = [
    "ArxivCollector",
    "BlueskyCollector",
    "ForumMagnumCollector",
    "GitHubCollector",
    "OpenAlexWorksCollector",
    "RssCollector",
]
