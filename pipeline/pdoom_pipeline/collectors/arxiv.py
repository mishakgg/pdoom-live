"""arXiv API metadata collector. Stores titles, authors, and abstract excerpts."""

from __future__ import annotations

from urllib.parse import urlencode

import defusedxml.ElementTree as ET

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import arxiv_id_from_url, canonicalize_url

COLLECTOR_VERSION = "arxiv-0.1.0"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
API = "https://export.arxiv.org/api/query"


class ArxivCollector:
    collector = "arxiv"
    platform = "arxiv"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/atom+xml", "text/xml", "application/xml"),
            max_bytes=1_000_000,
        )

    def collect_query(self, *, source_identity: str, search_query: str, observed_at: str, max_results: int = 25) -> list[SourceObservation]:
        if max_results < 1 or max_results > 50:
            raise CollectorFailure("invalid_content", "max_results must be between 1 and 50")
        url = API + "?" + urlencode({"search_query": search_query, "start": 0, "max_results": max_results})
        result = self.fetcher.get(url)
        return self.parse(result.body, source_identity=source_identity, observed_at=observed_at)

    def parse(self, payload: bytes, *, source_identity: str, observed_at: str) -> list[SourceObservation]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise CollectorFailure("invalid_content", f"malformed arxiv feed: {exc}") from exc
        observations: list[SourceObservation] = []
        for entry in list(root):
            if entry.tag != f"{ATOM}entry":
                continue
            observations.append(_entry(entry, source_identity=source_identity, observed_at=observed_at))
        return observations


def _entry(entry, *, source_identity: str, observed_at: str) -> SourceObservation:
    id_url = _child_text(entry, f"{ATOM}id")
    versioned = _versioned_id(id_url)
    bare = arxiv_id_from_url(id_url) or versioned
    if not bare:
        raise CollectorFailure("invalid_content", "arxiv entry missing id")
    title = _child_text(entry, f"{ATOM}title")
    summary = _child_text(entry, f"{ATOM}summary")
    published = _normalize_time(_child_text(entry, f"{ATOM}published"))
    updated = _normalize_time(_child_text(entry, f"{ATOM}updated"))
    authors = []
    for author in entry.findall(f"{ATOM}author"):
        name = _child_text(author, f"{ATOM}name")
        if name:
            authors.append(
                AuthorCandidate(
                    name=name,
                    role="author",
                    attribution_method="arxiv_author_metadata",
                    confidence="high",
                )
            )
    text, truncated = excerpt(summary, 1500)
    canonical = canonicalize_url(f"https://arxiv.org/abs/{bare}")
    observation = SourceObservation(
        source_identity=source_identity,
        platform="arxiv",
        upstream_id=versioned or bare,
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=published,
        author_candidates=authors,
        title=title or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "upstream_version": versioned or bare,
            "updated_at_source": updated,
            "truncated": truncated,
            "arxiv_id": bare,
        },
        collection_method="arxiv_api",
        collector="arxiv",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _child_text(parent, tag: str) -> str:
    element = parent.find(tag)
    if element is None or element.text is None:
        return ""
    return " ".join(element.text.split())


def _versioned_id(id_url: str) -> str:
    if not id_url:
        return ""
    tail = id_url.rstrip("/").split("/")[-1]
    return tail


def _normalize_time(value: str) -> str | None:
    if not value:
        return None
    if value.endswith("Z"):
        return value
    if "+" in value[10:] or value.endswith("Z"):
        return value.replace("+00:00", "Z")
    return value
