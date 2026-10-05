"""Metadata catalog of public UNESCO pages about the Recommendation on the Ethics of Artificial Intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
and the recommendation articles are not stored. A date the page does not state
stays unknown. A displayed last-update time is not a publication date. Rights
stay unknown unless the page states a reuse licence that allows copying. A
public page, a copyright notice, or a link to terms of use is not a licence.

Allowed hosts are unesco.org and its subdomains. This catalog is not a
collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "unesco_ai_pages"
CATALOG_FILENAME = "unesco_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY_NC_SA_3_0_IGO = "cc_by_nc_sa_3_0_igo"
RIGHTS_CC_BY_SA_3_0_IGO = "cc_by_sa_3_0_igo"
RIGHTS_CC_BY_4_0 = "cc_by_4_0"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CC_BY_NC_SA_3_0_IGO,
        RIGHTS_CC_BY_SA_3_0_IGO,
        RIGHTS_CC_BY_4_0,
        RIGHTS_CREATIVE_COMMONS,
    }
)
OFFICIAL_HOST_SUFFIXES = ("unesco.org",)
PUBLISHER = "UNESCO"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "article",
        "articles",
        "body",
        "content",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "preamble",
        "quotation",
        "quote",
        "recommendation_text",
        "text",
        "transcript",
        "transcript_text",
    }
)
_PRIMARY_TYPES = frozenset({"article", "newsarticle", "report"})
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_JSONLD = re.compile(r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>")
_TAG = re.compile(r"(?is)<[^>]+>")
_CREATED = re.compile(r'(?is)<div\b[^>]*class="[^"]*\bcreated-time\b[^"]*"[^>]*>(.*?)</div>')
_ADOPTION = re.compile(r"date and place of adoption\s+(\d{1,2})\s+([a-z]+)\s+(20\d{2})")
_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([a-z]+)\s+(20\d{2})\b")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_ATTR = re.compile(r"""([:\w.-]+)\s*=\s*(['"])(.*?)\2""")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*['"]([^'"]+)['"]""")
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
        "dcterms:issued",
    }
)
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
_CC_BY_NC_SA_30_IGO = re.compile(
    r"cc[-\s]?by[-\s]?nc[-\s]?sa[-\s]?3\.0(?:[-\s]?igo)?|"
    r"attribution[-\s]?noncommercial[-\s]?sharealike\s*3\.0\s*igo|"
    r"creativecommons\.org/licenses/by-nc-sa/3\.0(?:/igo)?"
)
_CC_BY_SA_30_IGO = re.compile(
    r"cc[-\s]?by[-\s]?sa[-\s]?3\.0(?:[-\s]?igo)?|"
    r"attribution[-\s]?sharealike\s*3\.0\s*igo|"
    r"creativecommons\.org/licenses/by-sa/3\.0(?:/igo)?"
)
_CC_BY_40 = re.compile(
    r"creative commons attribution 4\.0(?: international)?|"
    r"cc[-\s]?by[-\s]?4\.0|"
    r"creativecommons\.org/licenses/by/4\.0"
)
_CC_STATEMENT = re.compile(
    r"licen[cs]ed under (?:a |the )?creative commons|"
    r"licen[cs]e type:\s*cc[-\s]?by|"
    r"creativecommons\.org/licenses/|"
    r"creativecommons\.org/publicdomain/"
)


class CatalogError(ValueError):
    """A catalog row or page failed the UNESCO page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_unesco_host(hostname: str) -> bool:
    """True for unesco.org and its subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_HOST_SUFFIXES)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _plain(_without_hidden(page_text))
    hrefs = " ".join(_HREF.findall(_without_hidden(page_text)))
    structured = _jsonld_licence_text(page_text)
    return _rights_label(f"{visible} {hrefs} {structured}")


def date_from_page(page_text: str) -> str:
    """Use the page's own adoption or publication date, else unknown.

    A created-time display wins, then a labeled adoption date, then schema.org
    datePublished or an issued/published meta tag. Last update, dateModified,
    and dates on embedded cards are not the page date.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible_html = _without_hidden(page_text)
    created = _created_date(visible_html)
    if created:
        return created
    adopted = _adoption_date(visible_html)
    if adopted:
        return adopted
    published = _schema_date(page_text)
    if published:
        return published
    meta = _meta_published_date(visible_html)
    if meta:
        return meta
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
        raise CatalogError("canonical URL must be a unesco.org https URL")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not official_unesco_host(host)
        or not parsed.path
        or parsed.path == "/"
        or parsed.path.endswith("/")
    ):
        raise CatalogError(f"canonical URL must be a unesco.org https URL: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _rights_label(text: str) -> str:
    folded = _normalize(text).casefold()
    if _CC_BY_NC_SA_30_IGO.search(folded):
        return RIGHTS_CC_BY_NC_SA_3_0_IGO
    if _CC_BY_SA_30_IGO.search(folded):
        return RIGHTS_CC_BY_SA_3_0_IGO
    if _CC_BY_40.search(folded):
        return RIGHTS_CC_BY_4_0
    if _CC_STATEMENT.search(folded):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def _created_date(html: str) -> str | None:
    match = _CREATED.search(html)
    if not match:
        return None
    return _day_month_year(_plain(match.group(1)))


def _adoption_date(html: str) -> str | None:
    match = _ADOPTION.search(_plain(html).casefold())
    if not match:
        return None
    return _compose_date(match.group(1), match.group(2), match.group(3))


def _schema_date(page_text: str) -> str | None:
    for blob in _JSONLD.findall(page_text):
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            continue
        for node in _nodes(payload):
            if not _is_primary_work(node.get("@type")):
                continue
            found = _iso_prefix(node.get("datePublished"))
            if found:
                return found
    return None


def _meta_published_date(html: str) -> str | None:
    for tag in _META.findall(html):
        attrs = _attrs(tag)
        key = (attrs.get("name") or attrs.get("property") or "").casefold()
        if key not in _PUBLISHED_META:
            continue
        found = _iso_prefix(attrs.get("content", ""))
        if found:
            return found
    return None


def _jsonld_licence_text(page_text: str) -> str:
    parts: list[str] = []
    for blob in _JSONLD.findall(page_text):
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            continue
        for node in _nodes(payload):
            licence = node.get("license")
            if isinstance(licence, str):
                parts.append(licence)
            elif isinstance(licence, dict):
                parts.append(str(licence.get("@id") or licence.get("url") or ""))
    return " ".join(parts)


def _is_primary_work(value: object) -> bool:
    if isinstance(value, str):
        return value.casefold() in _PRIMARY_TYPES
    if isinstance(value, list):
        return any(isinstance(item, str) and item.casefold() in _PRIMARY_TYPES for item in value)
    return False


def _nodes(value: object):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nodes(item)


def _iso_prefix(value: object) -> str | None:
    if isinstance(value, dict):
        value = value.get("@value")
    if not isinstance(value, str):
        return None
    prefix = value.strip()[:10]
    if _iso_date(prefix):
        return prefix
    return None


def _day_month_year(text: str) -> str | None:
    match = _DAY_MONTH_YEAR.search(text.casefold())
    if not match:
        return None
    return _compose_date(match.group(1), match.group(2), match.group(3))


def _compose_date(day_text: str, month_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_text.casefold())
    if month is None:
        return None
    try:
        composed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return composed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text))
    return re.sub(r"\s+", " ", _normalize(text)).strip()


def _normalize(text: str) -> str:
    return (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )


def _attrs(tag: str) -> dict[str, str]:
    return {key.casefold(): unescape(value).strip() for key, _, value in _ATTR.findall(tag)}


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
