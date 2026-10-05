"""Europe PMC article metadata.

Confirms one public search for a catastrophic-AI-risk query. The request is
a single JSON page from the Europe PMC search API. Abstracts, full-text
links, and the next-page URL in that payload are not stored or followed.
PDFs and full text are not downloaded.

A missing license, copyright flag, publication date, or year stays unknown.
This module is not imported by belief collection or any job. RssCollector
remains the only belief collector.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "europepmc-metadata-0.1.0"
API_ORIGIN = "https://www.ebi.ac.uk"
SEARCH_PATH = "/europepmc/webservices/rest/search"
CONFIRMED_QUERY = '"catastrophic risk" AND "artificial intelligence"'
PAGE_SIZE = 1
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_RIGHTS_CHARS = 300
UNKNOWN = "unknown"

_SOURCE = re.compile(r"^[A-Z]{2,6}$")
_RECORD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,80}$")
_DOI = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


@dataclass(frozen=True)
class EuropePmcArticle:
    title: str
    year: int | str
    publication_date: str
    authors: tuple[str, ...]
    canonical_url: str
    license: str
    source: str
    record_id: str

    def as_record(self) -> dict[str, object]:
        return {
            "title": self.title,
            "year": self.year,
            "publication_date": self.publication_date,
            "authors": list(self.authors),
            "canonical_url": self.canonical_url,
            "license": self.license,
            "source": self.source,
            "id": self.record_id,
        }


class EuropePmcCollector:
    """Retrieve the one confirmed search page. The default fetcher makes one attempt."""

    collector = "europepmc"
    platform = "europepmc"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self) -> tuple[EuropePmcArticle, ...]:
        url = confirmed_search_url()
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url] or result.url != url:
            raise CollectorFailure("blocked_by_policy", "europe pmc retrieval does not follow another url")
        if _looks_like_pdf(result.url) or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return parse_search(result.body)


def confirmed_search_url() -> str:
    """URL for the single confirmed search. It does not address a PDF or full text."""
    query = urlencode(
        (
            ("query", CONFIRMED_QUERY),
            ("resultType", "core"),
            ("pageSize", str(PAGE_SIZE)),
            ("format", "json"),
            ("cursorMark", "*"),
            ("synonym", "false"),
        )
    )
    url = f"{API_ORIGIN}{SEARCH_PATH}?{query}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.ebi.ac.uk" or parsed.path != SEARCH_PATH:
        raise CollectorFailure("unsafe_url", "europe pmc retrieval stays on the search api")
    if parsed.fragment or _looks_like_pdf(url) or "fulltext" in (parsed.path + parsed.query).lower():
        raise CollectorFailure("blocked_by_policy", "pdf and full text are not requested")
    return url


def parse_search(payload: bytes) -> tuple[EuropePmcArticle, ...]:
    """Read title, year, publication date, authors, canonical URL, and license.

    Year and publication date are read from ``pubYear`` and ``firstPublicationDate``
    only. License is read from ``license``, or from ``copyright`` when license is
    absent. Any of those that are missing or blank stay ``unknown``.
    """
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "europe pmc payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed europe pmc payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "europe pmc payload is not an object")
    result_list = data.get("resultList")
    if not isinstance(result_list, dict):
        raise CollectorFailure("invalid_content", "europe pmc response missing resultList")
    results = result_list.get("result", [])
    if isinstance(results, dict):
        results = [results]
    if not isinstance(results, list):
        raise CollectorFailure("invalid_content", "europe pmc result list is not a list")
    if len(results) > PAGE_SIZE:
        raise CollectorFailure("content_too_large", "europe pmc page exceeds the bounded page size")
    articles: list[EuropePmcArticle] = []
    for item in results:
        if not isinstance(item, dict):
            raise CollectorFailure("invalid_content", "europe pmc result was not an object")
        articles.append(_article(item))
    return tuple(articles)


def _article(item: dict) -> EuropePmcArticle:
    source = _source(item.get("source"))
    record_id = _record_id(item.get("id"))
    return EuropePmcArticle(
        title=_title(item.get("title")),
        year=_year(item.get("pubYear")),
        publication_date=_publication_date(item.get("firstPublicationDate")),
        authors=_authors(item),
        canonical_url=_canonical_url(source, record_id, item.get("doi")),
        license=_license(item),
        source=source,
        record_id=record_id,
    )


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "europe pmc title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "europe pmc title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "europe pmc title exceeds limit")
    return title


def _year(value: object) -> int | str:
    if isinstance(value, bool) or value is None:
        return UNKNOWN
    if isinstance(value, int):
        year = value
    elif isinstance(value, str) and value.strip().isdigit():
        year = int(value.strip())
    else:
        return UNKNOWN
    if 1000 <= year <= 9999:
        return year
    return UNKNOWN


def _publication_date(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    return _calendar_date(value.strip()) or UNKNOWN


def _calendar_date(value: str) -> str | None:
    parts = value.split("-")
    if len(parts) not in {1, 2, 3} or not all(part.isdigit() for part in parts):
        return None
    year = int(parts[0])
    if year < 1000 or year > 9999:
        return None
    if len(parts) == 1:
        return f"{year:04d}"
    month = int(parts[1])
    if month < 1 or month > 12:
        return None
    if len(parts) == 2:
        return f"{year:04d}-{month:02d}"
    day = int(parts[2])
    try:
        datetime(year, month, day)
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _authors(item: dict) -> tuple[str, ...]:
    if "authorList" in item and item.get("authorList") is not None:
        names = _author_list(item.get("authorList"))
        if names:
            return names
    raw = item.get("authorString")
    if raw is None:
        return ()
    if not isinstance(raw, str):
        raise CollectorFailure("invalid_content", "europe pmc author string is not text")
    return _author_string(raw)


def _author_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, dict):
        raise CollectorFailure("invalid_content", "europe pmc author list is not an object")
    authors = value.get("author", [])
    if authors is None:
        return ()
    if isinstance(authors, dict):
        authors = [authors]
    if not isinstance(authors, list):
        raise CollectorFailure("invalid_content", "europe pmc authors are not a list")
    if len(authors) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "europe pmc author list exceeds limit")
    names: list[str] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        full_name = author.get("fullName")
        if not isinstance(full_name, str):
            continue
        name = " ".join(full_name.split())
        if not name:
            continue
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "europe pmc author name exceeds limit")
        names.append(name)
    return tuple(names)


def _author_string(value: str) -> tuple[str, ...]:
    text = " ".join(value.split())
    if text.endswith("."):
        text = text[:-1].rstrip()
    names = [" ".join(part.split()) for part in text.split(",")]
    cleaned = tuple(name for name in names if name)
    if len(cleaned) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "europe pmc author list exceeds limit")
    for name in cleaned:
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "europe pmc author name exceeds limit")
    return cleaned


def _license(item: dict) -> str:
    for key in ("license", "copyright"):
        if key not in item:
            continue
        value = item.get(key)
        if not isinstance(value, str):
            continue
        text = " ".join(value.split())
        if not text:
            continue
        if len(text) > MAX_RIGHTS_CHARS:
            raise CollectorFailure("content_too_large", "europe pmc license exceeds limit")
        return text
    return UNKNOWN


def _source(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    source = value.strip().upper()
    if _SOURCE.fullmatch(source):
        return source
    return UNKNOWN


def _record_id(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    record_id = value.strip()
    if _RECORD_ID.fullmatch(record_id) and not _looks_like_pdf(record_id):
        return record_id
    return UNKNOWN


def _canonical_url(source: str, record_id: str, doi: object) -> str:
    if source != UNKNOWN and record_id != UNKNOWN:
        article = f"https://europepmc.org/article/{quote(source, safe='')}/{quote(record_id, safe='')}"
        if not _looks_like_pdf(article):
            return canonicalize_url(article)
    if isinstance(doi, str):
        text = doi.strip()
        lowered = text.lower()
        for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
            if lowered.startswith(prefix):
                text = text[len(prefix) :]
                break
        if _DOI.fullmatch(text) and not _looks_like_pdf(text):
            return canonicalize_url(f"https://doi.org/{quote(text, safe='/')}")
    return UNKNOWN


def _looks_like_pdf(value: str) -> bool:
    lowered = value.lower()
    return ".pdf" in lowered or "/pdf/" in lowered or "pdf=render" in lowered
