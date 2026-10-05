"""Metadata catalog of public Australian Government pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
are not stored. A date the page does not state as published stays unknown.
Rights stay unknown unless the page states a reuse licence that allows copying.
A public page, a copyright notice, or a link to terms is not a licence.

Allowed hosts are gov.au and its subdomains. This catalog is not a collector
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

CATALOG_ID = "australia_ai_pages"
CATALOG_FILENAME = "australia_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
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
_DOCUMENT_SUFFIXES = (".pdf", ".doc", ".docx", ".zip", ".csv", ".xml", ".json", ".jpg", ".jpeg", ".png", ".gif", ".webp")
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_PUBLISHER_FIELD = re.compile(
    r"(?is)<h3\b[^>]*>\s*Publisher\s*</h3>.{0,1200}?<a\b[^>]*>(.*?)</a>"
)
_INITIATIVE = re.compile(r"(?is)An initiative of the\s+([A-Za-z][A-Za-z' ]{2,80})")
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
_MONTH_PATTERN = r"January|February|March|April|May|June|July|August|September|October|November|December"
_LONG_DATE = re.compile(rf"(\d{{1,2}})\s+({_MONTH_PATTERN})\s+(\d{{4}})", re.I)
_DATE_PUBLISHED = re.compile(rf"\bdate published\s*:\s*{_LONG_DATE.pattern}", re.I)
_PUBLISHED_COLON = re.compile(rf"(?<![A-Za-z])published\s*:\s*{_LONG_DATE.pattern}", re.I)
_PUBLISHED_WORD = re.compile(rf"(?<![A-Za-z])published\s+{_LONG_DATE.pattern}", re.I)
_CC_REUSE = re.compile(
    r"licensed under (?:a |the )?(?:creative commons|cc\s*by\b)|"
    r"available under (?:a |the )?(?:creative commons|cc\s*by\b)|"
    r"creative commons attribution|"
    r"creativecommons\.org/licenses/|"
    r"creativecommons\.org/publicdomain/|"
    r"\bcc\s*by\s*[- ]?\d"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Australian Government page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_australia_host(hostname: str) -> bool:
    """True for gov.au and its subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host) or _is_ip(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return host == "gov.au" or host.endswith(".gov.au")


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    licence_links = []
    for tag in re.findall(r"(?is)<a\b[^>]*>", html):
        href = _attrs(tag).get("href", "")
        if "creativecommons.org/" in href.casefold():
            licence_links.append(href)
    plain = (_plain(html) + " " + " ".join(licence_links)).casefold()
    if _CC_REUSE.search(plain):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Return a publication date, or unknown when the page does not state one.

    Date updated, last updated, and dcterms.date are not publication dates.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    plain = _plain(html)
    published = _first_labeled_date(plain, (_DATE_PUBLISHED, _PUBLISHED_COLON, _PUBLISHED_WORD))
    if published:
        return published
    from_time = _published_time(html)
    if from_time:
        return from_time
    issued = _meta_iso(html, "dcterms.issued")
    if issued:
        return issued
    created = _meta_iso(html, "dcterms.created")
    if created and _page_states_day(plain, created):
        return created
    return UNKNOWN_DATE


def title_from_page(page_text: str) -> str:
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    heading = _H1.search(html)
    h1 = _plain(heading.group(1)) if heading else ""
    title_tag = _TITLE.search(html)
    document = ""
    if title_tag:
        document = _plain(title_tag.group(1)).split("|", 1)[0].strip()
    if h1 and document.startswith(h1) and document:
        return document
    metas = _meta_map(html)
    og = _plain(metas.get("og:title", ""))
    if og:
        return og.split("|", 1)[0].strip()
    if h1:
        return h1
    if document:
        return document
    raise CatalogError("title is required")


def publisher_from_page(page_text: str) -> str:
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    field = _PUBLISHER_FIELD.search(html)
    if field:
        name = _plain(field.group(1))
        if name:
            return name
    metas = _meta_map(html)
    contributor = _plain(metas.get("dcterms.contributor", ""))
    if contributor:
        return contributor
    creator = _plain(metas.get("dcterms.creator", ""))
    expanded = _expanded_short_name(html, creator)
    if expanded:
        return expanded
    initiative = _INITIATIVE.search(html)
    if initiative:
        name = _plain(initiative.group(1))
        if name:
            return name
    site = _plain(metas.get("og:site_name", ""))
    if site:
        return site
    title_tag = _TITLE.search(html)
    if title_tag and "|" in title_tag.group(1):
        suffix = _plain(title_tag.group(1)).rsplit("|", 1)[-1].strip()
        if suffix:
            return suffix
    raise CatalogError("publisher is required")


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
        raise CatalogError("canonical URL must be a gov.au https URL")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
        or parsed.port not in (None, 443)
        or not official_australia_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "(s(" in path.casefold()
        or _is_document(path)
    ):
        raise CatalogError(f"canonical URL must be a gov.au https URL: {url}")
    if path in {"", "/"}:
        raise CatalogError(f"canonical URL path is not a stable government page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
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
    text = _TAG.sub(" ", page_text)
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in _ATTR.finditer(tag):
        if match.group(2) is not None:
            value = match.group(2)
        elif match.group(3) is not None:
            value = match.group(3)
        else:
            value = match.group(4) or ""
        found[match.group(1).casefold()] = unescape(value).strip()
    return found


def _meta_map(html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(html):
        item = _attrs(tag)
        key = (item.get("name") or item.get("property") or "").casefold()
        if key and key not in found:
            found[key] = item.get("content", "")
    return found


def _first_labeled_date(plain: str, patterns: tuple[re.Pattern[str], ...]) -> str | None:
    for pattern in patterns:
        match = pattern.search(plain)
        if match is None:
            continue
        parsed = _from_long_date(match.group(1), match.group(2), match.group(3))
        if parsed:
            return parsed
    return None


def _published_time(html: str) -> str | None:
    for match in _TIME.finditer(html):
        inner = _plain(match.group(0))
        if "published" not in inner.casefold():
            continue
        labeled = _first_labeled_date(inner, (_PUBLISHED_COLON, _PUBLISHED_WORD))
        if labeled:
            return labeled
        attrs = _attrs(match.group(1))
        iso = _iso_prefix(attrs.get("datetime", ""))
        if iso:
            return iso
    return None


def _meta_iso(html: str, name: str) -> str | None:
    return _iso_prefix(_meta_map(html).get(name, ""))


def _iso_prefix(value: str) -> str | None:
    text = value.strip()
    if len(text) < 10:
        return None
    prefix = text[:10]
    if _iso_date(prefix):
        return prefix
    return None


def _from_long_date(day: str, month: str, year: str) -> str | None:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        parsed = date(int(year), month_number, int(day))
    except ValueError:
        return None
    return parsed.isoformat()


def _page_states_day(plain: str, iso: str) -> bool:
    parsed = date.fromisoformat(iso)
    month = next(name for name, number in _MONTHS.items() if number == parsed.month)
    titled = month.capitalize()
    lowered = plain.casefold()
    for day in {str(parsed.day), f"{parsed.day:02d}"}:
        if f"{day} {titled}".casefold() in lowered and str(parsed.year) in plain:
            return True
    return False


def _expanded_short_name(html: str, short: str) -> str:
    if not short:
        return ""
    marker = f"({short})"
    for tag in re.findall(r"(?is)<img\b[^>]*>", html):
        alt = _plain(_attrs(tag).get("alt", ""))
        if marker in alt:
            name = alt.split("(", 1)[0].strip()
            if name:
                return name
    return short


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_ip(host: str) -> bool:
    try:
        import ipaddress

        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _is_document(path: str) -> bool:
    lowered = path.casefold()
    return any(lowered.endswith(suffix) for suffix in _DOCUMENT_SUFFIXES)
