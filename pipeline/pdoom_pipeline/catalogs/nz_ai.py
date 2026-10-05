"""Metadata catalog of public New Zealand government pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
are not stored. A date the page does not state stays unknown. Rights stay
unknown unless the page states a reuse licence that allows copying. A public
page, a copyright notice, or a link to terms is not a licence.

Allowed hosts are govt.nz and its subdomains. This catalog is not a collector
and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "nz_ai_pages"
CATALOG_FILENAME = "nz_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY = "creative_commons_attribution"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CC_BY})
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
_ISSUED_META = frozenset({"dcterms.issued", "dcterms:issued", "dc.date.issued"})
_MODIFIED_META = frozenset({"dcterms.modified", "dcterms:modified", "dc.date.modified"})
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_ATTR = re.compile(r"""([:\w.-]+)\s*=\s*(['"])(.*?)\2""")
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_LABELED_DATE = re.compile(
    r"\b(?:date published|last updated|date modified)\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))\b",
    re.I,
)
_CC_BY = re.compile(r"creative commons attribution\s+4\.0\s+international\b")
_CC_BY_URL = re.compile(r"creativecommons\.org/licenses/by/4\.0\b")


class CatalogError(ValueError):
    """A catalog row or page failed the New Zealand government page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_nz_government_host(hostname: str) -> bool:
    """True for govt.nz and its subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return labels[-2:] == ["govt", "nz"]


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    plain = _plain(page_text).casefold()
    if _CC_BY.search(plain) or _CC_BY_URL.search(plain):
        return RIGHTS_CC_BY
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use an issued or published date, then a stated updated date, else unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    issued = _first_iso_date(_meta_values(html, _ISSUED_META))
    if issued:
        return issued
    plain = _plain(page_text)
    published = _labeled_date(plain, "date published")
    if published:
        return published
    updated = _labeled_date(plain, "last updated")
    if updated:
        return updated
    modified = _first_iso_date(_meta_values(html, _MODIFIED_META))
    if modified:
        return modified
    labeled_modified = _labeled_date(plain, "date modified")
    if labeled_modified:
        return labeled_modified
    return UNKNOWN_DATE


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
        raise CatalogError("canonical URL must be a govt.nz https URL")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
        or parsed.port not in (None, 443)
        or host.endswith(".")
        or not official_nz_government_host(host)
    ):
        raise CatalogError(f"canonical URL must be a govt.nz https URL: {url}")
    if not parsed.path or parsed.path == "/" or "(s(" in parsed.path.casefold():
        raise CatalogError(f"canonical URL path is not a stable government page: {url}")
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


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = _TAG.sub(" ", _without_hidden(page_text))
    text = unescape(text)
    text = (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def _attrs(tag: str) -> dict[str, str]:
    return {key.casefold(): unescape(value).strip() for key, _, value in _ATTR.findall(tag)}


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    found: list[str] = []
    for tag in _META.findall(html):
        attrs = _attrs(tag)
        key = attrs.get("name") or attrs.get("property") or ""
        if key.casefold() in names:
            found.append(attrs.get("content", ""))
    return found


def _first_iso_date(values: list[str]) -> str | None:
    for value in values:
        if _iso_date(value):
            return value
    return None


def _labeled_date(plain: str, label: str) -> str | None:
    for match in _LABELED_DATE.finditer(plain):
        if not match.group(0).casefold().startswith(label):
            continue
        iso, day, month, year = match.groups()
        if iso and _iso_date(iso):
            return iso
        parsed = _written_date(day, month, year)
        if parsed:
            return parsed
    return None


def _written_date(day: str | None, month: str | None, year: str | None) -> str | None:
    if not day or not month or not year:
        return None
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        parsed = date(int(year), month_number, int(day))
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
