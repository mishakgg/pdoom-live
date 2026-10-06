"""Metadata catalog of public Freedom House pages on AI, technology, and internet freedom.

Hosts are freedomhouse.org and www.freedomhouse.org. www.freedomhouse.org
redirects to freedomhouse.org. robots.txt on both hosts is the same Drupal
file and allows the public research and news paths. It disallows admin,
search, user login, and Drupal core. Each stored URL was confirmed with one
bounded GET that stayed on these hosts. Donation pages, person profiles,
login walls, PDFs, and unrelated topics are omitted.

A Cloudflare challenge, a captcha, an authentication wall, an HTML document
served in place of robots.txt, a host that does not resolve, or a redirect
off these hosts is not stored. An empty catalog is correct in those cases.
This module does not bypass those controls.

A row keeps the title, publisher, canonical URL, date, and rights label.
Page text, abstracts, PDFs, quotes, transcripts, and chart data are not
stored. The live URL is stored as confirmed. A different rel=canonical does
not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone, including a
https://creativecommons.org/licenses/by/4.0/ URL. ``creative_commons`` is
CC0, CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``,
``cc_by_nc_sa``, or ``cc_by_nc_nd``. Text cc-by-nc maps to cc_by_nc. A
hyphen is a word boundary, so CC BY does not match CC BY-NC and licenses/by
does not match licenses/by-nc. Two different restricted deeds stay unknown.
A permissive anchor on a restricted deed URL or on a public-domain mark URL
stays unknown. A CC0 anchor on a publicdomain/mark URL stays unknown. A
generic creativecommons.org/licenses or /licenses URL is not a deed,
including a missing slash, http, www, or a query string. Anchor text on that
generic URL stays unknown. A specific deed URL still counts. A software
licence beside any Creative Commons deed stays unknown. Two software
licences stay unknown. mit, apache-2.0, and mpl-2.0 are sole software
licences. Bare MIT stays unknown. Licensed under the MIT License is mit.
Apache License, Version 2.0 is apache-2.0. ``uk_ogl`` is only the British
phrase Open Government Licence. Open Government License stays unknown.
``us_government_work`` comes only from an explicit rights metadata field. A
photo credit, caption credit, or image credit that names someone else's
licence stays unknown, including Photo credit: UNDRR, CC BY-NC-ND 2.0 and
Photo: UNDRR, CC BY-NC-ND 2.0. When the page states its own CC BY licence
and a separate photo credit names another licence, the page stays
creative_commons_attribution. Script, style, and comment text does not count.

Publication dates only. Updated, modified, and copyright years stay unknown.
A missing publication date stays unknown. This module does not fetch and it
does not import requests. It is not a belief collector. ``runner_wired``
stays false. Belief collection stays on RssCollector.
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

CATALOG_ID = "freedomhouse_pages"
CATALOG_FILENAME = "freedomhouse_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Freedom House"
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
OFFICIAL_HOSTS = frozenset({"freedomhouse.org", "www.freedomhouse.org"})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
FETCH_TIMEOUT_SECONDS = 20
FETCH_MAX_REDIRECTS = 3
FETCH_MAX_BYTES = 4_000_000
# Confirmed from one GET of https://freedomhouse.org/robots.txt on 2026-10-06.
# www.freedomhouse.org/robots.txt returned the same text and stayed on www.
CONFIRMED_ROBOTS = """User-agent: *
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
Disallow: /README.md
Disallow: /composer/Metapackage/README.txt
Disallow: /composer/Plugin/ProjectMessage/README.md
Disallow: /composer/Plugin/Scaffold/README.md
Disallow: /composer/Plugin/VendorHardening/README.txt
Disallow: /composer/Template/README.txt
Disallow: /modules/README.txt
Disallow: /sites/README.txt
Disallow: /themes/README.txt
Disallow: /web.config
# Paths (clean URLs)
Disallow: /admin/
Disallow: /comment/reply/
Disallow: /filter/tips
Disallow: /node/add/
Disallow: /search/
Disallow: */search?*
# Search, in every language prefix. Bare `/search` has no index value, and the
# leading-wildcard form above is a Google/Bing extension that stricter crawlers
# ignore, so state it explicitly too.
Disallow: /search
Disallow: /*/search
# Faceted listings. Facets combine into an effectively infinite URL space
# (observed up to 14 simultaneous f[N] params), all of it thin or duplicate
# content. Blocks facets wherever they appear -- /search, /experts,
# /about-us/our-experts -- rather than per-path. Both raw and encoded brackets.
Disallow: /*?f[
Disallow: /*&f[
Disallow: /*?f%5B
Disallow: /*&f%5B
# Unaliased node listing pagination. Canonical content is reachable via the
# sitemap, so crawling these adds nothing.
Disallow: /node?page=
Disallow: /*/node?page=
Disallow: /user/register
Disallow: /user/password
Disallow: /user/login
Disallow: /user/logout
Disallow: /media/oembed
Disallow: /*/media/oembed
# Paths (no clean URLs)
Disallow: /index.php/admin/
Disallow: /index.php/comment/reply/
Disallow: /index.php/filter/tips
Disallow: /index.php/node/add/
Disallow: /index.php/search/
Disallow: /index.php/user/password
Disallow: /index.php/user/register
Disallow: /index.php/user/login
Disallow: /index.php/user/logout
Disallow: /index.php/media/oembed
Disallow: /index.php/*/media/oembed
Disallow: /index.php/search
Disallow: /index.php/*?f[
Disallow: /index.php/*&f[

# Sitemap
# Canonical, parameter-free URLs for every indexable page. With faceted and
# paginated URLs disallowed above, this is how crawlers are meant to discover
# content. The index itself paginates via ?page=N, which none of the rules
# above match.
Sitemap: https://freedomhouse.org/sitemap.xml
"""
CATALOG_DESCRIPTION = (
    "Metadata for public Freedom House research and news HTML about artificial intelligence, technology, and internet freedom on freedomhouse.org and www.freedomhouse.org. "
    "www.freedomhouse.org redirects to freedomhouse.org. Each row was one bounded GET that robots.txt allows. "
    "Donation pages, person profiles, login walls, PDFs, and unrelated topics are omitted. "
    "A challenge, HTML in place of robots.txt, an unresolved host, or an off-host redirect is not stored. "
    "Rows keep title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "A missing publication date is unknown. Updated, modified, and copyright years are not publication dates. "
    "Not a belief collector. runner_wired stays false."
)

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
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
_CONTENT_ROOTS = frozenset(
    {"article", "report", "reports", "country", "issues", "policy-recommendations"}
)
_EXCLUDED_PARTS = frozenset(
    {
        "about-us",
        "account",
        "admin",
        "attachment",
        "auth",
        "author",
        "authors",
        "career",
        "careers",
        "cart",
        "cdn-cgi",
        "checkout",
        "comment",
        "donate",
        "donation",
        "donations",
        "expert",
        "experts",
        "give",
        "log-in",
        "login",
        "newsletter",
        "our-experts",
        "people",
        "person",
        "privacy",
        "privacy-policy",
        "profile",
        "profiles",
        "search",
        "sign-in",
        "signin",
        "sign-up",
        "signup",
        "staff",
        "team",
        "user",
        "ways-to-give",
        "wp-admin",
        "wp-login.php",
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
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
)
# Cloudflare's public pages load /cdn-cgi/challenge-platform/scripts/jsd/main.js.
# That beacon is not an interstitial. A challenge page still matches the head
# markers, cf-mitigated, or a captcha.
_ANYWHERE_MARKERS = (
    "cf-mitigated",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "akamaighost",
    "errors.edgesuite.net",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_DRUPAL_DATE = re.compile(r"(?i)(?:[a-z]+,\s*)?(\d{1,2})/(\d{1,2})/(\d{4})\b")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LANG = re.compile(r"^[a-z]{2}(?:-[a-z]{2,8})?$")
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_SITE_SUFFIXES = (
    " | Freedom House",
    " - Freedom House",
    " – Freedom House",
    " — Freedom House",
    " | FreedomHouse",
)
_WALL_TITLE = re.compile(r"(?i)^\s*(log[\s-]*in|sign[\s-]*in|donate|donation|support us)\s*$")
_PUBLISHER_NAME = re.compile(r"(?i)\bfreedom\s*house\b")
_GENERIC_LICENSES_URL = re.compile(
    r"(?i)^(?:(?:https?:)?//)?(?:www\.)?creativecommons\.org/licenses/?(?:[?#]\S*)?$"
)
_MARK_URL = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
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
# A hyphen is a word boundary, so CC BY does not match CC BY-NC.
# Longer deeds are listed first. (?!-) keeps licenses/by from matching licenses/by-nc.
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
_MIT_TEXT = re.compile(r"(?<!modified )(?:\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_TEXT = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:,)?(?:[\s,]+version)?[\s,]*2(?:\.0)?\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_TEXT = re.compile(r"\bmpl[\s-]*2\.0\b|\bmozilla public licen[cs]e(?:[\s,]+version)?[\s,]*2(?:\.0)?\b")
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
_CREDIT_SPAN = re.compile(
    r"(?is)\b(?:(?:photo|image|caption)\s+credits?|(?:photo|image|caption)\s*:)\s*"
    r"(?:[^<.]|<[^>]*>|\.(?=\d)){0,500}"
)
_OPEN_CREDIT = re.compile(
    r"(?is)<([a-z0-9]+)\b[^>]*\b(?:class|id)\s*=\s*(['\"])[^'\"]*"
    r"(?:photo|image|caption)[\s_-]+credits?[^'\"]*\2[^>]*>"
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
_TOPIC_PHRASES = (
    "freedom-on-the-net",
    "freedom-net",
    "internet-freedom",
    "artificial-intelligence",
    "machine-learning",
    "generative-ai",
    "social-media",
    "big-tech",
    "facial-recognition",
)
_TOPIC_TOKENS = frozenset(
    {
        "ai",
        "cyber",
        "cybersecurity",
        "digital",
        "encryption",
        "internet",
        "online",
        "spyware",
        "surveillance",
        "technologies",
        "technology",
    }
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
    """A catalog row or page failed the Freedom House page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document fields must be catalog_id, description, runner_wired, and entries")
    _reject_stored_body(document)
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the Freedom House catalog contract")
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
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _reject_stored_body(entry, path="entry")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public Freedom House research or news page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public Freedom House research or news page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    """True for freedomhouse.org and www.freedomhouse.org only."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_topic_path(path: str) -> bool:
    """True for research or news HTML about AI, technology, or internet freedom.

    Donation pages, person profiles, login walls, PDFs, and unrelated topics
    stay out. A hyphen-delimited ``ai`` token does not match a longer word.
    """

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    lowered = path.lower()
    if _is_download(lowered) or _has_excluded_part(lowered):
        return False
    parts = _content_parts(lowered)
    if parts is None:
        return False
    return _states_topic(parts)


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
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    head = lowered[:2500]
    return any(marker in title or marker in head for marker in _HEAD_MARKERS)


def robots_allows(robots_text: str, path: str) -> bool:
    """True when robots.txt does not disallow ``path``.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. The longest matching Allow or Disallow wins. An empty
    Disallow does not block a path.
    """

    if not isinstance(robots_text, str) or not isinstance(path, str):
        return False
    sample = robots_text[:800].casefold()
    if "<html" in sample or "<!doctype" in sample or is_challenge_page(robots_text[:8000]):
        return False
    rules = _wildcard_rules(robots_text)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    query = ""
    if "?" in target:
        target, query = target.split("?", 1)
        query = "?" + query
    candidate = target + query
    allow_len = -1
    disallow_len = -1
    for kind, pattern in rules:
        if not _rule_matches(pattern, candidate):
            continue
        length = len(pattern)
        if kind == "allow" and length >= allow_len:
            allow_len = length
        elif kind == "disallow" and length >= disallow_len:
            disallow_len = length
    if allow_len < 0 and disallow_len < 0:
        return True
    return allow_len >= disallow_len


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
) -> bool:
    """A page is stored only from HTML that stayed on an official host."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers and _challenge_headers(headers):
        return False
    if not _stayed_on_official_hosts(page_url, final_url, hops):
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
    hops: tuple[str, ...] | list[str] | None = None,
    robots_text: str | None = None,
    resolved: bool = True,
) -> dict | None:
    """Return metadata when one bounded response is an on-host topic page.

    A challenge, an HTML robots document, a host that does not resolve, an
    off-host redirect, a donation page, a person profile, a login wall, a
    PDF, or an unrelated topic is not stored.
    """

    if resolved is not True:
        return None
    target = final_url or page_url
    if robots_text is not None:
        path = urlparse(target).path or "/"
        if not robots_allows(robots_text, path):
            return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        hops=hops,
    ):
        return None
    assert isinstance(page_html, str)
    if _is_login_or_donation(page_html, target):
        return None
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
    mix of those is creative_commons. A sole restricted deed keeps its own
    token. Two restricted deeds stay unknown. A software licence beside any
    Creative Commons deed stays unknown. Two software licences stay unknown.
    Bare MIT stays unknown. Licensed under the MIT License is mit. A generic
    creativecommons.org/licenses URL stays unknown, including when its anchor
    says CC BY, CC BY 4.0, or CC BY-SA, and including a missing slash, http, a
    www host, or a query string. A specific deed URL still counts. Deceptive
    permissive anchor text on a restricted or public-domain mark URL stays
    unknown. A CC0 anchor on a public-domain mark URL stays unknown. A photo
    credit, caption credit, or image credit stays unknown. uk_ogl requires the
    British phrase Open Government Licence. us_government_work requires a
    rights field. Script, style, and comment text does not count.
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

    Updated, modified, and copyright years are not publication dates. Script,
    style, and comment text does not count, except a JSON-LD datePublished
    value. Several different publication dates do not yield one date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    without_comments = _COMMENT.sub(" ", page_html)
    published: list[str] = []
    for raw in _DATE_PUBLISHED.findall(" ".join(_LDJSON.findall(without_comments))):
        parsed = _parse_publication_value(raw)
        if parsed and parsed not in published:
            published.append(parsed)
    if len(published) == 1:
        return published[0]
    if len(published) > 1:
        return UNKNOWN_DATE
    visible = _HIDDEN.sub(" ", without_comments)
    for attrs in _TIME.findall(visible):
        parsed_attrs = _attrs(f"<time {attrs}>")
        itemprop = parsed_attrs.get("itemprop", "").casefold()
        if itemprop != "datepublished":
            continue
        parsed = _parse_publication_value(parsed_attrs.get("datetime", ""))
        if parsed:
            return parsed
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _parse_publication_value(metas.get(key, ""))
        if parsed:
            return parsed
    return _published_prose(_plain_text(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Freedom House when the page states that name.

    A person named on the page is not the publisher. The stored name is
    Freedom House.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    titled = " ".join(_clean_text(metas.get(key, "")) for key in _PUBLISHER_KEYS)
    title_tag = _TITLE.search(visible)
    title_text = title_tag.group(1) if title_tag else ""
    blob = " ".join((titled, title_text, _plain_text(visible)))
    if _PUBLISHER_NAME.search(blob) is None:
        raise CatalogError("publisher is required")
    return PUBLISHER


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if _is_login_or_donation(page_html, page_url):
        raise CatalogError("login and donation pages are not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _is_login_or_donation(page_html: str, page_url: str) -> bool:
    path = (urlparse(page_url).path or "/").lower()
    if _has_excluded_part(path):
        return True
    try:
        title = title_from_page(page_html)
    except CatalogError:
        return False
    return _WALL_TITLE.fullmatch(title) is not None


def _content_parts(path: str) -> list[str] | None:
    parts = [part for part in path.split("/") if part]
    if not parts:
        return None
    if (
        parts[0] not in _CONTENT_ROOTS
        and _LANG.fullmatch(parts[0])
        and len(parts) > 1
        and parts[1] in _CONTENT_ROOTS
    ):
        parts = parts[1:]
    if not parts or parts[0] not in _CONTENT_ROOTS:
        return None
    return parts


def _states_topic(parts: list[str]) -> bool:
    tokens: list[str] = []
    for part in parts:
        tokens.extend(piece for piece in part.split("-") if piece)
    filtered: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] == "online" and index + 1 < len(tokens) and tokens[index + 1] == "survey":
            index += 2
            continue
        filtered.append(tokens[index])
        index += 1
    joined = "-".join(filtered)
    if any(phrase in joined for phrase in _TOPIC_PHRASES):
        return True
    return any(token in _TOPIC_TOKENS for token in filtered)


def _has_excluded_part(path: str) -> bool:
    parts = [part for part in path.lower().split("/") if part]
    return any(part in _EXCLUDED_PARTS for part in parts)


def _is_download(path: str) -> bool:
    bare = path[:-1] if path.endswith("/") else path
    return bare.endswith(_DOWNLOAD_SUFFIXES)


def _stayed_on_official_hosts(
    page_url: str,
    final_url: str | None,
    hops: tuple[str, ...] | list[str] | None,
) -> bool:
    chain = [url for url in (hops or []) if isinstance(url, str)]
    if not chain:
        chain = [page_url]
    if final_url and chain[-1] != final_url:
        chain.append(final_url)
    if not chain:
        return False
    for url in chain:
        if not is_official_host((urlparse(url).hostname or "").lower().rstrip(".")):
            return False
    return True


def _challenge_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "sg-captcha" or "sg-captcha" in text:
            return True
        if name == "server" and "akamai" in text and "403" in text:
            return True
    return False


def _wildcard_rules(body: str) -> list[tuple[str, str]] | None:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, list(rules)))
        agents = []
        rules = []

    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().casefold()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value.casefold())
            continue
        if key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    flush()
    chosen: list[tuple[str, str]] | None = None
    wildcard: list[tuple[str, str]] | None = None
    for group_agents, group_rules in groups:
        for agent in group_agents:
            if agent == "*":
                wildcard = group_rules
            elif agent.startswith("pdoom"):
                chosen = group_rules
    if chosen is not None:
        return chosen
    return wildcard


def _rule_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    anchored_end = pattern.endswith("$")
    body = pattern[:-1] if anchored_end else pattern
    pieces = ["^"]
    for char in body:
        if char == "*":
            pieces.append(".*")
        else:
            pieces.append(re.escape(char))
    if anchored_end:
        pieces.append("$")
    try:
        return re.search("".join(pieces), path) is not None
    except re.error:
        return False


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    without_comments = _COMMENT.sub(" ", page_text)
    visible = _strip_credit_elements(_HIDDEN.sub(" ", without_comments))
    visible = _strip_credit_spans(visible)
    visible = _strip_mark_anchors(_strip_generic_license_anchors(visible))
    codes: set[str] = set()
    gov = False
    for value in _license_meta_texts(visible):
        codes |= _codes_in_string(value)
    for value in _rights_element_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    for key, value in _metas(visible).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            if _states_us_government_work(value):
                gov = True
            codes |= _codes_in_string(value)
    folded = _fold(_plain_text(visible))
    codes |= _codes_in_folded(folded)
    if OGL_PHRASE in folded:
        codes.add("uk_ogl")
    for href in _hrefs(visible):
        if _is_generic_cc_licenses_url(href) or _MARK_URL.search(_fold(href)):
            continue
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


def _license_meta_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key in {"license", "licence"} or key.endswith((".license", ".licence", ":license", ":licence")):
            found.append(value)
    return found


def _rights_element_texts(page_html: str) -> list[str]:
    found: list[str] = []
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


def _is_generic_cc_licenses_url(href: str) -> bool:
    return _GENERIC_LICENSES_URL.fullmatch(_fold(href).strip()) is not None


def _strip_credit_elements(page_html: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in _OPEN_CREDIT.finditer(page_html):
        if match.start() < cursor:
            continue
        end = _matching_close(page_html, match.end(), match.group(1).lower())
        if end is None or end - match.start() > 8000:
            continue
        parts.append(page_html[cursor : match.start()])
        parts.append(" ")
        cursor = end
    parts.append(page_html[cursor:])
    return "".join(parts)


def _matching_close(page_html: str, start: int, tag: str) -> int | None:
    token = re.compile(rf"(?is)</?{re.escape(tag)}\b[^>]*>")
    depth = 1
    for match in token.finditer(page_html, start):
        piece = match.group(0)
        if piece.startswith("</"):
            depth -= 1
            if depth == 0:
                return match.end()
            continue
        if piece.rstrip().endswith("/>"):
            continue
        depth += 1
    return None


def _strip_credit_spans(page_html: str) -> str:
    """Drop photo, image, and caption credits so someone else's licence does not count."""

    def replace(match: re.Match[str]) -> str:
        head = page_html[: match.start()]
        if head.rfind("<") > head.rfind(">"):
            return match.group(0)
        return " "

    return _CREDIT_SPAN.sub(replace, page_html)


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _MARK_URL.search(_fold(href)):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _strip_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose URL is a generic creativecommons.org/licenses page.

    CC BY, CC BY 4.0, or CC BY-SA text on that URL is not a licence statement.
    A specific deed URL such as /licenses/by/4.0/ still counts.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _published_prose(plain: str) -> str:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        parsed = _prose_date(match)
        if parsed and parsed not in found:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def _prose_date(match: re.Match[str]) -> str | None:
    if match.group(1):
        return _iso_day(match.group(1))
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4))
    return _calendar_date(match.group(6), match.group(5), match.group(7))


def _parse_publication_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    iso = _iso_day(text)
    if iso:
        return iso
    match = _DRUPAL_DATE.search(text)
    if match:
        try:
            parsed = date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError:
            return None
        return parsed.isoformat()
    named = re.search(
        r"(?i)\b([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\b|\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b",
        text,
    )
    if named is None:
        return None
    if named.group(3):
        return _calendar_date(named.group(1), named.group(2), named.group(3))
    return _calendar_date(named.group(5), named.group(4), named.group(6))


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be plain text")


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


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
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
