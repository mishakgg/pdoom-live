"""Metadata catalog of public Timaeus pages.

The official host is timaeus.co. www.timaeus.co redirects there. Each stored
URL was confirmed with one bounded HTML GET. A row keeps the title, publisher,
canonical URL, date, and rights label. Page bodies, abstracts, PDFs, and chart
data are not stored. A Cloudflare challenge, a captcha, an HTTP 202, an Akamai
403, a robots disallow, or an off-host redirect is not stored. An empty entry
list is valid.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means only a stated CC0, CC BY, or CC BY-SA deed.
CC BY-NC, CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA are their own tokens and are
never folded into ``creative_commons``. A page that states both a restricted
deed and a permissive deed stays unknown. A hyphen is a word boundary, so CC BY does not
match CC BY-NC, and licenses/by does not match licenses/by-nc. A generic
creativecommons.org/licenses/ URL is not a permissive deed. The Public Domain
Mark is not CC0. mit and apache-2.0 are their own tokens. A copyright notice,
All rights reserved, a terms link, or a host name is not a licence.

A page that does not state a publication date keeps the date unknown. Updated,
modified, and copyright years are not publication dates. The live URL is stored
as confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "timaeus_pages"
CATALOG_FILENAME = "timaeus_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Timaeus"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_MIT,
        RIGHTS_APACHE,
    }
)
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "timaeus.co"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PATH = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)+$")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_LICENSE_META_KEYS = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dcterms.rights",
    }
)
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"')
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sgcaptcha",
    "cf-turnstile",
    "g-recaptcha",
    "hcaptcha",
    "/cdn-cgi/challenge",
)
_DOWNLOAD = re.compile(
    r"(?i)\.(?:pdf|zip|csv|json|xml|docx?|xlsx?|pptx?|png|jpe?g|gif|webp|svg|mp[34]|epub|css|js|txt)(?:/|$)"
)
_BLOCKED_PREFIXES = ("/_astro", "/wp-admin", "/wp-content", "/wp-includes", "/wp-json")
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
_PUBLISHED_LABEL = re.compile(
    r"(?is)<(?:div|p|span|time)\b[^>]*>\s*Published\s*</(?:div|p|span|time)>\s*"
    r"<(?:div|p|span|time)\b[^>]*>\s*"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+(\d{4})"
)
_SITE_PREFIXES = ("Timaeus | ", "Timaeus - ", "Timaeus — ", "Timaeus – ")
_SITE_SUFFIXES = (
    " | Timaeus Research",
    " | Timaeus Blog",
    " | Timaeus Projects",
    " | Timaeus News",
    " | Timaeus",
    " - Timaeus",
    " — Timaeus",
    " – Timaeus",
)
_SKIP_H1 = frozenset({"timaeus", "menu", "navigation"})
_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Longer deeds are listed first. A hyphen is a word boundary, so a bare
# "licenses/by" or "CC BY" match must not succeed on by-nc, by-nd, or by-sa.
_DEED_END = r"(?![a-z0-9-])"
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    + _DEED_END
)
_TEXT_CODES = (
    ("by-nc-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd{_DEED_END}")),
    ("by-nc-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa{_DEED_END}")),
    ("by-nc", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b){_DEED_END}")),
    ("by-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nd{_DEED_END}")),
    ("by-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![\s-]*(?:nc|nd)\b){_DEED_END}")),
    ("by", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b){_DEED_END}")),
    (
        "zero",
        re.compile(
            rf"(?i)(?<![a-z0-9])cc0{_DEED_END}"
            rf"|(?<![a-z0-9])cc[\s-]+0{_DEED_END}"
            rf"|(?<![a-z0-9])cc[\s-]*zero\b"
            rf"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
)
_NAME_CODES = (
    (
        "by-nc-nd",
        re.compile(r"(?i)creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"(?i)creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share))"
        ),
    ),
    ("by-nd", re.compile(r"(?i)creative commons attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"(?i)creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "by",
        re.compile(
            r"(?i)creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CODES = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_RESTRICTED_ORDER = (
    ("by-nc-nd", RIGHTS_CC_BY_NC_ND),
    ("by-nc-sa", RIGHTS_CC_BY_NC_SA),
    ("by-nc", RIGHTS_CC_BY_NC),
    ("by-nd", RIGHTS_CC_BY_ND),
)
_MIT = re.compile(
    r"(?i)(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?=/|$|[?#])"
    r"|\bmit licen[cs]e\b"
    r"|\blicen[cs]ed under (?:the )?mit(?:\s+licen[cs]e)?\b"
)
_APACHE = re.compile(
    r"(?i)(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?=/|$|[?#])"
    r"|(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
    r"|\blicen[cs]ed under (?:the )?apache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2\.0\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Timaeus page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    _require_text(document.get("description"), "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if len(order) > 1 and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be a known token or unknown")


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
        raise CatalogError("canonical URL must be a public Timaeus page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or host != OFFICIAL_HOST
        or parsed.netloc.lower() != OFFICIAL_HOST
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
        or "%" in path
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Timaeus page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: Mapping[str, str] | None = None) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return True
            if name in {"sg-captcha", "x-akamai-transformed"} and token:
                return True
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:8000].casefold()
    plain = _plain_text(page_html[:8000]).casefold()
    return any(marker in sample or marker in plain for marker in _CHALLENGE_MARKERS)


def robots_disallows(robots_text: str, path: str) -> bool:
    """True when User-agent: * disallows this path.

    The longest matching Allow or Disallow rule wins. Allow: / does not
    disallow the site. A path outside the official site is not decided here.
    """

    if not isinstance(robots_text, str) or not isinstance(path, str) or not path.startswith("/"):
        return False
    groups: list[dict] = []
    current: dict | None = None
    for raw in robots_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().casefold()
        value = value.strip()
        if key == "user-agent":
            if current is None or current["rules"]:
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(value.casefold())
        elif key in {"allow", "disallow"} and current is not None:
            current["rules"].append((key, value))
    rules: list[tuple[str, str]] = []
    for group in groups:
        if "*" in group["agents"]:
            rules.extend(group["rules"])
    best_len = -1
    blocked = False
    for kind, rule in rules:
        # An empty Disallow allows every path. An empty Allow does not match.
        if not rule or not path.startswith(rule):
            continue
        if len(rule) >= best_len:
            best_len = len(rule)
            blocked = kind == "disallow"
    return blocked


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    robots_text: str | None = None,
) -> bool:
    """A page is stored only from HTML on the official host.

    HTTP 202, a non-HTML body, a challenge, a captcha, an Akamai or other
    403, a robots disallow, and an off-host URL are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html, headers):
        return False
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return False
    if robots_text is not None and robots_disallows(robots_text, urlparse(page_url).path or "/"):
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML.

    The title comes from that HTML. A challenge page, an HTTP 202, an HTTP
    403, a robots disallow, or a non-HTML response is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        robots_text=robots_text,
    ):
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=page_url)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. A sole CC BY-NC,
    CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND deed stays its own token. When a
    restricted deed and a permissive deed both appear, the label stays
    unknown. An anchor whose text says CC BY, CC BY-SA, or CC0 while the
    href is a restricted deed or the Public Domain Mark stays unknown. A
    hyphen does not let CC BY match CC BY-NC, and licenses/by does not match
    licenses/by-nc. The Public Domain Mark is not CC0. mit and apache-2.0
    are not folded into ``creative_commons``. Script and style text does not
    count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _HIDDEN.sub(" ", page_text)
    if _deceptive_permissive_anchor(visible):
        return RIGHTS_UNKNOWN
    plain = _fold(_plain_text(visible))
    hrefs = _fold(" ".join(_hrefs(visible)))
    metas = _fold(" ".join(_license_meta_values(visible)))
    licences = _fold(" ".join(_ld_licenses(page_text)))
    blob = "\n".join((plain, hrefs, metas, licences))
    codes = _cc_codes(blob, prose=plain)
    mit = bool(_MIT.search(blob))
    apache = bool(_APACHE.search(blob))
    restricted = [token for code, token in _RESTRICTED_ORDER if code in codes]
    permissive = bool(codes & _PERMISSIVE)
    if restricted and permissive:
        return RIGHTS_UNKNOWN
    if restricted:
        return restricted[0]
    if permissive and (mit or apache):
        return RIGHTS_UNKNOWN
    if mit and apache:
        return RIGHTS_UNKNOWN
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    A visible Published label is the page date. article:modified_time,
    og:updated_time, a last-updated line, an effective date, and a copyright
    year are not publication dates. Several different Published labels are
    not one date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    labeled: list[str] = []
    for match in _PUBLISHED_LABEL.finditer(visible):
        parsed = _month_date(match.group(1), match.group(2), match.group(3))
        if parsed:
            labeled.append(parsed)
    distinct = set(labeled)
    if len(distinct) == 1:
        return labeled[0]
    if len(distinct) > 1:
        return UNKNOWN_DATE
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            date.fromisoformat(match.group(1))
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    headings = []
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if title and title.casefold() not in _SKIP_H1:
            headings.append(title)
    site = _clean_text(metas.get("og:site_name", ""))
    # A document title is trusted when the site name states Timaeus. Event
    # pages whose meta title never names Timaeus keep the visible heading.
    site_names_publisher = re.search(r"(?i)\btimaeus\b", site) is not None
    if site_names_publisher:
        for key in ("og:title", "citation_title", "dcterms.title"):
            if not metas.get(key):
                continue
            title = _clean_title(metas[key])
            if title and title.casefold() not in _SKIP_H1:
                return title
    if headings:
        return headings[0]
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title and title.casefold() not in _SKIP_H1:
                return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return Timaeus when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _HIDDEN.sub(" ", page_html)
    site = _metas(visible).get("og:site_name", "")
    if re.search(r"(?i)\btimaeus\b", _clean_text(site)):
        return PUBLISHER
    if re.search(r"(?i)\btimaeus\b", _plain_text(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if _PATH.fullmatch(path) is None:
        return False
    lowered = path.casefold()
    if _DOWNLOAD.search(lowered):
        return False
    return not lowered.startswith(_BLOCKED_PREFIXES)


def _deceptive_permissive_anchor(visible_html: str) -> bool:
    """True when anchor text claims CC BY, CC BY-SA, or CC0 but the href does not.

    A by-nc, by-nd, by-nc-sa, by-nc-nd, or public-domain mark URL is not the
    deed named by that visible text. The Public Domain Mark is not CC0.
    """

    for attrs_blob, inner in _ANCHOR.findall(visible_html):
        href = _attrs(f"<a {attrs_blob}>").get("href", "")
        href_codes = _url_codes(_fold(href))
        if not (href_codes & _RESTRICTED_CODES or "mark" in href_codes):
            continue
        text_codes = _prose_codes(_fold(_plain_text(inner)))
        if text_codes & _PERMISSIVE:
            return True
    return False


def _url_codes(blob: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(blob):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code.casefold())
    return codes


def _prose_codes(prose: str) -> set[str]:
    codes: set[str] = set()
    for code, pattern in _TEXT_CODES:
        if pattern.search(prose):
            codes.add(code)
    for code, pattern in _NAME_CODES:
        if pattern.search(prose):
            codes.add(code)
    return codes


def _cc_codes(blob: str, *, prose: str) -> set[str]:
    return _url_codes(blob) | _prose_codes(prose)


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _month_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        return date(int(year_text), month, int(day_text)).isoformat()
    except ValueError:
        return None


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for prefix in _SITE_PREFIXES:
            if text.startswith(prefix) and len(text) > len(prefix):
                text = text[len(prefix) :].strip()
                changed = True
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(_HIDDEN.sub(" ", page_text))


def _fold(value: str) -> str:
    text = value.casefold().translate(_DASHES).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _license_meta_values(page_html: str) -> list[str]:
    metas = _metas(page_html)
    return [metas[key] for key in _LICENSE_META_KEYS if metas.get(key)]


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINKISH.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _ld_licenses(page_text: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            found.append(raw.replace("\\/", "/"))
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
