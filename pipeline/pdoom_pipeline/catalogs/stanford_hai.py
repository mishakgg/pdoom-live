"""Metadata catalog of public Stanford HAI pages on AI policy, the AI Index, and AI safety.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights stays unknown unless that page states a reuse licence. A copyright
notice, a terms link, a footer, or the fact that the page is public is not a
licence. CC-BY-NC and CC-BY-ND stay non-permissive tokens. A page that does
not state a publication date keeps the date unknown. Updated, modified, and
copyright years are not publication dates. The live URL is stored as
confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "stanford_hai_pages"
CATALOG_FILENAME = "stanford_hai_pages.json"
PUBLISHER = "Stanford HAI"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY = "cc_by"
RIGHTS_CC_BY_SA = "cc_by_sa"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC0 = "cc0"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CC_BY,
        RIGHTS_CC_BY_SA,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC0,
    }
)
UNKNOWN_DATE = "unknown"
ALLOWED_HOSTS = frozenset({"hai.stanford.edu", "www.hai.stanford.edu"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
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
    r"(?i)(?<![A-Za-z])Date\s*:?\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+(\d{4})"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "datepublished",
)
_SITE_SUFFIXES = (
    " | Stanford HAI",
    " - Stanford HAI",
    " | Stanford Institute for Human-Centered AI",
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
    ".svg",
    ".bmp",
    ".tif",
    ".tiff",
    ".ico",
)
_GRANT = re.compile(r"\b(?:licensed|released|available)\s+under\b", re.I)
_CC_HREF = re.compile(
    r"creativecommons\.org/(?:licenses|publicdomain)/([a-z0-9-]+)",
    re.I,
)


class CatalogError(ValueError):
    """A catalog row or page failed the Stanford HAI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    _require_text(document.get("description"), "description", MAX_DESCRIPTION_CHARS)
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
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be a short rights token or {RIGHTS_UNKNOWN}")
    return entry


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
        raise CatalogError("canonical URL must be a public Stanford HAI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or host not in ALLOWED_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL is not a public Stanford HAI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in ALLOWED_HOSTS and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a short rights token when the page states a reuse licence.

    A copyright notice, a terms link, a footer, and a public page stay
    unknown. CC-BY-NC and CC-BY-ND are recorded as those tokens, not as a
    permissive yes. The licence deed text is not returned.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    token = _token_from_licence_href(visible)
    if token:
        return token
    plain = _plain_text(visible)
    if _GRANT.search(plain) is None:
        return RIGHTS_UNKNOWN
    return _token_from_licence_words(plain.casefold()) or RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, an Updated or Modified label, and
    a copyright year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key))
        if parsed:
            return parsed
    plain = _plain_text(page_html)
    for match in _LABELED_DATE.finditer(plain):
        prefix = plain[max(0, match.start() - 24) : match.start()].casefold()
        if any(word in prefix for word in ("updat", "modif", "copyright", "©")):
            continue
        parsed = _calendar_date(match.group(1), match.group(2), match.group(3))
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


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    The publisher is the organization, not an author biography.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": PUBLISHER,
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _is_download(path: str) -> bool:
    return path.lower().endswith(_DOWNLOAD_SUFFIXES)


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


def _visible_html(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible_html(page_text))


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group(1)


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _token_from_licence_href(visible_html: str) -> str | None:
    found: list[str] = []
    for tag in [*_LINK.findall(visible_html), *_ANCHOR.findall(visible_html)]:
        attrs = _attrs(tag)
        href = attrs.get("href", "")
        rel = attrs.get("rel", "").lower().split()
        if "license" in rel or "creativecommons.org/" in href.casefold():
            token = _token_from_cc_path(href)
            if token and token not in found:
                found.append(token)
    if not found:
        return None
    return _prefer_restrictive(found)


def _token_from_licence_words(plain: str) -> str | None:
    normalized = (
        plain.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .casefold()
    )
    windows = [
        normalized[max(0, match.start() - 60) : match.start() + 240]
        for match in _GRANT.finditer(normalized)
    ]
    if not windows:
        return None
    normalized = " ".join(windows)
    flags: list[str] = []
    if re.search(r"\bcc0\b|publicdomain/zero|public domain dedication", normalized):
        flags.append(RIGHTS_CC0)
    has_nc = re.search(r"cc[\s-]*by[\s-]*nc\b|attribution-noncommercial", normalized)
    has_nd = re.search(
        r"cc[\s-]*by(?:[\s-]*nc)?[\s-]*nd\b|attribution-noncommercial-noderiv|"
        r"attribution-noderivatives|no-derivatives|noderivatives",
        normalized,
    )
    has_sa = re.search(
        r"cc[\s-]*by(?:[\s-]*nc)?[\s-]*sa\b|attribution-sharealike|share-alike|share alike",
        normalized,
    )
    has_by = re.search(r"cc[\s-]*by\b|creative commons attribution", normalized)
    if has_nc and has_nd:
        flags.append(RIGHTS_CC_BY_NC_ND)
    elif has_nc and has_sa:
        flags.append(RIGHTS_CC_BY_NC_SA)
    elif has_nc:
        flags.append(RIGHTS_CC_BY_NC)
    elif has_nd:
        flags.append(RIGHTS_CC_BY_ND)
    elif has_sa:
        flags.append(RIGHTS_CC_BY_SA)
    elif has_by:
        flags.append(RIGHTS_CC_BY)
    path_token = _token_from_cc_path(normalized)
    if path_token:
        flags.append(path_token)
    if not flags:
        return None
    return _prefer_restrictive(flags)


def _token_from_cc_path(value: str) -> str | None:
    match = _CC_HREF.search(value)
    if match is None:
        return None
    slug = match.group(1).casefold()
    return {
        "by-nc-nd": RIGHTS_CC_BY_NC_ND,
        "by-nc-sa": RIGHTS_CC_BY_NC_SA,
        "by-nc": RIGHTS_CC_BY_NC,
        "by-nd": RIGHTS_CC_BY_ND,
        "by-sa": RIGHTS_CC_BY_SA,
        "by": RIGHTS_CC_BY,
        "zero": RIGHTS_CC0,
    }.get(slug)


def _prefer_restrictive(tokens: list[str]) -> str:
    order = (
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_SA,
        RIGHTS_CC0,
        RIGHTS_CC_BY,
    )
    for token in order:
        if token in tokens:
            return token
    return RIGHTS_UNKNOWN


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
