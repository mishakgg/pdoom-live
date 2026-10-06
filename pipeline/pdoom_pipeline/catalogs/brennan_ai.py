"""Metadata catalog of public Brennan Center for Justice AI and technology pages.

Hosts are www.brennancenter.org and brennancenter.org. brennancenter.org
redirects to www.brennancenter.org. A row is stored only after one bounded
HTML GET that robots.txt allows and that stays on those hosts. Pages are
artificial-intelligence and technology reports, analysis, policy solutions,
court cases, series, events, and topic pages, plus AI-series collection pages
whose titles state artificial intelligence, automated systems, data brokers,
social-media monitoring, or police surveillance transparency.

If a host does not resolve, robots.txt is HTML or a challenge, or the page is
a Cloudflare, cookie, or captcha challenge, or the URL redirects off these
hosts, nothing from that response is stored. An empty catalog is valid in
those cases. Login walls, PDFs, and downloads are omitted.

A row keeps the title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, chart data, and PDFs are
not stored. The live URL is stored as confirmed. A different rel=canonical
does not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is CC0,
CC BY-SA, or a permissive mix of those. One sole restricted deed keeps
``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``, or ``cc_by_nc_nd``. A hyphen is
a word boundary, so CC BY does not match CC BY-NC and licenses/by does not
match licenses/by-nc. Two different restricted deeds stay unknown. A software
licence beside any Creative Commons deed stays unknown. Two software licences
stay unknown. A generic creativecommons.org/licenses or /licenses/ URL is not
a deed: anchor text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays
unknown. The same rule covers a missing trailing slash, http, a www host, and
a query string. A specific deed URL still counts. Text elsewhere on the page
still counts. Deceptive permissive anchor text on a restricted deed URL or on
a public-domain mark URL stays unknown. A CC0 anchor on a public-domain mark
URL stays unknown. A photo credit, caption credit, or image credit that names
someone else's licence stays unknown. ``uk_ogl`` requires the British phrase
Open Government Licence. American spelling License stays unknown.
``us_government_work`` requires an explicit rights metadata field. Bare MIT
stays unknown. Licensed under the MIT License is mit. Apache License,
Version 2.0 is apache-2.0. Script, style, and comment text does not count.

Updated, modified, and copyright years are not publication dates. This module
does not fetch. It is not a belief collector, and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "brennan_ai_pages"
CATALOG_FILENAME = "brennan_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Brennan Center for Justice"
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
OFFICIAL_HOSTS = frozenset({"www.brennancenter.org", "brennancenter.org"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public Brennan Center for Justice pages about artificial intelligence and technology "
    "on www.brennancenter.org and brennancenter.org. Each row was confirmed with one bounded GET that "
    "stayed on those hosts. A host that does not resolve, an HTML or challenge robots.txt, a Cloudflare, "
    "cookie, or captcha challenge, a robots disallow, or an off-host redirect is omitted. An empty "
    "catalog is valid. Rows store title, publisher, canonical URL, publication date, and rights. Page "
    "text is not stored. creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, "
    "or a permissive mix of those. A missing date is unknown. Updated, modified, and copyright years are "
    "not publication dates. This catalog is not a belief collector and runner_wired is false."
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
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PUBLICATION_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dc.date.issued",
        "dcterms.issued",
        "publish_date",
    }
)
_PAGE_DATE_TYPES = frozenset(
    {
        "analysisnewsarticle",
        "article",
        "blogposting",
        "liveblogposting",
        "newsarticle",
        "opinionnewsarticle",
        "report",
        "scholarlyarticle",
        "socialmediaposting",
        "techarticle",
    }
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META_SUFFIXES = ("license", "licence")
_TITLE_KEYS = ("og:title", "citation_title", "twitter:title", "dcterms.title")
_GENERIC_TITLES = frozenset({"brennan center for justice", "brennan center"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_PUBLISHED_LABEL = re.compile(
    r"(?is)<div\b[^>]*\bpage-info-header__date\b[^>]*>\s*<label>\s*Published\s*</label>\s*([^<]+)"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " | Brennan Center for Justice",
    " - Brennan Center for Justice",
    " – Brennan Center for Justice",
    " — Brennan Center for Justice",
)
_SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_WORK_SECTIONS = frozenset(
    {"analysis-opinion", "court-cases", "policy-solutions", "research-reports"}
)
_TOPIC_SEGMENTS = frozenset({"ai", "grok", "tech", "technologies", "technology"})
_TOPIC_PHRASES = (
    "algorithm",
    "artificial-intelligence",
    "automated-decision",
    "biometric",
    "chatgpt",
    "deep-fake",
    "deepfake",
    "face-recognition",
    "facial-recognition",
    "generative-ai",
    "machine-learning",
    "predictive-policing",
)
_EXCLUDED_MARKERS = ("big-tech-money", "political-spending", "qualcomm")
# AI-series collection pages whose slugs do not carry an AI or technology token.
# Titles confirmed on the series pages name artificial intelligence, automated
# systems, data brokers, social-media monitoring, or police transparency law.
_EXACT_PATHS = frozenset(
    {
        "/our-work/analysis-opinion/dhs-must-overhaul-its-flawed-automated-systems",
        "/our-work/analysis-opinion/new-york-city-must-strengthen-police-transparency-law",
        "/our-work/research-reports/closing-data-broker-loophole",
        "/our-work/research-reports/comment-submitted-office-management-and-budget-federal-procurement",
        "/our-work/research-reports/comments-submitted-federal-trade-commission-social-media-monitoring",
        "/our-work/research-reports/comments-submitted-office-management-and-budget-draft-guidance-government",
    }
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".epub",
    ".mp3",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
)
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "cf-browser-verification",
    "attention required",
    "sorry, you have been blocked",
    "are you a robot",
    "are you human",
    "cookie challenge",
)
_ANYWHERE_MARKERS = (
    "sg-captcha",
    "sgcaptcha",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
    "hcaptcha",
    "g-recaptcha",
    "/.well-known/sgcaptcha/",
)
_LOGIN_WALL = re.compile(
    r"(?is)<input\b[^>]*type\s*=\s*['\"]password['\"]|please (?:log|sign) in|authentication required"
)
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
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-)"
    r"|publicdomain/(?P<pd>zero|mark)(?!-))"
    r"(?![a-z0-9])"
)
_TEXT_DEEDS = (
    (
        "cc-by-nc-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc\b(?!-)"
            r"|creative commons attribution[\s-]*non[\s-]*commercial\b(?!-)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nd\b(?!-)"
            r"|creative commons attribution[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*sa\b(?!-)"
            r"|creative commons attribution[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc0",
        re.compile(r"\bcc[\s-]*0\b|\bcc0\b|\bcc[\s-]*zero\b|creative commons zero\b"),
    ),
    (
        "cc-by",
        re.compile(r"\bcc[\s-]*by\b(?!-)|creative commons attribution\b(?!-)"),
    ),
)
_PERMISSIVE = frozenset({"cc0", "cc-by", "cc-by-sa"})
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-nd", "cc-by-nc-sa"})
_RESTRICTED_TOKENS = {
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_MIT_TEXT = re.compile(
    r"(?<!modified )(?:\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b)"
)
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_TEXT = re.compile(
    r"\bapache[\s-]*2\.0\b|\bapache licen[cs]e,?\s*(?:version\s+)?2(?:\.0)?\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_TEXT = re.compile(
    r"\bmpl[\s-]*2\.0\b|\bmozilla public licen[cs]e(?:[\s-]*version)?[\s-]*2(?:\.0)?\b"
)
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_SOFTWARE = (
    ("mit", _MIT_TEXT, _MIT_URL),
    ("apache-2.0", _APACHE_TEXT, _APACHE_URL),
    ("mpl-2.0", _MPL_TEXT, _MPL_URL),
)
_SOFTWARE_TOKENS = {
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_CREDIT_PHRASE = re.compile(
    r"(?i)\b(?:photo|image|caption)\s+credits?\b|\b(?:photo|image|caption)\s*:"
)
_CREDIT_CLASS = re.compile(
    r"(?i)(?:photo[\s_-]*credit|image[\s_-]*credit|caption[\s_-]*credit|wp-caption)"
)
_CREDIT_CLOSE = re.compile(
    r"(?i)</(?:p|figcaption|li|div|h[1-6]|blockquote|section|article|td|dd|cite|span|small|figure)\b"
)
_CREDIT_BLOCK = re.compile(r"(?is)<(p|li|figcaption|td|dd|figure)\b([^>]*)>(.*?)</\1>")
_FIGURE_CAPTION = re.compile(r"(?i)^figure\s+\d+\b")
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"', re.I)
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
_ROBOTS_END = "$"


class CatalogError(ValueError):
    """A catalog row or page failed the Brennan Center page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for www.brennancenter.org and brennancenter.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_topic_path(path: str) -> bool:
    """True for an artificial-intelligence or technology HTML path on the official hosts."""

    if not isinstance(path, str) or not path.startswith("/") or path != path.casefold():
        return False
    if ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    bare = path[:-1] if path.endswith("/") and path != "/" else path
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if bare in _EXACT_PATHS:
        return True
    parts = [part for part in bare.split("/") if part]
    if not parts or any(_SEGMENT.fullmatch(part) is None for part in parts):
        return False
    if parts[0] == "our-work":
        if len(parts) != 3 or parts[1] not in _WORK_SECTIONS:
            return False
    elif parts[0] in {"series", "events"}:
        if len(parts) != 2:
            return False
    elif parts[0] == "topics":
        if len(parts) < 2:
            return False
    else:
        return False
    return _topic_slug(parts[-1])


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    return content_type.split(";", 1)[0].strip().casefold() in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _ANYWHERE_MARKERS):
        return True
    head = lowered[:8000]
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    blob = head + "\n" + title
    return any(marker in blob for marker in _HEAD_MARKERS)


def is_login_wall(page_html: str) -> bool:
    """True when the response is an authentication form rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    return _LOGIN_WALL.search(page_html[:20000]) is not None


def robots_allows_path(robots_text: str, path: str, user_agent: str = "pdoom.live-collector") -> bool:
    """True when robots.txt does not disallow path for this collector.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. Wildcard and end-anchored rules are honored.
    """

    if not isinstance(robots_text, str):
        return False
    sample = robots_text[:800].casefold()
    if "<html" in sample or is_challenge_page(robots_text[:8000]):
        return False
    groups = _robots_groups(robots_text)
    if not groups:
        return True
    rules = _matching_rules(groups, user_agent)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    return _path_allowed(rules, target)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    requested_urls: list[str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a block or challenge."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if is_login_wall(page_html):
        return False
    if headers and _blocked_headers(headers):
        return False
    urls = list(requested_urls or [])
    if final_url:
        urls.append(final_url)
    for url in urls:
        if not _on_official_host(url):
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
    requested_urls: list[str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded GET confirmed an on-topic page.

    A challenge, a captcha, a cookie wall, a non-HTML body, a robots disallow,
    a login page, an unresolved host, or an off-host redirect is not stored.
    """

    if robots_text is not None:
        for url in [page_url, *(requested_urls or []), final_url or ""]:
            if not url:
                continue
            if not robots_allows_path(robots_text, _robots_path(url)):
                return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=final_url,
        requested_urls=requested_urls if requested_urls is not None else [page_url],
    ):
        return None
    assert isinstance(page_html, str)
    stored_url = final_url or page_url
    try:
        return page_record(page_html, page_url=stored_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A hyphen is a word boundary, so CC BY-NC is not CC BY. Anchor text on a
    generic creativecommons.org/licenses URL does not count, including CC BY,
    CC BY 4.0, and CC BY-SA. A missing trailing slash, http, a www host, and
    a query string on that path stay unknown. Text elsewhere still counts. A
    specific deed URL still counts. Deceptive permissive anchor text on a
    restricted or public-domain mark URL stays unknown, including a CC0
    anchor on a public-domain mark URL. A photo, caption, or image credit
    that names someone else's licence stays unknown. A software licence beside
    any Creative Commons deed stays unknown. Two software licences stay
    unknown. Two different restricted deeds stay unknown. Script, style, and
    comment text does not count. Bare MIT stays unknown. Licensed under the
    MIT License is mit. Apache License, Version 2.0 is apache-2.0.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, gov = _licence_signals(page_text)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = codes & set(_SOFTWARE_TOKENS)
    ogl = "uk_ogl" in codes
    if restricted and (permissive or software or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if software and (permissive or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(software) == 1:
        return _SOFTWARE_TOKENS[next(iter(software))]
    if gov and (permissive or ogl):
        return RIGHTS_UNKNOWN
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    if ogl and permissive:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if permissive == frozenset({"cc-by"}):
        return RIGHTS_CC_ATTRIBUTION
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    datePublished, publish_date, article:published_time, and a Published label
    count. article:modified_time, updated_date, sort_date, dateModified, an
    Updated label, a related-content time tag, and a copyright year do not.
    Disagreeing publication dates stay unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found: list[str] = []
    for raw in _page_date_published_values(page_html):
        parsed = _iso_day(raw)
        if parsed:
            found.append(parsed)
    visible = _without_hidden(page_html)
    for key, content in _meta_pairs(visible):
        if key not in _PUBLICATION_META:
            continue
        parsed = _iso_day(content)
        if parsed:
            found.append(parsed)
    for raw in _PUBLISHED_LABEL.findall(visible):
        parsed = _human_date(_clean_text(raw))
        if parsed:
            found.append(parsed)
    distinct = set(found)
    if len(distinct) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _usable_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _usable_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _usable_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Brennan Center for Justice when the page states that name."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher", "publisher"):
        if PUBLISHER.casefold() in _clean_text(metas.get(key, "")).casefold():
            return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if is_login_wall(page_html):
        raise CatalogError("login wall is not stored")
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
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog contract")
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
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError("rights must be a known label or unknown")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Brennan Center AI or technology page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or not is_official_host(host)
        or parsed.netloc.lower() != host
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or path != path.casefold()
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Brennan Center AI or technology page: {url}")
    return url


def _topic_slug(slug: str) -> bool:
    if any(marker in slug for marker in _EXCLUDED_MARKERS):
        return False
    segments = set(slug.split("-"))
    if segments & _TOPIC_SEGMENTS:
        return True
    return any(phrase in slug for phrase in _TOPIC_PHRASES)


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and is_official_host(parsed.hostname or "")


def _robots_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _blocked_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name in {"sg-captcha", "x-captcha"}:
            return True
        if "captcha" in name:
            return True
    return False


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    page_text = _strip_image_credits(page_text)
    page_text = _strip_generic_license_anchors(_strip_mark_anchors(page_text))
    without_comments = _COMMENT.sub(" ", page_text)
    codes: set[str] = set()
    gov = False
    for license_text, rights_text in _jsonld_rights(without_comments):
        codes |= _codes_in_string(license_text)
        codes |= _codes_in_string(rights_text)
        if _states_us_government_work(rights_text):
            gov = True
    visible = _SCRIPT_STYLE.sub(" ", without_comments)
    for value in _license_meta_texts(visible):
        codes |= _codes_in_string(value)
    for value in _rights_field_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    plain = _plain(visible)
    folded = _fold(plain)
    codes |= _codes_in_folded(folded)
    if _OGL_PHRASE.search(folded):
        codes.add("uk_ogl")
    for href in _hrefs(visible):
        codes |= _codes_in_string(href)
    return codes, gov


def _codes_in_string(value: str) -> set[str]:
    if not value:
        return set()
    return _codes_in_folded(_fold(value))


def _codes_in_folded(folded: str) -> set[str]:
    """Licence codes in one folded string. Longer deeds win overlaps."""

    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            codes.add(f"cc-{license_code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
    hits: list[tuple[int, int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            hits.append((match.end() - match.start(), match.start(), match.end(), code))
    hits.sort(key=lambda item: (-item[0], item[1]))
    occupied: list[tuple[int, int]] = []
    for _length, start, end, code in hits:
        if any(start < right and end > left for left, right in occupied):
            continue
        occupied.append((start, end))
        codes.add(code)
    for code, text_pattern, url_pattern in _SOFTWARE:
        if text_pattern.search(folded) or url_pattern.search(folded):
            codes.add(code)
    return codes


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _fold(value))
    return _GOV_WORK.search(text) is not None


def _jsonld_rights(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for block in _LDJSON.findall(page_html):
        licenses = [item.replace("\\/", "/") for item in _LD_LICENSE.findall(block)]
        rights = [item.replace("\\/", "/") for item in _LD_RIGHTS.findall(block)]
        if not licenses and not rights:
            continue
        width = max(len(licenses), len(rights), 1)
        licenses.extend([""] * (width - len(licenses)))
        rights.extend([""] * (width - len(rights)))
        found.extend(zip(licenses, rights, strict=True))
    return found


def _license_meta_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _meta_pairs(page_html):
        if key in {"license", "licence"} or key.endswith((".license", ".licence", ":license", ":licence")):
            found.append(value)
        elif any(key == suffix for suffix in _LICENSE_META_SUFFIXES):
            found.append(value)
    return found


def _rights_field_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _meta_pairs(page_html):
        if key in _RIGHTS_META or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
    for tag in re.findall(r"(?is)<[^>]*\bitemprop\s*=\s*['\"]rights['\"][^>]*>", page_html):
        content = _attrs(tag).get("content", "")
        if content:
            found.append(content)
    return found


def _page_date_published_values(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
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
    if isinstance(payload.get("@graph"), list):
        _collect_published(payload["@graph"], found)
        return
    types = payload.get("@type", "")
    if isinstance(types, str):
        types = [types]
    names = {str(item).casefold() for item in types} if isinstance(types, list) else set()
    raw = payload.get("datePublished")
    if isinstance(raw, str) and (not names or names & _PAGE_DATE_TYPES):
        found.append(raw)
    for value in payload.values():
        if isinstance(value, (dict, list)):
            _collect_published(value, found)


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        folded = _fold(href)
        if "creativecommons.org/publicdomain/mark" in folded:
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for the Creative Commons licences index, not a deed."""

    text = unescape(href or "").strip()
    if not text:
        return False
    if text.startswith("//"):
        text = "https:" + text
    elif "://" not in text:
        bare = text.lstrip("/")
        lowered = bare.casefold()
        if lowered.startswith("creativecommons.org") or lowered.startswith("www.creativecommons.org"):
            text = "https://" + bare
        else:
            return False
    parsed = urlparse(text)
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in _GENERIC_CC_HOSTS:
        return False
    path = (parsed.path or "").casefold()
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _strip_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose href is only the generic licences index."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _strip_image_credits(page_html: str) -> str:
    """Drop photo, caption, and image credits that name someone else's licence."""

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if _CREDIT_CLASS.search(attrs):
            return " "
        if len(body) <= 800:
            plain = _clean_text(body)
            if _FIGURE_CAPTION.match(plain) and _codes_in_string(plain):
                return " "
        return match.group(0)

    stripped = _CREDIT_BLOCK.sub(replace_block, page_html)
    return _drop_credit_sentences(stripped)


def _drop_credit_sentences(page_html: str) -> str:
    out: list[str] = []
    cursor = 0
    while cursor < len(page_html):
        match = _CREDIT_PHRASE.search(page_html, cursor)
        if match is None:
            out.append(page_html[cursor:])
            break
        previous_open = page_html.rfind("<", cursor, match.start())
        previous_close = page_html.rfind(">", cursor, match.start())
        if previous_open > previous_close:
            out.append(page_html[cursor:match.end()])
            cursor = match.end()
            continue
        out.append(page_html[cursor:match.start()])
        index = match.end()
        while index < len(page_html):
            if page_html[index] == "<":
                if _CREDIT_CLOSE.match(page_html, index) or re.match(r"(?i)<br\b", page_html[index:]):
                    break
                end = page_html.find(">", index)
                if end == -1:
                    index = len(page_html)
                    break
                index = end + 1
                continue
            if page_html[index] in ".?!":
                nxt = page_html[index + 1] if index + 1 < len(page_html) else ""
                if page_html[index] == "." and nxt.isdigit():
                    index += 1
                    continue
                index += 1
                break
            index += 1
        cursor = index
    return "".join(out)


def _human_date(value: str) -> str | None:
    text = value.strip().rstrip(".")
    iso = _iso_day(text)
    if iso and _DATE.fullmatch(text):
        return iso
    month_first = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{1,2}),\s+(\d{4})", text)
    if month_first:
        return _calendar_date(month_first.group(1), month_first.group(2), month_first.group(3))
    day_first = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})", text)
    if day_first:
        return _calendar_date(day_first.group(2), day_first.group(1), day_first.group(3))
    return None


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold().rstrip("."))
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    value = match.group(1)
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
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


def _usable_title(value: str) -> str:
    title = _clean_title(value)
    if not title or title.casefold() in _GENERIC_TITLES:
        return ""
    return title


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    lowered = text.casefold()
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix.casefold()) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                lowered = text.casefold()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _meta_pairs(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and attrs.get("content"):
            found.append((key, attrs["content"]))
    return found


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs in _ANCHOR.findall(page_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if href:
            found.append(href)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
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
    wildcard: list[tuple[str, str]] = []
    saw_wildcard = False
    for agents, rules in groups:
        matched_specific = False
        for agent in agents:
            if agent == "*":
                saw_wildcard = True
                wildcard.extend(rules)
                continue
            if product.startswith(agent) or (haystack.startswith(agent) and agent):
                matched_specific = True
        if matched_specific:
            specific.append((max(len(agent) for agent in agents if agent != "*"), rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    if saw_wildcard:
        return wildcard
    return None


def _path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    allowed = -1
    disallowed = -1
    for kind, pattern in rules:
        if not pattern or not _robots_pattern_matches(pattern, path):
            continue
        weight = len(pattern)
        if kind == "allow":
            allowed = max(allowed, weight)
        else:
            disallowed = max(disallowed, weight)
    if allowed < 0 and disallowed < 0:
        return True
    return allowed >= disallowed


def _robots_pattern_matches(pattern: str, path: str) -> bool:
    anchored = pattern.endswith(_ROBOTS_END)
    body = pattern[:-1] if anchored else pattern
    parts: list[str] = []
    for char in body:
        if char == "*":
            parts.append(".*")
        else:
            parts.append(re.escape(char))
    expression = "".join(parts)
    if anchored:
        return re.search(f"^{expression}$", path) is not None
    return re.search(f"^{expression}", path) is not None
