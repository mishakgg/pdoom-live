"""Metadata catalog of public RIKEN Center for Advanced Intelligence Project pages.

Each stored URL was confirmed with one bounded GET of HTML on aip.riken.jp.
www.aip.riken.jp is an allowed host when a response stays there. Other RIKEN
hosts are omitted. A row keeps the title, publisher, canonical URL, date, and
rights label. Page text, abstracts, PDFs, quotes, transcripts, and chart data
are not stored. A Cloudflare challenge, a captcha, an authentication wall, a
robots disallow, a non-HTML body, or a redirect off the two allowed hosts is
not stored.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA,
or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``, or
``cc_by_nc_nd``. Mixed restricted and permissive text stays unknown. A
permissive anchor on a restricted deed URL or a public-domain mark URL stays
unknown, including a CC0 anchor on a publicdomain/mark URL. A generic
creativecommons.org/licenses or /licenses/ URL is not a deed. Anchor text on
it, including CC BY, CC BY 4.0, and CC BY-SA, stays unknown. That includes a
missing slash, http, a www host, and a query string. A specific deed URL still
counts, and text elsewhere on the page still counts. MIT, Apache-2.0, and
MPL-2.0 stay their own tokens. A software licence beside any Creative Commons
deed stays unknown. Two software licences stay unknown. Two different
restricted deeds stay unknown. Apache License, Version 2.0, including the
comma, is apache-2.0. ``uk_ogl`` requires the British phrase Open Government
Licence. ``us_government_work`` comes only from an explicit rights metadata
field. A photo credit, caption credit, or image credit that names someone
else's licence stays unknown. Script, style, and comment text does not count.

Updated, modified, and copyright years are not publication dates. A missing
date stays unknown. The live URL is stored as confirmed; a different
rel=canonical does not replace it. This module does not fetch and it is not a
belief collector. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "riken_aip_pages"
CATALOG_FILENAME = "riken_aip_pages.json"
RUNNER_WIRED = False
PUBLISHER = "RIKEN Center for Advanced Intelligence Project"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
OFFICIAL_HOST = "aip.riken.jp"
WWW_HOST = "www.aip.riken.jp"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, WWW_HOST})
OGL_PHRASE = "open government licence"
MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Confirmed public research, news, and publication pages on aip.riken.jp. "
    "www.aip.riken.jp is an allowed host. Other RIKEN hosts are omitted. "
    "Each URL was one bounded GET. A Cloudflare challenge, captcha, authentication wall, "
    "robots disallow, or off-host redirect stores no row. "
    "Rows keep a title, publisher, canonical URL, date, and rights. "
    "Page text, abstracts, PDFs, quotes, transcripts, and chart data are omitted. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "Sole CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND keep their tokens. "
    "uk_ogl requires the British phrase Open Government Licence. "
    "Missing publication dates stay unknown. Updated, modified, and copyright years are not dates. "
    "Not a belief collector and runner_wired is false."
)

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
        "summary",
        "text",
        "transcript",
        "transcript_text",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SCOPE_PATH = re.compile(
    r"^/(?:"
    r"news-list|labs-list|pressrelease|"
    r"news(?:/[^/]+)+|"
    r"labs(?:/[^/]+)+|"
    r"pressrelease(?:/[^/]+)+"
    r")/?$"
)
_PCT = re.compile(r"%[0-9a-f]{2}")
_UNSAFE_PCT = re.compile(r"(?i)%(?:2f|2e|5c|00)")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H3 = re.compile(r"(?is)<h3\b[^>]*>(.*?)</h3>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_POSTED_DATE = re.compile(
    r"""(?is)<div\b[^>]*\bclass\s*=\s*["'][^"']*\bposted-date\b[^"']*["'][^>]*>(.*?)</div>"""
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HREF_ATTR = re.compile(
    r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset(
    {
        "rights",
        "dc.rights",
        "dcterms.rights",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "checking your browser",
    "sgcaptcha",
    "sg-captcha",
    "attention required! | cloudflare",
    "are you a robot",
    "akamai bot manager",
    "errors.edgesuite.net",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "attention required! | cloudflare",
        "access denied",
    }
)
_SITE_SUFFIXES = (
    " | Center for Advanced Intelligence Project",
    " - Center for Advanced Intelligence Project",
    " | RIKEN Center for Advanced Intelligence Project",
    " - RIKEN Center for Advanced Intelligence Project",
    " | 革新知能統合研究センター",
    " - 革新知能統合研究センター",
    " | RIKEN AIP",
    " - RIKEN AIP",
)
_GENERIC_TITLES = frozenset(
    {
        "center for advanced intelligence project",
        "riken center for advanced intelligence project",
        "革新知能統合研究センター",
        "riken aip",
        "riken",
        "top page",
    }
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".lzh",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_LOGIN_SEGMENTS = frozenset(
    {
        "account",
        "log-in",
        "login",
        "register",
        "sign-in",
        "signin",
        "signup",
        "wp-admin",
        "wp-login",
        "wp-login.php",
    }
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
_MONTH_DATE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+(\d{1,2}),\s+(\d{4})\b"
)
_JP_DATE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
_SLASH_DATE = re.compile(r"\b(\d{4})/(\d{1,2})/(\d{1,2})\b")
_DASHES = str.maketrans(
    {
        "\u00a0": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Longer deeds are first. `(?![-a-z0-9])` keeps licenses/by from matching
# licenses/by-nc, and the text patterns refuse a following NC, ND, or SA.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![-a-z0-9])"
)
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)"),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    ("cc-by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "cc0",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    (
        "cc-by",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)"),
    ),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_PD_MARK = re.compile(r"public domain mark\b")
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_RESTRICTED_TOKEN = {
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
}
_MIT = re.compile(
    r"\bmit licen[cs]e\b"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
# The comma in "Apache License, Version 2.0" is part of the licence name.
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,\s*version|\s+version|\s*,)?\s*2\.0\b"
    r"|apache\.org/licenses/license-2\.0(?![a-z0-9-])"
    r"|spdx\.org/licenses/apache-2\.0(?![a-z0-9-])"
)
_MPL = re.compile(
    r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])"
    r"|\bmpl\s*2\.0\b"
    r"|\bmozilla public licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_GENERIC_CC_LICENSES = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:\?[^#]*)?(?:#.*)?$"
)
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|caption|image)\s+credits?\b")
_CREDIT_SENTENCE = re.compile(
    r"(?i)\b(?:photo|caption|image)\s+credits?\b(?:[^.<]|<(?!/?(?:p|figcaption|li)\b)[^>]*>){0,500}\."
)
_CREDIT_OPEN = re.compile(
    r"(?is)<(p|figcaption|li|em|span|caption|figure|small|cite|dd|td|div)\b[^>]*>"
)
_US_GOV = re.compile(
    r"\b(?:u\.?\s*s\.?|united states)\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+(?:united states|u\.?\s*s\.?)\s+government\b"
)
_US_GOV_NEGATED = re.compile(
    r"\bnot\s+(?:a\s+)?(?:u\.?\s*s\.?|united states)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united states|u\.?\s*s\.?)\s+government\b"
)
_NON_DATE_WORDS = ("updated", "update", "modified", "modification", "copyright", "©")


class CatalogError(ValueError):
    """A catalog row or page failed the RIKEN AIP page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for aip.riken.jp and www.aip.riken.jp."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows path.

    An HTML challenge body is not treated as a disallow of every path. The
    longest matching Allow or Disallow pattern wins. Equal lengths allow.
    """

    if not isinstance(body, str):
        return False
    if "<html" in body[:800].casefold():
        return True
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    best_allow = -1
    best_disallow = -1
    for kind, pattern in rules:
        if _robots_matches(pattern, target):
            length = len(pattern)
            if kind == "allow":
                best_allow = max(best_allow, length)
            else:
                best_disallow = max(best_disallow, length)
    if best_disallow < 0:
        return True
    if best_allow < 0:
        return False
    return best_allow >= best_disallow


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page.

    A dns-prefetch to challenges.cloudflare.com on an ordinary page is not a
    challenge. Just a moment, a captcha, or an access-denied title is.
    """

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(_visible(page_html[:12000]))
    if match is None:
        return False
    title = _plain(match.group(1)).casefold()
    return title in _CHALLENGE_TITLES


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if _challenge_headers(headers):
        return False
    target = final_url or page_url
    if not _on_official_host(target) or _is_login_url(target):
        return False
    lowered = page_html[:12000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
) -> dict | None:
    """Return metadata when the bounded GET returned the page HTML."""

    target = final_url or page_url
    if hops and any(not _on_official_host(hop) for hop in hops):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=target,
    ):
        return None
    if robots_txt is not None and not robots_path_allowed(target, robots_txt):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def robots_path_allowed(url: str, robots_txt: str | None = None) -> bool:
    """A missing robots document does not block. A disallow blocks the path."""

    if not _on_official_host(url):
        return False
    if robots_txt is None:
        return True
    path = urlparse(url).path or "/"
    return robots_allows(robots_txt, path)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is
    CC0, CC BY-SA, or a permissive mix of those. A sole restricted deed keeps
    its token. A permissive label on a restricted or public-domain mark URL
    stays unknown. A generic creativecommons.org/licenses URL is not a deed.
    A photo, caption, or image credit does not count. Script, style, and
    comment text do not count. ``us_government_work`` requires a rights
    metadata field.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, gov = _rights_signals(page_text)
    if "pd-mark" in cc_codes:
        return RIGHTS_UNKNOWN
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    families = [
        family
        for family in (
            restricted,
            permissive,
            software,
            {RIGHTS_UK_OGL} if ogl else set(),
            {RIGHTS_US_GOVERNMENT_WORK} if gov else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive == {"cc-by"}:
            return RIGHTS_CC_BY
        return RIGHTS_CREATIVE_COMMONS
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, and a date inside script, style, or a comment are not publication
    dates. A listing of other posts is not this page's publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    found: list[str] = []
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        _add_date(found, _iso_day(metas.get(key, "")))
    for raw in _POSTED_DATE.findall(visible):
        parsed = _date_in_posted_block(raw)
        _add_date(found, parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title and not _generic_title(title):
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title and not _generic_title(title):
            return title
    for heading in _H3.findall(visible):
        title = _clean_title(heading)
        if title and not _generic_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the center when the page names RIKEN and the center.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    title_tag = _TITLE.search(visible)
    title = _plain(title_tag.group(1)) if title_tag else ""
    blob = f"{title} {_plain(visible)}".casefold()
    center = (
        "center for advanced intelligence project" in blob
        or "riken aip" in blob
        or "理研aip" in blob
        or "革新知能統合研究センター" in blob
    )
    if center and ("riken" in blob or "理研" in blob):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def confirmed_url(page_html: str, page_url: str) -> str:
    """Keep the live URL. A different rel=canonical does not replace it."""

    live = validate_canonical_url(_normalize_percent(page_url))
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_normalize_percent(_join_official(live, href)))
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
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or description != description.strip() or not description:
        raise CatalogError("description is required")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog statement")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
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
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public RIKEN AIP page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
    ):
        raise CatalogError(f"canonical URL must be a public RIKEN AIP page: {url}")
    try:
        path = _percent_path(parsed.path or "/")
    except ValueError as exc:
        raise CatalogError(f"canonical URL must be a public RIKEN AIP page: {url}") from exc
    normalized = f"https://{host}{path}"
    if not _acceptable_path(path) or _is_login_url(normalized):
        raise CatalogError(f"canonical URL must be a public RIKEN AIP page: {url}")
    return normalized


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    visible = _visible(page_text)
    gov = _states_us_government_work(visible)
    scanned = _drop_generic_cc_anchors(_drop_credit_licences(visible))
    folded = _fold(scanned)
    return _cc_codes(folded), _software_codes(folded), _states_ogl(scanned), gov


def _states_us_government_work(visible_html: str) -> bool:
    """True only when a rights metadata field states a US government work."""

    for value in _rights_meta_values(visible_html):
        text = _fold(value)
        if _US_GOV_NEGATED.search(text):
            continue
        if _US_GOV.search(text):
            return True
    return False


def _rights_meta_values(visible_html: str) -> list[str]:
    values: list[str] = []
    for tag in _META.findall(visible_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key in _RIGHTS_META or key.endswith(".rights") or key.endswith(":rights"):
            content = attrs.get("content", "")
            if content:
                values.append(content)
    return values


def _drop_generic_cc_anchors(html: str) -> str:
    """Remove anchors that point at the generic Creative Commons licences URL.

    The anchor text is not a deed. Text outside the anchor still is.
    """

    def replace(match: re.Match[str]) -> str:
        href_match = _HREF_ATTR.search(match.group(1))
        if href_match is None:
            return match.group(0)
        href = href_match.group(1) or href_match.group(2) or href_match.group(3) or ""
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    folded = _fold(href).replace(" ", "")
    return _GENERIC_CC_LICENSES.fullmatch(folded) is not None


def _drop_credit_licences(html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names."""

    html = _CREDIT_SENTENCE.sub(" ", html)
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(html):
        start_region = max(0, match.start() - 500)
        opens = list(_CREDIT_OPEN.finditer(html[start_region : match.start()]))
        removed = False
        if opens:
            last = opens[-1]
            abs_open = start_region + last.start()
            close = re.search(
                rf"(?is)</{last.group(1)}\s*>",
                html[match.end() : match.end() + 1500],
            )
            if close is not None:
                abs_end = match.end() + close.end()
                if abs_end - abs_open <= 2000:
                    spans.append((abs_open, abs_end))
                    removed = True
        if removed:
            continue
        end = min(match.end() + 800, len(html))
        spans.append((match.start(), end))
    if not spans:
        return html
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    pieces: list[str] = []
    cursor = 0
    for start, end in merged:
        pieces.append(html[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(html[cursor:])
    return "".join(pieces)


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("code")
        if code:
            codes.add(f"cc-{code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
        elif match.group("pd") == "mark":
            codes.add("pd-mark")
    for name, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(name)
    if _PD_MARK.search(folded):
        codes.add("pd-mark")
    return codes


def _software_codes(folded: str) -> set[str]:
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_ogl(visible_html: str) -> bool:
    folded = _fold(_plain(visible_html))
    return OGL_PHRASE in folded


def _date_in_posted_block(raw: str) -> str | None:
    text = _plain(raw).casefold()
    if any(word in text for word in _NON_DATE_WORDS):
        return None
    found = _MONTH_DATE.search(text)
    if found:
        return _ymd(int(found.group(3)), _MONTHS[found.group(1)], int(found.group(2)))
    jp = _JP_DATE.search(text)
    if jp:
        return _ymd(int(jp.group(1)), int(jp.group(2)), int(jp.group(3)))
    slash = _SLASH_DATE.search(text)
    if slash:
        return _ymd(int(slash.group(1)), int(slash.group(2)), int(slash.group(3)))
    return _iso_day(text)


def _add_date(found: list[str], value: str | None) -> None:
    if value and value not in found:
        found.append(value)


def _wildcard_rules(body: str) -> list[tuple[str, str]] | None:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value.lower())
            continue
        if key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    flush()
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            return group_rules
    return None


def _robots_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "^" + ".*".join(re.escape(chunk) for chunk in body.split("*"))
    if anchored:
        regex += "$"
    return re.search(regex, path) is not None


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return is_official_host(host)


def _is_login_url(url: str) -> bool:
    if not isinstance(url, str) or "://" not in url:
        return False
    path = (urlparse(url).path or "/").casefold()
    segments = {part for part in path.split("/") if part}
    if segments & _LOGIN_SEGMENTS:
        return True
    return "wp-login" in path or path.startswith("/wp-admin")


def _acceptable_path(path: str) -> bool:
    if not path.startswith("/") or "\\" in path or "//" in path or ".." in path:
        return False
    if _UNSAFE_PCT.search(path):
        return False
    if "%" in path and not _well_formed_percent(path):
        return False
    decoded = unquote(path)
    if (
        "%" in decoded
        or ".." in decoded
        or "\\" in decoded
        or "//" in decoded
        or any(char.isascii() and (char.isspace() or ord(char) < 32) for char in decoded)
    ):
        return False
    if any(char.isascii() and char.isalpha() and char.isupper() for char in decoded):
        return False
    bare = decoded[:-1] if decoded.endswith("/") else decoded
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _SCOPE_PATH.fullmatch(decoded) is not None


def _well_formed_percent(path: str) -> bool:
    index = 0
    while index < len(path):
        if path[index] != "%":
            index += 1
            continue
        token = path[index : index + 3]
        if _PCT.fullmatch(token) is None:
            return False
        index += 3
    return True


def _percent_path(path: str) -> str:
    """Return one lowercase percent-encoded path. Slash separators stay literal."""

    decoded = unquote(path or "/")
    if not decoded.startswith("/"):
        decoded = "/" + decoded
    encoded = quote(decoded, safe="/-._~")
    return re.sub(r"%[0-9A-Fa-f]{2}", lambda match: match.group(0).lower(), encoded)


def _normalize_percent(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host:
        return url.strip()
    return f"https://{host}{_percent_path(parsed.path or '/')}"


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(value: str) -> str:
    return _clean_text(value)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _plain(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _generic_title(value: str) -> bool:
    return value.casefold() in _GENERIC_TITLES


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _reject_stored_body(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(str(key).casefold() for key in value)
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
        if len(value) > MAX_DESCRIPTION_CHARS and path != "$.description":
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _same_page(left: str, right: str) -> bool:
    return unquote(left).rstrip("/") == unquote(right).rstrip("/")


def _join_official(base: str, href: str) -> str:
    ref = unescape(href).strip()
    parsed = urlparse(ref)
    if parsed.scheme in {"http", "https"}:
        host = (parsed.hostname or "").lower().rstrip(".")
        path = parsed.path or "/"
        return f"https://{host}{path}"
    if ref.startswith("/"):
        host = (urlparse(base).hostname or OFFICIAL_HOST).lower()
        path = ref.split("#", 1)[0].split("?", 1)[0]
        return f"https://{host}{path}"
    return ref


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _ymd(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(_visible(page_html)):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "sg-captcha":
            return True
    return False
