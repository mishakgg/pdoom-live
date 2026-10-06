"""Metadata catalog of public Kempner Institute pages.

Hosts are kempnerinstitute.harvard.edu and www.kempnerinstitute.harvard.edu.
Each stored URL was confirmed with one bounded GET that returned HTML and
stayed on those hosts. robots.txt disallows /wp/wp-admin/ except
admin-ajax.php, /wp-json/, /?rest_route=, and one uploads JSON path. An
unresolved host, an HTML or challenge robots.txt, a Cloudflare challenge, a
cookie challenge, a captcha, a login wall, a non-HTML response, or a redirect
off these hosts is not stored.

A row keeps the title, publisher, canonical URL, date, and rights label.
Page text, abstracts, PDFs, quotes, transcripts, and chart data are not
stored. The live URL is stored as confirmed. A different rel=canonical does
not replace it. This module does not invent a probability.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA,
or a permissive mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or
CC BY-NC-ND keeps that token. Two different restricted deeds stay unknown. A
software licence beside any Creative Commons deed stays unknown. Two software
licences stay unknown. mit, apache-2.0, and mpl-2.0 stay their own tokens.
Apache License, Version 2.0 is apache-2.0. uk_ogl requires the British phrase
Open Government Licence. us_government_work is only an explicit rights
metadata field.

A generic creativecommons.org/licenses or /licenses/ URL is not a deed. Anchor
text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays unknown. The same
is true for a missing slash, http, a www host, and a query string. A specific
deed URL still counts. Text elsewhere on the page still counts. Deceptive
permissive anchor text on a restricted deed URL or on a public-domain mark URL
stays unknown. A CC0 anchor on a public-domain mark URL stays unknown.

A photo credit, caption credit, image credit, or background-credits section
that names someone else's licence does not count. Publication dates only.
Updated, modified, and copyright years are not publication dates. Script,
style, and comment text does not count. Bare MIT is not the MIT License.

This module does not fetch and it does not import requests. It is not a
belief collector. runner_wired stays false.
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

CATALOG_ID = "kempner_pages"
CATALOG_FILENAME = "kempner_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Kempner Institute"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CC_ATTRIBUTION,
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
OFFICIAL_HOSTS = frozenset(
    {"kempnerinstitute.harvard.edu", "www.kempnerinstitute.harvard.edu"}
)
OGL_PHRASE = "open government licence"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Public Kempner Institute pages on kempnerinstitute.harvard.edu and "
    "www.kempnerinstitute.harvard.edu. Each row follows one bounded robots-allowed "
    "HTML GET that stayed on these hosts. An unresolved host, HTML or challenge "
    "robots.txt, a Cloudflare, cookie, or captcha challenge, or an off-host redirect "
    "stores nothing. Rows keep title, publisher, canonical URL, date, and rights. "
    "Page text is not stored. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, "
    "or a permissive mix. Sole CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND keep "
    "their tokens. uk_ogl requires the British phrase Open Government Licence. "
    "Missing publication dates stay unknown. Updated, modified, and copyright years "
    "are not dates. Not a belief collector. runner_wired stays false."
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
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
)
_BLOCKED_PREFIXES = (
    "/app/uploads/",
    "/wp-admin",
    "/wp-content/",
    "/wp-includes/",
    "/wp-json",
    "/wp/wp-admin",
    "/xmlrpc.php",
)
_LOGIN_PARTS = frozenset(
    {
        "account",
        "log-in",
        "login",
        "register",
        "sign-in",
        "signin",
        "signup",
        "wp-admin",
        "wp-login.php",
        "xmlrpc.php",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "please enable cookies",
    "enable cookies to continue",
    "cookies must be enabled",
    "cookie challenge",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "errors.edgesuite.net",
    "akamaighost",
    "are you a robot",
)
_DATE_PREFIX = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_HEADING = re.compile(r"(?is)<h([1-6])\b[^>]*>.*?</h\1>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_GENERIC_LICENSES_URL = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:[?#]\S*)?$"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dcterms.licence"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_ARTICLE_TYPES = frozenset(
    {"article", "blogposting", "newsarticle", "scholarlyarticle", "report"}
)
_PAGE_TYPES = frozenset({"webpage", "profilepage"})
_SITE_SUFFIXES = (
    " | kempner institute",
    " - kempner institute",
    " – kempner institute",
    " — kempner institute",
)
_CREDIT_PHRASE = re.compile(
    r"(?i)\b(?:photo|caption|image)(?:\s|&nbsp;)+credits?\b"
)
_CREDIT_HEADING = re.compile(
    r"(?i)\b(?:photo|caption|image|background)(?:\s|&nbsp;)+credits?\b"
)
_BLOCK_CLOSE = re.compile(
    r"(?i)^</(?:p|div|li|figcaption|figure|caption|blockquote|section|article|td|dd|h[1-6])\b"
)
_PUBLISHED_PROSE = re.compile(
    r"(?<!last )(?<!updated )(?<!modified )(?<!copyright )(?<!was )"
    r"\b(?:publication date|date published|published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})"
    r"|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"
    r"|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
    re.IGNORECASE,
)
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
# Longer deeds are listed first. A hyphen is a word boundary, so licenses/by
# and CC BY do not match licenses/by-nc or CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-))"
    r"(?![a-z0-9-])"
)
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("cc-by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)")),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("cc-by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("cc-by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
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
    ("pd-mark", re.compile(r"\bpublic domain mark\b")),
)
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
    r"|\blicen[cs]ed under (?:the )?mit\b(?!-)"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
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
    r"|mozilla\.org/mpl/2\.0(?![a-z0-9-])"
    r"|spdx\.org/licenses/mpl-2\.0(?![a-z0-9-])"
)
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Kempner Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for kempnerinstitute.harvard.edu and www.kempnerinstitute.harvard.edu."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def robots_allows(body: str, path: str) -> bool:
    """True when every User-agent: * group allows path.

    The longest matching Allow or Disallow wins. Equal lengths allow. An HTML
    document or a challenge page served in place of robots.txt allows nothing.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or "<!doctype html" in sample:
        return False
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    allowed = -1
    disallowed = -1
    for kind, pattern in rules:
        if not _robots_matches(pattern, target):
            continue
        if kind == "allow":
            allowed = max(allowed, len(pattern))
        else:
            disallowed = max(disallowed, len(pattern))
    if disallowed < 0:
        return True
    if allowed < 0:
        return False
    return allowed >= disallowed


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is a Cloudflare, cookie, or captcha interstitial."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    return any(marker in title for marker in _CHALLENGE_MARKERS)


def is_login_wall(page_html: str) -> bool:
    """True when the response is a login form rather than a public page."""

    if not isinstance(page_html, str):
        return False
    sample = page_html[:20000].casefold()
    return 'type="password"' in sample or "type='password'" in sample


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge.

    HTTP 202, a Cloudflare, cookie, or captcha challenge, an Akamai block, a
    login wall, and a final URL on another host are not stored.
    """

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if is_login_wall(page_html):
        return False
    lowered = page_html[:12000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
        return False
    if headers and _blocked_headers(headers):
        return False
    if final_url is not None and not _on_official_host(final_url):
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
    """Return metadata when one bounded GET returned an allowed public page.

    A Cloudflare, cookie, or captcha challenge, an HTTP 202, a robots
    disallow, an HTML robots.txt, a non-HTML body, a login page, or an
    off-host redirect is not stored.
    """

    target = final_url or page_url
    if hops and any(not _on_official_host(hop) for hop in hops):
        return None
    if robots_txt is not None and not _robots_allow_url(robots_txt, target):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=target,
    ):
        return None
    if not isinstance(page_html, str):
        return None
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY and licenses/by is not licenses/by-nc.
    A photo credit, caption credit, image credit, or background-credits
    section does not count. Script, style, and comment text does not count.
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
            {"uk_ogl"} if ogl else set(),
            {"us_government_work"} if gov else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive & {"cc0", "cc-by-sa"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_CC_ATTRIBUTION
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    JSON-LD datePublished on an article or web page and a publication meta
    tag count. Event start dates, updated times, modified times, and copyright
    years do not. A date inside script, style, or comment text does not count
    unless it is that datePublished field.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    article_dates: list[str] = []
    page_dates: list[str] = []
    for node in _ld_nodes(page_html):
        raw = node.get("datePublished")
        parsed = _iso_day(raw) if isinstance(raw, str) else None
        if not parsed:
            continue
        types = _ld_types(node)
        if types & _ARTICLE_TYPES:
            _add_unique(article_dates, parsed)
        elif types & _PAGE_TYPES:
            _add_unique(page_dates, parsed)
    meta_dates: list[str] = []
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        _add_unique(meta_dates, _iso_day(metas.get(key, "")))
    if len(article_dates) > 1 or len(page_dates) > 1 or len(meta_dates) > 1:
        return UNKNOWN_DATE
    chosen = article_dates or page_dates
    if meta_dates and chosen and meta_dates != chosen:
        return UNKNOWN_DATE
    if meta_dates and not chosen:
        chosen = meta_dates
    elif meta_dates and chosen:
        chosen = meta_dates
    if len(chosen) == 1:
        return chosen[0]
    fallback: list[str] = []
    for item in _time_dates(visible):
        _add_unique(fallback, item)
    for item in _prose_dates(_plain(visible)):
        _add_unique(fallback, item)
    if len(fallback) == 1:
        return fallback[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Kempner Institute when the page states that publisher.

    A person named on the page is not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site:
        if _names_kempner(site):
            return PUBLISHER
        raise CatalogError("publisher must be Kempner Institute")
    if _names_kempner(_plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError(
            "catalog fields must be catalog_id, description, runner_wired, and entries"
        )
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    if document.get("description") != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the Kempner Institute catalog contract")
    if len(CATALOG_DESCRIPTION) > MAX_DESCRIPTION_CHARS:
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
        raise CatalogError(
            "entry fields must be title, publisher, canonical URL, date, and rights"
        )
    _require_text(entry.get("title"), "title")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError(f"canonical URL must be a public Kempner Institute page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or host not in OFFICIAL_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _is_blocked_path(path)
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be a public Kempner Institute page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _ISO_DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    cc_codes: set[str] = set()
    software: set[str] = set()
    gov = False
    ogl_parts: list[str] = []
    for node in _ld_nodes(page_text):
        for raw in _json_strings(node.get("license")) + _json_strings(node.get("licence")):
            cleaned = _strip_credit_plain(raw)
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
            ogl_parts.append(cleaned)
        for raw in _json_strings(node.get("rights")):
            cleaned = _strip_credit_plain(raw)
            if _states_us_government_work(cleaned):
                gov = True
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
            ogl_parts.append(cleaned)
    visible = _visible(page_text)
    for key, value in _metas(visible).items():
        cleaned = _strip_credit_plain(value)
        if key in _LICENSE_META:
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
            ogl_parts.append(cleaned)
        if key in _RIGHTS_META:
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
            ogl_parts.append(cleaned)
            if _states_us_government_work(cleaned):
                gov = True
    scanned = _drop_generic_cc_anchors(_drop_credit_text(visible))
    plain = _plain(scanned)
    cc_codes |= _cc_codes(plain)
    software |= _software_codes(plain)
    for href in _hrefs(scanned):
        cc_codes |= _cc_codes(href)
        software |= _software_codes(href)
    ogl = OGL_PHRASE in plain.casefold() or any(OGL_PHRASE in _fold(part) for part in ogl_parts)
    return cc_codes, software, ogl, gov


def _drop_generic_cc_anchors(page_html: str) -> str:
    """Remove anchors that point at the generic Creative Commons licence index.

    That URL names no deed. CC BY or CC BY-SA written as its anchor text is
    not a licence. A versioned deed URL keeps its text.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _GENERIC_LICENSES_URL.fullmatch(_fold(href).replace(" ", "")):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _drop_credit_text(page_html: str) -> str:
    """Drop photo, caption, image, and background-credit licences.

    The page's own licence outside those credits still counts.
    """

    html = _drop_credit_sections(page_html)
    return _drop_credit_sentences(html)


def _drop_credit_sections(page_html: str) -> str:
    headings = list(_HEADING.finditer(page_html))
    spans: list[tuple[int, int]] = []
    for index, match in enumerate(headings):
        text = _TAG.sub(" ", match.group(0))
        if _CREDIT_HEADING.search(unescape(text)) is None:
            continue
        level = int(match.group(1))
        end = len(page_html)
        for nxt in headings[index + 1 :]:
            if int(nxt.group(1)) <= level:
                end = nxt.start()
                break
        footer = page_html.casefold().find("<footer", match.start())
        if footer != -1:
            end = min(end, footer)
        spans.append((match.start(), end))
    return _cut_spans(page_html, spans)


def _drop_credit_sentences(page_html: str) -> str:
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(page_html):
        start = match.start()
        last_open = page_html.rfind("<", 0, start)
        last_close = page_html.rfind(">", 0, start)
        if last_open > last_close:
            continue
        end = match.end()
        while end < len(page_html):
            if page_html[end] == ".":
                end += 1
                break
            if page_html[end] == "<":
                close = page_html.find(">", end)
                if close == -1:
                    end = len(page_html)
                    break
                tag = page_html[end : close + 1]
                if _BLOCK_CLOSE.match(tag):
                    break
                end = close + 1
                continue
            end += 1
        spans.append((start, end))
    return _cut_spans(page_html, spans)


def _strip_credit_plain(value: str) -> str:
    text = unescape(value)
    return re.sub(
        r"(?i)\b(?:photo|caption|image)(?:\s|&nbsp;)+credits?\b[^.]*\.?",
        " ",
        text,
    )


def _cut_spans(page_html: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return page_html
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    parts: list[str] = []
    last = 0
    for start, end in merged:
        parts.append(page_html[last:start])
        parts.append(" ")
        last = end
    parts.append(page_html[last:])
    return "".join(parts)


def _cc_codes(value: str) -> set[str]:
    folded = _fold(value)
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
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _software_codes(value: str) -> set[str]:
    folded = _fold(value)
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _fold(value))
    return _GOV_WORK.search(text) is not None


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
    merged: list[tuple[str, str]] = []
    found = False
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            found = True
            merged.extend(group_rules)
    if not found:
        return None
    return merged


def _robots_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "^" + ".*".join(re.escape(chunk) for chunk in body.split("*"))
    if anchored:
        regex += "$"
    return re.search(regex, path) is not None


def _robots_allow_url(body: str, url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query and not robots_allows(body, f"{path}?{parsed.query}"):
        return False
    return robots_allows(body, path)


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and is_official_host(parsed.hostname or "")


def _bare_path(path: str) -> str:
    if not path:
        return "/"
    bare = path[:-1] if path.endswith("/") and len(path) > 1 else path
    return bare or "/"


def _is_download(path: str) -> bool:
    return _bare_path(path).lower().endswith(_DOWNLOAD_SUFFIXES)


def _is_blocked_path(path: str) -> bool:
    lowered = (path or "/").casefold()
    if any(lowered.startswith(prefix) for prefix in _BLOCKED_PREFIXES):
        return True
    parts = {part for part in lowered.split("/") if part}
    return bool(parts & _LOGIN_PARTS)


def _blocked_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name == "sg-captcha" or "sg-captcha" in token:
            return True
        if name == "server" and "akamaighost" in token:
            return True
    return False


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip(" -|")
                changed = True
                break
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


def _names_kempner(value: str) -> bool:
    return "kempner institute" in _clean_text(value).casefold()


def _require_text(value: object, field: str) -> None:
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
        if len(value) > MAX_DESCRIPTION_CHARS and path != "$.description":
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _iso_day(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None
    return parsed.isoformat()


def _add_unique(found: list[str], value: str | None) -> None:
    if value and value not in found:
        found.append(value)


def _calendar_date(month_name: str, day: str, year: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        return date(int(year), month, int(day)).isoformat()
    except ValueError:
        return None


def _prose_dates(plain: str) -> list[str]:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        if match.group(1):
            parsed = _iso_day(match.group(1))
        elif match.group(4):
            parsed = _calendar_date(match.group(2), match.group(3), match.group(4))
        else:
            parsed = _calendar_date(match.group(6), match.group(5), match.group(7))
        _add_unique(found, parsed)
    return found


def _time_dates(visible: str) -> list[str]:
    found: list[str] = []
    for attrs, _inner in _TIME.findall(visible):
        attr = _attrs(f"<time {attrs}>")
        klass = attr.get("class", "").casefold()
        if "published" not in klass or "updated" in klass or "modified" in klass:
            continue
        _add_unique(found, _iso_day(attr.get("datetime", "")))
    return found


def _ld_nodes(page_html: str) -> list[dict]:
    nodes: list[dict] = []
    commented = _COMMENT.sub(" ", page_html)
    for blob in _LDJSON.findall(commented):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        nodes.extend(_flatten_ld(data))
    return nodes


def _flatten_ld(data: object) -> list[dict]:
    if isinstance(data, list):
        nodes: list[dict] = []
        for item in data:
            nodes.extend(_flatten_ld(item))
        return nodes
    if isinstance(data, dict):
        nodes = [data]
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                nodes.extend(_flatten_ld(item))
        return nodes
    return []


def _ld_types(node: dict) -> set[str]:
    raw = node.get("@type")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return set()
    return {str(item).casefold() for item in raw}


def _json_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        found: list[str] = []
        for key in ("url", "@id", "name", "text"):
            item = value.get(key)
            if isinstance(item, str):
                found.append(item)
        return found
    if isinstance(value, list):
        found = []
        for item in value:
            found.extend(_json_strings(item))
        return found
    return []


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for match in _HREF.finditer(page_html):
        href = unescape(match.group(1) or match.group(2) or match.group(3) or "").strip()
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


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.casefold(), unescape(raw).strip())
    return attrs
