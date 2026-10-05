"""Metadata catalog of public White House OSTP pages about AI policy.

Rows keep a title, publisher, canonical URL, date, and rights label for HTML
pages on an official whitehouse.gov or ostp host. Page bodies, executive-order
text, and PDFs are not stored. A row is recorded only after a bounded GET
returned the page HTML. This module does not fetch.

Rights is ``us_government_work`` only when a rights field says the item is a
US government work. A public page, a .gov host, or a copyright year is not
enough. ``creative_commons`` means only CC0, CC BY, or CC BY-SA. Other
Creative Commons deeds stay ``unknown``. Updated, modified, and copyright
years are not publication dates. A missing date is ``unknown``.

This catalog is not a belief collector. ``runner_wired`` stays false.
"""

from __future__ import annotations

import ipaddress
import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ostp_ai_pages"
CATALOG_FILENAME = "ostp_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
ALLOWED_RIGHTS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_US_GOVERNMENT_WORK, RIGHTS_CREATIVE_COMMONS}
)
OFFICIAL_HOST_SUFFIXES = ("whitehouse.gov", "ostp.gov")
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_JSONLD = re.compile(r"(?is)<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_RIGHTS_DD = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
    "dc.date.issued",
    "parsely-pub-date",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_RIGHTS_META = frozenset(
    {
        "rights",
        "dc.rights",
        "dcterms.rights",
        "license",
        "dc.license",
        "dcterms.license",
    }
)
_SITE_SUFFIXES = (
    " | The White House",
    " – The White House",
    " — The White House",
    " - The White House",
    " | OSTP",
    " – OSTP",
    " — OSTP",
    " - OSTP",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".csv",
    ".json",
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
)
_PATH_PREFIXES = (
    "/ostp",
    "/releases/",
    "/presidential-actions/",
    "/priorities/tech-innovation",
    "/edai",
)
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_CC_URL = re.compile(
    r"(?i)(?:https?:)?//(?:www\.)?creativecommons\.org/"
    r"(publicdomain/zero|licenses/(?:by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?:/[^\s\"'<>]*)?"
)
_CC_TEXT = (
    (re.compile(r"(?i)\bcc[\s-]?by[\s-]?nc[\s-]?nd\b"), "cc-by-nc-nd"),
    (re.compile(r"(?i)\bcc[\s-]?by[\s-]?nc[\s-]?sa\b"), "cc-by-nc-sa"),
    (re.compile(r"(?i)\bcc[\s-]?by[\s-]?nc\b"), "cc-by-nc"),
    (re.compile(r"(?i)\bcc[\s-]?by[\s-]?nd\b"), "cc-by-nd"),
    (re.compile(r"(?i)\bcc[\s-]?by[\s-]?sa\b"), "cc-by-sa"),
    (re.compile(r"(?i)\bcc[\s-]?by\b"), "cc-by"),
    (re.compile(r"(?i)\bcc[\s-]?0\b|\bcc[\s-]?zero\b"), "cc0"),
    (
        re.compile(r"(?i)creative commons attribution[\s-]+non[\s-]?commercial[\s-]+share[\s-]?alike"),
        "cc-by-nc-sa",
    ),
    (
        re.compile(
            r"(?i)creative commons attribution[\s-]+non[\s-]?commercial[\s-]+no[\s-]?derivatives"
        ),
        "cc-by-nc-nd",
    ),
    (
        re.compile(r"(?i)creative commons attribution[\s-]+non[\s-]?commercial"),
        "cc-by-nc",
    ),
    (
        re.compile(r"(?i)creative commons attribution[\s-]+no[\s-]?derivatives"),
        "cc-by-nd",
    ),
    (
        re.compile(r"(?i)creative commons attribution[\s-]+share[\s-]?alike"),
        "cc-by-sa",
    ),
    (re.compile(r"(?i)creative commons attribution\b"), "cc-by"),
    (re.compile(r"(?i)creative commons zero\b|creative commons cc0\b"), "cc0"),
)
_CC_ALLOWED = frozenset({"cc0", "cc-by", "cc-by-sa"})
_CC_URL_FAMILY = {
    "publicdomain/zero": "cc0",
    "licenses/by-nc-nd": "cc-by-nc-nd",
    "licenses/by-nc-sa": "cc-by-nc-sa",
    "licenses/by-nc": "cc-by-nc",
    "licenses/by-nd": "cc-by-nd",
    "licenses/by-sa": "cc-by-sa",
    "licenses/by": "cc-by",
}


class CatalogError(ValueError):
    """A catalog row or page failed the OSTP AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for whitehouse.gov, ostp.gov, and their subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host) or _is_ip(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_HOST_SUFFIXES)


def rights_from_page(page_html: str) -> str:
    """Classify rights from a rights field.

    ``us_government_work`` requires a rights field that says the item is a US
    government work. ``creative_commons`` requires CC0, CC BY, or CC BY-SA.
    Other Creative Commons deeds, a public page, a .gov host, and a copyright
    year stay ``unknown``.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    text = _plain(" ".join(_rights_fields(page_html)))
    if not text:
        return RIGHTS_UNKNOWN
    if not _NEGATED_GOV_WORK.search(text) and _GOV_WORK.search(text):
        return RIGHTS_US_GOVERNMENT_WORK
    if _creative_commons(text):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return YYYY-MM-DD, or unknown when the page states no publication date.

    Updated, modified, and copyright years are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        found = _date_prefix(metas.get(key))
        if found:
            return found
    for raw in _jsonld_strings(page_html, "datepublished"):
        found = _date_prefix(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        if metas.get(key):
            title = _clean_title(metas[key])
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
    site = _metas(_visible_html(page_html)).get("og:site_name", "").strip()
    if site and "://" not in site:
        return _clean_text(site)
    for node in _jsonld_dicts(page_html):
        publisher = node.get("publisher")
        name = _org_name(publisher)
        if name:
            return name
        kinds = node.get("@type")
        if kinds == "GovernmentOrganization" or (
            isinstance(kinds, list) and "GovernmentOrganization" in kinds
        ):
            name = _org_name(node.get("name"))
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
            continue
    return validate_canonical_url(page_url)


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one HTML page.

    The record does not include the document body, executive-order text, or a
    PDF. ``page_url`` is the URL that returned HTML.
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
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if description != description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CatalogError(f"entries[{index}] must be an object")
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
    if set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be us_government_work, creative_commons, or unknown")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an official White House or OSTP HTML page")
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
        or not is_official_host(host)
        or not _official_html_path(path, host)
    ):
        raise CatalogError(f"canonical URL is not an official White House or OSTP HTML page: {url}")
    return url


def _official_html_path(path: str, host: str) -> bool:
    if not path.startswith("/") or ".." in path or "\\" in path or "//" in path:
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES) or "/wp-content/" in lowered:
        return False
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    if not bare:
        return False
    if host == "ostp.gov" or host.endswith(".ostp.gov"):
        return True
    for prefix in _PATH_PREFIXES:
        root = prefix.rstrip("/")
        if bare == root or bare.startswith(root + "/"):
            return True
    return False


def _rights_fields(page_html: str) -> list[str]:
    """Rights and license fields only. Script text and the article body do not count."""
    fields: list[str] = []
    visible = _visible_html(page_html)
    for tag in _META.findall(visible):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in _RIGHTS_META and attrs.get("content"):
            fields.append(attrs["content"][:2000])
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").lower().split()
        if "license" in rel and attrs.get("href"):
            fields.append(attrs["href"][:2000])
    for block in _RIGHTS_DD.findall(visible):
        fields.append(_clean_text(block)[:2000])
    for node in _jsonld_dicts(page_html):
        for key in ("license", "rights"):
            if key in node:
                fields.extend(part[:2000] for part in _text_values(node[key]))
    return fields


def _creative_commons(text: str) -> bool:
    families: set[str] = set()
    remaining = text
    for match in list(_CC_URL.finditer(remaining)):
        path = match.group(1).lower()
        family = _CC_URL_FAMILY.get(path)
        if family:
            families.add(family)
        remaining = remaining.replace(match.group(0), " ")
    for pattern, family in _CC_TEXT:
        if pattern.search(remaining):
            families.add(family)
            remaining = pattern.sub(" ", remaining)
    allowed = families & _CC_ALLOWED
    other = families - _CC_ALLOWED
    return bool(allowed) and not other


def _jsonld_strings(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for node in _jsonld_dicts(page_html):
        for name, value in node.items():
            if name.lower() == key:
                found.extend(_text_values(value))
    return found


def _jsonld_dicts(page_html: str) -> list[dict]:
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in _JSONLD.findall(page_html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        walk(data)
    return found


def _text_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        name = value.get("name") or value.get("url") or value.get("@id")
        if isinstance(name, str):
            return [name]
        return []
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_text_values(item))
        return found
    return []


def _org_name(value: object) -> str | None:
    if isinstance(value, str):
        text = _clean_text(value)
        if text and "://" not in text:
            return text
        return None
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str):
            text = _clean_text(name)
            if text and "://" not in text:
                return text
    return None


def _visible_html(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


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


def _date_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "://" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


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
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(value: str) -> str:
    text = _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", value))
    return _clean_text(text)


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True
