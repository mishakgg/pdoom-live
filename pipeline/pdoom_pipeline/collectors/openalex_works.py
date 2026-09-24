"""OpenAlex works collector keyed by a resolved author id."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import arxiv_id_from_url, canonicalize_url

COLLECTOR_VERSION = "openalex-works-0.1.0"
API = "https://api.openalex.org/works"
MAX_ABSTRACT_POSITIONS = 4000


class OpenAlexWorksCollector:
    collector = "openalex_works"
    platform = "openalex"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(allowed_content_types=("application/json",), max_bytes=2_000_000)

    def collect_author(self, *, source_identity: str, openalex_author_id: str, observed_at: str, per_page: int = 25) -> list[SourceObservation]:
        author_id = openalex_author_id.rstrip("/").split("/")[-1]
        if not author_id.startswith("A") or not author_id[1:].isdigit():
            raise CollectorFailure("invalid_content", "openalex author id must look like A123")
        if per_page < 1 or per_page > 50:
            raise CollectorFailure("invalid_content", "per_page must be between 1 and 50")
        query = urlencode(
            {
                "filter": f"authorships.author.id:{author_id}",
                "per-page": per_page,
                "sort": "publication_date:desc",
                "select": "id,display_name,publication_date,doi,ids,authorships,primary_location,abstract_inverted_index,language",
                "mailto": "collector@pdoom.live",
            }
        )
        result = self.fetcher.get(f"{API}?{query}")
        return self.parse(result.body, source_identity=source_identity, observed_at=observed_at)

    def parse(self, payload: bytes, *, source_identity: str, observed_at: str) -> list[SourceObservation]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CollectorFailure("invalid_content", f"malformed openalex payload: {exc}") from exc
        works = data.get("results") if isinstance(data, dict) else None
        if not isinstance(works, list):
            raise CollectorFailure("invalid_content", "openalex response missing results")
        observations = []
        for work in works:
            if isinstance(work, dict):
                observations.append(_work(work, source_identity=source_identity, observed_at=observed_at))
        return observations


def _work(work: dict, *, source_identity: str, observed_at: str) -> SourceObservation:
    openalex_url = str(work.get("id") or "")
    work_id = openalex_url.rstrip("/").split("/")[-1]
    if not work_id.startswith("W"):
        raise CollectorFailure("invalid_content", "openalex work missing id")
    landing = ((work.get("primary_location") or {}) or {}).get("landing_page_url") or ""
    doi = work.get("doi") or ""
    canonical_source = landing or doi or openalex_url
    try:
        canonical = canonicalize_url(canonical_source)
    except ValueError:
        canonical = canonicalize_url(openalex_url)
    arxiv_id = arxiv_id_from_url(canonical)
    authors = []
    for authorship in work.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        name = str(author.get("display_name") or "").strip()
        if not name:
            continue
        authors.append(
            AuthorCandidate(
                name=name,
                role="author",
                attribution_method="openalex_authorship",
                confidence="high",
                person_id=None,
            )
        )
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    text, truncated = excerpt(abstract, 800)
    published = work.get("publication_date")
    published_at = f"{published}T00:00:00Z" if isinstance(published, str) and len(published) == 10 else None
    observation = SourceObservation(
        source_identity=source_identity,
        platform="openalex",
        upstream_id=work_id,
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=published_at,
        author_candidates=authors,
        title=str(work.get("display_name") or "") or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "upstream_version": work_id,
            "truncated": truncated,
            "openalex_url": canonicalize_url(openalex_url) if openalex_url else None,
            "doi": doi or None,
            "arxiv_id": arxiv_id,
            "language": work.get("language"),
        },
        collection_method="openalex_api",
        collector="openalex_works",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def reconstruct_abstract(inverted: object) -> str:
    if not inverted:
        return ""
    if not isinstance(inverted, dict):
        raise CollectorFailure("invalid_content", "abstract index is not an object")
    positions: list[tuple[int, str]] = []
    for token, indexes in inverted.items():
        if not isinstance(token, str) or not isinstance(indexes, list):
            raise CollectorFailure("invalid_content", "abstract index has an invalid token")
        if len(token) > 200:
            raise CollectorFailure("invalid_content", "abstract token exceeds limit")
        for index in indexes:
            if not isinstance(index, int) or index < 0 or index > MAX_ABSTRACT_POSITIONS:
                raise CollectorFailure("content_too_large", "abstract index position exceeds limit")
            positions.append((index, token))
    if len(positions) > MAX_ABSTRACT_POSITIONS:
        raise CollectorFailure("content_too_large", "abstract index exceeds token limit")
    positions.sort()
    return " ".join(token for _, token in positions)
