"""Metadata catalog of public Mila pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
are not stored. A date the page does not state stays unknown. Updated,
modified, and copyright years are not publication dates. Rights stay unknown
unless the page states CC0, CC BY, or CC BY-SA and does not also state a
restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A hyphen is a word boundary, so CC BY does not match CC BY-NC. A
public page, a copyright notice, All rights reserved, or a terms link is not
a licence. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "mila_pages"
CATALOG_FILENAME = "mila_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "mila.quebec"
PUBLISHER = "Mila"
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
_SLASH_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})")
_PATH = re.compile(r"^/en(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*/?$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_NODE_POST_DATE = re.compile(
    r'(?is)\bfield-name-node-post-date\b.{0,400}?'
    r'<div\b[^>]*class="[^"]*\bfield-item\b[^"]*"[^>]*>\s*([^<]{4,80})'
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s*[|–—-]\s*Mila(?:\s*[-–—]\s*Quebec Artificial Intelligence Institute)?\s*$"
)
_DRUPAL_TABS = re.compile(r"(?i)\s+Primary tabs\b.*$")
_GENERIC_TITLES = frozenset({"home", "mila"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
    "attention required! | cloudflare",
    "checking your browser",
    "enable javascript and cookies",
    "sorry, you have been blocked",
    "access denied",
)
# Longer deeds are matched first. A hyphen is not a word character, so CC BY
# uses a negative lookahead and does not match CC BY-NC or CC BY-ND.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?![a-z-])"
    r"|publicdomain/(?P<pd>zero|mark)(?![a-z-]))"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]?by[\s-]nc[\s-]nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]?by[\s-]nc[\s-]sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]?by[\s-]nc\b")),
    ("by-nd", re.compile(r"\bcc[\s-]?by[\s-]nd\b")),
    ("by-sa", re.compile(r"\bcc[\s-]?by[\s-]sa\b")),
    ("zero", re.compile(r"\bcc0\b|\bcreative commons zero\b|\bcc zero\b")),
    ("by", re.compile(r"\bcc[\s-]?by(?![\s-](?:nc|nd)\b)\b")),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
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
_MONTH_DAY = re.compile(r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$")
_DAY_MONTH = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$")


class CatalogError(ValueError):
    """A catalog row or page failed the Mila page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_mila_host(hostname: str) -> bool:
    """True only for the official mila.quebec host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:8000].casefold()
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    blob = head + "\n" + title
    return any(marker in blob for marker in _CHALLENGE_MARKERS)


def response_is_catalog_html(content_type: object, body: str) -> bool:
    """True when one response is the page HTML rather than a block or file."""

    if not is_html_content_type(content_type):
        return False
    if not isinstance(body, str) or not body.strip():
        return False
    if is_challenge_page(body):
        return False
    head = body[:4000].casefold()
    return "<html" in head or "<!doctype" in head


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND.
    A Creative Commons URL counts only when its deed is one of those. The
    Public Domain Mark is not CC0.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            codes.update(_cc_codes(raw.replace("\\/", "/")))
    visible = _without_hidden(page_text)
    for href in _hrefs(visible):
        codes.update(_cc_codes(href))
    for content in _meta_values(visible, _LICENSE_META):
        codes.update(_cc_codes(content))
    codes.update(_cc_codes(_plain(visible)))
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for raw in _jsonld_date_published(page_text):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    for raw in _meta_values(page_text, _PUBLISHED_META):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    posted = _page_post_date(page_text)
    if posted:
        return posted
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for inner in _H1.findall(page_html):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    raw = _metas(page_html).get("og:title", "")
    title = _clean_title(raw)
    if not _usable_title(title):
        title_tag = _TITLE.search(page_html)
        title = _clean_title(title_tag.group(1)) if title_tag else ""
    if not _usable_title(title):
        raise CatalogError("title is required")
    return title


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if _page_states_publisher(page_html):
        return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was confirmed. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not a Mila page")
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
        declared = validate_canonical_url(_absolute_url(live, href))
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
    if not isinstance(url, str) or not url or url != url.strip() or "\\" in url or "@" in url:
        raise CatalogError("canonical URL must be an https mila.quebec page")
    host, port, path, query, fragment = _parse_https(url)
    if (
        port is not None
        or query
        or fragment
        or not official_mila_host(host)
        or ".." in path
        or "//" in path
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https mila.quebec page: {url}")
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
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _reject_stored_body(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(value)
        if found:
            names = ", ".join(sorted(found))
            raise CatalogError(f"{path} must not store page text ({names})")
        for key, item in value.items():
            if path == "$" and key == "description":
                continue
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


def _parse_https(url: str) -> tuple[str, str | None, str, str, str]:
    if not url.startswith("https://"):
        raise CatalogError(f"canonical URL must be an https mila.quebec page: {url}")
    rest = url[len("https://") :]
    fragment = ""
    query = ""
    if "#" in rest:
        rest, fragment = rest.split("#", 1)
        fragment = "#" + fragment
    if "?" in rest:
        rest, query = rest.split("?", 1)
        query = "?" + query
    if "/" in rest:
        authority, path = rest.split("/", 1)
        path = "/" + path
    else:
        authority, path = rest, ""
    if not authority or any(char in authority for char in " \t"):
        raise CatalogError(f"canonical URL must be an https mila.quebec page: {url}")
    port = None
    host = authority
    if host.startswith("["):
        raise CatalogError(f"canonical URL must be an https mila.quebec page: {url}")
    if ":" in host:
        host, port = host.rsplit(":", 1)
        if not port.isdigit():
            raise CatalogError(f"canonical URL must be an https mila.quebec page: {url}")
    return host, port, path, query, fragment


def _same_page(left: str, right: str) -> bool:
    left_host, _, left_path, _, _ = _parse_https(left)
    right_host, _, right_path, _, _ = _parse_https(right)
    return left_host.casefold() == right_host.casefold() and left_path.rstrip("/") == right_path.rstrip("/")


def _absolute_url(base: str, href: str) -> str:
    target = unescape(href).strip()
    if target.startswith("https://") or target.startswith("http://"):
        return target
    if target.startswith("//"):
        return "https:" + target
    host, _, path, _, _ = _parse_https(base)
    if target.startswith("/"):
        return f"https://{host}{target}"
    parent = path.rsplit("/", 1)[0]
    return f"https://{host}{parent}/{target}"


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value).replace("\u00ad", "")
    text = _SITE_SUFFIX.sub("", text).strip()
    return _DRUPAL_TABS.sub("", text).strip()


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    if title.casefold() in _GENERIC_TITLES:
        return False
    return "<" not in title and ">" not in title and len(title) <= MAX_FIELD_CHARS


def _page_states_publisher(page_html: str) -> bool:
    values = [_metas(page_html).get("og:site_name", ""), _metas(page_html).get("og:title", "")]
    title_tag = _TITLE.search(page_html)
    if title_tag:
        values.append(title_tag.group(1))
    for blob in _LDJSON.findall(page_html):
        if re.search(r'"name"\s*:\s*"Mila"', blob):
            return True
    for value in values:
        if re.search(r"\bMila\b", unescape(value)):
            return True
    return re.search(r"\bMila\b", _plain(_without_hidden(page_html))) is not None


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
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for double, single, bare in _HREF.findall(page_html):
        href = unescape(double or single or bare).strip()
        if href:
            found.append(href)
    return found


def _cc_codes(value: str) -> set[str]:
    """Return Creative Commons deed codes stated in text or a URL.

    Restricted deeds stay in the set so a mixed notice does not become
    ``creative_commons``. The Public Domain Mark is recorded as ``mark`` and
    is not treated as CC0.
    """

    folded = (
        unescape(value)
        .casefold()
        .replace("\\/", "/")
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    if "creative commons" in folded:
        noncommercial = re.search(r"non[\s-]?commercial", folded) is not None
        noderiv = re.search(r"no[\s-]?deriv", folded) is not None
        sharealike = re.search(r"share[\s-]?alike", folded) is not None
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
        elif re.search(r"\battribution\b", folded):
            codes.add("by")
    if "public domain mark" in folded:
        codes.add("mark")
    return codes


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
    if isinstance(published, str) and published.strip():
        found.append(published)


def _page_post_date(page_html: str) -> str | None:
    """Return the page's own post date, not a date on a related card."""

    visible = _without_hidden(page_html)
    for match in _NODE_POST_DATE.finditer(visible):
        lookahead = visible[match.end() : match.end() + 500]
        if "field-name-node-title" in lookahead:
            continue
        parsed = _human_date(match.group(1))
        if parsed:
            return parsed
    return None


def _human_date(value: str) -> str | None:
    text = re.sub(r"\s+", " ", unescape(value).replace("\xa0", " ")).strip()
    month_day = _MONTH_DAY.fullmatch(text)
    if month_day:
        return _ymd(int(month_day.group(3)), month_day.group(1), int(month_day.group(2)))
    day_month = _DAY_MONTH.fullmatch(text)
    if day_month:
        return _ymd(int(day_month.group(3)), day_month.group(2), int(day_month.group(1)))
    return _iso_day(text)


def _ymd(year: int, month_name: str, day: int) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        found = date(year, month, day)
    except ValueError:
        return None
    return found.isoformat()


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    slash = _SLASH_DATE.match(text)
    if slash:
        text = f"{slash.group(1)}-{slash.group(2)}-{slash.group(3)}" + text[slash.end() :]
    match = _DATE_PREFIX.match(text)
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
