"""Metadata catalog of public World Economic Forum research and news pages about AI.

Hosts are www.weforum.org and weforum.org. Stored pages are research or news
HTML about artificial intelligence. Person profiles, login walls, PDFs, and
unrelated topics are omitted. Each stored URL was confirmed with one bounded
GET of public HTML that robots.txt allowed. A Cloudflare challenge, a captcha,
an authentication wall, an HTML document in place of robots.txt, a host that
does not resolve, an HTTP error, a non-HTML body, a robots disallow, or a
redirect off these hosts is not stored. An empty entries list is valid in
those cases. A row keeps the title, publisher, canonical URL, publication
date, and rights label. Page text, abstracts, quotes, transcripts, chart
data, and PDFs are not stored. This catalog does not invent p(doom) numbers.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` means CC BY alone, including a specific
https://creativecommons.org/licenses/by/4.0/ URL. ``creative_commons`` means
CC0, CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``,
``cc_by_nc_sa``, or ``cc_by_nc_nd``. The text cc-by-nc maps to ``cc_by_nc``.
Mixed restricted and permissive text stays unknown. Deceptive permissive
anchor text on a restricted deed URL or a public-domain mark URL stays
unknown. A CC0 anchor on a public-domain mark URL stays unknown. A generic
https://creativecommons.org/licenses or /licenses URL, including a missing
slash, http, www, or a query string, is not a deed. Anchor text on that
generic URL stays unknown. A specific deed URL still counts. A software
licence beside any Creative Commons deed stays unknown. Two software licences
stay unknown. Two different restricted deeds stay unknown. mit, apache-2.0,
and mpl-2.0 are sole software licences. Apache License, Version 2.0 is
apache-2.0. Bare MIT stays unknown. Licensed under the MIT License is mit.
A photo credit, caption credit, or image credit that names someone else's
licence stays unknown, including ``Photo credit: UNDRR, CC BY-NC-ND 2.0``
and ``Photo: UNDRR, CC BY-NC-ND 2.0``. A page that states its own CC BY
licence and a separate photo credit that names another licence stays
``creative_commons_attribution``. ``uk_ogl`` is only the British phrase
Open Government Licence. Open Government License stays unknown.
``us_government_work`` comes only from an explicit rights metadata field.
Public Domain Mark, all rights reserved, terms, and the host name stay
unknown. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
Script, style, and comment text does not count.

Publication dates only. Updated, modified, and copyright years are not
publication dates. A missing date stays unknown. The live URL is stored as
confirmed; a different rel=canonical does not replace it. This module does
not fetch, does not use the requests library, and is not a belief collector.
``runner_wired`` stays false. Belief collection stays on RssCollector.
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

CATALOG_ID = "wef_pages"
CATALOG_FILENAME = "wef_pages.json"
RUNNER_WIRED = False
PUBLISHER = "World Economic Forum"
CATALOG_DESCRIPTION = (
    "Metadata for confirmed public World Economic Forum research and news HTML "
    "about artificial intelligence on www.weforum.org and weforum.org. Each stored "
    "URL was confirmed with one bounded HTML GET that robots.txt allowed. A Cloudflare "
    "challenge, a captcha, an authentication wall, an HTML document in place of robots.txt, "
    "a host that does not resolve, an HTTP error, a non-HTML body, a robots disallow, or a "
    "redirect off these hosts is not stored. An empty entries list is valid. Person profiles, "
    "login walls, PDFs, and unrelated topics are omitted. Rows store a title, publisher, "
    "canonical URL, publication date, and rights. Page text, abstracts, quotes, transcripts, "
    "chart data, and PDFs are not stored. creative_commons_attribution means CC BY alone. "
    "creative_commons means CC0, CC BY-SA, or a permissive mix of those. A sole restricted "
    "deed keeps its own token. A missing publication date is unknown. Updated, modified, and "
    "copyright years are not publication dates. This catalog is not a belief collector and "
    "runner_wired is false."
)
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY = "creative_commons_attribution"
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
        RIGHTS_CC_BY,
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
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "www.weforum.org"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, "weforum.org"})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 1200

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_HEADLINE = re.compile(r'"headline"\s*:\s*"((?:\\.|[^"\\])*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"', re.I)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_HEADER_DATE = re.compile(
    r"(?is)<(?:div|span|time|p)\b[^>]*\bclass\s*=\s*['\"][^'\"]*\bsingle-header__date\b[^'\"]*['\"][^>]*>(.*?)</(?:div|span|time|p)>"
)
_WEF_PUBLISHED = re.compile(
    r"(?is)<div\b[^>]*\barticle-details__header\b[^>]*>(.*?)</div>\s*<div\b[^>]*>(.*?)</div>"
)
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_CREDIT_BLOCK = re.compile(r"(?is)<(p|li|figcaption|td|dd|figure)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_SITE_SUFFIXES = (
    " > Press releases | World Economic Forum",
    " | World Economic Forum",
    " - World Economic Forum",
    " – World Economic Forum",
    " — World Economic Forum",
    " > Press releases",
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
)
_EXCLUDED_SEGMENTS = frozenset(
    {
        "account",
        "accounts",
        "amp",
        "attachment",
        "author",
        "authors",
        "bio",
        "bios",
        "cart",
        "category",
        "cdn-cgi",
        "checkout",
        "comments",
        "communities",
        "contributors",
        "embed",
        "events",
        "experts",
        "feed",
        "login",
        "log-in",
        "member-login",
        "organisations",
        "organizations",
        "page",
        "people",
        "person",
        "podcasts",
        "privacy-policy",
        "profile",
        "profiles",
        "search",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "speakers",
        "staff",
        "tag",
        "team",
        "topics",
        "videos",
        "wp",
        "wp-admin",
        "wp-content",
        "wp-includes",
        "wp-json",
        "wp-login.php",
        "xmlrpc.php",
    }
)
_PERSON_SEGMENTS = frozenset(
    {
        "author",
        "authors",
        "bio",
        "bios",
        "contributors",
        "experts",
        "organisations",
        "organizations",
        "people",
        "person",
        "profile",
        "profiles",
        "speakers",
        "staff",
        "team",
    }
)
# Hyphen and slash are token boundaries. "ai" inside campaign or email does not count.
_TOPIC_PATH = re.compile(
    r"artificial-intelligence|machine-learning|generative-ai|large-language|"
    r"facial-recognition|automated-decision|deep-?fakes?|neural-networks?|"
    r"openai|chatgpt|genai|foundation-models?|chatbots?|"
    r"(?:^|[-/])ai(?:$|[-/])|(?:^|[-/])agi(?:$|[-/])|(?:^|[-/])llms?(?:$|[-/])|"
    r"(?:^|[-/])gpt(?:$|[-/])|deep-learning"
)
_GENERIC_TITLES = frozenset(
    {
        "world economic forum",
        "wef",
        "press releases",
        "stories",
        "publications",
        "home",
        "news",
    }
)
_NEWS_SECTIONS = frozenset({"stories", "media"})
_RESEARCH_SECTIONS = frozenset({"publications"})
_PAGE_SECTIONS = _NEWS_SECTIONS | _RESEARCH_SECTIONS
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "cf-browser-verification",
    "attention required! | cloudflare",
)
_ANYWHERE_MARKERS = (
    "sg-captcha",
    "sgcaptcha",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
)
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
# Longer deeds are listed first. (?!-) makes a hyphen a token boundary, so
# CC BY does not match CC BY-NC and licenses/by does not match licenses/by-nc.
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
            r"|\bcc[\s-]*by[\s-]*non[\s-]*commercial\b(?!-)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nd\b(?!-)"
            r"|creative commons attribution[\s-]*no[\s-]*deriv"
            r"|\bcc[\s-]*by[\s-]*noderiv"
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
        re.compile(
            r"\bcc[\s-]*by\b(?!-)"
            r"|creative commons attribution\b(?!-)"
        ),
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
# "modified MIT" is not the MIT licence. The lookbehind is applied after casefold.
_MIT_TEXT = re.compile(r"(?<!modified )(?:\bmit license\b|\blicensed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
# The comma in "Apache License, Version 2.0" is part of the licence name.
_APACHE_TEXT = re.compile(
    r"\bapache[\s-]*2\.0\b|\bapache license,?\s*(?:version\s+)?2(?:\.0)?\b"
)
_APACHE_URL = re.compile(r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])")
_MPL_TEXT = re.compile(r"\bmpl[\s-]*2\.0\b|\bmozilla public license(?:[\s-]*version)?[\s-]*2(?:\.0)?\b")
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
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:(?:photo|image|caption)\s+credits?|photo\s*:)")
_CREDIT_CLASS = re.compile(r"(?i)(?:photo[\s_-]*credit|image[\s_-]*credit|caption[\s_-]*credit|wp-caption)")
_BLOCK_BOUNDARY = re.compile(
    r"(?i)</(?:p|figcaption|li|dd|dt|h[1-6]|caption|blockquote|td|th|div)>"
)
_LOGIN_WALL = re.compile(
    r"(?i)\b(?:this content is password protected|please log in to continue|you must be logged in to view)\b"
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
    r"\b(?:published|publication date|date published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
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
    """A catalog row or page failed the World Economic Forum page rules."""


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
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public World Economic Forum research or news page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    netloc = parsed.netloc.lower()
    if (
        parsed.scheme != "https"
        or netloc != host
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
        or not _ai_page_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public World Economic Forum research or news page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in OFFICIAL_HOSTS and not hostname_is_blocked(host)


def host_resolution_stores_a_page(resolved: bool, hostname: str) -> bool:
    """A host that does not resolve is not stored, even when the name looks official."""

    if resolved is not True:
        return False
    return is_official_host(hostname)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

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


def robots_allows(body: str, path: str) -> bool:
    """True when the * group does not disallow path.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. Comment-only robots text allows every path.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if any(token in sample for token in ("<html", "<!doctype html", "<head", "<body")) or is_challenge_page(body[:8000]):
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


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or off-host block."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            text = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in text:
                return False
            if name == "sg-captcha" or "sg-captcha" in text:
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
    resolved: bool | None = None,
) -> dict | None:
    """Return metadata when the response is an allowed on-host AI page.

    A challenge page, a login wall, a non-HTML body, an error status, a robots
    disallow, a host that does not resolve, or a redirect off www.weforum.org
    and weforum.org is not stored. A redirect that stays on those hosts is
    stored at the final URL.
    """

    if resolved is False:
        return None
    target = final_url or page_url
    parsed = urlparse(target)
    if not is_official_host(parsed.hostname or ""):
        return None
    if robots_txt is not None and not robots_allows(robots_txt, parsed.path or "/"):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
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

    A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token.
    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
    mix of those is creative_commons. Mixed restricted and permissive text
    stays unknown. A CC BY or CC BY-SA anchor on a restricted or public-domain
    mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL stays
    unknown. A generic creativecommons.org/licenses or /licenses URL stays
    unknown, including a missing slash, http, www, or a query string, even when
    the anchor text says CC BY, CC BY 4.0, or CC BY-SA. A specific deed URL
    still counts. Text cc-by-nc maps to cc_by_nc. A photo credit, caption
    credit, image credit, or Photo: sentence that names someone else's licence
    stays unknown, including Photo credit: UNDRR, CC BY-NC-ND 2.0 and
    Photo: UNDRR, CC BY-NC-ND 2.0. A page licence outside that credit still
    counts. Two different restricted deeds stay unknown. A software licence
    beside any Creative Commons deed stays unknown. Two software licences stay
    unknown. Bare MIT stays unknown. Licensed under the MIT License is mit.
    Apache License, Version 2.0, including the comma, is apache-2.0.
    uk_ogl is only the British phrase Open Government Licence. Open Government
    License stays unknown. us_government_work comes only from an explicit rights
    metadata field. Script, style, and comment text does not count.
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
        return RIGHTS_CC_BY
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, and a copyright
    year are not publication dates. dateModified and dateCreated are not used.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    without_comments = _COMMENT.sub(" ", page_html)
    for raw in _DATE_PUBLISHED.findall(" ".join(_LDJSON.findall(without_comments))):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    visible = _HIDDEN.sub(" ", without_comments)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    published = _wef_published_date(visible)
    if published:
        return published
    header = _header_publication_date(visible)
    if header:
        return header
    return _published_prose(_plain_text(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    candidates: list[str] = []
    headline = _jsonld_headline(page_html)
    if headline:
        candidates.append(headline)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        cleaned = _clean_title(metas.get(key, ""))
        if cleaned and not _generic_title(cleaned):
            candidates.append(cleaned)
    heading = _H1.search(visible)
    if heading:
        cleaned = _clean_title(_TAG.sub(" ", heading.group(1)))
        if cleaned and not _generic_title(cleaned):
            candidates.append(cleaned)
    title_tag = _TITLE.search(visible)
    if title_tag:
        cleaned = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if cleaned and not _generic_title(cleaned):
            candidates.append(cleaned)
    if not candidates:
        raise CatalogError("title is required")
    for candidate in candidates:
        if len(candidate) >= 12:
            return candidate
    return max(candidates, key=len)


def publisher_from_page(page_html: str) -> str:
    """Return World Economic Forum when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if PUBLISHER.casefold() in _clean_text(metas.get(key, "")).casefold():
            return PUBLISHER
    if PUBLISHER.casefold() in _plain_text(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
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
    validate_entry(record)
    return record


def _ai_page_path(path: str) -> bool:
    """True for research or news HTML about artificial intelligence.

    News lives under /stories/ and /media/. Research lives under /publications/.
    Person profiles, login paths, topic indexes, and downloads are not catalog
    pages. The topic token must be a path-segment boundary, so campaign or
    email does not count as AI.
    """

    if path != path.lower() or not path.endswith("/") or path == "/":
        return False
    raw = path[:-1]
    if raw.endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in raw.split("/") if part]
    if not parts or parts[0] not in _PAGE_SECTIONS:
        return False
    if parts[0] == "stories":
        if len(parts) != 3:
            return False
    elif len(parts) != 2:
        return False
    if any(part in _EXCLUDED_SEGMENTS or part in _PERSON_SEGMENTS for part in parts):
        return False
    if any(_SEGMENT.fullmatch(part) is None for part in parts):
        return False
    return _TOPIC_PATH.search(path) is not None


def is_login_wall(page_html: str) -> bool:
    """True when the response is an authentication wall rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    visible = _visible_html(page_html)
    title_match = _TITLE.search(visible)
    title = _clean_title(_TAG.sub(" ", title_match.group(1))) if title_match else ""
    if title.casefold() in {"log in", "login", "sign in", "signin", "member login", "members only"}:
        return True
    plain = _plain_text(visible)
    return _LOGIN_WALL.search(plain) is not None


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text.

    A CC0, CC BY, or CC BY-SA label on that URL is not a licence statement.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        folded = _fold(href)
        if "creativecommons.org/publicdomain/mark" in folded:
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for the Creative Commons licences index, not a specific deed.

    http and https, a www host, a missing trailing slash, and a query string
    stay on that generic path. A deed such as /licenses/by/4.0/ does not.
    """

    if not isinstance(href, str) or not href.strip():
        return False
    folded = _fold(href).strip()
    candidate = folded
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif "://" not in candidate and (
        candidate.startswith("creativecommons.org") or candidate.startswith("www.creativecommons.org")
    ):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").rstrip(".")
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    path = parsed.path or ""
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _strip_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose URL is a generic creativecommons.org/licenses/ page.

    CC BY, CC BY 4.0, or CC BY-SA text on that URL is not a licence statement.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _strip_image_credits(page_html: str) -> str:
    """Drop photo, caption, and image credits that name someone else's licence.

    The credit is not a licence to reuse the page. A reuse licence stated
    outside that credit still counts. ``Photo: UNDRR, CC BY-NC-ND 2.0`` is a
    credit sentence, as is ``Photo credit: UNDRR, CC BY-NC-ND 2.0``.
    """

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if len(body) > 800:
            return match.group(0)
        if _CREDIT_CLASS.search(attrs):
            return " "
        return match.group(0)

    return _without_credit_sentences(_CREDIT_BLOCK.sub(replace_block, page_html))


def _without_credit_sentences(page_html: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in _CREDIT_PHRASE.finditer(page_html):
        if match.start() < cursor:
            continue
        parts.append(page_html[cursor : match.start()])
        window = page_html[match.end() : match.end() + 500]
        parts.append(" ")
        cursor = match.end() + _credit_end(window)
    parts.append(page_html[cursor:])
    return "".join(parts)


def _credit_end(window: str) -> int:
    stops = [len(window)]
    sentence = _sentence_end(window)
    if sentence is not None:
        stops.append(sentence)
    boundary = _BLOCK_BOUNDARY.search(window)
    if boundary:
        stops.append(boundary.start())
    return min(stops)


def _sentence_end(window: str) -> int | None:
    in_tag = False
    for index, char in enumerate(window):
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            continue
        if in_tag or char not in ".?!":
            continue
        if index + 1 == len(window) or window[index + 1] in " \t\n\r<":
            return index + 1
    return None


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    without_comments = _COMMENT.sub(" ", page_text)
    codes: set[str] = set()
    gov = False
    for license_text, rights_text in _jsonld_rights(without_comments):
        codes |= _codes_in_string(license_text)
        codes |= _codes_in_string(rights_text)
        if _states_us_government_work(rights_text):
            gov = True
    visible = _HIDDEN.sub(" ", without_comments)
    visible = _strip_image_credits(visible)
    visible = _strip_generic_license_anchors(_strip_mark_anchors(visible))
    for value in _license_meta_texts(visible):
        codes |= _codes_in_string(value)
    for value in _rights_field_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    plain = _plain_text(visible)
    folded = _fold(plain)
    codes |= _codes_in_folded(folded)
    if OGL_PHRASE in folded:
        codes.add("uk_ogl")
    for href in _hrefs(visible):
        codes |= _codes_in_string(href)
    return codes, gov


def _codes_in_string(value: str) -> set[str]:
    if not value:
        return set()
    return _codes_in_folded(_fold(value))


def _codes_in_folded(folded: str) -> set[str]:
    """Licence codes in one folded string. Restricted deeds are matched first."""

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
    for key, value in _metas(page_html).items():
        if key in {"license", "licence"} or key.endswith((".license", ".licence", ":license", ":licence")):
            found.append(value)
    return found


def _rights_field_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(page_html):
        if not _is_rights_element(attrs):
            continue
        text = _plain_text(body)
        if text and len(text) <= MAX_TEXT_CHARS:
            found.append(text)
    return found


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False


def _wef_published_date(visible: str) -> str | None:
    """Publication day from a World Economic Forum Published header."""

    for header, body in _WEF_PUBLISHED.findall(visible):
        if _fold(_plain_text(header)) != "published":
            continue
        text = _plain_text(body)
        folded = _fold(text)
        if any(token in folded for token in ("updated", "modified", "copyright")):
            continue
        parsed = _calendar_or_iso(text)
        if parsed:
            return parsed
    return None


def _jsonld_headline(page_html: str) -> str:
    without_comments = _COMMENT.sub(" ", page_html)
    for block in _LDJSON.findall(without_comments):
        match = _LD_HEADLINE.search(block)
        if match is None:
            continue
        raw = match.group(1)
        try:
            text = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            text = raw.replace("\\/", "/")
        cleaned = _clean_title(str(text))
        if cleaned and not _generic_title(cleaned):
            return cleaned
    return ""


def _generic_title(value: str) -> bool:
    return value.casefold() in _GENERIC_TITLES


def _header_publication_date(visible: str) -> str | None:
    """Publication day from the article header, not a last-updated footer."""

    match = _HEADER_DATE.search(visible)
    if match is None:
        return None
    text = _plain_text(match.group(1))
    folded = _fold(text)
    if any(token in folded for token in ("updated", "modified", "copyright")):
        return None
    return _calendar_or_iso(text)


def _calendar_or_iso(text: str) -> str | None:
    match = re.search(
        r"\b(\d{4}-\d{2}-\d{2})\b|\b([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\b|\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b",
        text,
    )
    if match is None:
        return None
    if match.group(1):
        return _iso_day(match.group(1))
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4))
    return _calendar_date(match.group(6), match.group(5), match.group(7))


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    if match.group(1):
        return _iso_day(match.group(1)) or UNKNOWN_DATE
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4)) or UNKNOWN_DATE
    return _calendar_date(match.group(6), match.group(5), match.group(7)) or UNKNOWN_DATE


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value))
    text = text.replace("\xa0", " ").replace("\ufffc", " ").replace("\ufeff", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible_html(page_text))


def _visible_html(page_text: str) -> str:
    return _HIDDEN.sub(" ", _COMMENT.sub(" ", page_text))


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _iso_day(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group(1)


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
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs in _ANCHOR.findall(page_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if href:
            found.append(href)
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


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
