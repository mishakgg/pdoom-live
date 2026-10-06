"""Metadata catalog of public Chatham House pages about artificial intelligence.

Hosts are www.chathamhouse.org and chathamhouse.org. chathamhouse.org redirects
to www.chathamhouse.org. robots.txt on www was fetched and allows public HTML.
It disallows /search/, /admin/, /user/login/, /core/, and /profiles/, and sets
Crawl-delay: 10. sitemap.xml returned HTTP 403. /topics/technology and public
AI article URLs then returned a Cloudflare block page (HTTP 403, title
Attention Required). Those paths contribute an empty catalog. The block was
not bypassed. The home page returned HTML and is not an AI page, so it is not
a row.

A row is stored only when one bounded GET returns HTML that stays on
www.chathamhouse.org or chathamhouse.org. Person profiles, PDFs, login walls,
and pages outside artificial intelligence, machine learning, or AI policy are
omitted. Each row keeps the title, publisher, canonical URL, date, and rights
label. Page text, abstracts, quotes, transcripts, and chart data are not
stored. Publisher is Chatham House. The live URL is stored as confirmed. A
different rel=canonical does not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution is CC BY alone, including a
https://creativecommons.org/licenses/by/4.0/ URL. creative_commons is CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
Two different restricted deeds stay unknown. A software licence beside any
Creative Commons deed stays unknown. Two software licences stay unknown. A
sole MIT License is mit. A sole MPL-2.0 is mpl-2.0. Apache License, Version
2.0 is apache-2.0. uk_ogl requires the exact British phrase Open Government
Licence. Open Government License stays unknown. us_government_work comes only
from an explicit rights metadata field.

A generic https://creativecommons.org/licenses/ URL stays unknown, including a
missing slash, http, www, or a query string. Anchor text on that generic URL
stays unknown. A specific deed URL still counts. Deceptive permissive anchor
text on a restricted deed URL or a public-domain mark URL stays unknown. A
CC0 anchor on a public-domain mark URL stays unknown. Photo credit, caption
credit, and image credit that name someone else's licence stay unknown,
including "Photo credit: UNDRR, CC BY-NC-ND 2.0" and "Photo: UNDRR, CC
BY-NC-ND 2.0". A page that says Licensed under CC BY 4.0 and also has that
photo credit stays creative_commons_attribution.

Publication dates only. Updated, modified, and copyright years stay unknown.
Script, style, and comment text does not count. This module does not fetch
and it does not import requests. It is not a belief collector. runner_wired
stays false.
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

CATALOG_ID = "chatham_ai_pages"
CATALOG_FILENAME = "chatham_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Chatham House"
OFFICIAL_HOSTS = frozenset({"www.chathamhouse.org", "chathamhouse.org"})
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
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
OGL_PHRASE = "open government licence"
MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public Chatham House pages on artificial intelligence, machine learning, "
    "or AI policy. Hosts are www.chathamhouse.org and chathamhouse.org. Publisher is "
    "Chatham House. The apex redirects to www. robots.txt allows public HTML and disallows "
    "/search/, /admin/, /user/login/, /core/, and /profiles/. sitemap.xml, the technology "
    "topic, and AI articles returned a Cloudflare block, so those paths are empty. "
    "Person profiles, PDFs, and login walls are omitted. Rows store a title, publisher, "
    "canonical URL, date, and rights. Page text is not stored. creative_commons_attribution "
    "is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. A missing date "
    "stays unknown. Updated, modified, and copyright years are not publication dates. "
    "Not a belief collector. runner_wired is false."
)
# Fetched from https://www.chathamhouse.org/robots.txt. The apex host redirects there.
# Crawl-delay is 10 seconds. These rules allow public article paths.
CONFIRMED_ROBOTS_TXT = """#
# robots.txt
#
# This file is to prevent the crawling and indexing of certain parts
# of your site by web crawlers and spiders run by sites like Yahoo!
# and Google. By telling these "robots" where not to go on your site,
# you save bandwidth and server resources.
#
# This file will be ignored unless it is at the root of your host:
# Used:    http://example.com/robots.txt
# Ignored: http://example.com/site/robots.txt
#
# For more information about the robots.txt standard, see:
# http://www.robotstxt.org/robotstxt.html

User-agent: *
Sitemap: https://www.chathamhouse.org/sitemap.xml
Crawl-delay: 10
Disallow: /search/
Disallow: /search*
Disallow: /search/*
Allow: /sitemap.xml*
# CSS, JS, Images
Allow: /core/*.css$
Allow: /core/*.css?
Allow: /core/*.js$
Allow: /core/*.js?
Allow: /core/*.gif
Allow: /core/*.jpg
Allow: /core/*.jpeg
Allow: /core/*.png
Allow: /core/*.svg
Allow: /profiles/*.css$
Allow: /profiles/*.css?
Allow: /profiles/*.js$
Allow: /profiles/*.js?
Allow: /profiles/*.gif
Allow: /profiles/*.jpg
Allow: /profiles/*.jpeg
Allow: /profiles/*.png
Allow: /profiles/*.svg
# Directories
Disallow: /core/
Disallow: /profiles/
# Files
Disallow: /README.txt
Disallow: /web.config
# Paths (clean URLs)
Disallow: /admin/
Disallow:/conflicteconomies
Disallow: /comment/reply/
Disallow:/dashboard/
Disallow: /filter/tips
Disallow: /node/add/
Disallow:/redirect-back-after-login/
Disallow: /user/register/
Disallow: /user/password/
Disallow: /user/login/
Disallow: /user/logout/
# Paths (no clean URLs)
Disallow: /index.php/admin/
Disallow: /index.php/comment/reply/
Disallow: /index.php/filter/tips
Disallow: /index.php/node/add/
Disallow: /index.php/search/
Disallow: /index.php/user/password/
Disallow: /index.php/user/register/
Disallow: /index.php/user/login/
Disallow: /index.php/user/logout/
Disallow:/*%2525*
"""
# HTTP 403 Cloudflare block pages. Each path contributes no row.
CHALLENGE_SKIPPED_PATHS = (
    "https://www.chathamhouse.org/sitemap.xml",
    "https://www.chathamhouse.org/topics/technology",
    "https://www.chathamhouse.org/2026/09/artificial-intelligence-real-fears-time-slow-down-independent-thinking-podcast",
    "https://www.chathamhouse.org/2026/09/chatham-house-fellow-gives-evidence-uk-parliament-committee-global-ai-governance-and-risks",
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
_PROFILE_PARTS = frozenset(
    {
        "author",
        "authors",
        "bio",
        "biography",
        "expert",
        "experts",
        "our-people",
        "people",
        "person",
        "persons",
        "profile",
        "profiles",
        "staff",
    }
)
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "admin",
        "cdn-cgi",
        "comment",
        "core",
        "dashboard",
        "filter",
        "log-in",
        "login",
        "node",
        "search",
        "sign-in",
        "signin",
        "signup",
        "user",
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
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_TITLE_CHALLENGE = (
    "just a moment",
    "attention required",
    "sorry, you have been blocked",
)
_BODY_CHALLENGE = (
    "sorry, you have been blocked",
    "checking your browser",
    "cf-browser-verification",
    "performing security verification",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "enable javascript and cookies",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
_YEAR = re.compile(r"(?:19|20)\d{2}")
_MONTH = re.compile(r"(?:0[1-9]|1[0-2])")
_SEGMENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"((?:\\.|[^"\\])*)"')
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"((?:\\.|[^"\\])*)"')
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_TYPE = re.compile(r'"@type"\s*:\s*"([^"]*)"')
_LD_TYPE_LIST = re.compile(r'"@type"\s*:\s*\[([^\]]*)\]')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_PASSWORD = re.compile(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]")
_GENERIC_LICENSES_URL = re.compile(
    r"(?i)^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:[?#]\S*)?$"
)
_MARK_URL = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
_CREDIT_START = re.compile(
    r"(?i)\b(?:photo|caption|image)(?:[\s-]+credits?\b|\s*:)"
)
_BLOCK_CLOSE = re.compile(
    r"(?i)^</(?:p|div|li|figcaption|figure|caption|blockquote|section|article|td|dd|h[1-6])\b"
)
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_ARTICLE_TYPES = frozenset(
    {"article", "blogposting", "newsarticle", "scholarlyarticle", "report"}
)
_SITE_SUFFIXES = (
    " | chatham house - international affairs think tank",
    " - chatham house - international affairs think tank",
    " | chatham house",
    " - chatham house",
)
_SITE_ONLY = frozenset(
    {
        "chatham house",
        "chatham house - international affairs think tank",
    }
)
_AI_TOPIC = re.compile(
    r"(?i)(?:"
    r"artificial[\s-]+intelligence"
    r"|machine[\s-]+learning"
    r"|large[\s-]+language[\s-]+models?"
    r"|\bchatgpt\b"
    r"|\b(?:a\.i\.|ai)\b"
    r")"
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
# Longer deeds are listed first. `(?!-)` makes a hyphen a word boundary, so
# licenses/by and CC BY do not match licenses/by-nc or CC BY-NC.
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
        re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b)"),
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
    r"(?<!modified )\bmit licen[cs]e\b"
    r"|(?<!modified )(?<!modified the )\blicen[cs]ed under (?:the )?mit\b(?!-)"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
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
_PUBLISHED_PROSE = re.compile(
    r"(?<!last )(?<!updated )(?<!modified )(?<!copyright )"
    r"\b(?:publication date|date published|published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})"
    r"|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"
    r"|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
    re.I,
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


class CatalogError(ValueError):
    """A catalog row or page failed the Chatham House page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for www.chathamhouse.org and chathamhouse.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def robots_allows(body: str, path: str) -> bool:
    """True when the * group does not disallow path.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. Comment-only robots text allows every path.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or is_challenge_page(body[:8000]):
        return False
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix or not target.startswith(prefix):
            continue
        if kind == "allow":
            allowed = max(allowed, len(prefix))
        else:
            disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is a Cloudflare block or captcha interstitial.

    A normal page that only loads /cdn-cgi/challenge-platform/scripts/ is not
    a challenge. The block page titles Attention Required and Sorry, you have
    been blocked are.
    """

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    if any(marker in title for marker in _TITLE_CHALLENGE):
        return True
    sample = page_html[:12000].casefold()
    return any(marker in sample for marker in _BODY_CHALLENGE)


def is_login_wall(page_html: str) -> bool:
    """True when the visible response asks for a password."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    return _PASSWORD.search(_visible(page_html)) is not None


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge.

    HTTP 202, HTTP 401, HTTP 403, a Cloudflare or SiteGround challenge, an
    Akamai block, a login wall, and a final URL on another host are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
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
) -> dict | None:
    """Return metadata when the response is an allowed Chatham House AI page.

    A Cloudflare block, a captcha, an authentication wall, a robots disallow,
    a non-HTML body, a login wall, a person profile, a PDF, an off-topic page,
    or an off-host redirect is not stored.
    """

    target = final_url or page_url
    if robots_txt is not None:
        path = urlparse(target).path or "/"
        if not robots_allows(robots_txt, path):
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


def rows_for_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> list[dict]:
    """Return catalog rows for one response.

    A Cloudflare block, a captcha, an authentication wall, an unresolved host
    response, or a robots disallow records an empty catalog for that path.
    """

    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        robots_txt=robots_txt,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY and licenses/by is not licenses/by-nc.
    Photo credit, caption credit, image credit, and a Photo: credit sentence
    do not count. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, gov = _rights_signals(page_text)
    cc_codes.discard("pd-mark")
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
        return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated times, modified times, and copyright years are not publication dates.
    A date inside script, style, or comment text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    source = _COMMENT.sub(" ", page_html)
    found: list[str] = []
    for blob in _LDJSON.findall(source):
        if not _ld_types(blob) & _ARTICLE_TYPES:
            continue
        for raw in _DATE_PUBLISHED.findall(blob):
            parsed = _iso_day(raw)
            if parsed:
                found.append(parsed)
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            found.append(parsed)
    unique = set(found)
    if len(unique) == 1:
        return next(iter(unique))
    if len(unique) > 1:
        return UNKNOWN_DATE
    return _published_prose(_plain(visible))


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
    """Return Chatham House when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if _names_chatham(metas.get(key, "")):
            return PUBLISHER
    if _names_chatham(_plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed Chatham House AI page.

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
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    if document.get("description") != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the Chatham House catalog contract")
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
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    if not _in_scope(str(entry.get("title")), str(entry.get("canonical_url"))):
        raise CatalogError("page is outside artificial intelligence, machine learning, or AI policy")
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError(f"canonical URL must be a public Chatham House AI page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != host
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
        or not _is_content_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public Chatham House AI page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    cc_codes: set[str] = set()
    software: set[str] = set()
    gov = False
    commented = _COMMENT.sub(" ", page_text)
    for blob in _LDJSON.findall(commented):
        for raw in _LD_LICENSE.findall(blob):
            cleaned = _drop_credit_clauses(raw)
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
        for raw in _LD_RIGHTS.findall(blob):
            cleaned = _drop_credit_clauses(raw)
            if _states_us_government_work(cleaned):
                gov = True
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
    visible = _drop_non_deed_anchors(_drop_credit_clauses(_visible(page_text)))
    for key, value in _metas(visible).items():
        cleaned = _drop_credit_clauses(value)
        if key in _LICENSE_META or key in _RIGHTS_META:
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
        if key in _RIGHTS_META and _states_us_government_work(cleaned):
            gov = True
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(visible):
        if not _is_rights_element(attrs):
            continue
        text = _drop_credit_clauses(_plain(body))
        if text and len(text) <= MAX_FIELD_CHARS:
            cc_codes |= _cc_codes(text)
            software |= _software_codes(text)
            if _states_us_government_work(text):
                gov = True
    plain = _plain(visible)
    cc_codes |= _cc_codes(plain)
    software |= _software_codes(plain)
    for href in _hrefs(visible):
        cc_codes |= _cc_codes(href)
        software |= _software_codes(href)
    ogl = OGL_PHRASE in plain.casefold()
    return cc_codes, software, ogl, gov


def _drop_non_deed_anchors(page_html: str) -> str:
    """Drop generic licence-index anchors and public-domain mark anchors.

    Anchor text on those URLs is not a licence. A specific deed URL keeps its
    text, so a CC BY label on a restricted deed still conflicts with that deed.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        folded = _fold(href)
        if _GENERIC_LICENSES_URL.fullmatch(folded) or _MARK_URL.search(folded):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _drop_credit_clauses(page_html: str) -> str:
    """Drop photo, caption, and image credits, including a Photo: sentence.

    The page's own licence outside that sentence still counts. "Photo credit:
    UNDRR, CC BY-NC-ND 2.0" and "Photo: UNDRR, CC BY-NC-ND 2.0" do not.
    """

    normalized = page_html.replace("&nbsp;", " ").replace("&#160;", " ").replace("\xa0", " ")
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_START.finditer(normalized):
        start = match.start()
        last_open = normalized.rfind("<", 0, start)
        last_close = normalized.rfind(">", 0, start)
        if last_open > last_close:
            continue
        end = match.end()
        while end < len(normalized):
            if normalized[end] == ".":
                if end + 1 < len(normalized) and normalized[end + 1].isdigit():
                    end += 1
                    continue
                end += 1
                break
            if normalized[end] == "<":
                close = normalized.find(">", end)
                if close == -1:
                    end = len(normalized)
                    break
                tag = normalized[end : close + 1]
                if _BLOCK_CLOSE.match(tag):
                    break
                end = close + 1
                continue
            end += 1
        spans.append((start, end))
    return _cut_spans(normalized, spans)


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
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            return group_rules
    return None


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and is_official_host(parsed.hostname or "")


def _is_content_path(path: str) -> bool:
    if path != path.lower() or (len(path) > 1 and path.endswith("/")):
        return False
    raw = path[:-1] if path.endswith("/") and len(path) > 1 else path
    if raw.lower().endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in raw.split("/") if part]
    if not parts or any(part in _PROFILE_PARTS or part in _BLOCKED_PARTS for part in parts):
        return False
    if not all(_SEGMENT.fullmatch(part) for part in parts):
        return False
    if len(parts) >= 3 and _YEAR.fullmatch(parts[0]) and _MONTH.fullmatch(parts[1]):
        return True
    if parts[0] in {"publications", "events"} and len(parts) >= 2:
        return True
    if parts[0] == "topics" and len(parts) >= 2 and _AI_TOPIC.search(path):
        return True
    return False


def _in_scope(title: str, url: str) -> bool:
    path = urlparse(url).path
    return _AI_TOPIC.search(f"{title}\n{path}") is not None


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


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    if match.group(1):
        return _iso_day(match.group(1)) or UNKNOWN_DATE
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4)) or UNKNOWN_DATE
    return _calendar_date(match.group(6), match.group(5), match.group(7)) or UNKNOWN_DATE


def _names_chatham(value: str) -> bool:
    return re.search(r"\bchatham house\b", _clean_text(value).casefold()) is not None


def _ld_types(blob: str) -> set[str]:
    found = {match.group(1).casefold() for match in _LD_TYPE.finditer(blob)}
    for match in _LD_TYPE_LIST.finditer(blob):
        for part in match.group(1).split(","):
            token = part.strip().strip("\"'").casefold()
            if token:
                found.add(token)
    return found


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _clean_text(value).translate(_DASHES)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix) and len(folded) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    if text.casefold() in _SITE_ONLY:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


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


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


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


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False
