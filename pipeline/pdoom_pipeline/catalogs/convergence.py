"""Metadata catalog of public Convergence Analysis pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights is ``creative_commons`` only when the page states CC0, CC BY, or
CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown.
A copyright notice, an all-rights-reserved line, and a terms link are not
licences. Updated, modified, and copyright years are not publication dates.
A page that does not state a publication date keeps the date unknown. The
live URL is stored as confirmed; a different rel=canonical does not replace
it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "convergence_pages"
CATALOG_FILENAME = "convergence_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "www.convergenceanalysis.org"
SITE_NAME = "Convergence Analysis"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
_SITE_H1_MAX = 60

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_TAG = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>|<[^>]+>")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_INNER_TEXT = re.compile(r"(?is)>([^<]+)<")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_FRAMER_DATE = re.compile(
    r"""(?is)<([a-z0-9]+)\b[^>]*\bdata-framer-name\s*=\s*["']Date["'][^>]*>(.*?)</\1>"""
)
_FULL_DATE = re.compile(
    r"(?i)\b(?P<month>January|February|March|April|May|June|July|August|"
    r"September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|"
    r"Sept|Oct|Nov|Dec)\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{4})\b"
)
_COPYRIGHT_LINE = re.compile(
    r"(?i)^copyright\s*(?:©|\(c\))\s*\d{4}\s+(.+)$"
)
_PUBLISHED_BY = re.compile(r"(?i)\bpublished by\s+([^,.;:]{2,120})")
_RIGHTS_RESERVED = re.compile(r"(?i)\s*[,.]?\s*all rights reserved\.?$")
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_SITE_SUFFIXES = (
    " | Convergence Analysis",
    " - Convergence Analysis",
    " – Convergence Analysis",
    " — Convergence Analysis",
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
# Longer licences are listed first so CC BY-NC-SA is not read as CC BY or CC BY-SA.
_CC_MENTION = re.compile(
    r"(?i)"
    r"creativecommons\.org/publicdomain/zero/\d+\.\d+|"
    r"creativecommons\.org/licenses/by-nc-sa/\d+\.\d+|"
    r"creativecommons\.org/licenses/by-nc-nd/\d+\.\d+|"
    r"creativecommons\.org/licenses/by-nc/\d+\.\d+|"
    r"creativecommons\.org/licenses/by-nd/\d+\.\d+|"
    r"creativecommons\.org/licenses/by-sa/\d+\.\d+|"
    r"creativecommons\.org/licenses/by/\d+\.\d+|"
    r"creative commons attribution-noncommercial-sharealike|"
    r"creative commons attribution-noncommercial-noderivatives|"
    r"creative commons attribution-noncommercial-noderivs|"
    r"creative commons attribution-noncommercial|"
    r"creative commons attribution-noderivatives|"
    r"creative commons attribution-noderivs|"
    r"creative commons attribution-sharealike|"
    r"creative commons attribution|"
    r"creative commons zero|"
    r"\bcc\s*0\b|"
    r"\bcc[-\s]?by-nc-sa\b|"
    r"\bcc[-\s]?by-nc-nd\b|"
    r"\bcc[-\s]?by-nc\b|"
    r"\bcc[-\s]?by-nd\b|"
    r"\bcc[-\s]?by-sa\b|"
    r"\bcc[-\s]?by\b"
)
_ALLOWED_CC = frozenset({"cc0", "by", "by-sa"})


class CatalogError(ValueError):
    """A catalog row or page failed the Convergence Analysis page rules."""


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
        raise CatalogError("canonical URL must be a public Convergence Analysis page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    decoded = unquote(path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or host != OFFICIAL_HOST
        or hostname_is_blocked(host)
        or ".." in decoded
        or "\\" in decoded
        or "//" in path
        or "%" in decoded
        or _encoded_separator(path)
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Convergence Analysis page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons only for a stated CC0, CC BY, or CC BY-SA licence.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. Script and
    style text does not count. A copyright notice, an all-rights-reserved
    line, a terms link, or the bare word licence does not state a reuse licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    # Phrase checks use visible text. URL checks keep hrefs, which tag
    # stripping would drop. Script and style blocks are already removed.
    haystack = _plain_text(page_text) + "\n" + visible
    allowed = False
    for match in _CC_MENTION.finditer(haystack.casefold()):
        kind = _cc_kind(match.group(0))
        if kind == "denied":
            return RIGHTS_UNKNOWN
        if kind == "allowed":
            allowed = True
    if allowed:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, last-updated lines, and copyright
    years are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    plain = _clean_text(visible)
    labeled = _originally_published(plain)
    if labeled:
        return labeled
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key))
        if parsed:
            return parsed
    labeled = _published_label(visible)
    if labeled:
        return labeled
    labeled = _published_time(visible)
    if labeled:
        return labeled
    labeled = _single_stated_date(visible)
    if labeled:
        return labeled
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    title = ""
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                break
    if not title:
        title_tag = _TITLE.search(visible)
        if title_tag:
            title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
    headings = _headings(visible)
    if title == SITE_NAME:
        for heading in headings:
            if heading != SITE_NAME and len(heading) <= _SITE_H1_MAX:
                return heading
    specific = _series_page_heading(title, headings)
    if specific:
        return specific
    if title:
        return title
    if headings:
        return headings[0]
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    for raw in _INNER_TEXT.findall(visible):
        holder = _copyright_holder(_clean_text(raw))
        if holder:
            return holder
    published = _PUBLISHED_BY.search(_clean_text(visible))
    if published:
        name = _RIGHTS_RESERVED.sub("", published.group(1)).strip(" .")
        if name and name.casefold() not in {"the author", "the authors"}:
            return name
    site = _metas(visible).get("og:site_name", "").strip()
    if site and site.casefold() not in {"gov.uk", OFFICIAL_HOST}:
        return _clean_text(site)
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
    lowered = unquote(path).lower()
    return not lowered.endswith(_DOWNLOAD_SUFFIXES)


def _encoded_separator(path: str) -> bool:
    lowered = path.lower()
    return "%2f" in lowered or "%5c" in lowered or "%00" in lowered


def _series_page_heading(title: str, headings: list[str]) -> str:
    """Use the content heading when the title tag only repeats a series banner.

    Report sections on this site repeat one banner heading twice and put the
    page heading third. A later heading on a long article is a section, so
    this only applies when those three headings are the whole page.
    """

    if len(headings) != 3 or headings[0] != headings[1]:
        return ""
    heading = headings[2]
    if not heading or heading in {headings[0], title}:
        return ""
    banner = headings[0]
    if title == banner or banner.endswith(title) or (title and title.endswith(banner)):
        return heading
    if "appendix" in title.casefold() and "appendix" in banner.casefold():
        return heading
    return ""


def _headings(visible: str) -> list[str]:
    headings: list[str] = []
    for match in _H1.finditer(visible):
        heading = _clean_text(_TAG.sub(" ", match.group(1)))
        if heading:
            headings.append(heading)
    return headings


def _originally_published(plain: str) -> str:
    match = re.search(r"(?i)originally published(.{0,80})", plain)
    if match is None:
        return ""
    return _date_in(match.group(1))


def _published_label(visible: str) -> str:
    for raw in _INNER_TEXT.findall(visible):
        text = _clean_text(raw)
        match = re.fullmatch(r"(?i)published\s+(.+)", text)
        if match is None:
            continue
        found = _date_in(match.group(1))
        if found and _date_in(text) == found and not re.search(r"(?i)updat|modif", text):
            return found
    return ""


def _published_time(visible: str) -> str:
    for match in _TIME.finditer(visible):
        before = _clean_text(visible[max(0, match.start() - 240) : match.start()])[-80:]
        lowered = before.casefold()
        if "updat" in lowered or "modif" in lowered or "published" not in lowered:
            continue
        attrs = _attrs(match.group(1))
        parsed = _iso_prefix(attrs.get("datetime"))
        if parsed:
            return parsed
        found = _date_in(_clean_text(match.group(2)))
        if found:
            return found
    return ""


def _single_stated_date(visible: str) -> str:
    found: list[str] = []
    for match in _FRAMER_DATE.finditer(visible):
        text = _clean_text(match.group(2))
        dated = _FULL_DATE.fullmatch(text)
        if dated is None or re.search(r"(?i)updat|modif", text):
            continue
        parsed = _calendar_date(dated.group("month"), dated.group("day"), dated.group("year"))
        if not parsed:
            continue
        before = _clean_text(visible[max(0, match.start() - 160) : match.start()])[-60:]
        if re.search(r"(?i)updat|modif", before):
            continue
        found.append(parsed)
    if len(found) == 1:
        return found[0]
    return ""


def _date_in(text: str) -> str:
    if not isinstance(text, str):
        return ""
    match = _FULL_DATE.search(text)
    if match:
        return _calendar_date(match.group("month"), match.group("day"), match.group("year"))
    iso = _DATE_PREFIX.match(text.strip())
    if iso is None:
        located = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if located is None:
            return ""
        iso_text = located.group(1)
    else:
        iso_text = iso.group(1)
    try:
        date.fromisoformat(iso_text)
    except ValueError:
        return ""
    return iso_text


def _calendar_date(month: str, day: str, year: str) -> str:
    try:
        parsed = date(int(year), _MONTHS[month.lower()], int(day))
    except (KeyError, TypeError, ValueError):
        return ""
    return parsed.isoformat()


def _iso_prefix(value: object) -> str:
    if not isinstance(value, str):
        return ""
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return ""
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
    except ValueError:
        return ""
    return match.group(1)


def _copyright_holder(text: str) -> str:
    match = _COPYRIGHT_LINE.match(text)
    if match is None:
        return ""
    name = _RIGHTS_RESERVED.sub("", match.group(1)).strip(" .")
    if not name or name.casefold() == "copyright":
        return ""
    return name


def _cc_kind(mention: str) -> str:
    text = mention.casefold().replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    if "publicdomain/zero/" in text or "creative commons zero" in text or re.fullmatch(r"cc\s*0", text):
        return "allowed"
    if "licenses/by-nc-sa/" in text or "licenses/by-nc-nd/" in text or "licenses/by-nc/" in text or "licenses/by-nd/" in text:
        return "denied"
    if "licenses/by-sa/" in text or "licenses/by/" in text:
        return "allowed"
    if "noncommercial" in text or "noderiv" in text:
        return "denied"
    if "sharealike" in text:
        return "allowed"
    if "creative commons attribution" in text:
        return "allowed"
    compact = re.sub(r"[\s-]+", "-", text)
    if compact in {"cc-by-nc-sa", "cc-by-nc-nd", "cc-by-nc", "cc-by-nd"}:
        return "denied"
    if compact in {"cc-by-sa", "cc-by", "cc-0", "cc0"}:
        return "allowed"
    return ""


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
    return _clean_text(_visible(page_text))


def _visible(page_html: str) -> str:
    return _HIDDEN.sub(" ", page_html)


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
