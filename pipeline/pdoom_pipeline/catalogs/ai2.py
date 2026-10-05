"""Metadata catalog of public Allen Institute for AI pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights is ``creative_commons`` only when the page states CC0, CC BY, or
CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown.
A public page, a copyright notice, an all-rights-reserved line, or a terms
link is not a licence. A page that does not state a publication date keeps
the date unknown. Updated, modified, and copyright years are not publication
dates. The live URL is stored as confirmed; a different rel=canonical does
not replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ai2_pages"
CATALOG_FILENAME = "ai2_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
AI2_HOST = "allenai.org"
WWW_HOST = "www.allenai.org"
OFFICIAL_HOSTS = frozenset({AI2_HOST, WWW_HOST})
PUBLISHER_NAME = "The Allen Institute for Artificial Intelligence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_P = re.compile(r"(?is)<p\b[^>]*>(.*?)</p>")
_NEXT_HEADING = re.compile(r"(?is)<h[2-6]\b")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_DISPLAY_DATE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{1,2}),\s+(\d{4})$",
    re.I,
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
    "dcterms.issued",
)
_BEFORE_DATE = re.compile(r"\b(updated|modified|copyright)\b", re.I)
_SITE_SUFFIXES = (
    " | Ai2",
    " | Allen Institute for AI",
    " | Allen Institute for Artificial Intelligence",
    " - Ai2",
    " – Ai2",
    " — Ai2",
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
_CC_URL = re.compile(
    r"(?i)(?:(?:https?:)?//)?(?:www\.)?creativecommons\.org/[a-z0-9_./~%-]+"
)
_CC_CODES = {
    "by": "cc-by",
    "by-sa": "cc-by-sa",
    "by-nc": "disallowed",
    "by-nd": "disallowed",
    "by-nc-sa": "disallowed",
    "by-nc-nd": "disallowed",
}
_ALLOWED_CC = frozenset({"cc0", "cc-by", "cc-by-sa"})
_MODIFIERS = frozenset({"nc", "nd", "sa", "noncommercial", "noderivatives", "sharealike"})
_NC_ND = frozenset({"nc", "nd", "noncommercial", "noderivatives"})
_SHARE_ALIKE = frozenset({"sa", "sharealike"})
_LICENSE_TAILS = frozenset(
    {"international", "unported", "licence", "license", "legalcode", "deed", "universal", "version"}
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title", "twitter:title")


class CatalogError(ValueError):
    """A catalog row or page failed the Allen Institute page rules."""


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
    if not isinstance(url, str) or not url or url != url.strip() or any(ch.isspace() for ch in url):
        raise CatalogError("canonical URL must be a public Allen Institute for AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() not in OFFICIAL_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Allen Institute for AI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in OFFICIAL_HOSTS and not hostname_is_blocked(host)


def stated_reuse_licences(page_text: str) -> frozenset[str]:
    """Return CC0, CC BY, or CC BY-SA licences the page itself states.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND are not returned.
    A bare "creative commons" or "cc-by" substring is not CC BY when
    NonCommercial, NoDerivatives, or ShareAlike follows. Script and style
    text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    found: set[str] = set()
    for match in _CC_URL.finditer(visible):
        family = _family_from_cc_url(unescape(match.group(0)))
        if family:
            found.add(family)
    for segment in _licence_segments(_plain_text(visible)):
        found.update(_families_in_segment(segment))
    return frozenset(name for name in found if name in _ALLOWED_CC)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons or unknown.

    creative_commons means the page states CC0, CC BY, or CC BY-SA.
    A public page, a copyright notice, an all-rights-reserved line, or a
    terms link is not a licence.
    """

    if stated_reuse_licences(page_text):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dcterms.modified, updated labels,
    and copyright years are not publication dates. A date on a later list of
    other works is not the page date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
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
    byline = _byline_date(visible)
    if byline:
        return byline
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
    plain = _plain_text(page_html)
    if PUBLISHER_NAME in plain:
        return PUBLISHER_NAME
    site = _metas(_visible_html(page_html)).get("og:site_name", "").strip()
    if site:
        cleaned = _clean_text(site)
        if cleaned:
            return cleaned
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
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
    if path in {"", "/"}:
        return True
    if ".." in path or "\\" in path or "//" in path or not path.startswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    if bare == "/api" or bare.startswith("/api/"):
        return False
    return True


def _byline_date(visible_html: str) -> str | None:
    """Use a date-only paragraph in the header, not a date later in the article.

    The first paragraph may be a short dek. A date inside that header is the
    publication date. Updated, modified, and copyright labels are not.
    """

    heading = _H1.search(visible_html)
    if heading is None:
        return None
    rest = visible_html[heading.end() :]
    stop = _NEXT_HEADING.search(rest)
    region = rest[: stop.start()] if stop else rest[:6000]
    seen = 0
    for match in _P.finditer(region):
        text = _clean_text(match.group(1))
        if not text:
            continue
        seen += 1
        parsed = _parse_display_date(text)
        if parsed is not None:
            before = _clean_text(region[: match.start()])
            if _BEFORE_DATE.search(before):
                return None
            return parsed
        if len(text) > 400 or seen >= 4:
            return None
    return None


def _parse_display_date(text: str) -> str | None:
    if _DATE.fullmatch(text):
        try:
            date.fromisoformat(text)
        except ValueError:
            return None
        return text
    match = _DISPLAY_DATE.fullmatch(text)
    if match is None:
        return None
    month = _MONTHS[match.group(1).casefold()]
    day = int(match.group(2))
    year = int(match.group(3))
    try:
        found = date(year, month, day)
    except ValueError:
        return None
    return found.isoformat()


def _family_from_cc_url(url: str) -> str | None:
    lowered = url.casefold()
    marker = "creativecommons.org/"
    index = lowered.find(marker)
    if index < 0:
        return None
    path = lowered[index + len(marker) :].split("?", 1)[0].split("#", 1)[0].strip("/")
    if path.startswith("publicdomain/zero"):
        return "cc0"
    if not path.startswith("licenses/"):
        return None
    code = path[len("licenses/") :].split("/", 1)[0]
    return _CC_CODES.get(code)


def _licence_segments(text: str) -> list[str]:
    normalized = text.casefold().replace("\xa0", " ")
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        normalized = normalized.replace(dash, "-")
    normalized = normalized.replace("non-commercial", "noncommercial")
    normalized = normalized.replace("non commercial", "noncommercial")
    normalized = normalized.replace("no-derivatives", "noderivatives")
    normalized = normalized.replace("no derivatives", "noderivatives")
    normalized = normalized.replace("share-alike", "sharealike")
    normalized = normalized.replace("share alike", "sharealike")
    normalized = re.sub(r"[.!;?,\n\r]+", " | ", normalized)
    normalized = re.sub(r"[^a-z0-9|]+", "-", normalized)
    segments: list[str] = []
    for piece in normalized.split("|"):
        segment = re.sub(r"-{2,}", "-", piece).strip("-")
        if segment:
            segments.append(segment)
    return segments


def _families_in_segment(segment: str) -> set[str]:
    parts = segment.split("-")
    found: set[str] = set()
    found.update(_token_families(parts))
    found.update(_prose_families(parts))
    return found


def _token_families(parts: list[str]) -> set[str]:
    found: set[str] = set()
    index = 0
    while index < len(parts):
        if parts[index] == "cc0":
            found.add("cc0")
            index += 1
            continue
        if parts[index] == "cc" and index + 1 < len(parts) and parts[index + 1] == "0":
            found.add("cc0")
            index += 2
            continue
        if parts[index] == "cc" and index + 1 < len(parts) and parts[index + 1] == "by":
            cursor = index + 2
            modifiers: list[str] = []
            while cursor < len(parts) and parts[cursor] in _MODIFIERS:
                modifiers.append(parts[cursor])
                cursor += 1
            if modifiers:
                found.add(_family_from_modifiers(modifiers))
                index = cursor
                continue
            if _bare_cc_by_accepted(parts, index, cursor):
                found.add("cc-by")
                index = cursor
                continue
        index += 1
    return found


def _prose_families(parts: list[str]) -> set[str]:
    found: set[str] = set()
    index = 0
    while index < len(parts) - 1:
        if parts[index] != "creative" or parts[index + 1] != "commons":
            index += 1
            continue
        cursor = index + 2
        kind: str | None = None
        if cursor < len(parts) and parts[cursor] in {"zero", "cc0"}:
            kind = "cc0"
            cursor += 1
        elif (
            cursor + 2 < len(parts)
            and parts[cursor] == "public"
            and parts[cursor + 1] == "domain"
            and parts[cursor + 2] == "dedication"
        ):
            kind = "cc0"
            cursor += 3
        if cursor < len(parts) and parts[cursor] == "attribution":
            if kind is None:
                kind = "cc-by"
            cursor += 1
        modifiers: list[str] = []
        while cursor < len(parts) and parts[cursor] in _MODIFIERS:
            modifiers.append(parts[cursor])
            cursor += 1
        if kind == "cc0" and not modifiers:
            found.add("cc0")
        elif kind == "cc-by" or modifiers:
            found.add(_family_from_modifiers(modifiers))
        index = max(cursor, index + 2)
    return found


def _family_from_modifiers(modifiers: list[str]) -> str:
    if any(modifier in _NC_ND for modifier in modifiers):
        return "disallowed"
    if any(modifier in _SHARE_ALIKE for modifier in modifiers):
        return "cc-by-sa"
    return "cc-by"


def _bare_cc_by_accepted(parts: list[str], cc_index: int, next_index: int) -> bool:
    if next_index >= len(parts) or _is_license_tail(parts[next_index]):
        return True
    if parts[next_index] in {"and", "or"} and _has_licence_context(parts, cc_index):
        return True
    return False


def _is_license_tail(token: str) -> bool:
    return token.isdigit() or token in _LICENSE_TAILS


def _has_licence_context(parts: list[str], cc_index: int) -> bool:
    window = parts[max(0, cc_index - 6) : cc_index]
    markers = {"licence", "license", "licensed", "licensing", "under", "terms"}
    return any(token in markers for token in window)


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


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible_html(page_text))


def _visible_html(page_text: str) -> str:
    return _HIDDEN.sub(" ", page_text)


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
