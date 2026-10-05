"""Metadata catalog of public Georgetown CSET pages about AI safety or AI policy.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
and PDFs are not stored. A date the page does not state stays unknown.
Modification times are not publication dates. Rights stay unknown unless the
page states a reuse licence that allows copying. A public page, a copyright
notice, or a link to site policies is not a licence. This catalog is not a
collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cset_pages"
CATALOG_FILENAME = "cset_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_OPEN_GOVERNMENT = "open_government_licence"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_OPEN_GOVERNMENT})
OFFICIAL_HOST = "cset.georgetown.edu"
PUBLISHER = "Center for Security and Emerging Technology"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
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
        "pdf",
        "pdoom",
        "p_doom",
        "probability",
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PATH = re.compile(r"^/(?:publication|research-area|topic)/[a-z0-9]+(?:-[a-z0-9]+)*/$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>")
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b([^>]*)>(.*?)</h1>")
_PAGE_TITLE = re.compile(r'(?is)<h1\b[^>]*class="[^"]*\bpage-title__title\b[^"]*"[^>]*>(.*?)</h1>')
_SITE_SUFFIX = re.compile(
    r"(?i)\s*\|\s*Center for Security and Emerging Technology(?:\s+Georgetown AI)?\s*$"
)
_GENERIC_TITLES = frozenset({"reports", "publications", "related content", "introduction"})
_ARCHIVES_SUFFIX = re.compile(r"(?i)\s+Archives$")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_CC_STATEMENT = re.compile(
    r"(?i)(?:licen[cs]ed|available|released|published) under (?:the )?(?:terms of )?(?:a |the )?"
    r"(?:creative commons\b|cc[-\s]?(?:by(?:-[a-z]{2}){0,2}|0)\b)"
)
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/(?:licenses/(?:by(?:-[a-z]{2}){0,2}|zero)|publicdomain/(?:zero|mark))(?:/|$)"
)
_OGL_STATEMENT = re.compile(
    r"(?i)(?:licen[cs]ed|available|released|published) under (?:the )?(?:terms of )?(?:a |the )?"
    r"open government licen[cs]e\b"
)
_OGL_URL = re.compile(r"(?i)nationalarchives\.gov\.uk/doc/open-government-licen[cs]e(?:/|$)")


class CatalogError(ValueError):
    """A catalog row or page failed the Georgetown CSET page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_cset_host(hostname: str) -> bool:
    """True only for the official cset.georgetown.edu host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            label = _label_for_licence_text(raw.replace("\\/", "/"))
            if label != RIGHTS_UNKNOWN:
                return label
    visible = _without_hidden(page_text)
    for href in _license_hrefs(visible):
        label = _label_for_licence_text(href)
        if label != RIGHTS_UNKNOWN:
            return label
    for content in _meta_values(visible, _LICENSE_META):
        label = _label_for_licence_text(content)
        if label != RIGHTS_UNKNOWN:
            return label
    return _label_for_licence_text(_plain(visible))


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Modification times stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    for raw in _meta_values(page_text, _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    heading = _PAGE_TITLE.search(page_html)
    if heading:
        title = _clean_text(heading.group(1))
        if _usable_title(title):
            return title
    for attrs, inner in _H1.findall(page_html):
        if "site-name" in attrs.casefold():
            continue
        title = _clean_text(inner)
        if _usable_title(title):
            return title
    raw = _metas(page_html).get("og:title", "")
    title = _ARCHIVES_SUFFIX.sub("", _SITE_SUFFIX.sub("", _clean_text(raw))).strip()
    if not _usable_title(title):
        raise CatalogError("title is required")
    return title


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    publisher = _clean_text(_metas(page_html).get("og:site_name", ""))
    if not publisher:
        raise CatalogError("publisher is required")
    return publisher


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(urljoin(live, href.strip()))
    except CatalogError:
        return live
    if _same_page(declared, live):
        return declared
    return live


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document["runner_wired"] is not False:
        raise CatalogError("runner_wired must be false")
    entries = document["entries"]
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
    _require_text(entry, "title")
    _require_text(entry, "publisher")
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https cset.georgetown.edu page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not official_cset_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https cset.georgetown.edu page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


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


def _same_page(left: str, right: str) -> bool:
    a = urlparse(left)
    b = urlparse(right)
    return (a.hostname or "").lower() == (b.hostname or "").lower() and a.path.rstrip("/") == b.path.rstrip("/")


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    return title.casefold() not in _GENERIC_TITLES


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _license_hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel and attrs.get("href"):
            hrefs.append(attrs["href"])
    return hrefs


def _label_for_licence_text(value: str) -> str:
    if _CC_URL.search(value) or _CC_STATEMENT.search(value):
        return RIGHTS_CREATIVE_COMMONS
    if _OGL_URL.search(value) or _OGL_STATEMENT.search(value):
        return RIGHTS_OPEN_GOVERNMENT
    return RIGHTS_UNKNOWN


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
