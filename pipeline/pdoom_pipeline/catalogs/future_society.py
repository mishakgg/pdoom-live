"""Metadata catalog of public The Future Society pages.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
and PDFs are not stored. A date the page does not state stays unknown. Updated
times, modification times, and copyright years are not publication dates.
Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA and does
not also state a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A hyphen is a word boundary, so CC BY does not match
CC BY-NC. A public page, a copyright notice, or a terms link is not a licence.
A robot challenge omits the row, so the catalog may be empty. This catalog is
not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "future_society_pages"
CATALOG_FILENAME = "future_society_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "thefuturesociety.org"
PUBLISHER = "The Future Society"
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
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_CANONICAL = re.compile(r"^https://thefuturesociety.org(?P<path>/[^?#]*)$")
_PATH = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"([^"]*)"')
_LABELED_PUBLISHED = re.compile(
    r"(?i)\b(?:date published|publication date|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b([^>]*)>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s*the future society\s*$")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# creative_commons is only CC0, CC BY, or CC BY-SA. A hyphen is a word
# boundary, so CC BY must not match CC BY-NC or CC BY-ND. A generic
# creativecommons.org/licenses/ URL is not a copying licence. Public Domain
# Mark is not CC0.
_CC_RESTRICTED = re.compile(
    r"(?:"
    r"creativecommons\.org/licenses/by-nc(?:-sa|-nd)?(?:/|\b)"
    r"|creativecommons\.org/licenses/by-nd(?:/|\b)"
    r"|cc[-\s]*by[-\s]*nc(?:[-\s]*sa|[-\s]*nd)?\b"
    r"|cc[-\s]*by[-\s]*nd\b"
    r"|creative commons attribution[-\s]*non[-\s]*commercial"
    r"|creative commons attribution[-\s]*no[-\s]*deriv"
    r")"
)
_CC_PERMISSIVE = re.compile(
    r"(?:"
    r"creativecommons\.org/publicdomain/zero(?:/|\b)"
    r"|creativecommons\.org/licenses/by-sa(?:/|\b)"
    r"|creativecommons\.org/licenses/by(?:/|\b)(?!-)"
    r"|\bcc0\b"
    r"|creative commons (?:cc0|zero)\b"
    r"|creative commons attribution[-\s]*share[-\s]*alike\b"
    r"|creative commons attribution\b(?![-\s]*(?:non[-\s]*commercial|no[-\s]*deriv))"
    r"|cc[-\s]*by[-\s]*sa\b"
    r"|cc[-\s]*by\b(?![-\s]*(?:nc|nd)\b)"
    r")"
)
_DASHES = ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212")


class CatalogError(ValueError):
    """A catalog row or page failed The Future Society page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_future_society_host(hostname: str) -> bool:
    """True only for the official thefuturesociety.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA. Noncommercial and
    no-derivatives deeds stay unknown, including when a permissive phrase and
    a restricted deed both appear. Anchor text does not outrank a restricted
    licence URL.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    corpus = _licence_corpus(page_text)
    if _CC_RESTRICTED.search(corpus):
        return RIGHTS_UNKNOWN
    if _CC_PERMISSIVE.search(corpus):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    visible = _without_hidden(page_text)
    for raw in _meta_values(visible, _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    labeled = _LABELED_PUBLISHED.search(_plain(visible))
    if labeled and _iso_date(labeled.group(1)):
        return labeled.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    candidates: list[str] = []
    for attrs, inner in _H1.findall(visible):
        if "site-name" in attrs.casefold():
            continue
        candidates.append(inner)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            candidates.append(metas[key])
    title_tag = _TITLE.search(visible)
    if title_tag:
        candidates.append(title_tag.group(1))
    cleaned = [title for item in candidates if (title := _clean_title(item))]
    for title in cleaned:
        if title.casefold() != PUBLISHER.casefold():
            return title
    if cleaned:
        return cleaned[0]
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    publisher = _plain(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if publisher.casefold() != PUBLISHER.casefold():
        raise CatalogError("publisher is required")
    return PUBLISHER


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
    joined = _join_official(href)
    if joined is None:
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
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document["runner_wired"] is not False:
        raise CatalogError("runner_wired must be false")
    entries = document["entries"]
    # An empty list is valid: a robot challenge omits every candidate row.
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
        raise CatalogError("canonical URL must be an https thefuturesociety.org page")
    match = _CANONICAL.fullmatch(url)
    path = match.group("path") if match else ""
    if (
        match is None
        or not official_future_society_host(OFFICIAL_HOST)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https thefuturesociety.org page: {url}")
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
    left_match = _CANONICAL.fullmatch(left)
    right_match = _CANONICAL.fullmatch(right)
    if left_match is None or right_match is None:
        return False
    return left_match.group("path").rstrip("/") == right_match.group("path").rstrip("/")


def _join_official(href: str) -> str | None:
    target = unescape(href).strip()
    if not target or any(char in target for char in (" ", "\n", "\r", "\t")):
        return None
    if target.startswith("https://"):
        return target
    if target.startswith("/") and not target.startswith("//"):
        return f"https://{OFFICIAL_HOST}{target}"
    return None


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _plain(value)).strip()


def _fold_licence(value: str) -> str:
    text = value.casefold().replace("\xa0", " ")
    for dash in _DASHES:
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text).strip()


def _licence_corpus(page_text: str) -> str:
    parts: list[str] = []
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            parts.append(raw.replace("\\/", "/"))
    visible = _without_hidden(page_text)
    parts.append(_plain(visible))
    parts.extend(_hrefs(visible))
    parts.extend(_meta_values(visible, _LICENSE_META))
    return _fold_licence("\n".join(parts))


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


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINKISH.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _canonical_href(page_html: str) -> str:
    visible = _without_hidden(page_html)
    for tag in _LINKISH.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
