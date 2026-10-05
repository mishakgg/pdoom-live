"""Metadata catalog of public UK Information Commissioner's Office pages about AI.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
and PDFs are not stored. A date the page does not state stays unknown.
Updated times, modified times, and copyright years are not publication dates.
``creative_commons`` means the page states CC0, CC BY, or CC BY-SA and does not
also state a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND
stay unknown. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
A Creative Commons URL is not ``creative_commons`` unless the deed is CC0,
CC BY, or CC BY-SA. Public Domain Mark is not CC0. ``uk_ogl`` means the page
text states the phrase open government licence. Crown copyright alone does not
count, and the American spelling license does not count. A public page, a
copyright notice, All rights reserved, or a terms link is not a licence. This
catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ico_ai_pages"
CATALOG_FILENAME = "ico_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL})
OFFICIAL_HOST = "ico.org.uk"
PUBLISHER = "Information Commissioner's Office"
OGL_PHRASE = "open government licence"
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
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
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
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_STATED_DATE = re.compile(
    r"(?is)<span\b[^>]*>\s*Date\s*</span>\s*<strong\b[^>]*>\s*"
    r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*</strong>"
)
_SITE_SUFFIX = re.compile(r"(?i)\s*[|\u2013\u2014-]\s*ICO\s*$")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PATH = re.compile(r"^/[a-z0-9/-]+/$")
_AI_PATH = re.compile(
    r"(?:artificial-intelligence|generative-ai|(?:^|/)ai(?:-|/|$)|[-/]ai(?:[-/]|$))"
)
_DOWNLOAD = re.compile(
    r"\.(?:pdf|zip|csv|json|xml|docx?|xlsx?|pptx?|png|jpe?g|gif|webp|svg|mp[34]|epub)(?:/|$)"
)
# Longer deeds are listed first. A hyphen ends the CC BY token, so CC BY does
# not match CC BY-NC, CC BY-ND, or CC BY-SA.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?![a-z-])"
    r"|publicdomain/(?P<pd>zero|mark)(?![a-z-]))"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"\bcc(?:[-\s]+)?by(?:[-\s]+)?nc(?:[-\s]+)?nd\b")),
    ("by-nc-sa", re.compile(r"\bcc(?:[-\s]+)?by(?:[-\s]+)?nc(?:[-\s]+)?sa\b")),
    ("by-nc", re.compile(r"\bcc(?:[-\s]+)?by(?:[-\s]+)?nc\b")),
    ("by-nd", re.compile(r"\bcc(?:[-\s]+)?by(?:[-\s]+)?nd\b")),
    ("by-sa", re.compile(r"\bcc(?:[-\s]+)?by(?:[-\s]+)?sa\b")),
    ("zero", re.compile(r"\bcc0\b|\bcc(?:[-\s]+)?zero\b|\bcreative commons(?:[-\s]+(?:cc0|zero))\b")),
    ("by", re.compile(r"\bcc(?:[-\s]+)?by\b(?!-)")),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[-\s]+non-?commercial[-\s]+no-?deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[-\s]+non-?commercial[-\s]+share-?alike"),
    ),
    ("by-nc", re.compile(r"creative commons attribution[-\s]+non-?commercial\b")),
    ("by-nd", re.compile(r"creative commons attribution[-\s]+no-?deriv")),
    ("by-sa", re.compile(r"creative commons attribution[-\s]+share-?alike")),
    ("by", re.compile(r"creative commons attribution\b(?![-\s]+(?:non-?commercial|no-?deriv))")),
    ("mark", re.compile(r"public domain mark\b")),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
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
_DASHES = {ord("\u2013"): "-", ord("\u2014"): "-", ord("\u2212"): "-"}


class CatalogError(ValueError):
    """A catalog row or page failed the ICO page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_ico_host(hostname: str) -> bool:
    """True only for the official ico.org.uk host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state a restricted deed. ``uk_ogl`` requires the phrase
    open government licence in the page text. Crown copyright, a copyright
    notice, and the American spelling license do not state that phrase.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            codes.update(_cc_codes(raw.replace("\\/", "/")))
    visible = _without_hidden(page_text)
    plain = _plain(visible)
    codes.update(_cc_codes(plain))
    for href in _hrefs(visible):
        codes.update(_cc_codes(href))
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if OGL_PHRASE in plain.casefold():
        return RIGHTS_UK_OGL
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown.

    ICO pages put a later review stamp in DC.Date. That meta tag is not a
    publication date. A visible Date label and a publication meta are.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for raw in _jsonld_published(page_text):
        found = _iso_prefix(raw)
        if found:
            return found
    for raw in _meta_values(page_text, _PUBLISHED_META):
        found = _iso_prefix(raw)
        if found:
            return found
    visible = unescape(_without_hidden(page_text)).replace("\xa0", " ")
    for day, month, year in _STATED_DATE.findall(visible):
        found = _human_date(day, month, year)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in ("og:title", "dc.title", "twitter:title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return PUBLISHER


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
        declared = validate_canonical_url(_resolve(live, href.strip()))
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
        raise CatalogError("canonical URL must be an https ico.org.uk AI page")
    parsed = _parse_https_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https ico.org.uk AI page: {url}")
    host, path = parsed
    if (
        not official_ico_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _PATH.fullmatch(path) is None
        or _DOWNLOAD.search(path) is not None
        or _AI_PATH.search(path) is None
        or _blocked_section(path)
    ):
        raise CatalogError(f"canonical URL must be an https ico.org.uk AI page: {url}")
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


def _parse_https_url(url: str) -> tuple[str, str] | None:
    """Return host and path for a simple https URL, without a query or fragment."""
    if not url.startswith("https://") or any(mark in url for mark in ("?", "#", "\\")):
        return None
    rest = url[len("https://") :]
    if "@" in rest or rest.startswith("/") or "//" in rest:
        return None
    host, slash, path = rest.partition("/")
    if not slash:
        return None
    if host != host.lower() or ":" in host or host != OFFICIAL_HOST:
        return None
    return host, "/" + path


def _blocked_section(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    return any(part in {"private", "restricted"} for part in parts)


def _same_page(left: str, right: str) -> bool:
    a = _parse_https_url(left)
    b = _parse_https_url(right)
    if a is None or b is None:
        return False
    return a[0] == b[0] and a[1].rstrip("/") == b[1].rstrip("/")


def _resolve(page_url: str, href: str) -> str:
    if href.startswith("https://") or href.startswith("http://"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return f"https://{OFFICIAL_HOST}{href}"
    base = page_url.rsplit("/", 1)[0]
    return f"{base}/{href}"


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _plain(value)).strip()


def _usable_title(title: str) -> bool:
    if not title or title.casefold() in {"ico", PUBLISHER.casefold()}:
        return False
    return len(title) <= MAX_FIELD_CHARS and "<" not in title and ">" not in title


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
    """Return Creative Commons deeds stated in text or in a URL.

    Restricted deeds are recorded separately from CC0, CC BY, and CC BY-SA.
    A generic creativecommons.org/licenses/ URL adds no deed.
    """
    folded = _plain(value).casefold()
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _jsonld_published(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        text = blob.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            found.extend(_DATE_PUBLISHED.findall(text))
            continue
        _collect_published(payload, found)
    return found


def _collect_published(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_published(item, found)
        return
    if not isinstance(payload, dict):
        return
    if "@graph" in payload:
        _collect_published(payload["@graph"], found)
    published = payload.get("datePublished")
    if isinstance(published, str):
        found.append(published)


def _iso_prefix(raw: str) -> str:
    match = _DATE_PREFIX.match(raw.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return ""


def _human_date(day: str, month: str, year: str) -> str:
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
