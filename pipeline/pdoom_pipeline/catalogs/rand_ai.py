"""Metadata catalog of public RAND pages on AI safety, policy, or governance.

Each stored URL is a public www.rand.org HTML page. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Publisher is RAND. Rights is unknown unless the page states a reuse licence.
creative_commons means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. A public page, a copyright notice,
or a permissions link is not a licence. A page that does not state a
publication date keeps the date unknown. Updated, modified, and copyright
years are not publication dates. The live URL is stored as confirmed; a
different rel=canonical does not replace it. This module does not fetch and
it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "rand_ai_pages"
CATALOG_FILENAME = "rand_ai_pages.json"
PUBLISHER = "RAND"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
ALLOWED_RIGHTS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
UNKNOWN_DATE = "unknown"
RAND_HOST = "www.rand.org"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMERIC_DAY = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(r"(?is)<script\b[^>]*application/ld\+json[^>]*>(.*?)</script>")
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>|<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_SPAN = re.compile(r"(?is)<span\b[^>]*>.*?</span>")
_TYPE_DATE = re.compile(r"(?is)<div\b[^>]*\bclass\s*=\s*(['\"])[^'\"]*\btype-date\b[^'\"]*\1[^>]*>(.*?)</div>")
_P_DATE = re.compile(r"(?is)<p\b[^>]*\bclass\s*=\s*(['\"])[^'\"]*\bdate\b[^'\"]*\1[^>]*>(.*?)</p>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s+(?:[-–—|]\s*RAND(?:\s+Corporation)?)\s*$")
_HUMAN_DATE = re.compile(
    r"\b(?:published\s+)?([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b",
    re.IGNORECASE,
)
_PUBLICATION_DATE_KEYS = (
    "citation_publication_date",
    "citation_online_date",
    "article:published_time",
)
_CONTENT_PREFIXES = (
    "/topics/",
    "/pubs/research_reports/",
    "/pubs/research_briefs/",
    "/pubs/commentary/",
    "/pubs/perspectives/",
    "/pubs/external_publications/",
    "/pubs/working_papers/",
    "/pubs/testimonies/",
    "/pubs/articles/",
    "/global-and-emerging-risks/",
    "/education-employment-infrastructure/",
    "/randeurope/",
    "/congress/",
)
_DISALLOWED_PREFIXES = (
    "/test/",
    "/alumni/bulletin",
    "/search.html",
    "/search/advanced-search.html",
    "/site_info/robots1.html",
    "/site_info/robots2.html",
    "/about/people/",
    "/staff/",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".bmp",
    ".avif",
    ".tif",
    ".tiff",
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
# Longer codes are listed first so by-nc is not read as by.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?=/|\b|[?#]|$)"
)
_CC_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"\b(?:cc[-\s]?)?by-nc-nd\b")),
    ("by-nc-sa", re.compile(r"\b(?:cc[-\s]?)?by-nc-sa\b")),
    ("by-nc", re.compile(r"\b(?:cc[-\s]?)?by-nc\b")),
    ("by-nd", re.compile(r"\b(?:cc[-\s]?)?by-nd\b")),
    ("by-sa", re.compile(r"\b(?:cc[-\s]?)?by-sa\b")),
    ("zero", re.compile(r"\bcc0\b|\bcreative commons zero\b|\bcc zero\b")),
    ("by", re.compile(r"\bcc[-\s]by\b")),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_NONCOMMERCIAL = re.compile(r"non-?commercial")
_NODERIV = re.compile(r"no-?deriv")
_SHAREALIKE = re.compile(r"share-?alike")
_ATTRIBUTION = re.compile(r"\battribution\b")
_CC_MENTION = re.compile(r"creative commons|\bcc[-\s]by\b|\bcc0\b")


class CatalogError(ValueError):
    """A catalog row or page failed the RAND page rules."""


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
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError(f"canonical URL is not a public RAND page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != RAND_HOST
        or host != RAND_HOST
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
        raise CatalogError(f"canonical URL is not a public RAND page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == RAND_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons or unknown.

    creative_commons means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
    CC BY-NC-SA, and CC BY-NC-ND stay unknown. A cc-by or Creative Commons
    substring is not CC BY when NonCommercial, NoDerivatives, or ShareAlike
    follows; ShareAlike alone is CC BY-SA. Script, style, and comment text
    does not count. A copyright notice, a public page, or a link to terms or
    permissions is not a licence. The licence sentence itself is not returned.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _strip_hidden(page_text)
    plain = _plain_text(visible).casefold()
    codes = _cc_codes_in_text(plain)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold().split()
        if "license" not in rel and "licence" not in rel:
            continue
        codes.update(_cc_codes_in_text(attrs.get("href", "")))
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dateModified, rand-teaser-date,
    updated labels, and a copyright year are not publication dates. A date in
    the URL is not a publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_strip_hidden(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _numeric_day(metas.get(key, ""))
        if parsed:
            return parsed
    visible = _visible_publication_date(page_html)
    if visible:
        return visible
    for raw in _jsonld_date_published(page_html):
        parsed = _numeric_day(raw)
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _strip_hidden(page_html)
    metas = _metas(visible)
    citation = _clean_title(metas.get("citation_title", ""))
    if citation:
        return citation
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    social = _clean_title(metas.get("og:title", ""))
    if social:
        return social
    raise CatalogError("title is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the page text. ``page_url`` is the live URL
    that was fetched. A rel=canonical pointing somewhere else is not used.
    The publisher is RAND even when the page names a person.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": PUBLISHER,
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _official_path(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    if not lowered.endswith(".html"):
        return False
    if any(lowered.endswith(suffix) for suffix in _DOWNLOAD_SUFFIXES):
        return False
    if "jcr:content" in lowered or "_jcr_content" in lowered or "repec" in lowered:
        return False
    if lowered.endswith("/staff.html"):
        return False
    if any(lowered == prefix.rstrip("/") or lowered.startswith(prefix) for prefix in _DISALLOWED_PREFIXES):
        return False
    return any(lowered.startswith(prefix) for prefix in _CONTENT_PREFIXES)


def _cc_codes_in_text(plain: str) -> set[str]:
    """Return CC licence codes. A cc-by prefix is not CC BY when a qualifier follows."""

    folded = plain.casefold().replace("–", "-").replace("—", "-")
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT_CODES:
        if pattern.search(folded):
            codes.add(code)
    if _CC_MENTION.search(folded) is None and "creativecommons.org" not in folded:
        return codes
    noncommercial = _NONCOMMERCIAL.search(folded) is not None
    noderiv = _NODERIV.search(folded) is not None
    sharealike = _SHAREALIKE.search(folded) is not None
    if noncommercial and noderiv:
        codes.add("by-nc-nd")
    elif noncommercial and sharealike:
        codes.add("by-nc-sa")
    elif noncommercial:
        codes.add("by-nc")
    elif noderiv:
        codes.add("by-nd")
    elif sharealike:
        codes.add("by-sa")
    elif _ATTRIBUTION.search(folded):
        codes.add("by")
    if codes & _RESTRICTED_CC:
        codes.discard("by")
    elif "by-sa" in codes:
        codes.discard("by")
    return codes


def _visible_publication_date(page_html: str) -> str | None:
    visible = _strip_hidden(page_html)
    for tag in _SPAN.findall(visible):
        attrs = _attrs(tag)
        classes = set(attrs.get("class", "").split())
        if "published" not in classes:
            continue
        inner = re.search(r"(?is)>(.*)</span>\Z", tag)
        text = _plain_text(inner.group(1) if inner else "")
        parsed = _human_day(text)
        if parsed:
            return parsed
    for block in _TYPE_DATE.findall(visible):
        inner = block[1] if isinstance(block, tuple) else block
        for date_block in _P_DATE.findall(inner):
            text = date_block[1] if isinstance(date_block, tuple) else date_block
            parsed = _human_day(_plain_text(text))
            if parsed:
                return parsed
    return None


def _human_day(text: str) -> str | None:
    if not text:
        return None
    folded = text.casefold()
    if re.search(r"\b(updated|update|modified|modification|copyright)\b", folded):
        return None
    match = _HUMAN_DATE.search(text)
    if match is None:
        return None
    month = _MONTHS.get(match.group(1).casefold())
    if month is None:
        return None
    try:
        parsed = date(int(match.group(3)), month, int(match.group(2)))
    except ValueError:
        return None
    return parsed.isoformat()


def _jsonld_date_published(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        text = block.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            found.extend(_DATE_PUBLISHED.findall(text))
            continue
        _collect_date_published(payload, found)
    return found


def _collect_date_published(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_date_published(item, found)
        return
    if not isinstance(payload, dict):
        return
    if "@graph" in payload:
        _collect_date_published(payload["@graph"], found)
    published = payload.get("datePublished")
    if isinstance(published, str):
        found.append(published)


def _numeric_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    match = _NUMERIC_DAY.match(text)
    if match is None:
        return None
    try:
        parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None
    return parsed.isoformat()


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _clean_title(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    return _SITE_SUFFIX.sub("", text).strip()


def _strip_hidden(page_html: str) -> str:
    without_comments = _COMMENT.sub(" ", page_html)
    return _HIDDEN.sub(" ", without_comments)


def _plain_text(page_html: str) -> str:
    text = _TAG.sub(" ", page_html)
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


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
