"""Metadata catalog of public Stanford CRFM pages on crfm.stanford.edu.

Rows keep a title, publisher, canonical URL, date, and rights label. Page text
and PDFs are not stored. A date the page does not state stays unknown.
Updated, modified, and copyright years are not publication dates. Rights stay
unknown unless the page states CC0, CC BY, or CC BY-SA and does not also state
a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A hyphen is a word boundary, so CC BY does not match CC BY-NC. A
public page, a copyright notice, or a terms link is not a licence. Stanford
HAI pages are a separate catalog and are not stored here. This catalog is not
a collector and it does not fetch.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "crfm_pages"
CATALOG_FILENAME = "crfm_pages.json"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "crfm.stanford.edu"
PUBLISHER = "Stanford Center for Research on Foundation Models"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "chart",
        "content",
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
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
        "datepublished",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_YEAR = re.compile(r"^\d{4}$")
_URL = re.compile(r"^https://([a-z0-9.-]+)(/[a-zA-Z0-9._/-]*)?$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_HREF_TAG = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_H2 = re.compile(r"(?is)<h2\b([^>]*)>(.*?)</h2>")
_BLOG_TITLE = re.compile(
    r'(?is)<h2\b[^>]*class="[^"]*\bblog-title\b[^"]*"[^>]*>(.*?)</h2>'
)
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s*[|\-–—]\s*stanford crfm\s*$")
_SITE_TITLES = frozenset({"stanford crfm", "stanford center for research on foundation models"})
_REJECT_TITLES = frozenset({"404", "page not found", "page not found :("})
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
    ".js",
    ".css",
    ".mp3",
    ".mp4",
    ".gz",
    ".tgz",
    ".ico",
    ".woff",
    ".woff2",
)
_ASSET_MARKERS = ("/static/", "/assets/", "/css/", "/js/", "/img/")
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
_LABELED_PUBLISHED = re.compile(
    r"(?i)(?<![a-z])(?:date\s+)?(?:published|posted)\s*:?\s+"
    r"(?:(?P<iso>\d{4}-\d{2}-\d{2})\b|"
    r"(?P<month>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})\b)"
)
# Longer deeds are listed first. A hyphen is a word boundary, so CC BY must
# not match CC BY-NC, CC BY-ND, or CC BY-SA. by-sa is permissive on its own.
_RESTRICTED_TEXT = re.compile(
    r"(?i)(?:"
    r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
    r"|\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
    r"|\bcc[\s-]*by[\s-]*nc\b"
    r"|\bcc[\s-]*by[\s-]*nd\b"
    r"|creative commons attribution[\s-]+non[\s-]?commercial"
    r"|creative commons attribution[\s-]+no[\s-]?deriv"
    r")"
)
_PERMISSIVE_TEXT = re.compile(
    r"(?i)(?:"
    r"\bcc0\b"
    r"|\bcc[\s-]*zero\b"
    r"|creative commons (?:cc0|zero)\b"
    r"|creative commons attribution[\s-]+share[\s-]?alike\b"
    r"|creative commons attribution(?![\s-]*(?:share[\s-]?alike|non[\s-]?commercial|no[\s-]?deriv))"
    r"|\bcc[\s-]*by[\s-]*sa\b"
    r"|\bcc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)\b"
    r")"
)
_RESTRICTED_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"licenses/(?:by-nc-nd|by-nc-sa|by-nc|by-nd)(?![\w-])"
)
_PERMISSIVE_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/by-sa(?![\w-])|licenses/by(?![\w-])|publicdomain/zero(?![\w-]))"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Stanford CRFM page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_crfm_host(hostname: str) -> bool:
    """True only for the official crfm.stanford.edu host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND.
    A by-nc URL stays unknown even when the anchor text says CC BY. Public
    Domain Mark is not CC0. A generic creativecommons.org/licenses/ URL is not
    a permissive deed. Script, style, and comment text do not count.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    flags: set[str] = set()
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            flags |= _cc_flags(raw.replace("\\/", "/"))
    visible = _without_hidden(page_text)
    for href in _hrefs(visible):
        flags |= _cc_flags(href)
    for content in _meta_values(visible, _LICENSE_META):
        flags |= _cc_flags(content)
    # Anchor text is the label of its href. A by-nc URL stays unknown even
    # when the label says CC BY, and a Public Domain Mark URL is not CC0.
    flags |= _cc_flags(_plain(_strip_deed_anchor_text(visible)))
    if "restricted" in flags:
        return RIGHTS_UNKNOWN
    if "permissive" in flags:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            parsed = _iso_prefix(match.group(1))
            if parsed:
                return parsed
    for raw in _meta_values(page_text, _PUBLISHED_META):
        parsed = _iso_prefix(raw.strip())
        if parsed:
            return parsed
    plain = _plain(_without_hidden(page_text))
    for match in _LABELED_PUBLISHED.finditer(plain):
        if match.group("iso"):
            parsed = _iso_prefix(match.group("iso"))
        else:
            parsed = _calendar_date(match.group("month"), match.group("day"), match.group("year"))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str, *, page_url: str = "") -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    heading = _BLOG_TITLE.search(visible)
    if heading:
        title = _clean_title(heading.group(1))
        if _usable_title(title):
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    section = _single_section_heading(visible)
    if section:
        return section
    nav = _nav_label(visible, page_url)
    if _usable_title(nav):
        return nav
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title and title.casefold() not in _REJECT_TITLES:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the center name. Author bylines are not the publisher."""
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return PUBLISHER


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    record = {
        "title": title_from_page(page_html, page_url=page_url),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_join(live, href.strip()))
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
        raise CatalogError("catalog fields must be catalog_id, description, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
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
    if not isinstance(url, str) or not url or url != url.strip() or not url.startswith("https://"):
        raise CatalogError("canonical URL must be an https crfm.stanford.edu page")
    if any(mark in url for mark in ("%", "\\", "@", "?", "#")):
        raise CatalogError(f"canonical URL must be an https crfm.stanford.edu page: {url}")
    match = _URL.fullmatch(url)
    if match is None:
        raise CatalogError(f"canonical URL must be an https crfm.stanford.edu page: {url}")
    host = match.group(1)
    path = match.group(2) or ""
    if (
        not official_crfm_host(host)
        or host != OFFICIAL_HOST
        or not path
        or ".." in path
        or "//" in path
        or _is_download(path)
        or _is_asset(path)
    ):
        raise CatalogError(f"canonical URL must be an https crfm.stanford.edu page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
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


def _same_page(left: str, right: str) -> bool:
    left_match = _URL.fullmatch(left)
    right_match = _URL.fullmatch(right)
    if left_match is None or right_match is None:
        return False
    left_path = (left_match.group(2) or "").rstrip("/")
    right_path = (right_match.group(2) or "").rstrip("/")
    return left_match.group(1) == right_match.group(1) and left_path == right_path


def _join(base: str, href: str) -> str:
    if href.startswith("https://") or href.startswith("http://"):
        return href
    if href.startswith("//"):
        return "https:" + href
    match = _URL.fullmatch(base)
    if match is None:
        return href
    host = match.group(1)
    if href.startswith("/"):
        return f"https://{host}{href}"
    path = match.group(2) or "/"
    directory = path.rsplit("/", 1)[0]
    return f"https://{host}{directory}/{href}"


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


def _usable_title(title: str) -> bool:
    if not title or len(title) > MAX_FIELD_CHARS:
        return False
    folded = title.casefold()
    if folded in _SITE_TITLES or folded in _REJECT_TITLES or folded == PUBLISHER.casefold():
        return False
    if _YEAR.fullmatch(title):
        return False
    return "<" not in title and ">" not in title


def _single_section_heading(visible: str) -> str:
    found: list[str] = []
    for attrs, inner in _H2.findall(visible):
        if "blog-title" in attrs.casefold():
            continue
        title = _clean_title(inner)
        if _usable_title(title):
            found.append(title)
    if len(found) == 1:
        return found[0]
    return ""


def _nav_label(visible: str, page_url: str) -> str:
    match = _URL.fullmatch(page_url)
    if match is None:
        return ""
    path = _normalize_path(match.group(2) or "")
    preferred = ""
    fallback = ""
    for attrs, inner in _ANCHOR.findall(visible):
        attr_map = _attrs(f"<a {attrs}>")
        href = attr_map.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        href_path = _normalize_path(_href_path(href))
        if not href_path or href_path != path:
            continue
        text = _clean_title(inner)
        if not _usable_title(text) or len(text) > 40:
            continue
        if "nav-link" in attr_map.get("class", "").casefold() and not preferred:
            preferred = text
        elif not fallback:
            fallback = text
    return preferred or fallback


def _normalize_path(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path


def _href_path(href: str) -> str:
    if href.startswith("https://") or href.startswith("http://"):
        match = _URL.fullmatch(href.split("?", 1)[0].split("#", 1)[0])
        if match is None or match.group(1) != OFFICIAL_HOST:
            return ""
        return match.group(2) or ""
    if href.startswith("/"):
        path = href.split("?", 1)[0].split("#", 1)[0]
        return path
    return ""


def _is_download(path: str) -> bool:
    leaf = path.rsplit("/", 1)[-1].lower()
    return any(leaf.endswith(suffix) for suffix in _DOWNLOAD_SUFFIXES)


def _is_asset(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in _ASSET_MARKERS)


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _strip_deed_anchor_text(page_html: str) -> str:
    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if "creativecommons.org" in href.casefold():
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _HREF_TAG.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _cc_flags(value: str) -> set[str]:
    flags: set[str] = set()
    if _RESTRICTED_URL.search(value) or _RESTRICTED_TEXT.search(value):
        flags.add("restricted")
    if _PERMISSIVE_URL.search(value) or _PERMISSIVE_TEXT.search(value):
        flags.add("permissive")
    return flags


def _iso_prefix(value: str) -> str:
    if not isinstance(value, str):
        return ""
    match = _DATE_PREFIX.match(value.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return ""


def _calendar_date(month: str, day: str, year: str) -> str:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return ""
    try:
        parsed = date(int(year), month_number, int(day))
    except ValueError:
        return ""
    return parsed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
