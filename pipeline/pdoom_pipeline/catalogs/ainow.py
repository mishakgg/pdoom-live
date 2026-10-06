"""Metadata catalog of public AI Now Institute pages.

Rows keep a title, publisher, canonical URL, date, and rights label for official
HTML pages on ainowinstitute.org. Page bodies and PDFs are not stored. A date
the page does not state stays unknown. Updated times, modified times, and
copyright years are not publication dates. Rights stay unknown unless the page
states CC0, CC BY, or CC BY-SA and does not also state a restricted deed.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen is a
word boundary, so CC BY does not match CC BY-NC. A Creative Commons licences
index URL is not itself a copying licence. The Public Domain Mark is not CC0.
A public page, a copyright notice, All rights reserved, or a terms link is not
a licence. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ainow_pages"
CATALOG_FILENAME = "ainow_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "ainowinstitute.org"
PUBLISHER = "AI Now Institute"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "chart",
        "content",
        "description_text",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "pdf",
        "pdoom",
        "p_doom",
        "probability",
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = ("article:published_time", "citation_publication_date")
_TOP_PAGES = frozenset(
    {
        "2023-landscape",
        "about",
        "ai-nationalisms",
        "careers",
        "collections",
        "contact-us",
        "donate",
        "frequent-contributors",
        "lessons-from-the-fda-for-ai",
        "our-work",
        "people-page",
        "privacy-policy",
        "redirecting-europes-ai-industrial-policy",
        "terms-conditions",
    }
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
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEG = r"(?:[a-z0-9]|%[0-9a-f]{2})+(?:-(?:[a-z0-9]|%[0-9a-f]{2})+)*"
_PATH = re.compile(
    rf"^(?:/"
    rf"|/(?:{'|'.join(sorted(_TOP_PAGES))})"
    rf"|/research-areas(?:/{_SEG})?"
    rf"|/publications(?:/{_SEG}){{0,2}}"
    rf"|/collection/{_SEG}"
    rf"|/series/{_SEG}"
    rf")$"
)
_URL = re.compile(r"^(https)://([^/?#@\s]+)([^?#]*)(?:\?([^#]*))?(?:#(.*))?$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_SITE_SUFFIX = re.compile(r"(?i)\s+(?:[-|]|–|—)\s+AI Now Institute\s*$")
_ARCHIVES_SUFFIX = re.compile(r"(?i)\s+Archives$")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# Longer deeds are listed first so CC BY does not succeed inside CC BY-NC.
_CC_DEED = re.compile(
    r"(?i)(?<![a-z0-9])cc(?:"
    r"[\s-]*0"
    r"|[\s-]*by[\s-]*nc[\s-]*sa"
    r"|[\s-]*by[\s-]*nc[\s-]*nd"
    r"|[\s-]*by[\s-]*nc"
    r"|[\s-]*by[\s-]*nd"
    r"|[\s-]*by[\s-]*sa"
    r"|[\s-]*by"
    r")(?![a-z0-9])"
)
_ATTR_RESTRICTED = re.compile(
    r"(?i)creative\s+commons\s+attribution[\s-]*(?:non[\s-]*commercial|no[\s-]*derivatives?|no[\s-]*derivs?)"
)
_ATTR_SHARE_ALIKE = re.compile(r"(?i)creative\s+commons\s+attribution[\s-]*share[\s-]*alike")
_ATTR_BY = re.compile(
    r"(?i)creative\s+commons\s+attribution(?![\s-]*(?:non|no[\s-]*deriv|share))"
)
_CC0_TEXT = re.compile(
    r"(?i)(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
    r"|creative\s+commons\s+(?:public\s+domain\s+)?zero\b"
    r"|public\s+domain\s+zero\b"
)
# Specific deeds only. creativecommons.org/licenses/ by itself is not enough.
_RESTRICTED_URL = re.compile(
    r"(?i)creativecommons\.org/licenses/by-nc(?:-sa|-nd)?(?:/|$|[?#])"
    r"|creativecommons\.org/licenses/by-nd(?:/|$|[?#])"
)
_PERMISSIVE_URL = re.compile(
    r"(?i)creativecommons\.org/licenses/by-sa(?:/|$|[?#])"
    r"|creativecommons\.org/licenses/by(?:/|$|[?#])"
    r"|creativecommons\.org/publicdomain/zero(?:/|$|[?#])"
)
_PERMISSIVE_TOKENS = frozenset({"cc0", "ccby", "ccbysa"})
_RESTRICTED_PREFIXES = ("ccbync", "ccbynd")


class CatalogError(ValueError):
    """A catalog row or page failed the AI Now Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_ainow_host(hostname: str) -> bool:
    """True only for the official ainowinstitute.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` means the page states CC0, CC BY, or CC BY-SA and does
    not also state CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND. A by-nc URL
    stays unknown even when its anchor text says CC BY. The Public Domain Mark
    is not CC0.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    pieces: list[str] = []
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            pieces.append(raw.replace("\\/", "/"))
    visible = _without_hidden(page_text)
    pieces.append(visible)
    pieces.extend(_meta_values(visible, _LICENSE_META))
    permissive = False
    restricted = False
    for piece in pieces:
        allows, limits = _deed_flags(piece)
        permissive = permissive or allows
        restricted = restricted or limits
    if restricted or not permissive:
        return RIGHTS_UNKNOWN
    return RIGHTS_CREATIVE_COMMONS


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Modified, updated, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    metas = _metas(page_text)
    for key in _PUBLISHED_META:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in ("og:title", "citation_title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    visible = _without_hidden(page_html)
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if _usable_title(title):
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if _usable_title(title) and len(title) <= 160:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    publisher = _clean_text(_metas(page_html).get("og:site_name", ""))
    if publisher != PUBLISHER:
        raise CatalogError("publisher is required")
    return publisher


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical on another path is not substituted.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return validate_entry(
        {
            "title": title_from_page(page_html),
            "publisher": publisher_from_page(page_html),
            "canonical_url": confirmed_url(page_html, page_url),
            "date": date_from_page(page_html),
            "rights": rights_from_page(page_html),
        }
    )


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    joined = _join_url(live, href)
    if not joined:
        return live
    try:
        declared = validate_canonical_url(joined)
    except CatalogError:
        return live
    if _same_page(declared, live):
        return declared
    return live


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip() or description != description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document["runner_wired"] is not False:
        raise CatalogError("runner_wired must be false")
    entries = document["entries"]
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
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
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https ainowinstitute.org page")
    parts = _split_url(url)
    if parts is None:
        raise CatalogError(f"canonical URL must be an https ainowinstitute.org page: {url}")
    _scheme, host, path = parts
    authority = url[len("https://") :].split("/", 1)[0]
    if authority != OFFICIAL_HOST or not official_ainow_host(host) or not _official_path(path):
        raise CatalogError(f"canonical URL must be an https ainowinstitute.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _official_path(path: str) -> bool:
    lowered = path.casefold()
    if (
        ".." in lowered
        or "%2e%2e" in lowered
        or "%2f" in lowered
        or "%5c" in lowered
        or "\\" in path
        or "//" in path
        or lowered.endswith(_DOWNLOAD_SUFFIXES)
    ):
        return False
    return _PATH.fullmatch(lowered) is not None


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


def _same_page(left: str, right: str) -> bool:
    a = _split_url(left)
    b = _split_url(right)
    if a is None or b is None:
        return False
    return a[1] == b[1] and a[2].rstrip("/") == b[2].rstrip("/")


def _split_url(url: str) -> tuple[str, str, str] | None:
    if not isinstance(url, str) or not url or url != url.strip():
        return None
    match = _URL.fullmatch(url)
    if match is None:
        return None
    scheme, authority, path, query, fragment = match.groups()
    if query is not None or fragment is not None or ":" in authority or "@" in authority:
        return None
    host = authority.casefold().rstrip(".")
    if not path:
        return None
    return scheme, host, path


def _join_url(base: str, href: str) -> str:
    raw = unescape(href).strip()
    if not raw or raw.startswith(("#", "mailto:", "javascript:")):
        return ""
    if raw.startswith("https://") or raw.startswith("http://"):
        return raw.split("#", 1)[0].split("?", 1)[0]
    parts = _split_url(base)
    if parts is None:
        return ""
    _scheme, host, path = parts
    if raw.startswith("//"):
        return _join_url(base, "https:" + raw)
    if raw.startswith("/"):
        target = raw.split("#", 1)[0].split("?", 1)[0]
        return f"https://{host}{target}"
    directory = path.rsplit("/", 1)[0] or ""
    return f"https://{host}{directory}/{raw.split('#', 1)[0].split('?', 1)[0]}"


def _deed_flags(value: str) -> tuple[bool, bool]:
    text = _normalize_dashes(value)
    restricted = _RESTRICTED_URL.search(text) is not None or _ATTR_RESTRICTED.search(text) is not None
    permissive = (
        _PERMISSIVE_URL.search(text) is not None
        or _ATTR_SHARE_ALIKE.search(text) is not None
        or _ATTR_BY.search(text) is not None
        or _CC0_TEXT.search(text) is not None
    )
    for match in _CC_DEED.finditer(text):
        token = re.sub(r"[^a-z0-9]", "", match.group(0).casefold())
        if token.startswith(_RESTRICTED_PREFIXES):
            restricted = True
        elif token in _PERMISSIVE_TOKENS:
            permissive = True
    return permissive, restricted


def _normalize_dashes(value: str) -> str:
    return (
        value.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value) if "<" in value else value)
    text = _normalize_dashes(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    text = _SITE_SUFFIX.sub("", text).strip()
    return _ARCHIVES_SUFFIX.sub("", text).strip()


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() != PUBLISHER.casefold()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(_without_hidden(page_html)):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(_without_hidden(page_html)):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
