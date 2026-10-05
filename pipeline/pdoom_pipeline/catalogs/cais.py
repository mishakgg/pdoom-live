"""Metadata catalog of public Center for AI Safety pages.

Each stored URL was confirmed with one bounded GET. A row keeps a short title,
the publisher, that URL, a date, and a rights label. Statement text, paper
abstracts, and page bodies are not stored. A list of names on a page is not
an identity resolution. The fetched URL is stored; a different rel=canonical
is not read. A copyright year is not a publication date. Rights stays unknown
unless the page text states a reuse licence. This module does not fetch and
it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cais_pages"
CATALOG_FILENAME = "cais_pages.json"
PUBLISHER = "Center for AI Safety"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY_4_0 = "cc_by_4_0"
RIGHTS_CC0 = "cc0"
ALLOWED_RIGHTS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CC_BY_4_0, RIGHTS_CC0})
UNKNOWN_DATE = "unknown"
ALLOWED_HOSTS = frozenset({"safe.ai", "www.safe.ai"})
MAX_TITLE_CHARS = 120
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_JSONLD = re.compile(r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>")
_TAG = re.compile(r"(?is)<[^>]+>")
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
    " | Center for AI Safety",
    " | CAIS",
    " - Center for AI Safety",
    " - CAIS",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".gz",
    ".tgz",
    ".tar",
    ".epub",
)
_CC_BY_4_0 = re.compile(
    r"(?i)(?:"
    r"creative commons attribution 4\.0"
    r"|cc[-\s]?by[-\s]?4\.0"
    r"|creativecommons\.org/licenses/by/4\.0"
    r")"
)
_CC0 = re.compile(
    r"(?i)(?:"
    r"\bcc0\b"
    r"|creative commons zero"
    r"|creativecommons\.org/publicdomain/zero/1\.0"
    r")"
)
_LICENSE_KEYS = frozenset({"license", "licence"})


class CatalogError(ValueError):
    """A catalog row or page failed the Center for AI Safety page rules."""


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
    if "p(doom)" in description.casefold():
        raise CatalogError("description must not store a p(doom) figure")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
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
    _require_text(entry.get("title"), "title", MAX_TITLE_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_UNKNOWN}, {RIGHTS_CC_BY_4_0}, or {RIGHTS_CC0}")
    if "p(doom)" in entry["title"].casefold():
        raise CatalogError("title must not store a p(doom) figure")


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
        raise CatalogError("canonical URL must be a public Center for AI Safety page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or not is_cais_host(host)
        or hostname_is_blocked(host)
        or not _html_page_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Center for AI Safety page: {url}")
    return url


def is_cais_host(hostname: str) -> bool:
    """True for safe.ai or www.safe.ai, and false for a blocked hostname."""
    host = (hostname or "").strip().lower().rstrip(".")
    return host in ALLOWED_HOSTS and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a reuse-licence label stated by the page, or unknown.

    A copyright symbol, a copyright year, "all rights reserved", or a public
    statement is not a licence to copy the page. Text inside script, style,
    or comments does not count. JSON-LD license fields do.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible, licenses = _prepared(page_text)
    stated = _plain_text(visible)
    for extra in licenses:
        stated = f"{stated} {extra}"
    if _CC_BY_4_0.search(stated):
        return RIGHTS_CC_BY_4_0
    if _CC0.search(stated):
        return RIGHTS_CC0
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, and a copyright year are not
    publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible, _licenses, published = _prepared_dates(page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_day(metas.get(key, ""))
        if found:
            return found
    for raw in published:
        found = _iso_day(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible, _licenses = _prepared(page_html)
    metas = _metas(visible)
    candidates: list[str] = []
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            candidates.append(metas[key])
    heading = _H1.search(visible)
    if heading:
        candidates.append(heading.group(1))
    title_tag = _TITLE.search(visible)
    if title_tag:
        candidates.append(title_tag.group(1))
    for candidate in candidates:
        title = _clean_title(candidate)
        if title:
            return title
    raise CatalogError("title is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    ``page_url`` is the URL that was fetched. A rel=canonical pointing
    somewhere else is not used. The record does not include the page body,
    statement text, or a list of names.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": PUBLISHER,
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _html_page_path(path: str) -> bool:
    if any(token in path for token in ("..", "\\", "//", "%")):
        return False
    if path in {"", "/"}:
        return True
    lowered = path.lower()
    if not lowered.startswith("/"):
        return False
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    return not bare.endswith(_DOWNLOAD_SUFFIXES)


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if any(char in value for char in "<>\n\r\t"):
        raise CatalogError(f"{field} must be plain text")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _plain_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _plain_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _iso_day(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    day = match.group(1)
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    return day


def _prepared(page_html: str) -> tuple[str, list[str]]:
    visible, licenses, _published = _prepared_dates(page_html)
    return visible, licenses


def _prepared_dates(page_html: str) -> tuple[str, list[str], list[str]]:
    without_comments = _COMMENT.sub(" ", page_html)
    licenses, published = _jsonld_signals(without_comments)
    visible = _SCRIPT_STYLE.sub(" ", without_comments)
    return visible, licenses, published


def _jsonld_signals(page_html: str) -> tuple[list[str], list[str]]:
    licenses: list[str] = []
    published: list[str] = []
    for block in _JSONLD.findall(page_html):
        if len(block) > 20_000:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        _collect_jsonld(payload, licenses, published, depth=0)
    return licenses, published


def _collect_jsonld(node: object, licenses: list[str], published: list[str], depth: int) -> None:
    if depth > 8:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = key.casefold()
            if lowered in _LICENSE_KEYS and isinstance(value, str):
                licenses.append(value)
            elif lowered == "datepublished" and isinstance(value, str):
                published.append(value)
            else:
                _collect_jsonld(value, licenses, published, depth + 1)
        return
    if isinstance(node, list):
        for item in node:
            _collect_jsonld(item, licenses, published, depth + 1)


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
