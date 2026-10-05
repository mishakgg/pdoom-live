"""Metadata catalog of public Singapore government pages on AI Verify, the Model
AI Governance Framework, and the Singapore AI Safety Institute.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page bodies are not stored.
A date the page does not state stays unknown. Last-updated times are not
publication dates. Rights stay unknown unless the page states a reuse licence
that allows copying. A public page, a copyright notice, a terms-of-use link,
a regulatory licence, and the site credit "Open Government Products" are not
reuse licences. This module does not fetch and it is not a belief collector.
runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "singapore_ai_pages"
CATALOG_FILENAME = "singapore_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_SINGAPORE_OPEN_DATA = "singapore_open_data_licence"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_SINGAPORE_OPEN_DATA,
        RIGHTS_CREATIVE_COMMONS,
    }
)
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
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_ON = re.compile(r"\bpublished on\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", re.I)
_LAST_UPDATED = re.compile(
    r"\blast updated(?:\s+on)?\s*:?\s*\d{1,2}\s+[A-Za-z]+\s+\d{4}\b",
    re.I,
)
_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b")
_SODL = re.compile(
    r"(?:licen[cs]e\s*:\s*singapore open data licen[cs]e"
    r"|licen[cs]ed under (?:the )?singapore open data licen[cs]e"
    r"|available under (?:the )?(?:terms of the )?singapore open data licen[cs]e)"
)
_CREATIVE_COMMONS = re.compile(
    r"licen[cs]ed under (?:a |the )?creative commons|"
    r"creativecommons\.org/licenses/|"
    r"creativecommons\.org/publicdomain/"
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
    ".doc",
    ".docx",
)
_SITE_PREFIXES = ("PDPC | ",)
_SITE_SUFFIXES = (
    " | IMDA",
    " | IMDA PDPC",
    " | Ministry of Digital Development and Information",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_HOST_PUBLISHERS = (
    ("pdpc.gov.sg", "Personal Data Protection Commission"),
    ("mddi.gov.sg", "Ministry of Digital Development and Information"),
    ("imda.gov.sg", "Infocomm Media Development Authority"),
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class CatalogError(ValueError):
    """A catalog row or page failed the Singapore government page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_singapore_host(hostname: str) -> bool:
    """True for gov.sg, imda.gov.sg, and their subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return host == "gov.sg" or host.endswith(".gov.sg")


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    plain = _plain(page_text).casefold()
    if _SODL.search(plain):
        return RIGHTS_SINGAPORE_OPEN_DATA
    if _CREATIVE_COMMONS.search(plain):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Return a publication date, or unknown when the page does not state one.

    ``Published on`` wins. A last-updated or last-modified time is not a
    publication date. Script and style text does not count.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    plain = _plain(page_text)
    published = _PUBLISHED_ON.search(plain)
    if published:
        iso = _to_iso(*published.groups())
        if iso:
            return iso
    visible = _LAST_UPDATED.sub(" ", plain)
    for match in _DAY_MONTH_YEAR.finditer(visible):
        iso = _to_iso(*match.groups())
        if iso:
            return iso
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in _TITLE_KEYS:
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    for heading in _H1.findall(page_html):
        title = _clean_title(heading)
        if title:
            return title
    title_tag = _TITLE.search(page_html)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return the agency name the page states for its official host."""
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    host = (urlparse(page_url).hostname or "").lower().rstrip(".")
    plain = _plain(page_html).casefold()
    for suffix, name in _HOST_PUBLISHERS:
        if host == suffix or host.endswith("." + suffix):
            if name.casefold() in plain:
                return name
            break
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


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
        raise CatalogError("canonical URL must be a gov.sg or imda.gov.sg https URL")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
        or parsed.port not in (None, 443)
        or not official_singapore_host(host)
        or not path
        or path == "/"
        or ".." in path
        or "\\" in path
        or "//" in path
        or path.lower().endswith(_DOWNLOAD_SUFFIXES)
    ):
        raise CatalogError(f"canonical URL must be a gov.sg or imda.gov.sg https page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _to_iso_date(value) is None:
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


def _plain(page_text: str) -> str:
    text = _TAG.sub(" ", _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text)))
    text = unescape(text)
    text = (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for prefix in _SITE_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix) :].strip()
                changed = True
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


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
        attrs.setdefault(name.lower(), unescape(double or single or bare).strip())
    return attrs


def _to_iso(day: str, month: str, year: str) -> str | None:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        parsed = date(int(year), month_number, int(day))
    except ValueError:
        return None
    return parsed.isoformat()


def _to_iso_date(value: str) -> str | None:
    if _DATE.fullmatch(value) is None:
        return None
    year, month, day = value.split("-")
    try:
        parsed = date(int(year), int(month), int(day))
    except ValueError:
        return None
    if parsed.isoformat() != value:
        return None
    return value
