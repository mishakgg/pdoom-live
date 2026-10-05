"""Metadata catalog of public Google DeepMind publication pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Abstracts, page bodies, and
PDFs are not stored. Rights is ``creative_commons`` only when the page states
CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A public page, a copyright notice, an all-rights-reserved line, or a
terms link is not a licence. Updated, modified, and copyright years are not
publication dates. A page that does not state a publication date keeps the
date unknown. The live URL is stored as confirmed; a different rel=canonical
does not replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "deepmind_pages"
CATALOG_FILENAME = "deepmind_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
DEEPMIND_HOST = "deepmind.google"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
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
_DATE_NODE = re.compile(
    r"(?is)<([a-z0-9]+)\b[^>]*\bclass\s*=\s*"
    r"(?:\"[^\"]*\bsection-title__date\b[^\"]*\""
    r"|'[^']*\bsection-title__date\b[^']*'"
    r"|[^\s\"'>]*\bsection-title__date\b[^\s\"'>]*)"
    r"[^>]*>((?:(?!</\1>).){0,160})</\1>"
)
_HREF = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_SITE_SUFFIXES = (
    " — Google DeepMind",
    " – Google DeepMind",
    " - Google DeepMind",
    " | Google DeepMind",
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
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
_MDY = re.compile(rf"^({_MONTH})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})$", re.IGNORECASE)
_DMY = re.compile(rf"^(\d{{1,2}})\s+({_MONTH})\.?,?\s+(\d{{4}})$", re.IGNORECASE)
_ISO_INSTANT = re.compile(
    r"^(\d{4}-\d{2}-\d{2})(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)
_NOT_PUBLICATION = re.compile(
    r"(?i)\b(?:updated|update|modified|modification|copyright)\b|©|all rights reserved"
)
_PUBLISHED_PREFIX = re.compile(
    r"(?i)^(?:published|publication date|date)\s*:?\s*"
)
_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Permissive reuse notices. A following NC or ND suffix is a different licence.
_CC0 = re.compile(
    r"(?<![a-z0-9])cc[\s-]*0(?:[\s-]*1\.0)?(?![a-z0-9])|"
    r"creative commons(?:\s+cc0|\s+zero\b)"
)
_CC_BY_SA = re.compile(
    r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?:[\s-]*(?:v(?:ersion)?[\s-]*)?\d+(?:\.\d+)?)?(?![a-z0-9])|"
    r"creative commons attribution[\s-]*share[\s-]*alike"
)
_CC_BY = re.compile(
    r"(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)"
    r"(?:[\s-]*(?:v(?:ersion)?[\s-]*)?\d+(?:\.\d+)?)?(?![a-z0-9])|"
    r"creative commons attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
)
_RESTRICTIVE = re.compile(
    r"(?<![a-z0-9])cc[\s-]*by[\s-]*(?:nc(?:[\s-]*(?:sa|nd))?|nd)\b|"
    r"creative commons attribution[\s-]*(?:non[\s-]*commercial|no[\s-]*deriv)"
)
_CC_HREF = re.compile(
    r"(?i)creativecommons\.org/(?:publicdomain/zero/\d|licenses/"
    r"(by-nc-sa|by-nc-nd|by-nc|by-nd|by-sa|by)(?:/|[\s\"'#?]|$))"
)
_PERMISSIVE_HREF = frozenset({"by", "by-sa"})


class CatalogError(ValueError):
    """A catalog row or page failed the Google DeepMind publication rules."""


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
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")


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
        raise CatalogError("canonical URL must be a public Google DeepMind publication page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc != DEEPMIND_HOST
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
        or not _publication_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Google DeepMind publication page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == DEEPMIND_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons when the page states CC0, CC BY, or CC BY-SA.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown, including
    when a permissive phrase appears beside them. Script and style text does
    not count. A copyright notice, an all-rights-reserved line, a terms link,
    and a public page do not state a reuse licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    plain = _plain_text(visible).casefold().translate(_DASHES)
    kinds = _href_kinds(visible)
    if _RESTRICTIVE.search(plain) or "restrictive" in kinds:
        return RIGHTS_UNKNOWN
    permissive = _CC0.search(plain) or _CC_BY_SA.search(plain) or _CC_BY.search(plain)
    if "permissive" in kinds or permissive:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    The publications date label is the publication date. article:modified_time,
    og:updated_time, an Updated or Modified label, and a copyright year are not
    publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    labeled = _date_from_label(visible)
    if labeled:
        return labeled
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key))
        if parsed:
            return parsed
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


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher"):
        site = (metas.get(key) or "").strip()
        if site:
            return site
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed publication page.

    The record does not include the abstract or the document body. ``page_url``
    is the live URL that was fetched. A rel=canonical pointing somewhere else
    is not used.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _publication_path(path: str) -> bool:
    if path != path.lower() or path.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if path in {"/research/publications", "/research/publications/"}:
        return True
    match = re.fullmatch(r"/research/publications/(\d+)/?", path)
    if match is None:
        return False
    ident = match.group(1)
    return ident != "0" and not ident.startswith("0")


def _href_kinds(visible_html: str) -> set[str]:
    kinds: set[str] = set()
    for tag in _HREF.findall(visible_html):
        kind = _href_kind(_attrs(tag).get("href", ""))
        if kind:
            kinds.add(kind)
    return kinds


def _href_kind(href: str) -> str | None:
    match = _CC_HREF.search(href or "")
    if match is None:
        return None
    if "publicdomain/zero/" in match.group(0).casefold():
        return "permissive"
    token = (match.group(1) or "").casefold()
    if token in _PERMISSIVE_HREF:
        return "permissive"
    if token:
        return "restrictive"
    return None


def _date_from_label(visible_html: str) -> str | None:
    match = _DATE_NODE.search(visible_html)
    if match is None:
        return None
    inner = _plain_text(match.group(2))
    if not inner or _NOT_PUBLICATION.search(inner):
        return None
    text = _PUBLISHED_PREFIX.sub("", inner).strip()
    parsed = _calendar_text(text)
    if parsed:
        return parsed
    return _iso_prefix(text)


def _calendar_text(text: str) -> str | None:
    mdy = _MDY.fullmatch(text)
    if mdy:
        return _calendar_date(mdy.group(1), mdy.group(2), mdy.group(3))
    dmy = _DMY.fullmatch(text)
    if dmy:
        return _calendar_date(dmy.group(2), dmy.group(1), dmy.group(3))
    return None


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold().rstrip("."))
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    instant = _ISO_INSTANT.fullmatch(value.strip())
    if instant and _real_iso(instant.group(1)):
        return instant.group(1)
    return None


def _real_iso(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be plain text")


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


def _plain_text(page_text: str) -> str:
    return _clean_text(page_text)


def _visible_html(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


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
