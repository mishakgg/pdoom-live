"""DBLP bibliographic metadata from the public publication search API.

The confirmed response is one hit from
https://dblp.org/search/publ/api for ``title:catastrophic title:risk``.
Its title is "Actionable Guidance for High-Consequence AI Risk Management:
Towards Standards Addressing AI Catastrophic Risks." The DBLP key is
``journals/corr/abs-2206-08966``.

Stored fields are the title, author names kept as separate people, year,
venue, the DBLP record URL, and the DBLP key. A missing year or venue stays
``unknown``. Missing authors stay an empty list. An empty payload produces
no publication. This module does not download PDFs or full text and does
not invent a record.

``runner_wired`` is false. Belief collection still uses RssCollector only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "dblp-metadata-0.1.0"
API_ORIGIN = "https://dblp.org"
SEARCH_PATH = "/search/publ/api"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_HITS = 5
MAX_QUERY_CHARS = 300
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_KEY_CHARS = 240
_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./:-]{0,239}$")


@dataclass(frozen=True)
class DblpPublication:
    title: str
    authors: tuple[str, ...]
    year: str
    venue: str
    canonical_url: str
    dblp_key: str

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "venue": self.venue,
            "canonical_url": self.canonical_url,
            "dblp_key": self.dblp_key,
        }


class DblpCollector:
    """Read publication search metadata. Not wired into belief collection."""

    collector = "dblp"
    platform = "dblp"
    collector_version = COLLECTOR_VERSION
    runner_wired = False

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, query: str, *, hits: int = 1) -> list[DblpPublication]:
        url = search_url(query, hits=hits)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if not _is_search_url(hop):
                raise CollectorFailure("blocked_by_policy", "dblp collector only reads publication search metadata")
        content_type = result.headers.get("content-type", "")
        if "pdf" in content_type.lower() or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return parse_publications(result.body)


def search_url(query: str, *, hits: int = 1) -> str:
    cleaned = " ".join((query or "").split())
    if not cleaned or len(cleaned) > MAX_QUERY_CHARS or any(ord(char) < 32 for char in cleaned):
        raise CollectorFailure("invalid_content", "dblp query must be 1 to 300 characters")
    if "://" in cleaned or ".pdf" in cleaned.lower() or "/pdf" in cleaned.lower():
        raise CollectorFailure("blocked_by_policy", "dblp query must not be a url or pdf path")
    if hits < 1 or hits > MAX_HITS:
        raise CollectorFailure("invalid_content", "hits must be between 1 and 5")
    encoded = urlencode({"q": cleaned, "format": "json", "h": str(hits), "c": "0"})
    url = f"{API_ORIGIN}{SEARCH_PATH}?{encoded}"
    if not _is_search_url(url):
        raise CollectorFailure("unsafe_url", "dblp retrieval stays on the publication search api")
    return url


def parse_publications(payload: bytes) -> list[DblpPublication]:
    """Return bibliographic records. An empty payload returns no publications."""
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "dblp payload exceeds limit")
    if not payload.strip():
        return []
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed dblp payload: {exc}") from exc
    if data is None or data == {}:
        return []
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "dblp payload was not an object")
    result = data.get("result")
    if not isinstance(result, dict) or not result:
        return []
    hits = result.get("hits")
    if not isinstance(hits, dict):
        return []
    raw_hits = hits.get("hit")
    if raw_hits is None:
        return []
    if isinstance(raw_hits, dict):
        raw_hits = [raw_hits]
    if not isinstance(raw_hits, list):
        raise CollectorFailure("invalid_content", "dblp hits were not a list")
    if len(raw_hits) > MAX_HITS:
        raise CollectorFailure("content_too_large", "dblp response has more hits than the bounded page")
    publications: list[DblpPublication] = []
    for hit in raw_hits:
        if not isinstance(hit, dict):
            continue
        info = hit.get("info")
        if not isinstance(info, dict):
            continue
        publication = _publication(info)
        if publication is not None:
            publications.append(publication)
    return publications


def _is_search_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "dblp.org" or parsed.path != SEARCH_PATH:
        return False
    lowered = (parsed.path + "?" + parsed.query).lower()
    return ".pdf" not in lowered and "/pdf" not in lowered


def _publication(info: dict) -> DblpPublication | None:
    key = _key(info.get("key"))
    if not key:
        return None
    canonical = _canonical_url(info.get("url"), key)
    if not canonical:
        return None
    return DblpPublication(
        title=_title(info.get("title")),
        authors=_authors(info.get("authors")),
        year=_year(info.get("year")),
        venue=_text_field(info.get("venue")),
        canonical_url=canonical,
        dblp_key=key,
    )


def _key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text or len(text) > MAX_KEY_CHARS or not _KEY.fullmatch(text):
        return ""
    if ".." in text or "//" in text or text.lower().endswith(".pdf"):
        return ""
    return text


def _canonical_url(value: object, key: str) -> str:
    fallback = f"https://dblp.org/rec/{key}"
    candidate = value.strip() if isinstance(value, str) else ""
    for raw in (candidate, fallback):
        if not raw or _looks_like_pdf(raw):
            continue
        try:
            canonical = canonicalize_url(raw)
        except ValueError:
            continue
        parsed = urlparse(canonical)
        if parsed.scheme != "https" or parsed.hostname != "dblp.org":
            continue
        if not parsed.path.startswith("/rec/") or _looks_like_pdf(canonical):
            continue
        return canonical
    return ""


def _looks_like_pdf(value: str) -> bool:
    lowered = value.lower()
    return lowered.endswith(".pdf") or "/pdf/" in lowered or lowered.startswith("%pdf")


def _title(value: object) -> str:
    if not isinstance(value, str):
        return ""
    if len(value) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "dblp title exceeds limit")
    return _plain_text(value)


def _text_field(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = " ".join(value.split())
    if not text:
        return UNKNOWN
    if len(text) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "dblp field exceeds limit")
    return text


def _year(value: object) -> str:
    if isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, int) and 1000 <= value <= 9999:
        return f"{value:04d}"
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 4 and text.isdigit() and 1000 <= int(text) <= 9999:
            return text
    return UNKNOWN


def _authors(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise CollectorFailure("invalid_content", "dblp authors were not an object")
    raw = value.get("author")
    if raw is None:
        return ()
    if isinstance(raw, dict) or isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raise CollectorFailure("invalid_content", "dblp author list was not a list")
    if len(raw) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "dblp author list exceeds limit")
    names: list[str] = []
    for item in raw:
        name = _author_name(item)
        if not name:
            continue
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "dblp author name exceeds limit")
        names.append(name)
    return tuple(names)


def _author_name(item: object) -> str:
    if isinstance(item, str):
        return " ".join(item.split())
    if not isinstance(item, dict):
        return ""
    text = item.get("text")
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    extractor = _TextExtractor()
    try:
        extractor.feed(value)
        extractor.close()
    except Exception:
        return " ".join(value.split())
    return " ".join("".join(extractor.parts).split())
