"""Metadata catalog of public Alan Turing Institute pages on AI safety, governance, and policy.

A row is stored only when a response is the page HTML and the title is taken
from that response. A challenge page or a non-HTML response is not stored.
Page text is not stored. The publisher is The Alan Turing Institute. People
are not merged into the publisher. Rights is ``uk_ogl`` only when that HTML
states the Open Government Licence. Otherwise rights is ``unknown``. The
institute is not a UK government publisher. A page that does not state a
publication date keeps the date unknown. Updated and modified times are not
publication dates. The response URL is stored; a different rel=canonical does
not replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "turing_ai_pages"
CATALOG_FILENAME = "turing_ai_pages.json"
PUBLISHER = "The Alan Turing Institute"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_UK_OGL, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
ALLOWED_HOSTS = frozenset({"www.turing.ac.uk", "turing.ac.uk"})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_TAG = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>|<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_SITE_SUFFIXES = (
    " | The Alan Turing Institute",
    " - The Alan Turing Institute",
    " \u2013 The Alan Turing Institute",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".epub",
    ".mp3",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
)


class CatalogError(ValueError):
    """A catalog row or page failed the Alan Turing Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_UK_OGL} or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Alan Turing Institute page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() not in ALLOWED_HOSTS
        or host not in ALLOWED_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _html_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Alan Turing Institute page: {url}")
    return url


def is_turing_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in ALLOWED_HOSTS and not hostname_is_blocked(host)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    plain = _plain_text(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from an HTML response that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
                return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML.

    The title comes from that HTML. A challenge page, an error status, or a
    non-HTML response is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=page_url)


def rights_from_page(page_text: str) -> str:
    """Return uk_ogl when the page states the Open Government Licence.

    Script and style text does not count. Crown copyright alone, a copyright
    footer, a public page, and the American spelling "license" do not state
    the Open Government Licence. The institute is not a UK government publisher.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    if OGL_PHRASE in _plain_text(page_text).casefold():
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, and dcterms.modified are not
    publication dates. A displayed update time is not used.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    heading = _H1.search(page_html)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(page_html)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the institute when the page names it. Do not use a person byline."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _metas(page_html).get("og:site_name", "").strip()
    if site.casefold() == PUBLISHER.casefold():
        return PUBLISHER
    if site:
        raise CatalogError("publisher must be The Alan Turing Institute")
    title = _metas(page_html).get("og:title", "")
    if any(suffix.casefold() in title.casefold() for suffix in _SITE_SUFFIXES):
        return PUBLISHER
    raise CatalogError("publisher must be The Alan Turing Institute")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the response
    URL. A rel=canonical pointing somewhere else is not used. A challenge page
    is not stored.
    """

    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _html_path(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return path in {"", "/"} or path.startswith("/")


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(page_text)


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
