"""Metadata catalog of public Machine Intelligence Research Institute pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page bodies, essays, PDFs,
and reports are not stored. Rights is ``creative_commons`` only when the page
states CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A public page, a copyright notice, an
all-rights-reserved line, or a terms link is not a licence. Updated, modified,
and copyright years are not publication dates. A missing date stays unknown.
The live URL is stored as confirmed; a different rel=canonical does not
replace it. This module does not fetch. It is not a belief collector, and
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

CATALOG_ID = "miri_pages"
CATALOG_FILENAME = "miri_pages.json"
RUNNER_WIRED = False
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
PUBLISHER = "Machine Intelligence Research Institute"
MIRI_HOST = "intelligence.org"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_ISO_IN_TEXT = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_DATE_PUBLISHED_BLOCK = re.compile(
    r"(?is)<([a-z0-9]+)\b[^>]*\bitemprop\s*=\s*[\"']datePublished[\"'][^>]*>(.*?)</\1>"
)
_TIME_DATETIME = re.compile(
    r"""(?is)<time\b[^>]*\bdatetime\s*=\s*(?:"([^"]*)"|'([^']*)')[^>]*>"""
)
_TIME_TEXT = re.compile(r"(?is)<time\b[^>]*>(.*?)</time>")
_MONTH_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),\s+(\d{4})\b",
    re.I,
)
_CC_URL = re.compile(
    r"creativecommons\.org/(?:publicdomain/zero|licenses/"
    r"(by-nc-nd|by-nc-sa|by-nd|by-nc|by-sa|by))(?=/|\b)",
    re.I,
)
_CC0_TEXT = re.compile(
    r"\bcc[\s-]?0\b|"
    r"creative commons(?:\s+(?:cc[\s-]?0|zero|public\s+domain(?:\s+dedication)?))\b",
    re.I,
)
_CC_BY_SA_TEXT = re.compile(
    r"\bcc[\s-]?by[\s-]?sa\b|"
    r"creative commons(?:\s+attribution)?[\s-]+share[\s-]?alike\b",
    re.I,
)
_CC_BY_TEXT = re.compile(
    r"\bcc[\s-]?by\b(?![\s\-.:]{0,3}(?:nc|nd|sa)\b)|"
    r"creative commons attribution\b(?![\s\-.:]{0,3}"
    r"(?:non[\s-]?commercial|no[\s-]?deriv|share[\s-]?alike))",
    re.I,
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_SUFFIXES = (
    " | Machine Intelligence Research Institute",
    " - Machine Intelligence Research Institute",
    " – Machine Intelligence Research Institute",
    " — Machine Intelligence Research Institute",
    " | MIRI",
    " - MIRI",
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
}
_ALLOWED_URL_KINDS = frozenset({"by", "by-sa"})


class CatalogError(ValueError):
    """A catalog row or page failed the MIRI page rules."""


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
    if not isinstance(description, str):
        raise CatalogError("description is required")
    lowered = description.casefold()
    if "creative_commons" not in description or "unknown" not in lowered:
        raise CatalogError("description must state the rights labels")
    if "belief collector" not in lowered or "runner_wired stays false" not in lowered:
        raise CatalogError("description must state that runner_wired stays false")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append(_sort_key(entry))
        if len(order) > 1 and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public intelligence.org page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or host != MIRI_HOST
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
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public intelligence.org page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower()
    return host == MIRI_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons for a stated CC0, CC BY, or CC BY-SA licence.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A substring
    match on "creative commons" or "cc-by" is not CC BY when NonCommercial,
    NoDerivatives, or ShareAlike follows. Script and style text does not count.
    A copyright notice, an all-rights-reserved line, or a terms link does not
    state a reuse licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    allowed = False

    def replace_anchor(match: re.Match[str]) -> str:
        nonlocal allowed
        href = _attrs(match.group(1)).get("href", "")
        kind = _cc_url_kind(href)
        if kind == "allowed":
            allowed = True
            return " "
        if kind == "restrictive":
            return " "
        return match.group(0)

    remaining = _ANCHOR.sub(replace_anchor, visible)
    if allowed or _allowed_cc_url(remaining) or _allowed_cc_text(_plain(remaining)):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, and a copyright or updated year are
    not publication dates. A listing with more than one datePublished value
    does not choose one of those child dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _date_prefix(metas.get(key, ""))
        if parsed:
            return parsed
    stated = _single_itemprop_date(_without_hidden(page_html))
    if stated:
        return stated
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
    heading = _H1.search(page_html)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(page_html)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _metas(page_html).get("og:site_name", "").strip()
    if site == PUBLISHER:
        return site
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned the page HTML. A rel=canonical pointing somewhere else
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


def _official_path(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if lowered.startswith("/wp-admin") or lowered.startswith("/wp-json") or "/wp-content/" in lowered:
        return False
    return path in {"", "/"} or path.startswith("/")


def _sort_key(entry: dict) -> tuple[str, str]:
    published = "9999-99-99" if entry["date"] == UNKNOWN_DATE else entry["date"]
    return (published, entry["canonical_url"])


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


def _plain(page_text: str) -> str:
    text = _clean_text(page_text)
    return (
        text.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    visible = _without_hidden(page_html)
    for tag in _META.findall(visible):
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


def _date_prefix(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
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


def _single_itemprop_date(visible_html: str) -> str | None:
    blocks = _DATE_PUBLISHED_BLOCK.findall(visible_html)
    if len(blocks) != 1:
        return None
    return _date_in_block(blocks[0][1])


def _date_in_block(block_html: str) -> str | None:
    for datetime_double, datetime_single in _TIME_DATETIME.findall(block_html):
        parsed = _date_prefix(unescape(datetime_double or datetime_single))
        if parsed:
            return parsed
    for inner in _TIME_TEXT.findall(block_html):
        parsed = _human_or_iso(_plain(inner))
        if parsed:
            return parsed
    return _human_or_iso(_plain(block_html))


def _human_or_iso(text: str) -> str | None:
    match = _MONTH_DATE.search(text)
    if match:
        month = _MONTHS[match.group(1).casefold()]
        try:
            parsed = date(int(match.group(3)), month, int(match.group(2)))
        except ValueError:
            return None
        return parsed.isoformat()
    found = _ISO_IN_TEXT.search(text)
    if found and _iso_date(found.group(1)):
        return found.group(1)
    return None


def _cc_url_kind(value: str) -> str | None:
    match = _CC_URL.search(unescape(value or "").replace("&amp;", "&"))
    if match is None:
        return None
    kind = (match.group(1) or "").lower()
    if not kind or kind in _ALLOWED_URL_KINDS:
        return "allowed"
    return "restrictive"


def _allowed_cc_url(html: str) -> bool:
    for match in _CC_URL.finditer(html):
        kind = (match.group(1) or "").lower()
        if not kind or kind in _ALLOWED_URL_KINDS:
            return True
    return False


def _allowed_cc_text(plain: str) -> bool:
    folded = plain.casefold()
    if _CC0_TEXT.search(folded) or _CC_BY_SA_TEXT.search(folded) or _CC_BY_TEXT.search(folded):
        return True
    return False
