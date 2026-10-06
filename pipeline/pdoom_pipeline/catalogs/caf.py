"""Metadata catalog of public Cooperative AI Foundation pages.

The Charity Commission lists www.cooperativeai.org. That host redirects to
www.cooperativeai.com, which is the host that publishes the pages. A row is
stored only when one bounded GET of that host returns HTML. A parked page, a
Cloudflare or Akamai challenge, a SiteGround captcha, an HTTP 202 response, a
robot interstitial, a non-HTML response, or a redirect off the official host
is not stored.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, descriptions, chart data, and quotes are not stored.
A date the page does not state stays unknown. Updated, modified, and copyright
years are not publication dates. Rights stay unknown unless the page states
CC0, CC BY, or CC BY-SA. Those three are labeled creative_commons. CC BY-NC,
CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted deed wins
when it appears beside a permissive one. A hyphen is a word boundary, so CC BY
does not match CC BY-NC. A public page, a copyright notice, or a terms link is
not a licence. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "caf_pages"
CATALOG_FILENAME = "caf_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "www.cooperativeai.com"
PUBLISHER = "Cooperative AI Foundation"
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
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
        "dc.date.issued",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HTTP_URL = re.compile(
    r"(?P<scheme>https)://"
    r"(?:(?P<userinfo>[^/@]+)@)?"
    r"(?P<host>[^:/?#]+)"
    r"(?::(?P<port>[0-9]+))?"
    r"(?P<path>/[^?#]*)?"
    r"(?P<query>\?[^#]*)?"
    r"(?P<fragment>#.*)?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_OPEN_TAG = re.compile(r"(?is)<([a-z0-9]+)\b([^>]*)>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_MONTH_DAY = re.compile(
    r"(?i)\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),?\s+(\d{4})\b"
)
_DAY_MONTH = re.compile(
    r"(?i)\b(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{4})\b"
)
_SITE_SUFFIXES = (
    " | Cooperative AI Foundation",
    " | Cooperative AI",
    " - Cooperative AI Foundation",
    " - Cooperative AI",
    " – Cooperative AI Foundation",
    " — Cooperative AI Foundation",
)
_GENERIC_TITLES = frozenset({"cooperative ai", "cooperative ai foundation"})
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
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".gz",
    ".tgz",
    ".epub",
    ".txt",
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "checking your browser",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "sgcaptcha",
    "sg-captcha",
    "errors.edgesuite.net",
    "akamaighost",
    "this domain is parked",
    "this site is parked",
    "domain is for sale",
    "buy this domain",
    "sedoparking",
    "are you a robot",
    "verify you are human",
    "verify you are a human",
    "pardon our interruption",
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
# Longer restricted deeds are listed first. A hyphen is part of the deed, not
# a split between CC BY and a following token.
_PERMISSIVE_CODES = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CODES = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_CC_CODE = re.compile(
    r"creativecommons\.org/(?:licenses|publicdomain)/([a-z0-9-]+)",
    re.IGNORECASE,
)
_TEXT_DEEDS = (
    (
        "by-nc-nd",
        re.compile(
            r"\bcc(?:\s+|-)by(?:\s+|-)nc(?:\s+|-)nd\b"
            r"|creative commons attribution(?:\s|-)non-?commercial(?:\s|-)no-?derivatives\b"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"\bcc(?:\s+|-)by(?:\s+|-)nc(?:\s+|-)sa\b"
            r"|creative commons attribution(?:\s|-)non-?commercial(?:\s|-)share-?alike\b"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"\bcc(?:\s+|-)by(?:\s+|-)nc(?![\s-](?:sa|nd)\b)\b"
            r"|creative commons attribution(?:\s|-)non-?commercial\b"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"\bcc(?:\s+|-)by(?:\s+|-)nd(?![\s-](?:sa|nc)\b)\b"
            r"|creative commons attribution(?:\s|-)no-?derivatives\b"
        ),
    ),
    ("mark", re.compile(r"public domain mark\b|publicdomain/mark\b")),
    (
        "by-sa",
        re.compile(
            r"\bcc(?:\s+|-)by(?:\s+|-)sa\b"
            r"|creative commons attribution(?:\s|-)share-?alike\b"
        ),
    ),
    (
        "zero",
        re.compile(
            r"\bcc0\b|\bcc(?:\s+|-)0\b|creative commons(?:\s+public domain)?(?:\s|-)zero\b"
            r"|publicdomain/zero\b"
        ),
    ),
    (
        "by",
        re.compile(
            r"\bcc(?:\s+|-)by(?![\s-](?:nc|nd|sa)\b)\b"
            r"|creative commons attribution(?![\s-](?:non|no|share))"
        ),
    ),
)


class CatalogError(ValueError):
    """A catalog row or page failed the Cooperative AI Foundation page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_caf_host(hostname: str) -> bool:
    """True only for the host that publishes the foundation's pages."""
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
    """True when the response is an interstitial rather than the page.

    A newsletter widget script is not an interstitial. Parked pages, Cloudflare
    and Akamai challenges, SiteGround captchas, and robot checks are.
    """

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    plain = _plain(_without_hidden(page_html)).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML on the official host."""

    if status != 200 or status in _REDIRECT_STATUSES:
        return False
    if not isinstance(page_html, str) or not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html):
        return False
    if headers and _header_is_challenge(headers):
        return False
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata when one response is the page HTML.

    A challenge, an HTTP 202, a redirect, an off-host URL, or a non-HTML
    response is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return metadata_from_page(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return creative_commons only for CC0, CC BY, or CC BY-SA.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND, and the Public Domain Mark
    stay unknown. Longer restricted deeds are checked first. A hyphen does not
    let CC BY match CC BY-NC, and a creativecommons.org/licenses/ URL does not
    match every deed. A restricted deed wins beside a permissive one. A public
    page, a copyright notice, or a terms link is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    pieces = [_plain(visible)]
    for tag in _LINK.findall(visible):
        href = _attrs(tag).get("href", "")
        if "creativecommons.org" in href.casefold():
            pieces.append(href)
    for content in _meta_values(visible, _LICENSE_META):
        pieces.append(content)
    codes = _deed_codes(" ".join(pieces))
    if codes & _RESTRICTED_CODES:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CODES:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated times and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    for raw in _meta_values(page_text, _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    visible = _without_hidden(page_text)
    for match in _OPEN_TAG.finditer(visible):
        tokens = _class_tokens(match.group(2))
        if "blog-date" not in tokens or "grey" in tokens:
            continue
        if "text-large" not in tokens and "subpage-hero-subtitle" not in tokens:
            continue
        parsed = _human_date(_immediate_text(visible, match.end()))
        if parsed and not _labeled_update(visible, parsed):
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in ("og:title", "twitter:title", "citation_title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    visible = _without_hidden(page_html)
    seminar = _class_title(visible, required=("seminar",), prefix="text-4xl")
    if _usable_title(seminar):
        return seminar
    area = _class_title(visible, required=("research-areas",), prefix="text-4xl")
    if _usable_title(area):
        return area
    headings = [_clean_title(inner) for inner in _H1.findall(visible)]
    headings = [title for title in headings if _usable_title(title)]
    # Collection templates put the section name in the first h1 and the page
    # title in the second. A page with og:title never reaches this branch.
    if len(headings) >= 2:
        return headings[1]
    if headings:
        return headings[0]
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _plain(_without_hidden(page_html)).casefold()
    if "cooperative ai foundation" not in visible:
        raise CatalogError("publisher must be the Cooperative AI Foundation")
    return PUBLISHER


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL
    that returned HTML. A different rel=canonical is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href or not href.lower().startswith("https://"):
        return live
    try:
        declared = validate_canonical_url(href.strip())
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
        raise CatalogError("canonical URL must be an https www.cooperativeai.com page")
    parsed = _HTTP_URL.fullmatch(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https www.cooperativeai.com page: {url}")
    host = parsed.group("host").lower().rstrip(".")
    path = parsed.group("path") or ""
    if (
        parsed.group("scheme") != "https"
        or parsed.group("userinfo")
        or parsed.group("query")
        or parsed.group("fragment")
        or parsed.group("port")
        or not official_caf_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or path.lower().startswith("/.well-known")
        or path.lower().startswith("/cdn-cgi/")
        or path.lower().endswith(_DOWNLOAD_SUFFIXES)
    ):
        raise CatalogError(f"canonical URL must be an https www.cooperativeai.com page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _header_is_challenge(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "server" and text.strip() in {"akamaighost", "akamai"} and "challenge" in text:
            return True
    return False


def _deed_codes(value: str) -> set[str]:
    text = value.casefold().replace("\u2013", "-").replace("\u2014", "-")
    codes = {match.group(1).casefold() for match in _CC_CODE.finditer(text)}
    remaining = text
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(remaining):
            codes.add(code)
            remaining = pattern.sub(" ", remaining)
    return codes


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
    return a.group("host").lower().rstrip(".") == b.group("host").lower().rstrip(".") and (
        (a.group("path") or "").rstrip("/") == (b.group("path") or "").rstrip("/")
    )


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _GENERIC_TITLES


def _class_tokens(attrs: str) -> set[str]:
    return set(_attr_map(attrs).get("class", "").casefold().split())


def _immediate_text(page_html: str, index: int) -> str:
    chunk = page_html[index:].split("<", 1)[0]
    return _plain(chunk)


def _class_title(page_html: str, *, required: tuple[str, ...], prefix: str) -> str:
    for match in _OPEN_TAG.finditer(page_html):
        tokens = _class_tokens(match.group(2))
        if not all(name in tokens for name in required):
            continue
        if not any(token == prefix or token.startswith(prefix) for token in tokens):
            continue
        title = _clean_title(_immediate_text(page_html, match.end()))
        if title:
            return title
    return ""


_UPDATE_LABEL = re.compile(
    r"(?i)\b(?:last\s+updated|updated\s+on|last\s+modified|modified\s+on|date\s+modified)\b"
)


def _labeled_update(page_html: str, iso: str) -> bool:
    """True when the page calls this calendar day an update or modification."""

    plain = _plain(page_html)
    for match in _UPDATE_LABEL.finditer(plain):
        window = plain[match.start() : match.end() + 48]
        if _human_date(window) == iso:
            return True
    return False


def _human_date(value: str) -> str | None:
    month_first = _MONTH_DAY.search(value)
    if month_first:
        month = _MONTHS.get(month_first.group(1).casefold())
        day = int(month_first.group(2))
        year = int(month_first.group(3))
        return _ymd(year, month, day)
    day_first = _DAY_MONTH.search(value)
    if day_first:
        day = int(day_first.group(1))
        month = _MONTHS.get(day_first.group(2).casefold())
        year = int(day_first.group(3))
        return _ymd(year, month, day)
    return None


def _ymd(year: int, month: int | None, day: int) -> str | None:
    if month is None:
        return None
    try:
        found = date(year, month, day)
    except ValueError:
        return None
    return found.isoformat()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
    return found


def _attr_map(attrs: str) -> dict[str, str]:
    return _attrs(f"<x {attrs}>")


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


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
