"""Metadata catalog of public Ada Lovelace Institute pages.

The rows are official www.adalovelaceinstitute.org pages about AI safety or
governance. Each stored URL was confirmed with one bounded GET. A row keeps
the title, publisher, canonical URL, date, and rights label. Page text is not
stored. This module does not fetch, and it is not a belief collector.
``runner_wired`` stays false.

Rights stay unknown unless that page itself states a reuse licence that
allows copying. A public page, a copyright notice, or a link to a blog post
is not a licence. Script, style, and comment text does not count. When the
visible page states that its contents are shared under CC BY-NC 4.0, rights
is ``cc_by_nc_4_0``. That grant is used even if the page also names CC BY
4.0, because the non-commercial limit is the narrower copying permission the
page states. A page that states CC BY 4.0 and does not state the
non-commercial grant has rights ``cc_by_4_0``. A missing publication date
stays unknown. Updated and modified times are not publication dates. The
live URL is stored as confirmed; a different rel=canonical does not replace
it.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "adalovelace_pages"
CATALOG_FILENAME = "adalovelace_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY_NC_4_0 = "cc_by_nc_4_0"
RIGHTS_CC_BY_4_0 = "cc_by_4_0"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CC_BY_NC_4_0, RIGHTS_CC_BY_4_0})
OFFICIAL_HOST = "www.adalovelaceinstitute.org"
MAX_TEXT_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_PUBLICATION_DATE_KEYS = (
    "citation_publication_date",
    "article:published_time",
    "dcterms.created",
    "dcterms.issued",
    "dc.date.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("citation_publisher", "citation_technical_report_institution", "og:site_name")
_SITE_SUFFIXES = (" | Ada Lovelace Institute", " - Ada Lovelace Institute")
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
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)
_BLOCKED_PREFIXES = ("/wp-admin", "/wp-content", "/wp-includes", "/wp-json", "/xmlrpc.php")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4})[/-](\d{2})[/-](\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_GRANT_BY_NC = re.compile(
    r"(?:shared|licen[cs]ed) under (?:a |the )?"
    r"cc[\s-]*by[\s-]*nc[\s-]*4\.0\s*licen[cs]e"
    r"|creativecommons\.org/licenses/by-nc/4\.0",
    re.IGNORECASE,
)
_GRANT_BY = re.compile(
    r"(?:shared|licen[cs]ed) under (?:a |the )?"
    r"cc[\s-]*by(?![\s-]*nc)[\s-]*4\.0\s*licen[cs]e"
    r"|creativecommons\.org/licenses/by/4\.0",
    re.IGNORECASE,
)


class CatalogError(ValueError):
    """A catalog row or page failed the Ada Lovelace Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_host(hostname: str) -> bool:
    """True only for the official www.adalovelaceinstitute.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    haystack = f"{_plain(visible)} {' '.join(_hrefs(visible))}"
    if _GRANT_BY_NC.search(haystack):
        return RIGHTS_CC_BY_NC_4_0
    if _GRANT_BY.search(haystack):
        return RIGHTS_CC_BY_4_0
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time and og:updated_time are not publication dates.
    Prose that mentions another document's publication date is not used.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _parse_date(metas.get(key, ""))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        publisher = _clean_text(metas.get(key, ""))
        if publisher:
            return publisher
    title_tag = _TITLE.search(visible)
    if title_tag:
        raw = _clean_text(_TAG.sub(" ", title_tag.group(1)))
        if " | " in raw:
            publisher = raw.rsplit(" | ", 1)[1].strip()
            if publisher:
                return publisher
        if raw == "Ada Lovelace Institute":
            return raw
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or not description.strip() or description != description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for index, entry in enumerate(entries):
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if index and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise CatalogError("entry must be an object")
    _reject_stored_body(entry, path="entry")
    if set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Ada Lovelace Institute page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or host != OFFICIAL_HOST
        or parsed.netloc.lower() != OFFICIAL_HOST
        or not official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Ada Lovelace Institute page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _parse_date(value) != value:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _official_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    return not any(bare == prefix or bare.startswith(prefix + "/") for prefix in _BLOCKED_PREFIXES)


def _reject_stored_body(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(value)
        if found:
            names = ", ".join(sorted(found))
            raise CatalogError(f"{path} must not store page text ({names})")
        for key, item in value.items():
            _reject_stored_body(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_stored_body(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_TEXT_CHARS or "<" in value or ">" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _parse_date(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    parsed = "-".join(match.groups())
    try:
        date.fromisoformat(parsed)
    except ValueError:
        return None
    return parsed


def _visible_html(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _hrefs(visible_html: str) -> list[str]:
    found: list[str] = []
    for double, single in _HREF.findall(visible_html):
        href = unescape(double or single).strip()
        if href and href not in found:
            found.append(href)
    return found


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value) if "<" in value else value)
    text = (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
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
