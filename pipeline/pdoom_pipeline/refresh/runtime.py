"""Call admitted collectors with conditional requests and retained versions."""

from __future__ import annotations

from typing import Any

from pdoom_pipeline.collectors.arxiv import ArxivCollector
from pdoom_pipeline.collectors.github import GitHubCollector
from pdoom_pipeline.collectors.openalex_works import OpenAlexWorksCollector
from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.ingest.store import ObservationStore

ADMITTED = ("rss", "arxiv", "github", "openalex_works")


def call_adapter(
    name: str,
    *,
    fetcher: SafeFetcher,
    source: dict[str, Any],
    observed_at: str,
) -> dict[str, Any]:
    if name not in ADMITTED:
        raise CollectorFailure("parser_unsupported", f"adapter {name} is not admitted")
    try:
        observations = _collect(name, fetcher=fetcher, source=source, observed_at=observed_at)
    except CollectorFailure:
        if fetcher.last and fetcher.last.not_modified:
            return _fetched(fetcher, observations=[], outcome="unchanged")
        raise
    outcome = "unchanged" if fetcher.last and fetcher.last.not_modified else "fetched"
    return _fetched(fetcher, observations=observations, outcome=outcome)


def ingest_observations(store: ObservationStore, observations: list) -> list[dict[str, Any]]:
    results = []
    for observation in observations:
        ingested = store.ingest(observation)
        results.append(
            {
                "status": ingested.status,
                "logical_key": ingested.logical_key,
                "content_version": ingested.content_version,
                "content_hash": ingested.content_hash,
                "canonical_url": observation.canonical_url,
            }
        )
    return results


def adapter_for_source(source: dict[str, Any]) -> str | None:
    method = source.get("collection_method")
    if method == "rss_feed":
        return "rss"
    if method == "github_api":
        return "github"
    if method == "openalex_api":
        return "openalex_works"
    if method == "arxiv_api":
        return "arxiv"
    return None


def adapter_source(source: dict[str, Any]) -> dict[str, Any] | None:
    name = adapter_for_source(source)
    if name is None or not source.get("enabled", True):
        return None
    url = source["canonical_url"]
    payload: dict[str, Any] = {
        "adapter": name,
        "source_identity": source["id"],
        "url": url,
        "name": source.get("name") or source["id"],
    }
    if name == "github":
        username = url.rstrip("/").split("/")[-1]
        payload["username"] = username
        payload["url"] = f"https://api.github.com/users/{username}/repos?per_page=10&sort=updated&type=owner"
    elif name == "openalex_works":
        author = url.rstrip("/").split(":")[-1]
        payload["openalex_author_id"] = author
    elif name == "arxiv":
        payload["search_query"] = source.get("search_query") or ""
    return payload


def _collect(name: str, *, fetcher: SafeFetcher, source: dict[str, Any], observed_at: str):
    identity = source["source_identity"]
    if name == "rss":
        return RssCollector(fetcher=fetcher).collect(source_identity=identity, feed_url=source["url"], observed_at=observed_at)
    if name == "github":
        return GitHubCollector(fetcher=fetcher).collect_repos(
            source_identity=identity,
            username=source["username"],
            observed_at=observed_at,
        )
    if name == "openalex_works":
        return OpenAlexWorksCollector(fetcher=fetcher).collect_author(
            source_identity=identity,
            openalex_author_id=source["openalex_author_id"],
            observed_at=observed_at,
        )
    if not source.get("search_query"):
        raise CollectorFailure("invalid_content", "arxiv adapter requires search_query")
    return ArxivCollector(fetcher=fetcher).collect_query(
        source_identity=identity,
        search_query=source["search_query"],
        observed_at=observed_at,
    )


def _fetched(fetcher: SafeFetcher, *, observations: list, outcome: str) -> dict[str, Any]:
    last = fetcher.last
    headers = last.headers if last else {}
    return {
        "outcome": outcome,
        "observations": observations,
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "status": last.status if last else None,
        "not_modified": bool(last and last.not_modified),
    }
