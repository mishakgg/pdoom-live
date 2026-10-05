"""DOAJ article metadata.

Confirms one public search on the DOAJ article API. The query asks for a
title about AI safety, AI risk, or catastrophic risk, and the page size is
one. The captured hit is "AI Safety Is a Narrative Problem" (DOAJ
02a21dd062014f8d84e2a82498658eb0, DOI 10.1162/99608f92.562ff0f5). That title
is about AI safety.

The search record includes the title, one author name, the year, an eISSN,
and the DOI. It does not include a license or an abstract. The full-text
link from that response is not stored. A missing license or year stays
unknown. Author names stay separate list entries.

This module does not download PDFs or full text. It is not imported by
belief collection or any job.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "doaj-metadata-0.1.0"
API_ORIGIN = "https://doaj.org"
SEARCH_PATH = "/api/v3/search/articles"
CONFIRMED_QUERY = 'title:"AI safety" OR title:"AI risk" OR title:"catastrophic risk"'
PAGE_SIZE = 1
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_RIGHTS_CHARS = 300
UNKNOWN = "unknown"

_DOI = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
_ARTICLE_ID = re.compile(r"^[0-9a-fA-F]{32}$")
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


@dataclass(frozen=True)
class DoajArticle:
    title: str
    authors: tuple[str, ...]
    year: int | str
    doi: str
    canonical_url: str
    license: str
    article_id: str

    def as_record(self) -> dict[str, object]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "doi": self.doi,
            "canonical_url": self.canonical_url,
            "license": self.license,
            "article_id": self.article_id,
        }


class DoajCollector:
    """Retrieve the one confirmed search page. The default fetcher makes one attempt."""

    collector = "doaj"
    platform = "doaj"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self) -> tuple[DoajArticle, ...]:
        url = confirmed_search_url()
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url] or result.url != url:
            raise CollectorFailure("blocked_by_policy", "doaj retrieval does not follow another url")
        if _looks_like_pdf(result.url) or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return parse_search(result.body)


def confirmed_search_url() -> str:
    """URL for the single confirmed search. It does not address a PDF or full text."""
    encoded = quote(CONFIRMED_QUERY, safe="")
    query = urlencode((("page", "1"), ("pageSize", str(PAGE_SIZE))))
    url = f"{API_ORIGIN}{SEARCH_PATH}/{encoded}?{query}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "doaj.org" or not parsed.path.startswith(f"{SEARCH_PATH}/"):
        raise CollectorFailure("unsafe_url", "doaj retrieval stays on the article search api")
    if parsed.fragment or _looks_like_pdf(url) or "fulltext" in url.lower() or "abstract" in url.lower():
        raise CollectorFailure("blocked_by_policy", "pdf and full text are not requested")
    return url


def parse_search(payload: bytes) -> tuple[DoajArticle, ...]:
    """Read title, separate author names, year, DOI or article URL, and license.

    Year is read from ``bibjson.year`` only. License is read from
    ``bibjson.license`` or, when that is absent, ``bibjson.journal.license``.
    A missing or blank year or license stays ``unknown``. Full-text links are
    ignored, including PDF URLs.
    """
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "doaj payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed doaj payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "doaj payload is not an object")
    results = data.get("results")
    if not isinstance(results, list):
        raise CollectorFailure("invalid_content", "doaj response missing results")
    if len(results) > PAGE_SIZE:
        raise CollectorFailure("content_too_large", "doaj page exceeds the bounded page size")
    articles: list[DoajArticle] = []
    for item in results:
        if not isinstance(item, dict):
            raise CollectorFailure("invalid_content", "doaj result was not an object")
        articles.append(_article(item))
    return tuple(articles)


def _article(item: dict) -> DoajArticle:
    bibjson = item.get("bibjson")
    if not isinstance(bibjson, dict):
        raise CollectorFailure("invalid_content", "doaj result missing bibjson")
    doi = _doi(bibjson.get("identifier"))
    article_id = _article_id(item.get("id"))
    return DoajArticle(
        title=_title(bibjson.get("title")),
        authors=_authors(bibjson.get("author")),
        year=_year(bibjson.get("year")),
        doi=doi,
        canonical_url=_canonical_url(doi, article_id),
        license=_license(bibjson),
        article_id=article_id,
    )


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "doaj title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "doaj title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "doaj title exceeds limit")
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


def _authors(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "doaj authors are not a list")
    if len(value) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "doaj author list exceeds limit")
    names: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        raw = entry.get("name")
        if not isinstance(raw, str):
            continue
        name = " ".join(raw.split())
        if not name:
            continue
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "doaj author name exceeds limit")
        names.append(name)
    return tuple(names)


def _doi(value: object) -> str:
    if value is None:
        return UNKNOWN
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "doaj identifiers are not a list")
    for entry in value:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("type")
        if not isinstance(kind, str) or kind.strip().lower() != "doi":
            continue
        raw = entry.get("id")
        if not isinstance(raw, str):
            continue
        text = _strip_doi_prefix(raw.strip())
        if _DOI.fullmatch(text) and not _looks_like_pdf(text):
            return text
    return UNKNOWN


def _strip_doi_prefix(text: str) -> str:
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _article_id(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    article_id = value.strip()
    if _ARTICLE_ID.fullmatch(article_id):
        return article_id
    return UNKNOWN


def _canonical_url(doi: str, article_id: str) -> str:
    if doi != UNKNOWN:
        url = canonicalize_url(f"https://doi.org/{quote(doi, safe='/')}")
        if _looks_like_pdf(url) or urlparse(url).hostname != "doi.org":
            raise CollectorFailure("blocked_by_policy", "pdf is not a canonical url")
        return url
    if article_id == UNKNOWN:
        return UNKNOWN
    url = canonicalize_url(f"https://doaj.org/article/{quote(article_id, safe='')}")
    parsed = urlparse(url)
    if (
        _looks_like_pdf(url)
        or parsed.hostname != "doaj.org"
        or parsed.path != f"/article/{article_id}"
    ):
        return UNKNOWN
    return url


def _license(bibjson: dict) -> str:
    if "license" in bibjson:
        text = _license_value(bibjson.get("license"))
        if text:
            return text
    journal = bibjson.get("journal")
    if isinstance(journal, dict) and "license" in journal:
        text = _license_value(journal.get("license"))
        if text:
            return text
    return UNKNOWN


def _license_value(value: object) -> str | None:
    if isinstance(value, str):
        return _rights_text(value)
    if isinstance(value, dict):
        return _license_entry(value)
    if isinstance(value, list):
        for entry in value:
            text = _license_value(entry)
            if text:
                return text
    return None


def _license_entry(entry: dict) -> str | None:
    for key in ("type", "url", "title"):
        raw = entry.get(key)
        if not isinstance(raw, str):
            continue
        text = _rights_text(raw)
        if text is None:
            continue
        if key == "url" and not text.startswith(("https://", "http://")):
            continue
        return text
    return None


def _rights_text(value: str) -> str | None:
    text = " ".join(value.split())
    if not text or _looks_like_pdf(text):
        return None
    if len(text) > MAX_RIGHTS_CHARS:
        raise CollectorFailure("content_too_large", "doaj license exceeds limit")
    return text


def _looks_like_pdf(value: str) -> bool:
    lowered = value.lower()
    return lowered.endswith(".pdf") or "/pdf/" in lowered or ".pdf?" in lowered or lowered.startswith("%pdf")
