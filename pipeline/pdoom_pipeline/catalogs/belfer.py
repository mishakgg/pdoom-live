"""Metadata catalog of public Belfer Center pages on AI and emerging technology.

Hosts are www.belfercenter.org and belfercenter.org. Each stored URL was
confirmed with one bounded GET that returned public HTML. A Cloudflare
challenge, a captcha, an authentication wall, a robots disallow, a donation
page, a non-HTML response, or a redirect off those hosts is not stored. When
a sitemap or listing is blocked, that path contributes no rows.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, quotes, transcripts, and chart data are not stored.
Publisher is Belfer Center. A date the page does not state as a publication
date stays unknown. Updated, modified, and copyright years are not publication
dates. The live URL is stored as confirmed; a different rel=canonical does
not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone. creative_commons means CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps its own token. A hyphen continues the deed,
so CC BY does not match CC BY-NC and licenses/by does not match
licenses/by-nc. When a restricted deed and a permissive deed both appear,
rights stay unknown. Deceptive permissive anchor text on a restricted deed
URL or on a public-domain mark URL stays unknown. A CC0 anchor on a
public-domain mark URL stays unknown. A generic creativecommons.org/licenses
or /licenses/ URL is not a deed. Anchor text on it, including CC BY, CC BY
4.0, and CC BY-SA, stays unknown. The same rule covers a missing slash, http,
a www host, and a query string. A specific deed URL still counts. Text
elsewhere on the page still counts. A software licence beside any Creative
Commons deed stays unknown. Two software licences stay unknown. Two different
restricted deeds stay unknown. A photo credit, caption credit, or image
credit that names someone else's licence stays unknown. mit, apache-2.0, and
mpl-2.0 stay their own tokens. Apache License, Version 2.0 is apache-2.0.
uk_ogl requires the British phrase Open Government Licence.
us_government_work requires an explicit rights metadata field. Script, style,
and comment text does not count.

This module does not fetch. It is not a belief collector, and runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse, urlsplit

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "belfer_pages"
CATALOG_FILENAME = "belfer_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
PUBLISHER = "Belfer Center"
OFFICIAL_HOSTS = frozenset({"www.belfercenter.org", "belfercenter.org"})

RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_PERMISSIVE_CODES = frozenset({"by", "by-sa", "zero"})

MAX_FIELD_CHARS = 500
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
        "dataset",
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
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_CONTENT_TYPES = frozenset(
    {
        "article",
        "blogposting",
        "creativework",
        "newsarticle",
        "report",
        "scholarlyarticle",
        "techarticle",
        "webpage",
    }
)
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
    "cf-browser-verification",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
)
_ROBOTS_PREFIXES = (
    "/admin/",
    "/comment/reply/",
    "/core/",
    "/filter/tips",
    "/index.php/",
    "/media/oembed",
    "/node/add/",
    "/profiles/",
    "/search/",
    "/user/",
)
_LOGIN_SEGMENTS = frozenset({"login", "log-in", "signin", "sign-in", "wp-login", "wp-login.php", "user"})
_DONATION_SEGMENTS = frozenset(
    {"contribute", "donate", "donation", "donations", "give", "giving", "support-us", "ways-to-give"}
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".css",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".txt",
    ".webp",
    ".xml",
    ".zip",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"')
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_RIGHTS_DD = re.compile(r"(?is)<dt\b[^>]*>\s*rights\s*</dt>\s*<dd\b[^>]*>(.*?)</dd>")
_CREDIT_BLOCK = re.compile(
    r"(?is)<(p|figcaption|li|cite|small|caption|td|dd|figure|div|span)\b([^>]*)>(.*?)</\1>"
)
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|image|caption)[\s-]+credits?\b")
_CREDIT_SPAN = re.compile(
    r"(?is)\b(?:photo|image|caption)[\s-]+credits?\b(?:(?!</(?:p|figcaption|li|div|span)>).){0,500}?"
    r"(?:\.(?=\s|<|$)|</(?:p|figcaption|li|div|span)>)"
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s*(?:\||[-–—])\s*(?:the\s+)?belfer center(?:\s+for\s+science\s+and\s+international\s+affairs)?\s*$"
)
_BELFER_NAME = re.compile(r"(?i)\bbelfer center\b")
_OGL_PHRASE = re.compile(r"(?i)open\s+government\s+licence(?![a-z])")
_MIT = re.compile(
    r"(?i)(?:\bmit\s+licen[cs]e\b|\blicen[cs]ed under (?:the\s+)?mit(?:\s+licen[cs]e)?\b|"
    r"opensource\.org/licenses/mit(?![a-z0-9-])|spdx\.org/licenses/mit(?![a-z0-9-]))"
)
_APACHE = re.compile(
    r"(?i)(?:\bapache-2\.0\b|\bapache\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
    r"|\blicen[cs]ed under (?:the\s+)?apache\s+licen[cs]e\b|"
    r"apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)"
)
_MPL = re.compile(
    r"(?i)(?:\bmpl-2\.0\b|\bmozilla\s+public\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b|"
    r"mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)"
)
_US_GOV = re.compile(
    r"(?i)\b(?:u\.?\s*s\.?|united states)\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+(?:united states|u\.?\s*s\.?|us)\s+government\b"
)
_NEGATED_US_GOV = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united states|u\.?\s*s\.?|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united states|u\.?\s*s\.?|us)\s+government\s+works?\b"
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
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
_PUBLISHED_FULL = re.compile(
    rf"(?i)\bPublished:\s+(?:(?P<iso>\d{{4}}-\d{{2}}-\d{{2}})"
    rf"|(?P<mon>{_MONTH})\.?\s+(?P<day>\d{{1,2}}),\s+(?P<year>\d{{4}})"
    rf"|(?P<day2>\d{{1,2}})\s+(?P<mon2>{_MONTH})\.?\s+(?P<year2>\d{{4}}))"
)
_RELATED_CUT = re.compile(r"(?i)\brelated\b")
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
# Longer restricted deeds are listed first. (?!-) keeps CC BY from matching
# CC BY-NC, and licenses/by from matching licenses/by-nc.
_CC_RESTRICTED_URL = re.compile(
    r"(?i)creativecommons\.org/licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd)(?![a-z0-9-])"
)
_MARK_URL = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
_CC_PERMISSIVE_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<by>by(?!-))(?![a-z0-9])"
    r"|licenses/(?P<sa>by-sa)(?![a-z0-9-])"
    r"|publicdomain/(?P<zero>zero)(?![a-z0-9-]))"
)
_CC_CONTINUATION = (
    r"(?:nc|nd|sa|non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike)(?![a-z0-9])"
)
_CC_RESTRICTED_TEXT = (
    (
        "by-nc-nd",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc[-\s]nd(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]non[-\s]?commercial[-\s]no[-\s]?deriv"
            r"|creative commons attribution[-\s]+non[-\s]?commercial[-\s]+no[-\s]?deriv"
            r")"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc[-\s]sa(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]non[-\s]?commercial[-\s]share[-\s]?alike"
            r"|creative commons attribution[-\s]+non[-\s]?commercial[-\s]+share[-\s]?alike"
            r")"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]non[-\s]?commercial(?![-\s]*(?:share[-\s]?alike|no[-\s]?deriv))"
            r"|creative commons attribution[-\s]+non[-\s]?commercial(?![-\s]*(?:share[-\s]?alike|no[-\s]?deriv))"
            r")"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nd(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]no[-\s]?deriv"
            r"|creative commons attribution[-\s]+no[-\s]?deriv"
            r")"
        ),
    ),
)
_CC_PERMISSIVE_TEXT = (
    (
        "by-sa",
        re.compile(
            r"(?i)(?<![a-z0-9])cc[-\s]?by[-\s]sa(?![a-z0-9-])"
            r"|creative commons attribution[-\s]+share[-\s]?alike"
        ),
    ),
    (
        "by",
        re.compile(
            r"(?i)(?<![a-z0-9])cc[-\s]?by(?![\s-]*"
            + _CC_CONTINUATION
            + r")"
            r"|creative commons attribution(?![-\s]*(?:non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike))"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:cc[-\s]?0|cc[-\s]?zero)(?![a-z0-9])"
            r"|creative commons(?:\s+public\s+domain)?\s+zero(?![a-z])"
        ),
    ),
)


class CatalogError(ValueError):
    """A catalog row or page failed the Belfer Center page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_belfer_host(hostname: str) -> bool:
    """True only for www.belfercenter.org or belfercenter.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: dict | None = None) -> bool:
    """True for a Cloudflare, SiteGround, or Akamai interstitial, or a block page."""

    if isinstance(page_html, str) and page_html.strip():
        lowered = page_html.casefold()
        if any(marker in lowered for marker in _CHALLENGE_MARKERS):
            return True
        plain = _plain(_visible(page_html)).casefold()
        if len(plain) < 400 and "403 forbidden" in plain:
            return True
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name in {"cf-mitigated", "sg-captcha"} and "challenge" in token:
            return True
        if name == "server" and "akamaighost" in token:
            return True
    return False


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or a block.

    HTTP 202 and HTTP 403 are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers):
        return False
    return True


def robots_allows_path(robots_text: str, path: str) -> bool:
    """True when robots.txt does not disallow path.

    A challenge page served in place of robots.txt does not allow a fetch.
    """

    if not isinstance(robots_text, str) or is_challenge_page(robots_text):
        return False
    groups = _robots_groups(robots_text)
    if not groups:
        return True
    rules = _matching_rules(groups, "pdoom.live-collector")
    if rules is None:
        return True
    return _path_allowed(rules, path or "/")


def confirmed_fetch_url(requested_url: str, final_url: str) -> str | None:
    """Return the final URL when the GET stayed on an official Belfer host.

    A redirect off www.belfercenter.org and belfercenter.org is not stored.
    A redirect onto a different path is not stored. Moving between the two
    official hosts on the same path is still that page.
    """

    try:
        requested = validate_canonical_url(requested_url)
        final = validate_canonical_url(final_url)
    except CatalogError:
        return None
    requested_path = urlparse(requested).path.rstrip("/") or "/"
    final_path = urlparse(final).path.rstrip("/") or "/"
    if requested_path != final_path:
        return None
    return final


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A sole restricted Creative Commons deed keeps its token. CC BY alone is
    creative_commons_attribution. CC0, CC BY-SA, or a permissive mix of those
    is creative_commons. Mixed restricted and permissive text stays unknown.
    A permissive or CC0 anchor on a restricted or public-domain mark URL stays
    unknown. Anchor text on a generic creativecommons.org/licenses URL does
    not count. A photo, image, or caption credit does not count. Public
    Domain Mark is not CC0. uk_ogl needs the phrase Open Government Licence.
    us_government_work needs a rights metadata field. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _drop_generic_licence_anchor_text(_drop_credit_blocks(_visible(page_text)))
    if _anchor_licence_conflict(visible):
        return RIGHTS_UNKNOWN
    pieces = [_plain(visible), *_hrefs(visible), *_meta_values(visible, _LICENSE_META)]
    for blob in _LDJSON.findall(page_text):
        pieces.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(blob))
    folded = _fold("\n".join(pieces))
    restricted, permissive = _cc_codes(folded)
    software = _software_tokens(folded)
    ogl = _ogl_stated(visible)
    government = _states_us_government_work(page_text)
    if restricted:
        if permissive or software or ogl or government or len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive:
        if software or ogl or government:
            return RIGHTS_UNKNOWN
        if permissive == {"by"}:
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if software:
        if ogl or government or len(software) != 1:
            return RIGHTS_UNKNOWN
        return next(iter(software))
    if ogl and government:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:published_time, citation_publication_date, dcterms.issued,
    dcterms.created, JSON-LD datePublished, and a full Published date are
    publication dates. Updated, modified, and copyright years are not. A
    month and year without a day stays unknown. Distinct publication dates
    on one page stay unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found: list[str] = []
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_prefix(metas.get(key))
        if parsed and parsed not in found:
            found.append(parsed)
    for parsed in _jsonld_published_dates(page_html):
        if parsed not in found:
            found.append(parsed)
    visible_date = _visible_published(visible)
    if visible_date and visible_date not in found:
        found.append(visible_date)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    headings: list[str] = []
    for inner in _H1.findall(visible):
        title = _clean_title(_plain(inner))
        if title:
            headings.append(title)
    if len(headings) == 1 and not _is_site_name(headings[0]):
        return headings[0]
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title and not _is_site_name(title):
            return title
    for title in headings:
        if not _is_site_name(title):
            return title
    if headings:
        return headings[0]
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_plain(title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return Belfer Center when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible(page_html)
    metas = _metas(visible)
    blobs = [
        metas.get("og:site_name", ""),
        metas.get("citation_publisher", ""),
        _plain(visible),
    ]
    title_tag = _TITLE.search(visible)
    if title_tag:
        blobs.append(_plain(title_tag.group(1)))
    for blob in _LDJSON.findall(page_html):
        if _BELFER_NAME.search(blob):
            return PUBLISHER
    if any(_BELFER_NAME.search(blob) for blob in blobs):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict | None = None,
    final_url: str | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded response is that page's HTML.

    A challenge, an HTTP 202, an HTTP 403, a non-HTML body, a robots
    disallow, or a redirect off the official hosts is not stored.
    """

    if robots_text is not None and not robots_allows_path(robots_text, urlparse(page_url).path or "/"):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    landed = page_url if final_url is None else final_url
    confirmed = confirmed_fetch_url(page_url, landed)
    if confirmed is None:
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=confirmed)
    except CatalogError:
        return None


def listing_entries_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict | None = None,
    final_url: str | None = None,
    robots_text: str | None = None,
) -> list[dict]:
    """Return rows for one listing, or an empty list when that path is blocked.

    A Cloudflare challenge, captcha, authentication wall, or robots disallow
    contributes no rows for the path.
    """

    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        robots_text=robots_text,
    )
    if record is None:
        return []
    return [record]


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
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
        host = urlparse(url).hostname or ""
        if not official_belfer_host(host):
            raise CatalogError("canonical URL must stay on a Belfer Center host")
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
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Belfer Center page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or not official_belfer_host(host)
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
        or not path.startswith("/")
        or _robots_disallowed(path)
        or _login_path(path)
        or _donation_path(path)
        or _is_download(path)
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public Belfer Center page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _public_path(path: str) -> bool:
    if path == "/":
        return True
    parts = [part for part in path.split("/") if part]
    if not parts:
        return False
    if path.endswith("/") and path != "/":
        # A trailing slash is still the same public page when every segment is safe.
        pass
    return all(_SEGMENT.fullmatch(part) is not None for part in parts)


def _robots_disallowed(path: str) -> bool:
    """True for paths robots.txt disallows for this collector."""

    lowered = path.lower()
    if "/media/oembed" in lowered:
        return True
    for prefix in _ROBOTS_PREFIXES:
        if lowered == prefix.rstrip("/") or lowered.startswith(prefix):
            return True
    return False


def _login_path(path: str) -> bool:
    parts = [part.casefold() for part in path.split("/") if part]
    return any(part in _LOGIN_SEGMENTS for part in parts)


def _donation_path(path: str) -> bool:
    parts = [part.casefold() for part in path.split("/") if part]
    return any(part in _DONATION_SEGMENTS for part in parts)


def _is_download(path: str) -> bool:
    bare = path[:-1] if path.endswith("/") else path
    return bare.casefold().endswith(_DOWNLOAD_SUFFIXES)


def _generic_licences_url(href: str) -> bool:
    """True for creativecommons.org/licenses with no deed in the path.

    A trailing slash, an http scheme, a www host, and a query string stay on
    that generic path. licenses/by/4.0/ is a specific deed and is not generic.
    """

    raw = href.strip()
    if not raw:
        return False
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").casefold().rstrip(".")
    except ValueError:
        return False
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    return parsed.path.casefold() in {"/licenses", "/licenses/"}


def _drop_credit_blocks(visible_html: str) -> str:
    """Drop a photo, image, or caption credit that names someone else's licence.

    The credit is not a licence to copy the page. Text outside that credit
    remains.
    """

    visible_html = _CREDIT_SPAN.sub(" ", visible_html)

    def replace(match: re.Match[str]) -> str:
        attrs = match.group(2)
        inner = match.group(3)
        text = _plain(inner)
        credit = _CREDIT_PHRASE.search(text) or _CREDIT_PHRASE.search(attrs)
        if credit and len(text) <= 800:
            return " "
        return match.group(0)

    return _CREDIT_BLOCK.sub(replace, visible_html)


def _drop_generic_licence_anchor_text(visible_html: str) -> str:
    """Remove visible text from anchors that point at the generic licences URL.

    That text is not a licence statement. Text outside the anchor remains.
    """

    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1)
        href = _fold(_attrs(f"<a {attrs}>").get("href", ""))
        if _generic_licences_url(href):
            return f"<a {attrs}></a>"
        return match.group(0)

    return _ANCHOR.sub(replace, visible_html)


def _anchor_licence_conflict(visible_html: str) -> bool:
    """True when anchor text claims a permissive deed and the URL does not.

    A CC BY or CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or
    public-domain mark URL stays unknown. A CC0 anchor on a publicdomain/mark
    URL stays unknown. Anchor text that itself states the restricted deed is
    not this conflict.
    """

    for attrs, inner in _ANCHOR.findall(visible_html):
        href = _fold(_attrs(f"<a {attrs}>").get("href", ""))
        text_restricted, text_permissive = _cc_codes(_fold(_plain(inner)))
        if text_restricted or not text_permissive:
            continue
        if _MARK_URL.search(href) and text_permissive & {"by", "by-sa", "zero"}:
            return True
        if _CC_RESTRICTED_URL.search(href) and text_permissive & {"by", "by-sa", "zero"}:
            return True
    return False


def _ogl_stated(visible_html: str) -> bool:
    blobs = [_plain(visible_html), *_meta_values(visible_html, _LICENSE_META)]
    return any(_OGL_PHRASE.search(_fold(blob)) for blob in blobs)


def _states_us_government_work(page_text: str) -> bool:
    """True only when a rights metadata field says the item is a US government work."""

    fields: list[str] = []
    visible = _visible(page_text)
    metas = _metas(visible)
    for key in _RIGHTS_META:
        if metas.get(key):
            fields.append(metas[key])
    fields.extend(_RIGHTS_DD.findall(visible))
    for blob in _LDJSON.findall(page_text):
        fields.extend(_jsonld_rights(blob))
    for field in fields:
        text = _NEGATED_US_GOV.sub(" ", _fold(field))
        if _US_GOV.search(text):
            return True
    return False


def _jsonld_rights(blob: str) -> list[str]:
    found: list[str] = []
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return found
    _collect_rights(payload, found)
    return found


def _collect_rights(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_rights(item, found)
        return
    if not isinstance(payload, dict):
        return
    for name, value in payload.items():
        if str(name).casefold() == "rights" and isinstance(value, str):
            found.append(value)
        elif isinstance(value, (dict, list)):
            _collect_rights(value, found)


def _cc_codes(folded: str) -> tuple[set[str], set[str]]:
    restricted: set[str] = set()
    permissive: set[str] = set()
    for match in _CC_RESTRICTED_URL.finditer(folded):
        restricted.add(match.group("code").casefold())
    for code, pattern in _CC_RESTRICTED_TEXT:
        if pattern.search(folded):
            restricted.add(code)
    for match in _CC_PERMISSIVE_URL.finditer(folded):
        if match.group("by"):
            permissive.add("by")
        elif match.group("sa"):
            permissive.add("by-sa")
        elif match.group("zero"):
            permissive.add("zero")
    for code, pattern in _CC_PERMISSIVE_TEXT:
        if pattern.search(folded):
            permissive.add(code)
    return restricted, permissive


def _software_tokens(folded: str) -> set[str]:
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _visible(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(value: str) -> str:
    return unescape(value).replace("\\/", "/").translate(_DASHES)


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


def _is_site_name(title: str) -> bool:
    folded = title.casefold()
    return folded in {
        "belfer center",
        "the belfer center",
        "the belfer center for science and international affairs",
        "belfer center for science and international affairs",
    }


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
            _reject_stored_body(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_stored_body(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if len(value) > MAX_DESCRIPTION_CHARS and not path.endswith("description"):
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
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


def _jsonld_published_dates(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            for raw in _DATE_PUBLISHED.findall(blob):
                parsed = _iso_prefix(raw)
                if parsed and parsed not in found:
                    found.append(parsed)
            continue
        nodes = payload if isinstance(payload, list) else [payload]
        graph: list[object] = []
        for node in nodes:
            if isinstance(node, dict) and isinstance(node.get("@graph"), list):
                graph.extend(node["@graph"])
            else:
                graph.append(node)
        for node in graph:
            if not isinstance(node, dict):
                continue
            types = node.get("@type", [])
            if isinstance(types, str):
                types = [types]
            names = {str(item).casefold() for item in types}
            if not names & _CONTENT_TYPES:
                continue
            parsed = _iso_prefix(node.get("datePublished"))
            if parsed and parsed not in found:
                found.append(parsed)
    return found


def _visible_published(visible_html: str) -> str | None:
    plain = _plain(visible_html)
    cut = _RELATED_CUT.search(plain)
    window = plain[: cut.start()] if cut else plain
    match = _PUBLISHED_FULL.search(window)
    if match is None:
        return None
    prefix = window[max(0, match.start() - 40) : match.start()].casefold()
    if any(word in prefix for word in ("updat", "modif", "copyright", "©")):
        return None
    if match.group("iso"):
        return _iso_prefix(match.group("iso"))
    if match.group("mon"):
        return _calendar_date(match.group("mon"), match.group("day"), match.group("year"))
    return _calendar_date(match.group("mon2"), match.group("day2"), match.group("year2"))


def _calendar_date(month: str, day: str, year: str) -> str | None:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        return date(int(year), month_number, int(day)).isoformat()
    except ValueError:
        return None


def _hrefs(visible_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(visible_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
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


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.casefold(), unescape(raw).strip())
    return attrs


def _robots_groups(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in text.splitlines():
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
    return groups


def _matching_rules(
    groups: list[tuple[list[str], list[tuple[str, str]]]],
    user_agent: str,
) -> list[tuple[str, str]] | None:
    product = (user_agent or "").split("/", 1)[0].strip().lower()
    haystack = (user_agent or "").strip().lower()
    specific: list[tuple[int, list[tuple[str, str]]]] = []
    wildcard: list[tuple[str, str]] | None = None
    for agents, rules in groups:
        for agent in agents:
            if agent == "*":
                wildcard = rules
                continue
            if product.startswith(agent) or (haystack.startswith(agent) and agent):
                specific.append((len(agent), rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    return wildcard


def _path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix:
            continue
        if path.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed
