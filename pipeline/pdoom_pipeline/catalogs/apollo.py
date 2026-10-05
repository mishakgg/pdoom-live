"""Metadata catalog of public Apollo Research pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights stay unknown unless the page states a reuse licence. creative_commons
means only CC0, CC BY, or CC BY-SA. Negative lookaheads reject NonCommercial
and NoDerivatives, so CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A URL containing creativecommons.org/licenses/by-nc stays unknown.
uk_ogl is used only when the page text states the phrase "open government
licence". Apollo Research is not a UK government publisher. A page that does
not state a publication date keeps the date unknown. Updated, modified, last
updated, and copyright years are not publication dates. The live URL is stored
as confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "apollo_pages"
CATALOG_FILENAME = "apollo_pages.json"
PUBLISHER = "Apollo Research"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
ALLOWED_RIGHTS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL})
UNKNOWN_DATE = "unknown"
APOLLO_HOST = "www.apolloresearch.ai"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_HREF_TAG = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_ON_DAY_MONTH = re.compile(
    r"(?i)\bpublished on\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})\b"
)
_PUBLISHED_ON_MONTH_DAY = re.compile(
    r"(?i)\bpublished on\s+([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b"
)
_NOT_PUBLICATION_PREFIX = re.compile(r"(?i)(?:last|updated|modified)\s+$")
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
    "dc.date.issued",
)
_SITE_SUFFIXES = (
    " | Apollo Research",
    " – Apollo Research",
    " — Apollo Research",
    " - Apollo Research",
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
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)
_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
# Negative lookaheads reject NonCommercial and NoDerivatives. CC BY-NC,
# CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND therefore do not match CC BY or CC BY-SA.
_NOT_NC_OR_ND = r"(?![\s\-_./]*(?:NonCommercial|NoDerivatives|nc|nd)\b)"
_CC0_PHRASE = re.compile(
    r"\bcc[\s-]*0\b|creative\s+commons(?:\s+public\s+domain)?[\s-]+(?:cc[\s-]*0|zero)\b",
    re.IGNORECASE,
)
_CC_BY_PHRASE = re.compile(
    r"(?:"
    r"\bcc[\s-]*by(?:[\s-]*sa)?" + _NOT_NC_OR_ND + r"|creative\s+commons\s+attribution(?:[\s-]*share[\s-]*alike)?"
    + _NOT_NC_OR_ND
    + r")",
    re.IGNORECASE,
)
_CC0_URL = re.compile(r"creativecommons\.org/publicdomain/zero(?:/|\b)", re.IGNORECASE)
_CC_BY_URL = re.compile(
    r"creativecommons\.org/licenses/by" + _NOT_NC_OR_ND + r"(?:-sa)?(?:/|\b)",
    re.IGNORECASE,
)
_RESTRICTIVE_CC = re.compile(
    r"(?:"
    r"creativecommons\.org/licenses/by-(?:nc(?:-sa|-nd)?|nd)\b"
    r"|\bcc[\s-]*by[\s-]*(?:nc(?:[\s-]*(?:sa|nd))?|nd)\b"
    r"|creative\s+commons\s+attribution[\s-]*(?:non[\s-]*commercial|no[\s-]*derivatives)"
    r"|attribution[\s-]*(?:NonCommercial|NoDerivatives)\b"
    r")",
    re.IGNORECASE,
)


class CatalogError(ValueError):
    """A catalog row or page failed the Apollo Research page rules."""


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
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_UK_OGL}, {RIGHTS_CREATIVE_COMMONS}, or {RIGHTS_UNKNOWN}")


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
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Apollo Research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or host != APOLLO_HOST
        or parsed.netloc.lower() != APOLLO_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or host.endswith(".")
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL is not a public Apollo Research page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower()
    if not host or host.endswith("."):
        return False
    return host == APOLLO_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    creative_commons means only CC0, CC BY, or CC BY-SA. Negative lookaheads
    reject NonCommercial and NoDerivatives, so CC BY-NC, CC BY-ND, CC BY-NC-SA,
    and CC BY-NC-ND stay unknown. A URL containing
    creativecommons.org/licenses/by-nc stays unknown. uk_ogl is returned only
    when the visible page text states "open government licence". A public page,
    a copyright notice, and a terms link are not licences. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    plain = _plain(visible)
    stated = _rights_blobs(visible, plain)
    if _RESTRICTIVE_CC.search(stated):
        return RIGHTS_UNKNOWN
    if OGL_PHRASE in plain.casefold():
        return RIGHTS_UK_OGL
    if _states_creative_commons(stated):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, updated, modified, last updated,
    and a copyright year are not publication dates. A Webflow "Last Published"
    comment is not a publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key, ""))
        if parsed:
            return parsed
    return _published_on_date(_plain(visible)) or UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
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
    """Return Apollo Research when the page states that name.

    The organisation is not a UK government publisher. A person's name is not
    substituted for the organisation.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    if metas.get("og:site_name", "").strip() == PUBLISHER:
        return PUBLISHER
    for key in ("og:title", "citation_publisher"):
        if PUBLISHER in metas.get(key, ""):
            return PUBLISHER
    title_tag = _TITLE.search(visible)
    if title_tag and PUBLISHER in _clean_text(title_tag.group(1)):
        return PUBLISHER
    if re.search(rf"\b{re.escape(PUBLISHER)}\b", _plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    A Cloudflare challenge page is refused.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if _blocked_page(page_html):
        raise CatalogError("blocked page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _blocked_page(page_html: str) -> bool:
    head = page_html[:8000].casefold()
    if any(marker in head for marker in ("cf-browser-verification", "challenge-platform", "/cdn-cgi/challenge")):
        return True
    match = _TITLE.search(_visible(page_html[:8000]))
    if match is None:
        return False
    title = _clean_text(match.group(1)).casefold()
    return title in {"just a moment...", "attention required! | cloudflare", "access denied"}


def _states_creative_commons(stated: str) -> bool:
    return any(pattern.search(stated) for pattern in (_CC0_PHRASE, _CC0_URL, _CC_BY_PHRASE, _CC_BY_URL))


def _rights_blobs(visible: str, plain: str) -> str:
    parts = [plain.casefold()]
    for tag in _HREF_TAG.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            parts.append(href.casefold())
    metas = _metas(visible)
    for key in ("dc.rights", "dcterms.rights"):
        if metas.get(key):
            parts.append(metas[key].casefold())
    return "\n".join(parts)


def _published_on_date(plain: str) -> str | None:
    found: list[tuple[int, str]] = []
    for pattern, month_first in ((_PUBLISHED_ON_DAY_MONTH, False), (_PUBLISHED_ON_MONTH_DAY, True)):
        for match in pattern.finditer(plain):
            prefix = plain[max(0, match.start() - 16) : match.start()]
            if _NOT_PUBLICATION_PREFIX.search(prefix):
                continue
            if month_first:
                month_name, day_text, year_text = match.group(1), match.group(2), match.group(3)
            else:
                day_text, month_name, year_text = match.group(1), match.group(2), match.group(3)
            parsed = _calendar_date(year_text, month_name, day_text)
            if parsed:
                found.append((match.start(), parsed))
    if not found:
        return None
    found.sort(key=lambda item: item[0])
    return found[0][1]


def _calendar_date(year_text: str, month_name: str, day_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)


def _is_download(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
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


def _visible(page_html: str) -> str:
    return _HIDDEN.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_html: str) -> str:
    return _clean_text(page_html)


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
