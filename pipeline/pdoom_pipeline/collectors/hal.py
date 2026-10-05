"""HAL notice metadata.

Reads one public document notice at ``https://hal.science/{hal_id}``.
Bibliographic meta tags supply the title, publication date, authors, and
canonical URL. A Creative Commons link in the licence block is stored when
present. Visible licence text is stored only when that block has no
Creative Commons URL.

``api.archives-ouvertes.fr/robots.txt`` disallows ``/search/``.
``hal.science`` robots.txt disallows the JSON, BibTeX, and TEI exports
(``*/json``, ``*/bibtex``, ``*/tei``). This collector does not call those
paths. It does not download the PDF, including ``/document`` and ``/file/``
links that the notice itself displays.

A missing publication date or license stays ``unknown``. The online deposit
date is not substituted for a publication date. Page text is data, not
instructions. This module is not wired into belief collection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "hal-metadata-0.1.0"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 50
MAX_AUTHOR_CHARS = 300
MAX_LICENSE_CHARS = 300
MAX_METAS = 400
API_HOST = "hal.science"

_HAL_ID = re.compile(r"^hal-\d{6,12}(?:v\d{1,4})?$")
_NOTICE_PATH = re.compile(r"^/hal-\d{6,12}(?:v\d{1,4})?$")
_YMD = re.compile(r"^(\d{4})(?:[/-](\d{1,2})(?:[/-](\d{1,2}))?)?$")
_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
_DATE_FIELDS = ("citation_publication_date", "dc.issued", "dc.date")
_LICENSE_HOSTS = {"creativecommons.org", "www.creativecommons.org"}
_BLOCKED_MARKERS = (
    "/document",
    "/file/",
    "/preview/",
    "/json",
    "/bibtex",
    "/tei",
    "/rdf",
    "/dc",
    "/dcterms",
    "/endnote",
    "/datacite",
    "/openaire",
    "/search",
    "/oai",
    "/sword",
    ".pdf",
)


@dataclass(frozen=True)
class HalRecord:
    """Bibliographic fields taken from one HAL notice."""

    title: str
    date: str
    authors: tuple[str, ...]
    canonical_url: str
    license: str

    @property
    def hal_id(self) -> str:
        return self.canonical_url.rsplit("/", 1)[-1]

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "date": self.date,
            "authors": list(self.authors),
            "canonical_url": self.canonical_url,
            "license": self.license,
        }


class HalCollector:
    """Retrieve one public HAL notice. The default fetcher makes a single attempt."""

    collector = "hal"
    platform = "hal"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("text/html",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, hal_id: str) -> HalRecord:
        url = notice_url(hal_id)
        result = self.fetcher.get(url, headers={"Accept": "text/html"})
        hops = result.requested_urls or [result.url]
        if hops != [url]:
            raise CollectorFailure("blocked_by_policy", "hal collector reads one notice page")
        content_type = result.headers.get("content-type", "")
        if "pdf" in content_type.lower() or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return parse_notice(result.body)


class _NoticeParser(HTMLParser):
    """Collect bibliographic meta tags and the licence block. Does not execute script."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metas: list[tuple[str, str]] = []
        self.canonical_href: str | None = None
        self.license_hrefs: list[str] = []
        self.license_text: list[str] = []
        self._licence_stack: list[bool] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        parent = bool(self._licence_stack and self._licence_stack[-1])
        in_licence = parent or _licence_class(attr.get("class", ""))
        if tag not in _VOID_TAGS:
            self._licence_stack.append(in_licence)
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
            return
        if self._skip:
            return
        if len(self.metas) > MAX_METAS:
            raise CollectorFailure("content_too_large", "hal notice has too many meta tags")
        if tag == "meta":
            name = (attr.get("name") or attr.get("property") or "").strip().lower()
            if name:
                self.metas.append((name, attr.get("content", "")))
        elif tag == "link" and self.canonical_href is None and "canonical" in attr.get("rel", "").lower().split():
            self.canonical_href = attr.get("href", "")
        elif tag == "a" and in_licence:
            href = attr.get("href", "").strip()
            if href:
                self.license_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag not in _VOID_TAGS and self._licence_stack:
            self._licence_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        if self._licence_stack and self._licence_stack[-1]:
            self.license_text.append(data)


def notice_url(hal_id: str) -> str:
    """HTTPS URL of one notice page. PDF, export, and search paths are refused."""
    text = (hal_id or "").strip()
    if _request_blocked(text):
        raise CollectorFailure("blocked_by_policy", "hal collector reads one notice page")
    if not _HAL_ID.fullmatch(text):
        raise CollectorFailure("invalid_content", "hal id must look like hal-04963307 or hal-04963307v1")
    url = f"https://{API_HOST}/{text}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != f"/{text}":
        raise CollectorFailure("unsafe_url", "hal retrieval stays on one notice page")
    if parsed.query or parsed.fragment:
        raise CollectorFailure("unsafe_url", "hal retrieval stays on one notice page")
    return url


def parse_notice(payload: bytes) -> HalRecord:
    """Return title, publication date, authors, canonical URL, and license.

    Publication date and license are the string ``unknown`` when the notice
    omits them. ``citation_online_date`` is not a publication date.
    """
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "hal notice exceeds limit")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CollectorFailure("invalid_content", f"malformed hal notice: {exc}") from exc
    parser = _NoticeParser()
    parser.feed(text)
    parser.close()
    if len(parser.metas) > MAX_METAS:
        raise CollectorFailure("content_too_large", "hal notice has too many meta tags")
    canonical = _canonical_url(parser)
    return HalRecord(
        title=_title(parser.metas),
        date=_publication_date(parser.metas),
        authors=_authors(parser.metas),
        canonical_url=canonical,
        license=_license(parser),
    )


def _request_blocked(value: str) -> bool:
    lowered = value.lower()
    if "://" in lowered or lowered.startswith("//") or lowered.startswith("javascript:"):
        return _path_blocked(lowered) or "/search" in lowered
    return _path_blocked(lowered)


def _path_blocked(value: str) -> bool:
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    return any(marker in lowered for marker in _BLOCKED_MARKERS)


def _licence_class(value: str) -> bool:
    return any("licence" in token or "license" in token for token in value.lower().split())


def _meta_values(metas: list[tuple[str, str]], name: str) -> list[str]:
    return [content for key, content in metas if key == name]


def _plain(value: str) -> str:
    cleaned = "".join(char for char in value if ord(char) >= 32)
    return " ".join(cleaned.split())


def _title(metas: list[tuple[str, str]]) -> str:
    for name in ("citation_title", "dc.title"):
        for value in _meta_values(metas, name):
            title = _plain(value)
            if not title:
                continue
            if len(title) > MAX_TITLE_CHARS:
                raise CollectorFailure("content_too_large", "hal title exceeds limit")
            return title
    raise CollectorFailure("invalid_content", "hal notice is missing a title")


def _publication_date(metas: list[tuple[str, str]]) -> str:
    for name in _DATE_FIELDS:
        for value in _meta_values(metas, name):
            parsed = _calendar_date(value)
            if parsed != UNKNOWN:
                return parsed
    return UNKNOWN


def _calendar_date(value: str) -> str:
    match = _YMD.fullmatch(_plain(value))
    if match is None:
        return UNKNOWN
    year = int(match.group(1))
    if year < 1900 or year > 2100:
        return UNKNOWN
    month_text = match.group(2)
    if month_text is None:
        return f"{year:04d}"
    month = int(month_text)
    if month < 1 or month > 12:
        return UNKNOWN
    day_text = match.group(3)
    if day_text is None:
        return f"{year:04d}-{month:02d}"
    day = int(day_text)
    if day < 1 or day > 31:
        return UNKNOWN
    return f"{year:04d}-{month:02d}-{day:02d}"


def _authors(metas: list[tuple[str, str]]) -> tuple[str, ...]:
    values = _meta_values(metas, "citation_author")
    if not values:
        values = _meta_values(metas, "dc.creator")
    if len(values) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "hal author list exceeds limit")
    names: list[str] = []
    for value in values:
        name = _plain(value)
        if not name:
            continue
        if len(name) > MAX_AUTHOR_CHARS:
            raise CollectorFailure("content_too_large", "hal author name exceeds limit")
        names.append(name)
    return tuple(names)


def _canonical_url(parser: _NoticeParser) -> str:
    candidates = []
    if parser.canonical_href:
        candidates.append(parser.canonical_href)
    candidates.extend(_meta_values(parser.metas, "dc.identifier"))
    for candidate in candidates:
        notice = _notice_url(candidate)
        if notice:
            return notice
    raise CollectorFailure("invalid_content", "hal notice is missing a canonical url")


def _notice_url(value: str) -> str | None:
    text = value.strip()
    if not text or _path_blocked(text):
        return None
    try:
        canonical = canonicalize_url(text)
    except ValueError:
        return None
    parsed = urlparse(canonical)
    host = parsed.hostname or ""
    if host not in {API_HOST, "hal.archives-ouvertes.fr"}:
        return None
    if parsed.query or not _NOTICE_PATH.fullmatch(parsed.path):
        return None
    return f"https://{API_HOST}{parsed.path}"


def _license(parser: _NoticeParser) -> str:
    for href in parser.license_hrefs:
        stored = _license_href(href)
        if stored:
            return stored
    return _license_text(parser.license_text)


def _license_href(value: str) -> str | None:
    text = value.strip()
    if not text or text.lower().startswith(("javascript:", "data:", "file:")):
        return None
    if _path_blocked(text):
        return None
    try:
        canonical = canonicalize_url(text)
    except ValueError:
        return None
    parsed = urlparse(canonical)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or host not in _LICENSE_HOSTS:
        return None
    path = parsed.path.lower()
    if not (path.startswith("/licenses/") or path.startswith("/publicdomain/")):
        return None
    if len(canonical) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "hal license exceeds limit")
    return canonical


def _license_text(parts: list[str]) -> str:
    text = _plain(" ".join(parts))
    if not text or _path_blocked(text) or "://" in text:
        return UNKNOWN
    if len(text) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "hal license exceeds limit")
    return text
