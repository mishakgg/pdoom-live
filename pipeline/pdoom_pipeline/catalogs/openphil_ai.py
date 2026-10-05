"""Metadata catalog of public Open Philanthropy pages about AI risk, AI safety, or AI forecasting.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies,
abstracts, PDFs, chart data, and grant amounts are not stored. A date the page
does not state stays unknown. Updated times, modified times, and copyright years
are not publication dates. Rights stay unknown unless the page states CC0, CC BY,
or CC BY-SA and does not also state a restricted deed. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen is a word boundary, so the
text CC BY does not match CC BY-NC. A Creative Commons URL is not
creative_commons unless the deed is CC0, CC BY, or CC BY-SA. The Public Domain
Mark is not CC0. A public page, a copyright notice, All rights reserved, or a
terms link is not a licence. If a permissive deed and a restricted deed both
appear, rights stay unknown.

The official hosts are openphilanthropy.org and www.openphilanthropy.org. A
bounded GET that returns a redirect, a Cloudflare or robot challenge, or a
non-HTML body does not confirm a row. On 2026-10-05 those hosts answered AI
research paths with empty 301 responses whose Location left the official host,
so the stored catalog has no rows. This module does not fetch and it is not a
belief collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "openphil_ai_pages"
CATALOG_FILENAME = "openphil_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOSTS = frozenset({"openphilanthropy.org", "www.openphilanthropy.org"})
PUBLISHER = "Open Philanthropy"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "amount",
        "body",
        "chart",
        "chart_data",
        "content",
        "excerpt",
        "full_text",
        "grant_amount",
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
_LICENSE_KEYS = frozenset({"license", "licence"})
_SKIP_JSON_KEYS = frozenset({"articleBody", "description", "text", "comment"})
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-mitigated",
    "challenge-platform",
    "checking your browser",
    "enable javascript and cookies",
    "attention required",
    "cdn-cgi/challenge",
    "sorry, you have been blocked",
    "access denied",
    "403 forbidden",
)
_GENERIC_TITLES = frozenset({"research", "blog", "home", "focus", "focus areas"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PATH = re.compile(r"^/[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*/$")
_HTTP_URL = re.compile(
    r"^(?P<scheme>https?)://"
    r"(?:(?P<userinfo>[^/@\s]+)@)?"
    r"(?P<host>[^/:?#\s]+)"
    r"(?::(?P<port>\d+))?"
    r"(?P<path>/[^?#\s]*)?"
    r"(?:\?(?P<query>[^#\s]*))?"
    r"(?:#(?P<fragment>\S*))?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||\u2013|\u2014|-)\s*open philanthropy(?: project)?\s*$")
# Restricted deeds are listed before any permissive reading. A hyphen does not
# terminate CC BY, so CC BY-NC, CC BY-ND, and CC BY-SA are not CC BY.
_RESTRICTED_DEED = re.compile(
    r"(?i)(?:"
    r"creativecommons\.org/licenses/by-nc-nd(?![\w-])"
    r"|creativecommons\.org/licenses/by-nc-sa(?![\w-])"
    r"|creativecommons\.org/licenses/by-nc(?![\w-])"
    r"|creativecommons\.org/licenses/by-nd(?![\w-])"
    r"|creativecommons\.org/publicdomain/mark(?![\w-])"
    r"|cc[-\s]?by[-\s]nc[-\s]nd(?![a-z])"
    r"|cc[-\s]?by[-\s]nc[-\s]sa(?![a-z])"
    r"|cc[-\s]?by[-\s]nc(?![a-z])"
    r"|cc[-\s]?by[-\s]nd(?![a-z])"
    r"|attribution[-\s]non[-\s]?commercial[-\s]no[-\s]?deriv"
    r"|attribution[-\s]non[-\s]?commercial[-\s]share[-\s]?alike"
    r"|attribution[-\s]non[-\s]?commercial(?![a-z])"
    r"|attribution[-\s]no[-\s]?deriv"
    r"|public\s+domain\s+mark"
    r")"
)
_PERMISSIVE_DEED = re.compile(
    r"(?i)(?:"
    r"creativecommons\.org/publicdomain/zero(?![\w-])"
    r"|creativecommons\.org/licenses/by-sa(?![\w-])"
    r"|creativecommons\.org/licenses/by(?![\w-])"
    r"|\bcc0(?![\w-])"
    r"|creative\s+commons\s+(?:cc0|zero)(?![a-z])"
    r"|\bcc[-\s]?zero(?![a-z])"
    r"|cc[-\s]?by[-\s]sa(?![\s-]*(?:nc|nd)\b)(?![a-z])"
    r"|creative\s+commons\s+attribution(?![\s-]*(?:non[\s-]?commercial|no[\s-]?deriv))"
    r"|cc[-\s]?by(?![\s-](?:nc|nd|sa)\b)(?![a-z])"
    r")"
)
_UNICODE_DASHES = ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212")


class CatalogError(ValueError):
    """A catalog row or page failed the Open Philanthropy page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_openphil_host(hostname: str) -> bool:
    """True only for openphilanthropy.org and www.openphilanthropy.org."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def html_response_is_confirmable(*, status: int, content_type: str, body: str) -> bool:
    """True when one bounded GET returned an HTML page rather than a block.

    A redirect, a non-HTML body, a Cloudflare challenge, or a robot block does
    not confirm a catalog row.
    """

    if status != 200 or not isinstance(body, str) or not body.strip():
        return False
    if not isinstance(content_type, str):
        return False
    media = content_type.split(";", 1)[0].strip().lower()
    if media not in _HTML_TYPES:
        return False
    sample = body[:8000].casefold()
    if "<html" not in sample and "<!doctype html" not in sample:
        return False
    return not any(marker in sample for marker in _CHALLENGE_MARKERS)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND, or
    the Public Domain Mark. Anchor text that says CC BY does not override a
    by-nc URL. A generic creativecommons.org/licenses/ URL stays unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    uncommented = _COMMENT.sub(" ", page_text)
    licences = [_licence_text(value) for value in _jsonld_strings(uncommented, _LICENSE_KEYS)]
    visible = _SCRIPT_STYLE.sub(" ", uncommented)
    hrefs = [_licence_text(href) for href in _hrefs(visible)]
    blob = "\n".join([_plain(visible), *hrefs, *licences])
    if _RESTRICTED_DEED.search(blob):
        return RIGHTS_UNKNOWN
    if _PERMISSIVE_DEED.search(blob):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    uncommented = _COMMENT.sub(" ", page_text)
    for raw in _jsonld_strings(uncommented, frozenset({"datePublished"})):
        found = _iso_prefix(raw)
        if found:
            return found
    visible = _SCRIPT_STYLE.sub(" ", uncommented)
    for raw in _meta_values(visible, _PUBLISHED_META):
        found = _iso_prefix(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    raw = _metas(visible).get("og:title", "")
    title = _clean_title(raw)
    if _usable_title(title):
        return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))
    publisher = _clean_text(_metas(visible).get("og:site_name", ""))
    if not publisher:
        raise CatalogError("publisher is required")
    return publisher


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_resolve(live, href))
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
        raise CatalogError("canonical URL must be an https openphilanthropy.org page")
    parsed = _HTTP_URL.fullmatch(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https openphilanthropy.org page: {url}")
    parts = parsed.groupdict()
    host = parts["host"]
    path = parts["path"] or ""
    port = parts["port"]
    if (
        parts["scheme"] != "https"
        or parts["userinfo"]
        or parts["query"] is not None
        or parts["fragment"] is not None
        or port not in (None, "443")
        or host != host.lower()
        or host.endswith(".")
        or not official_openphil_host(host)
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https openphilanthropy.org page: {url}")
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
    a = _HTTP_URL.fullmatch(left)
    b = _HTTP_URL.fullmatch(right)
    if a is None or b is None:
        return False
    return a.group("host").lower() == b.group("host").lower() and (a.group("path") or "").rstrip("/") == (
        b.group("path") or ""
    ).rstrip("/")


def _resolve(base: str, href: str) -> str:
    ref = unescape(href).strip().replace("\\/", "/")
    if ref.startswith("https://") or ref.startswith("http://"):
        return ref
    parsed = _HTTP_URL.fullmatch(base)
    if parsed is None:
        raise CatalogError("canonical URL is not on the official host")
    host = parsed.group("host")
    if ref.startswith("//"):
        return "https:" + ref
    path = ref.split("#", 1)[0].split("?", 1)[0]
    if path.startswith("/"):
        return f"https://{host}{path}"
    raise CatalogError("canonical URL is not on the official host")


def _plain(page_text: str) -> str:
    return _licence_text(_TAG.sub(" ", page_text))


def _licence_text(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ")
    for dash in _UNICODE_DASHES:
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG.sub(" ", value))).replace("\xa0", " ").strip()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    return title.casefold() not in _GENERIC_TITLES


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
    for tag in _ANCHOR.findall(page_html) + _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _canonical_href(page_html: str) -> str:
    visible = _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _jsonld_strings(page_html: str, keys: frozenset[str]) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        if len(block) > 100_000:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            if "datePublished" in keys:
                found.extend(_DATE_PUBLISHED.findall(block))
            if keys & _LICENSE_KEYS:
                found.extend(_LD_LICENSE.findall(block))
            continue
        _collect_keys(payload, keys, found)
    return found


def _collect_keys(node: object, keys: frozenset[str], found: list[str], depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(node, dict):
        for name, value in node.items():
            if name in _SKIP_JSON_KEYS:
                continue
            if name in keys:
                _flatten_string(value, found)
            else:
                _collect_keys(value, keys, found, depth + 1)
        return
    if isinstance(node, list):
        for item in node[:30]:
            _collect_keys(item, keys, found, depth + 1)


def _flatten_string(value: object, found: list[str]) -> None:
    if isinstance(value, str):
        found.append(value)
        return
    if isinstance(value, dict):
        for key in ("@id", "url", "name", "id"):
            item = value.get(key)
            if isinstance(item, str):
                found.append(item)
        return
    if isinstance(value, list):
        for item in value[:10]:
            _flatten_string(item, found)


def _iso_prefix(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
