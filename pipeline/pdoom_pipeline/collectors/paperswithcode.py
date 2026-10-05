"""Papers with Code paper metadata.

Confirms one public keyword search, ``AI safety``, against the Papers with
Code API at ``https://paperswithcode.co/api/v1/papers/search``. The first hit
is paper 412, "Concrete Problems in AI Safety" (Dario Amodei, Chris Olah,
Jacob Steinhardt, Paul Christiano, John Schulman, and Dan Mané, published
2016-06-21). That paper is about AI safety.

The stored record keeps the paper id, canonical URL, title, publication date,
and each author name separately. A missing or unusable publication date stays
``unknown``. The abstract, PDF, thumbnail, and code archive are not stored or
requested. ``paperswithcode.com`` is not called: that host redirects away from
the API and does not return paper JSON.

This module is not imported by belief collection or the collector package.
``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "paperswithcode-metadata-0.1.0"
API_ORIGIN = "https://paperswithcode.co"
SEARCH_PATH = "/api/v1/papers/search"
CONFIRMED_QUERY = "AI safety"
PAGE = "1"
PAGE_SIZE = 1
SEARCH_MODE = "keyword"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
UNKNOWN = "unknown"

_PAPER_ID = re.compile(r"^[1-9][0-9]{0,11}$")
_ARXIV_ID = re.compile(r"^[0-9]{4}\.[0-9]{4,5}$")
_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


@dataclass(frozen=True)
class PapersWithCodePaper:
    """Bibliographic fields from one Papers with Code search hit."""

    paper_id: str
    url: str
    title: str
    publication_date: str
    authors: tuple[str, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "paper_id": self.paper_id,
            "url": self.url,
            "title": self.title,
            "publication_date": self.publication_date,
            "authors": list(self.authors),
        }


class PapersWithCodeCollector:
    """Retrieve the one confirmed search page. The default fetcher makes one attempt."""

    collector = "paperswithcode"
    platform = "paperswithcode"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self) -> tuple[PapersWithCodePaper, ...]:
        """Fetch the confirmed search page. Does not follow PDFs, datasets, or code."""
        url = confirmed_search_url()
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.status != 200 or result.requested_urls != [url] or result.url != url:
            raise CollectorFailure(
                "blocked_by_policy",
                "papers with code retrieval does not follow another url",
            )
        if _looks_like_download(result.url) or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf and code archives are not requested")
        return parse_search(result.body)


def confirmed_search_url() -> str:
    """URL for the single confirmed search. It does not address a PDF, dataset, or repository."""
    query = urlencode(
        (
            ("q", CONFIRMED_QUERY),
            ("page", PAGE),
            ("page_size", str(PAGE_SIZE)),
            ("mode", SEARCH_MODE),
        )
    )
    url = f"{API_ORIGIN}{SEARCH_PATH}?{query}"
    if not _is_metadata_search_url(url):
        raise CollectorFailure("blocked_by_policy", "papers with code retrieval stays on the search api")
    return url


def parse_search(payload: bytes) -> tuple[PapersWithCodePaper, ...]:
    """Read paper id, URL, title, publication date, and separate author names.

    Publication date is read from ``published`` only. A missing, blank, or
    unusable value stays ``unknown``. Abstract, PDF, thumbnail, and repository
    fields are ignored.
    """
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "papers with code payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed papers with code payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "papers with code payload is not an object")
    results = data.get("results")
    if not isinstance(results, list):
        raise CollectorFailure("invalid_content", "papers with code response missing results")
    if len(results) > PAGE_SIZE:
        raise CollectorFailure("content_too_large", "papers with code page exceeds the bounded page size")
    papers: list[PapersWithCodePaper] = []
    for item in results:
        if not isinstance(item, dict):
            raise CollectorFailure("invalid_content", "papers with code result was not an object")
        papers.append(_paper(item))
    return tuple(papers)


def _is_metadata_search_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "paperswithcode.co":
        return False
    if parsed.path != SEARCH_PATH or parsed.fragment or parsed.username or parsed.password:
        return False
    if _looks_like_download(parsed.path) or _looks_like_download(parsed.query):
        return False
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return (
        query.get("q") == CONFIRMED_QUERY
        and query.get("page") == PAGE
        and query.get("page_size") == str(PAGE_SIZE)
        and query.get("mode") == SEARCH_MODE
        and "include_resources" not in query
        and set(query) == {"q", "page", "page_size", "mode"}
    )


def _paper(item: dict) -> PapersWithCodePaper:
    paper_id = _paper_id(item.get("id"))
    return PapersWithCodePaper(
        paper_id=paper_id,
        url=_paper_url(item, paper_id),
        title=_title(item.get("title")),
        publication_date=_publication_date(item.get("published")),
        authors=_authors(item),
    )


def _paper_id(value: object) -> str:
    if isinstance(value, bool):
        raise CollectorFailure("invalid_content", "papers with code paper id is missing")
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "papers with code paper id is missing")
    paper_id = value.strip()
    if not _PAPER_ID.fullmatch(paper_id) or _looks_like_download(paper_id):
        raise CollectorFailure("invalid_content", "papers with code paper id is missing")
    return paper_id


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "papers with code title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "papers with code title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "papers with code title exceeds limit")
    return title


def _publication_date(value: object) -> str:
    if isinstance(value, bool) or value is None:
        return UNKNOWN
    if isinstance(value, int):
        if 1000 <= value <= 9999:
            return f"{value:04d}"
        return UNKNOWN
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if not text:
        return UNKNOWN
    if "T" in text:
        text = text.split("T", 1)[0]
    elif " " in text:
        text = text.split(" ", 1)[0]
    match = _DATE.fullmatch(text)
    if not match:
        return UNKNOWN
    year = int(match.group(1))
    if year < 1000 or year > 9999:
        return UNKNOWN
    month = match.group(2)
    day = match.group(3)
    if month is None:
        return f"{year:04d}"
    month_i = int(month)
    if month_i < 1 or month_i > 12:
        return UNKNOWN
    if day is None:
        return f"{year:04d}-{month_i:02d}"
    day_i = int(day)
    try:
        datetime(year, month_i, day_i)
    except ValueError:
        return UNKNOWN
    return f"{year:04d}-{month_i:02d}-{day_i:02d}"


def _authors(item: dict) -> tuple[str, ...]:
    """Keep each listed name. Do not dedupe, split, or join names into one person."""
    if "authors" in item and item.get("authors") is not None:
        return _name_list(item.get("authors"))
    if "author_links" in item and item.get("author_links") is not None:
        return _name_list(item.get("author_links"))
    return ()


def _name_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "papers with code authors are not a list")
    if len(value) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "papers with code author list exceeds limit")
    names: list[str] = []
    for entry in value:
        name = _author_name(entry)
        if name:
            names.append(name)
    return tuple(names)


def _author_name(entry: object) -> str | None:
    if isinstance(entry, str):
        text = entry
    elif isinstance(entry, dict):
        candidate = entry.get("name")
        if not isinstance(candidate, str):
            return None
        text = candidate
    else:
        return None
    name = " ".join(text.split())
    if not name:
        return None
    if len(name) > MAX_AUTHOR_NAME_CHARS:
        raise CollectorFailure("content_too_large", "papers with code author name exceeds limit")
    return name


def _paper_url(item: dict, paper_id: str) -> str:
    for key in ("url_abs", "source_url"):
        candidate = _http_paper_url(item.get(key))
        if candidate:
            return candidate
    arxiv_id = item.get("arxiv_id")
    if isinstance(arxiv_id, str) and _ARXIV_ID.fullmatch(arxiv_id.strip()):
        return f"https://arxiv.org/abs/{arxiv_id.strip()}"
    return f"https://paperswithcode.co/paper/{paper_id}"


def _http_paper_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or _looks_like_download(raw):
        return None
    try:
        canonical = canonicalize_url(raw)
    except ValueError:
        return None
    if _looks_like_download(canonical):
        return None
    return canonical


def _looks_like_download(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith("%pdf") or ".pdf" in lowered or "/pdf" in lowered:
        return True
    markers = (
        "github.com",
        "codeload",
        "/repositories",
        "/repository",
        "/datasets",
        "/dataset",
        "/files/",
        "include_resources",
    )
    return any(marker in lowered for marker in markers)
