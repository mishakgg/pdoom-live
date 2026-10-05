"""Metadata catalog of public Partnership on AI pages about AI safety or governance.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights stay unknown unless that page states a reuse licence that allows
copying. A public page, a copyright notice, and an all-rights-reserved line
are not licences. A missing publication date stays unknown. Updated and
modified times, and a copyright year, are not publication dates. This module
does not fetch and it is not a belief collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "pai_pages"
CATALOG_FILENAME = "pai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_OPEN_GOVERNMENT_LICENCE = "open_government_licence"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_OPEN_GOVERNMENT_LICENCE,
    }
)
OFFICIAL_HOST = "partnershiponai.org"
MAX_FIELD_CHARS = 300
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
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
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
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)
_BLOCKED_PREFIXES = ("/wp-admin", "/wp-content", "/wp-includes", "/wp-json")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_JSONLD = re.compile(r"(?is)<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(r"""([:\w.-]+)\s*=\s*(['"])(.*?)\2""")
_SITE_SUFFIX = re.compile(r"(?i)\s+[-|–—]\s+partnership on ai\s*$")
_SKIP_JSON_KEYS = frozenset({"articleBody", "description", "text", "comment"})
_STATED_CC = re.compile(
    r"(?ix)"
    r"(?:licen[cs]ed|made\s+available|available)\s+under\s+"
    r"(?:the\s+|a\s+)?(?:terms\s+of\s+(?:the\s+)?)?"
    r"(?:creative\s+commons\b|cc[\s-]?by\b|cc0\b|cc[\s-]?zero\b)"
    r"|creative\s+commons\s+(?:attribution|zero|public\s+domain)\b"
)
_CC_URL = re.compile(
    r"(?i)https?://(?:www\.)?creativecommons\.org/(?:licenses|publicdomain)/"
)
_STATED_OGL = re.compile(
    r"(?ix)"
    r"(?:licen[cs]ed|made\s+available|available)\s+under\s+"
    r"(?:the\s+|a\s+)?(?:terms\s+of\s+(?:the\s+)?)?open\s+government\s+licen[cs]e\b"
    r"|open\s+government\s+licen[cs]e\s+v\d"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Partnership on AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_pai_host(hostname: str) -> bool:
    """True only for the apex partnershiponai.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    A Creative Commons or Open Government Licence statement in visible page
    content, or a JSON-LD licence value, can set a label. Script, style, and
    comment text do not count. "All rights reserved", a copyright year, and
    the word licence by itself do not allow copying.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for value in _jsonld_strings(page_text, "license"):
        label = _rights_label(value)
        if label != RIGHTS_UNKNOWN:
            return label
    visible = _visible_html(page_text)
    label = _rights_label(_plain(visible))
    if label != RIGHTS_UNKNOWN:
        return label
    if _CC_URL.search(visible):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dateModified, and a copyright year
    are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in ("article:published_time", "citation_publication_date"):
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    for raw in _jsonld_strings(page_html, "datePublished"):
        found = _iso_prefix(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    og_title = _clean_title(metas.get("og:title", ""))
    heading = _H1.search(visible)
    h1 = _clean_title(heading.group(1)) if heading else ""
    if og_title and h1:
        if og_title.startswith(h1) or h1.startswith(og_title):
            return h1 if len(h1) > len(og_title) else og_title
        return og_title
    if og_title or h1:
        return og_title or h1
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_visible_html(page_html)).get("og:site_name", ""))
    if site:
        return site
    for value in _jsonld_publisher_names(page_html):
        name = _clean_text(value)
        if name:
            return name
    raise CatalogError("publisher is required")


def canonical_url_from_page(page_html: str, *, page_url: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for tag in _LINK.findall(_visible_html(page_html)):
        attrs = _attrs(tag)
        if "canonical" not in attrs.get("rel", "").lower().split():
            continue
        href = attrs.get("href", "").strip()
        if not href:
            continue
        try:
            return validate_canonical_url(urljoin(page_url, href))
        except CatalogError:
            break
    return validate_canonical_url(page_url)


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": canonical_url_from_page(page_html, page_url=page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


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
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public partnershiponai.org page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or not official_pai_host(host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public partnershiponai.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _rights_label(value: str) -> str:
    if _STATED_OGL.search(value):
        return RIGHTS_OPEN_GOVERNMENT_LICENCE
    if _STATED_CC.search(value) or _CC_URL.search(value):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def _official_path(path: str) -> bool:
    if not path.startswith("/") or path == "/":
        return False
    lowered = path.lower()
    if ".." in path or "\\" in path or "//" in path:
        return False
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    for prefix in _BLOCKED_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return False
    return True


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


def _visible_html(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    """Visible text for licence matching. Dashes become spaces so a split name still matches."""
    text = unescape(_TAG.sub(" ", page_text))
    text = (
        text.replace("\u2011", " ")
        .replace("\u2013", " ")
        .replace("\u2014", " ")
        .replace("\u2212", " ")
        .replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _clean_title(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return _SITE_SUFFIX.sub("", text).strip()


def _attrs(tag: str) -> dict[str, str]:
    return {key.casefold(): unescape(value).strip() for key, _, value in _ATTR.findall(tag)}


def _metas(html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _jsonld_strings(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for block in _JSONLD.findall(_COMMENT.sub(" ", page_html)):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        _collect_key(data, key, found)
    return found


def _jsonld_publisher_names(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _JSONLD.findall(_COMMENT.sub(" ", page_html)):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        _collect_publisher(data, found)
    return found


def _collect_key(node: object, key: str, found: list[str], depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(node, dict):
        for name, value in node.items():
            if name in _SKIP_JSON_KEYS:
                continue
            if name == key:
                _flatten_string(value, found)
            else:
                _collect_key(value, key, found, depth + 1)
        return
    if isinstance(node, list):
        for item in node[:30]:
            _collect_key(item, key, found, depth + 1)


def _collect_publisher(node: object, found: list[str], depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(node, dict):
        publisher = node.get("publisher")
        if isinstance(publisher, dict):
            name = publisher.get("name")
            if isinstance(name, str):
                found.append(name)
        elif isinstance(publisher, str):
            found.append(publisher)
        for name, value in node.items():
            if name in _SKIP_JSON_KEYS or name == "publisher":
                continue
            _collect_publisher(value, found, depth + 1)
        return
    if isinstance(node, list):
        for item in node[:30]:
            _collect_publisher(item, found, depth + 1)


def _flatten_string(value: object, found: list[str]) -> None:
    if isinstance(value, str):
        found.append(value)
        return
    if isinstance(value, dict):
        for key in ("@id", "url", "name", "id"):
            item = value.get(key)
            if isinstance(item, str):
                found.append(item)
        return
    if isinstance(value, list):
        for item in value[:10]:
            _flatten_string(item, found)


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
