"""Figshare public article metadata.

Reads one article from the public REST API at
https://api.figshare.com/v2/articles/{article_id}. The body is JSON metadata.
File download URLs are not requested, and file bytes are not stored.

A description is kept only when it is at most 400 characters. A longer
description is omitted rather than truncated. Each author stays a separate
name taken from that author's own ``full_name`` when present. Names are not
merged, deduped, or reordered to match a citation. A missing license or
publication date stays ``unknown``.

This module is not wired into belief collection.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url, hostname_is_blocked

COLLECTOR_VERSION = "figshare-metadata-0.1.0"
API_ORIGIN = "https://api.figshare.com"
ARTICLES_PATH = "/v2/articles"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_DESCRIPTION_CHARS = 400
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_LICENSE_CHARS = 120

_ARTICLE_ID = re.compile(r"^[1-9][0-9]{0,11}$")
_DOI = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
_PUBLISHED = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"(?:T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:\.\d{1,6})?(?P<tz>Z|[+-]\d{2}:\d{2}))?$"
)
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)
_FILE_HOSTS = frozenset({"ndownloader.figshare.com", "api.figshare.com"})
_EMBEDDED_FILE_KEYS = ("content", "bytes", "data", "body")


@dataclass(frozen=True)
class FigshareArticle:
    """Metadata fields taken from one public Figshare article."""

    article_id: str
    title: str
    authors: tuple[str, ...]
    published_date: str
    license: str
    canonical_url: str
    doi: str | None = None
    description: str | None = None

    def as_dict(self) -> dict[str, object]:
        record: dict[str, object] = {
            "id": self.article_id,
            "title": self.title,
            "authors": list(self.authors),
            "published_date": self.published_date,
            "license": self.license,
            "canonical_url": self.canonical_url,
        }
        if self.doi is not None:
            record["doi"] = self.doi
        if self.description is not None:
            record["description"] = self.description
        return record


class FigshareCollector:
    """Retrieve one public article. The default fetcher makes a single attempt."""

    collector = "figshare"
    platform = "figshare"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, article_id: str) -> FigshareArticle:
        """Fetch one article's JSON metadata. Does not follow file links."""
        requested_id = _require_request_id(article_id)
        url = article_request_url(requested_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if not _is_metadata_url(hop):
                raise CollectorFailure("blocked_by_policy", "figshare file downloads are not requested")
        if _looks_like_file_bytes(result.body):
            raise CollectorFailure("blocked_by_policy", "figshare file bytes are not metadata")
        article = self.parse(result.body)
        if article.article_id != requested_id:
            raise CollectorFailure("invalid_content", "figshare article id mismatch")
        return article

    def parse(self, payload: bytes) -> FigshareArticle:
        """Parse one articles API body. Performs no I/O."""
        return parse_figshare_article(payload)


def article_request_url(article_id: str) -> str:
    """JSON URL for one article. The path is ``/v2/articles/{id}``, never a file."""
    cleaned = _require_request_id(article_id)
    url = f"{API_ORIGIN}{ARTICLES_PATH}/{cleaned}"
    if not _is_metadata_url(url):
        raise CollectorFailure("blocked_by_policy", "figshare file downloads are not requested")
    return url


def parse_figshare_article(payload: bytes) -> FigshareArticle:
    """Return one article, or fail when the payload is empty or not one article.

    An empty object and a list of several articles do not become one record.
    Author lists from those articles are not combined.
    """
    if _looks_like_file_bytes(payload):
        raise CollectorFailure("blocked_by_policy", "figshare file bytes are not metadata")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "figshare payload exceeds limit")
    if not payload.strip():
        raise CollectorFailure("invalid_content", "empty figshare payload")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed figshare payload: {exc}") from exc
    if _contains_file_bytes(data):
        raise CollectorFailure("blocked_by_policy", "figshare file bytes are not metadata")
    article = _extract_article(data)
    if article is None:
        raise CollectorFailure("invalid_content", "empty figshare payload")
    return article


def _extract_article(data: object) -> FigshareArticle | None:
    if data is None or data == {}:
        return None
    if isinstance(data, list):
        if not data:
            return None
        if len(data) != 1 or not isinstance(data[0], dict):
            raise CollectorFailure("invalid_content", "expected one figshare article")
        return _from_article(data[0])
    if not isinstance(data, dict):
        return None
    return _from_article(data)


def _from_article(data: dict) -> FigshareArticle | None:
    if not data:
        return None
    _reject_non_public(data)
    article_id = _article_id(data.get("id"))
    title = _clean_title(data.get("title"))
    if article_id is None or title is None:
        return None
    doi = _doi(data)
    return FigshareArticle(
        article_id=article_id,
        title=title,
        authors=_authors(data.get("authors")),
        published_date=_published_date(data),
        license=_license(data),
        canonical_url=_canonical_url(data, article_id, doi),
        doi=doi,
        description=_description(data.get("description")),
    )


def _reject_non_public(data: dict) -> None:
    if data.get("is_public") is False or data.get("is_confidential") is True:
        raise CollectorFailure("blocked_by_policy", "figshare article is not public")
    status = data.get("status")
    if isinstance(status, str) and status.strip() and status.strip().lower() != "public":
        raise CollectorFailure("blocked_by_policy", "figshare article is not public")


def _require_request_id(article_id: str) -> str:
    text = (article_id or "").strip()
    if _ARTICLE_ID.fullmatch(text) is None:
        raise CollectorFailure("invalid_content", "figshare article id must be digits")
    return text


def _article_id(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if _ARTICLE_ID.fullmatch(text) is None:
        return None
    return text


def _clean_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    title = " ".join(value.split())
    if not title:
        return None
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "figshare title exceeds limit")
    return title


def _authors(value: object) -> tuple[str, ...]:
    """One name per author entry. Entries are not joined, split, or deduped."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "figshare authors are not a list")
    if len(value) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "figshare author list exceeds limit")
    names: list[str] = []
    for entry in value:
        name = _author_name(entry)
        if name:
            names.append(name)
    return tuple(names)


def _author_name(entry: object) -> str:
    if isinstance(entry, str):
        raw = entry
    elif isinstance(entry, dict):
        full_name = entry.get("full_name")
        if isinstance(full_name, str) and full_name.strip():
            raw = full_name
        else:
            first = entry.get("first_name") if isinstance(entry.get("first_name"), str) else ""
            last = entry.get("last_name") if isinstance(entry.get("last_name"), str) else ""
            raw = f"{first} {last}"
    else:
        return ""
    name = " ".join(str(raw).split())
    if not name:
        return ""
    if len(name) > MAX_AUTHOR_NAME_CHARS:
        raise CollectorFailure("content_too_large", "figshare author name exceeds limit")
    return name


def _published_date(data: dict) -> str:
    """Publication timestamp only. Created, modified, and timeline dates are not used."""
    value = data.get("published_date")
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    match = _PUBLISHED.fullmatch(text)
    if match is None:
        return UNKNOWN
    year = int(match.group("year"))
    month = int(match.group("month"))
    day = int(match.group("day"))
    if year < 1000 or year > 9999 or not 1 <= month <= 12 or not 1 <= day <= 31:
        return UNKNOWN
    if match.group("hour") is not None:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        second = int(match.group("second"))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59 or not 0 <= second <= 60:
            return UNKNOWN
    return text


def _license(data: dict) -> str:
    """License name when the article states one. Missing and URLs stay unknown."""
    if "license" not in data:
        return UNKNOWN
    return _license_name(data.get("license"))


def _license_name(value: object) -> str:
    if isinstance(value, list):
        if len(value) != 1:
            return UNKNOWN
        value = value[0]
    if isinstance(value, str):
        text: object = value
    elif isinstance(value, dict):
        text = value.get("name")
    else:
        return UNKNOWN
    if not isinstance(text, str):
        return UNKNOWN
    name = " ".join(text.split())
    if not name or len(name) > MAX_LICENSE_CHARS:
        return UNKNOWN
    if any(ord(char) < 32 for char in name):
        return UNKNOWN
    if name.lower().startswith(("http://", "https://", "doi:")):
        return UNKNOWN
    return name


def _doi(data: dict) -> str | None:
    """The article DOI. A related ``resource_doi`` is not substituted."""
    return _parse_doi(data.get("doi"))


def _parse_doi(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    if _DOI.fullmatch(text):
        return text
    return None


def _description(value: object) -> str | None:
    """Keep a short description. Longer text is omitted, not truncated."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > MAX_DESCRIPTION_CHARS:
        return None
    return text


def _canonical_url(data: dict, article_id: str, doi: str | None) -> str:
    for key in ("url_public_html", "figshare_url"):
        candidate = data.get(key)
        if isinstance(candidate, str) and _is_public_article_page(candidate, article_id):
            try:
                return canonicalize_url(candidate.strip())
            except ValueError:
                continue
    if doi:
        try:
            return canonicalize_url(f"https://doi.org/{doi}")
        except ValueError:
            pass
    return canonicalize_url(f"https://figshare.com/articles/{article_id}")


def _is_public_article_page(url: str, article_id: str) -> bool:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or not host or host in _FILE_HOSTS or hostname_is_blocked(host):
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    if _looks_like_file_path(parsed.path):
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if article_id not in parts or "account" in parts:
        return False
    return True


def _is_metadata_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host != "api.figshare.com":
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 3 or parts[0] != "v2" or parts[1] != "articles":
        return False
    if _ARTICLE_ID.fullmatch(parts[2]) is None:
        return False
    if _looks_like_file_path(parsed.path):
        return False
    return True


def _looks_like_file_path(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered for token in ("/files", "/download", ".pdf", ".zip", ".png", ".jpg", "ndownloader"))


def _looks_like_file_bytes(payload: bytes) -> bool:
    head = payload.lstrip().removeprefix(b"\xef\xbb\xbf")
    return head.startswith((b"%PDF", b"PK\x03\x04", b"\x89PNG", b"\xff\xd8\xff"))


def _contains_file_bytes(data: object) -> bool:
    articles = data if isinstance(data, list) else [data]
    for article in articles:
        if not isinstance(article, dict):
            continue
        files = article.get("files")
        if not isinstance(files, list):
            continue
        for entry in files:
            if not isinstance(entry, dict):
                continue
            for key in _EMBEDDED_FILE_KEYS:
                value = entry.get(key)
                if isinstance(value, (bytes, bytearray)) and value:
                    return True
                if isinstance(value, str) and value.strip():
                    return True
    return False
