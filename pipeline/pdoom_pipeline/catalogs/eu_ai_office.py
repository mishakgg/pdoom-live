"""Metadata catalog of public European AI Office pages.

Each stored URL was confirmed with one bounded GET of the European Commission
host. A row keeps the title, publisher, canonical URL, date, and rights label.
Page text, regulation text, and PDFs are not stored. Rights stay unknown
unless the page states a reuse licence. ``creative_commons`` means only CC0,
CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A public page, a copyright notice, or a terms link is not a licence.
An EU reuse decision or Decision 2011/833/EU is ``eu_reuse_decision`` when
the page states it. Updated, modified, and copyright years are not publication
dates. A page that does not state a publication date keeps the date unknown.
The live URL is stored as confirmed; a different rel=canonical does not
replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "eu_ai_office_pages"
CATALOG_FILENAME = "eu_ai_office_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_EU_REUSE = "eu_reuse_decision"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_EU_REUSE, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
COMMISSION_HOST_SUFFIXES = ("ec.europa.eu", "commission.europa.eu")
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HEADER_META = re.compile(r"(?is)<ul\b[^>]*\becl-page-header__meta\b[^>]*>(.*?)</ul>")
_MANAGED_BY = re.compile(
    r"(?is)<div\b[^>]*\becl-site-footer__description\b[^>]*>(.*?)</div>"
)
_COMMISSION_MARK = re.compile(
    r"""(?is)(?:alt\s*=\s*["']European Commission logo["']|aria-label\s*=\s*["'][^"']*European Commission[^"']*["'])"""
)
_LABELED_DATE = re.compile(
    r"(?i)\bpublication\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b"
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
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_IGNORED_DATE_KEYS = frozenset(
    {
        "article:modified_time",
        "og:updated_time",
        "dcterms.modified",
        "dc.date.modified",
    }
)
_SITE_SUFFIXES = (
    " | Shaping Europe’s digital future",
    " | Shaping Europe's digital future",
    " - Shaping Europe’s digital future",
    " - Shaping Europe's digital future",
)
_DOWNLOAD_SUFFIXES = (".pdf", ".zip", ".csv", ".json", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".webp")
_OFFICE_MARKERS = (
    "ai-office",
    "ai-board",
    "ai-scientific-panel",
    "ai-advisory-forum",
    "ai-code-practice",
    "contents-code-gpai",
    "guidelines-gpai",
    "ai-pact",
)
_CC_TOKEN = re.compile(
    r"(?i)(?:"
    r"creativecommons\.org/(?:licenses|publicdomain)/[a-z0-9./_-]+"
    r"|creative\s+commons\s+attribution(?:[\s-]+(?:non[\s-]?commercial|no[\s-]?derivativ\w*|share[\s-]?alike))*\b"
    r"|cc[\s-]*0\b"
    r"|cc[\s-]*by(?:[\s-]*(?:nc|nd|sa))*\b"
    r")"
)
_EU_REUSE = re.compile(
    r"(?i)(?:"
    r"\bdecision\s+2011/833/eu\b"
    r"|commission decision of 12 december 2011 on the reuse of commission documents"
    r")"
)


class CatalogError(ValueError):
    """A catalog row or page failed the European AI Office page rules."""


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
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS}, {RIGHTS_EU_REUSE}, or {RIGHTS_UNKNOWN}")


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
        raise CatalogError("canonical URL must be a public European AI Office page")
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
        or not is_official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _office_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public European AI Office page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    """True for the European Commission host and its subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in COMMISSION_HOST_SUFFIXES)


def rights_from_page(page_text: str) -> str:
    """Return a reuse-licence label stated by the page, or unknown.

    creative_commons is only CC0, CC BY, or CC BY-SA. Restrictive Creative
    Commons licences stay unknown. A copyright notice or a link to terms does
    not state a licence. When the page states both a permissive Creative
    Commons licence and an EU reuse decision, the Creative Commons licence is
    the label. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    plain = _plain_text(page_text)
    if _has_permissive_creative_commons(plain):
        return RIGHTS_CREATIVE_COMMONS
    if _EU_REUSE.search(plain):
        return RIGHTS_EU_REUSE
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    The Commission header label ``Publication`` counts. Last update, modified
    time, and copyright years do not.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    header = _HEADER_META.search(visible)
    if header:
        labeled = _labeled_publication(_plain_fragment(header.group(1)))
        if labeled:
            return labeled
    metas = _metas(visible)
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
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
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


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if not isinstance(page_url, str) or not page_url.strip():
        raise CatalogError("page URL is required")
    if _COMMISSION_MARK.search(page_html):
        return "European Commission"
    managed = _MANAGED_BY.search(page_html)
    if managed:
        name = _clean_text(re.sub(r"(?i)^this site is managed by:\s*", "", _plain_fragment(managed.group(1))))
        if name:
            return name
    site = _metas(_visible_html(page_html)).get("og:site_name", "").strip()
    if site:
        return _clean_text(site)
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
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _office_path(path: str) -> bool:
    lowered = path.lower()
    if not lowered.startswith("/"):
        return False
    if lowered.endswith(_DOWNLOAD_SUFFIXES) or lowered.endswith("/pdf") or "/printable/" in lowered:
        return False
    return any(marker in lowered for marker in _OFFICE_MARKERS)


def _has_permissive_creative_commons(plain: str) -> bool:
    return any(_permissive_cc(match.group(0)) for match in _CC_TOKEN.finditer(plain))


def _permissive_cc(token: str) -> bool:
    if _restrictive_cc(token):
        return False
    folded = token.casefold()
    if "creativecommons.org/" in folded:
        trimmed = folded.rstrip("/")
        return (
            "/publicdomain/zero" in folded
            or "/licenses/by-sa" in folded
            or "/licenses/by/" in folded
            or trimmed.endswith("/licenses/by")
        )
    return True


def _restrictive_cc(token: str) -> bool:
    folded = token.casefold()
    if "creativecommons.org/" in folded:
        return "/by-nc" in folded or "/by-nd" in folded
    compact = re.sub(r"[\s-]+", "", folded)
    return (
        "noncommercial" in compact
        or "noderivative" in compact
        or "ccbync" in compact
        or "ccbynd" in compact
    )


def _labeled_publication(text: str) -> str | None:
    match = _LABELED_DATE.search(text)
    if match is None:
        return None
    month = _MONTHS.get(match.group(2).casefold())
    if month is None:
        return None
    try:
        parsed = date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None
    return parsed.isoformat()


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
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_fragment(fragment: str) -> str:
    return _clean_text(fragment)


def _visible_html(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible_html(page_text))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in _IGNORED_DATE_KEYS:
            continue
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
