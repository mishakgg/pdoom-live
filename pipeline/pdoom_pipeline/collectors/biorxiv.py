"""bioRxiv preprint metadata.

Retrieves one preprint from the public details API at api.biorxiv.org.
The call is JSON metadata only. Abstracts, JATS XML, and PDFs are not
requested and are not copied into the record. This module is not wired
into belief collection.

A license is copied only when the details object itself includes one.
A missing license stays ``unknown`` and is not recorded as CC-BY.
Author names are split on semicolons and are not merged.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "biorxiv-metadata-0.1.0"
API_ORIGIN = "https://api.biorxiv.org"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_LICENSE_CHARS = 80

_DOI = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
_CONTENT_DOI = re.compile(r"^/content/(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?)(?:v\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class BiorxivPreprint:
    """Metadata for one bioRxiv preprint version."""

    title: str
    authors: tuple[str, ...]
    date: str
    doi: str
    version: str
    canonical_url: str
    license: str

    def as_record(self) -> dict[str, object]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "date": self.date,
            "doi": self.doi,
            "version": self.version,
            "canonical_url": self.canonical_url,
            "license": self.license,
        }


class BiorxivCollector:
    """Fetch and parse one bioRxiv details record. Not wired into the belief runner."""

    collector = "biorxiv"
    platform = "biorxiv"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, doi: str) -> BiorxivPreprint:
        """Fetch one details document. Does not follow redirects or PDF links."""
        url = details_url(doi)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url]:
            raise CollectorFailure("blocked_by_policy", "refusing a redirected biorxiv fetch")
        if _looks_like_pdf(result.url) or result.body.startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "biorxiv pdf is not downloaded")
        paper = self.parse(result.body)
        if paper.doi.lower() != _request_doi(doi).lower():
            raise CollectorFailure("invalid_content", "biorxiv doi mismatch")
        return paper

    def parse(self, payload: bytes) -> BiorxivPreprint:
        """Parse a details JSON body. Performs no I/O."""
        return parse_preprint(payload)


def details_url(doi: str) -> str:
    """JSON details URL for one bioRxiv DOI. The URL is never a PDF or JATS file."""
    bare = _request_doi(doi)
    encoded = quote(bare, safe="/")
    url = f"{API_ORIGIN}/details/biorxiv/{encoded}/na/json"
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.biorxiv.org"
        or parsed.query
        or parsed.fragment
    ):
        raise CollectorFailure("unsafe_url", "biorxiv retrieval stays on the details api")
    if len(parts) != 6 or parts[0] != "details" or parts[1] != "biorxiv":
        raise CollectorFailure("blocked_by_policy", "biorxiv retrieval is metadata json only")
    if parts[4] != "na" or parts[5] != "json":
        raise CollectorFailure("blocked_by_policy", "biorxiv retrieval is metadata json only")
    if _looks_like_pdf(parsed.path) or "jats" in parsed.path.lower():
        raise CollectorFailure("blocked_by_policy", "biorxiv pdf is not downloaded")
    return url


def parse_preprint(payload: bytes) -> BiorxivPreprint:
    """Return one preprint from a details payload.

    When the payload lists several versions of the same DOI, the highest
    version is kept. Author lists from other versions are not combined.
    """
    if payload.startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "biorxiv pdf is not downloaded")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "biorxiv payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed biorxiv payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "biorxiv payload was not an object")
    item = _one_preprint(data)
    doi = _response_doi(item.get("doi"))
    version = _version(item.get("version"))
    return BiorxivPreprint(
        title=_title(item.get("title")),
        authors=_authors(item.get("authors")),
        date=_posted_date(item.get("date")),
        doi=doi,
        version=version,
        canonical_url=_canonical_url(doi, version),
        license=_license(item),
    )


def _one_preprint(data: dict) -> dict:
    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        status = first.get("status") if isinstance(first, dict) else None
        if status != "ok":
            raise CollectorFailure("invalid_content", "biorxiv details status was not ok")
    collection = data.get("collection")
    if not isinstance(collection, list) or not collection:
        raise CollectorFailure("invalid_content", "biorxiv details collection is empty")
    items = [item for item in collection if isinstance(item, dict)]
    if len(items) != len(collection):
        raise CollectorFailure("invalid_content", "biorxiv collection item was not an object")
    for item in items:
        _require_biorxiv_server(item.get("server"))
    dois = {_response_doi(item.get("doi")).lower() for item in items}
    if len(dois) != 1:
        raise CollectorFailure("invalid_content", "expected one biorxiv preprint")
    if len(items) == 1:
        return items[0]
    ranked: list[tuple[int, dict]] = []
    for item in items:
        number = _version_number(item.get("version"))
        if number is None:
            raise CollectorFailure("invalid_content", "biorxiv version is not comparable")
        ranked.append((number, item))
    highest = max(number for number, _item in ranked)
    chosen = [item for number, item in ranked if number == highest]
    if len(chosen) != 1:
        raise CollectorFailure("invalid_content", "biorxiv versions were not distinct")
    return chosen[0]


def _require_biorxiv_server(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, str) or value.strip().lower() != "biorxiv":
        raise CollectorFailure("invalid_content", "details record is not from biorxiv")


def _request_doi(value: str) -> str:
    text = (value or "").strip()
    if not text or _looks_like_pdf(text):
        raise CollectorFailure("blocked_by_policy", "biorxiv pdf is not downloaded")
    lowered = text.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            lowered = text.lower()
            break
    if lowered.startswith(("http://", "https://")):
        parsed = urlparse(text)
        host = (parsed.hostname or "").lower()
        if host not in {"www.biorxiv.org", "biorxiv.org"} or not parsed.path.startswith("/content/"):
            raise CollectorFailure("invalid_content", "invalid biorxiv doi")
        if _looks_like_pdf(parsed.path):
            raise CollectorFailure("blocked_by_policy", "biorxiv pdf is not downloaded")
        match = _CONTENT_DOI.fullmatch(parsed.path.rstrip("/"))
        if not match:
            raise CollectorFailure("invalid_content", "invalid biorxiv doi")
        text = match.group(1)
    if not _DOI.fullmatch(text):
        raise CollectorFailure("invalid_content", "invalid biorxiv doi")
    return text


def _response_doi(value: object) -> str:
    text = str(value or "").strip()
    if not _DOI.fullmatch(text):
        raise CollectorFailure("invalid_content", "biorxiv preprint missing doi")
    return text


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "biorxiv preprint missing title")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "biorxiv preprint missing title")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "biorxiv title exceeds limit")
    return title


def _authors(value: object) -> tuple[str, ...]:
    """Split the details author string into names. Do not deduplicate or merge."""
    if value is None:
        return ()
    if isinstance(value, str):
        parts: list[object] = value.split(";")
    elif isinstance(value, list):
        parts = list(value)
    else:
        raise CollectorFailure("invalid_content", "biorxiv authors were not a list or string")
    if len(parts) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "biorxiv author list exceeds limit")
    names: list[str] = []
    for part in parts:
        if isinstance(part, dict):
            raw = part.get("name")
        else:
            raw = part
        if not isinstance(raw, str):
            continue
        name = " ".join(raw.split())
        if not name:
            continue
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "biorxiv author name exceeds limit")
        names.append(name)
    return tuple(names)


def _posted_date(value: object) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return UNKNOWN
    try:
        date.fromisoformat(value)
    except ValueError:
        return UNKNOWN
    return value


def _version(value: object) -> str:
    if isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, int) and value >= 1:
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit() and int(text) >= 1:
            return text
    return UNKNOWN


def _version_number(value: object) -> int | None:
    text = _version(value)
    if text == UNKNOWN:
        return None
    return int(text)


def _license(item: dict) -> str:
    """Copy a license string only when the details object includes one."""
    if "license" not in item:
        return UNKNOWN
    raw = item.get("license")
    if not isinstance(raw, str):
        return UNKNOWN
    text = " ".join(raw.split())
    if not text:
        return UNKNOWN
    if len(text) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "biorxiv license exceeds limit")
    return text


def _canonical_url(doi: str, version: str) -> str:
    if version == UNKNOWN:
        raw = f"https://www.biorxiv.org/content/{doi}"
    else:
        raw = f"https://www.biorxiv.org/content/{doi}v{version}"
    try:
        url = canonicalize_url(raw)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "biorxiv canonical url could not be built") from exc
    if _looks_like_pdf(url):
        raise CollectorFailure("blocked_by_policy", "biorxiv pdf is not downloaded")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"www.biorxiv.org", "biorxiv.org"} or not parsed.path.startswith("/content/"):
        raise CollectorFailure("invalid_content", "biorxiv canonical url is not a content page")
    return url


def _looks_like_pdf(value: str) -> bool:
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    return (
        lowered.endswith(".pdf")
        or lowered.endswith(".full.pdf")
        or "/pdf/" in lowered
        or ".full.pdf" in lowered
        or lowered.startswith("%pdf")
    )
