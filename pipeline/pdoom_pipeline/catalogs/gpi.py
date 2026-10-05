"""Metadata catalog of public Global Priorities Institute pages.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
and PDFs are not stored. A date the page does not state stays unknown.
Updated times, modified times, and copyright years are not publication dates.
Rights stay unknown unless the page states a reuse licence that allows copying.
``creative_commons`` means CC0, CC BY, or CC BY-SA, and only when the page does
not also state a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A hyphen is a word boundary, so CC BY does not match
CC BY-NC. A Creative Commons URL is not ``creative_commons`` unless its deed is
CC0, CC BY, or CC BY-SA. Public Domain Mark is not CC0. ``uk_ogl`` means the
page text states the phrase open government licence. Oxford or GPI copyright,
a public page, a copyright notice, and a terms link are not licences. This
catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "gpi_pages"
CATALOG_FILENAME = "gpi_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL})
OFFICIAL_HOSTS = frozenset(
    {
        "globalprioritiesinstitute.org",
        "www.globalprioritiesinstitute.org",
    }
)
PUBLISHER = "Global Priorities Institute"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "chart",
        "chart_data",
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
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
)
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
    }
)
_MODIFIED_META = frozenset(
    {
        "article:modified_time",
        "dc.date.modified",
        "dcterms.modified",
        "og:updated_time",
    }
)
_TITLE_KEYS = ("og:title", "twitter:title", "citation_title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_URL = re.compile(
    r"^(?P<scheme>https)://"
    r"(?:(?P<userinfo>[^/@\s]+)@)?"
    r"(?P<host>[A-Za-z0-9.-]+)"
    r"(?::(?P<port>\d+))?"
    r"(?P<path>/[^?#\s]*)"
    r"(?P<query>\?[^#\s]*)?"
    r"(?P<fragment>#[^\s]*)?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_PAGE_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LABELED_PUBLISHED = re.compile(
    r"\b(?:date published|(?<![a-z])published)\s*:\s*(\d{4}-\d{2}-\d{2})\b",
    re.I,
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s+(?:\||[-–—])\s+global priorities institute\s*$"
)
# Longer deeds are listed first. A hyphen is a non-word character, so a bare
# word boundary after BY would also match BY-NC. The CC BY pattern therefore
# refuses a following NC, ND, or SA token.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?=/|[?#]|$)"
)
_TEXT_CODES = (
    ("cc-by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("cc-by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("cc-by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b")),
    ("cc-by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("cc-by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b")),
    (
        "cc0",
        re.compile(
            r"\bcc[\s-]*0\b|\bcc[\s-]*zero\b|"
            r"\bcreative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("cc-by", re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)")),
)
_NAME_BLOCKING = re.compile(
    r"creative commons\s+attribution[\s-]*(?:share[\s-]*alike[\s-]*)?"
    r"(?:non[\s-]*commercial|no[\s-]*deriv)"
)
_NAME_BY_SA = re.compile(
    r"creative commons\s+attribution[\s-]*(?:share[\s-]*alike|sa)\b"
    r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))"
)
_NAME_BY = re.compile(
    r"creative commons\s+attribution\b"
    r"(?![\s-]*(?:share[\s-]*alike|sa|non[\s-]*commercial|no[\s-]*deriv|nc|nd)\b)"
)
_PD_MARK = re.compile(r"public domain mark\b")
_BLOCKING = frozenset(
    {
        "cc-by-nc",
        "cc-by-nc-nd",
        "cc-by-nc-sa",
        "cc-by-nd",
        "pd-mark",
    }
)
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_OGL_PHRASE = "open government licence"
_URL_CODES = {
    "by": "cc-by",
    "by-sa": "cc-by-sa",
    "by-nc": "cc-by-nc",
    "by-nd": "cc-by-nd",
    "by-nc-sa": "cc-by-nc-sa",
    "by-nc-nd": "cc-by-nc-nd",
    "zero": "cc0",
    "mark": "pd-mark",
}


class CatalogError(ValueError):
    """A catalog row or page failed the Global Priorities Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_gpi_host(hostname: str) -> bool:
    """True for globalprioritiesinstitute.org and its www host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when no
    restricted deed is also stated. A by-nc URL stays unknown even if the
    anchor text says CC BY. Public Domain Mark is not CC0. ``uk_ogl`` requires
    the phrase open government licence in the page text.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    codes = _cc_codes(visible)
    if codes & _BLOCKING:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE:
        return RIGHTS_CREATIVE_COMMONS
    if _OGL_PHRASE in _plain(visible).casefold():
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date.

    Updated times, modified times, and copyright years stay unknown.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    visible = _without_hidden(page_text)
    metas = _metas(visible)
    for key in _MODIFIED_META:
        metas.pop(key, None)
    for key in _PUBLISHED_META:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    match = _LABELED_PUBLISHED.search(_plain(visible))
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    html = _without_hidden(page_html)
    metas = _metas(html)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    title_tag = _PAGE_TITLE.search(html)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    for heading in _H1.findall(html):
        title = _clean_title(heading)
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    publisher = _clean_text(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if publisher != PUBLISHER:
        raise CatalogError("publisher is required")
    return publisher


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    record = {
        "title": title_from_page(page_html),
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
    declared_raw = _join(live, href.strip())
    try:
        declared = validate_canonical_url(declared_raw)
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
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document["runner_wired"] is not False:
        raise CatalogError("runner_wired must be false")
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
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
        raise CatalogError("canonical URL must be an https globalprioritiesinstitute.org page")
    parsed = _parse_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https globalprioritiesinstitute.org page: {url}")
    host = parsed["host"].lower().rstrip(".")
    path = parsed["path"] or ""
    if (
        parsed["scheme"] != "https"
        or parsed["userinfo"]
        or parsed["query"]
        or parsed["fragment"]
        or parsed["port"]
        or not official_gpi_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be an https globalprioritiesinstitute.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _parse_url(url: str) -> dict[str, str | None] | None:
    match = _URL.fullmatch(url)
    if match is None:
        return None
    return match.groupdict()


def _is_download(path: str) -> bool:
    lowered = path.casefold()
    if lowered != "/" and lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


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
    a = _parse_url(left)
    b = _parse_url(right)
    if a is None or b is None:
        return False
    host_a = a["host"].lower().rstrip(".") if a["host"] else ""
    host_b = b["host"].lower().rstrip(".") if b["host"] else ""
    path_a = (a["path"] or "").rstrip("/")
    path_b = (b["path"] or "").rstrip("/")
    return host_a == host_b and path_a == path_b


def _join(base: str, href: str) -> str:
    if href.startswith("https://"):
        return href
    if href.startswith("/") and not href.startswith("//"):
        parsed = _parse_url(base)
        if parsed and parsed["host"]:
            return f"https://{parsed['host'].lower().rstrip('.')}{href}"
    return href


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(value: str) -> str:
    text = value.casefold()
    return (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    visible = _without_hidden(page_html)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _cc_codes(visible_html: str) -> set[str]:
    folded = _fold(visible_html)
    codes = _codes_in_urls(folded)
    codes |= _codes_in_words(_fold(_plain(visible_html)))
    for content in _meta_values(visible_html, _LICENSE_META):
        folded_content = _fold(content)
        codes |= _codes_in_urls(folded_content)
        codes |= _codes_in_words(folded_content)
    return codes


def _codes_in_urls(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        token = match.group("license") or match.group("pd")
        if token:
            codes.add(_URL_CODES[token])
    return codes


def _codes_in_words(folded: str) -> set[str]:
    codes: set[str] = set()
    for code, pattern in _TEXT_CODES:
        if pattern.search(folded):
            codes.add(code)
    if _NAME_BLOCKING.search(folded):
        codes.add("cc-by-nc")
    elif _NAME_BY_SA.search(folded):
        codes.add("cc-by-sa")
    elif _NAME_BY.search(folded):
        codes.add("cc-by")
    if _PD_MARK.search(folded):
        codes.add("pd-mark")
    return codes


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
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
