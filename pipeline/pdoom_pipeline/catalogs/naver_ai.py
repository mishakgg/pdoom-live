"""Metadata catalog of public NAVER Labs pages about artificial intelligence.

Scope is research, blog, publication, and technology HTML on www.naverlabs.com
and naverlabs.com. Each stored URL was confirmed with one bounded GET of HTML
that robots allowed and that stayed on those hosts. A host that does not
resolve, an HTML document or challenge served as robots.txt, a Cloudflare,
cookie, or captcha challenge, a login wall, or a redirect off those hosts
stores nothing. An empty entries list is valid.

A row keeps the title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, PDFs, and chart data are
not stored. A model or dataset licence grants no page rights. A photo, image,
or caption credit that names someone else's licence stays unknown.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``,
``cc_by_nc_sa``, or ``cc_by_nc_nd``. Two different restricted deeds stay
unknown. Mixed restricted and permissive text stays unknown. A permissive
anchor on a restricted deed URL or a public-domain mark URL stays unknown,
including a CC0 anchor on a publicdomain/mark URL. A generic
https://creativecommons.org/licenses/ URL is not a deed. Visible anchor text
on it stays unknown. MIT, Apache-2.0, and MPL-2.0 stay their own tokens.
Bare MIT stays unknown. Licensed under the MIT License is mit. Apache
License, Version 2.0 is apache-2.0. A software licence beside any Creative
Commons deed stays unknown. Two software licences stay unknown. A mention of
a university is not a software licence. ``uk_ogl`` requires the exact British
phrase Open Government Licence. American spelling License stays unknown for
that phrase. ``us_government_work`` comes only from an explicit rights
metadata field. Script, style, and comment text does not count.

Updated, modified, and copyright years are not publication dates. A missing
date stays unknown. A year-only date stays unknown. The live URL is stored as
confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector. ``runner_wired`` stays false.
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

CATALOG_ID = "naver_ai_pages"
CATALOG_FILENAME = "naver_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "NAVER Labs"
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
OFFICIAL_HOST = "www.naverlabs.com"
APEX_HOST = "naverlabs.com"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, APEX_HOST})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Public NAVER Labs AI pages on www.naverlabs.com and naverlabs.com. "
    "Each row is one bounded robots-allowed HTML GET on those hosts. "
    "An unresolved host, HTML or challenge robots.txt, a Cloudflare, cookie, or captcha challenge, "
    "or an off-host redirect stores nothing. An empty catalog is valid. "
    "Rows keep a title, publisher, canonical URL, publication date, and rights. "
    "Abstracts, quotes, transcripts, PDFs, and chart data are omitted. "
    "Model and dataset licences do not establish page rights. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "A missing or year-only date is unknown. Updated, modified, and copyright years are not dates. "
    "Open Government Licence is the British phrase for uk_ogl. "
    "Not a belief collector. runner_wired is false."
)

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_DOT_DATE = re.compile(r"\b(\d{4})[./](\d{1,2})[./](\d{1,2})\b")
_SEQ_QUERY = re.compile(r"^seq=\d{1,12}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_H2 = re.compile(r"(?is)<h2\b[^>]*>(.*?)</h2>")
_ARTICLE_TITLE = re.compile(r'(?is)<h2\b[^>]*\bclass="[^"]*\barticle-tit\b[^"]*"[^>]*>(.*?)</h2>')
_PUB_TITLE = re.compile(r"(?is)<article\b[^>]*\bpub-article\b[^>]*>.*?<h2\b[^>]*>(.*?)</h2>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ARTICLE_HEADER = re.compile(
    r'(?is)<div\b[^>]*\bclass="[^"]*\barticle-title-box\b[^"]*"[^>]*>.*?</h2>'
)
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
    "dc.date.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_DETAIL_SLUGS = frozenset({"blogDetail", "publicationDetail"})
_EXCLUDED_SLUGS = frozenset(
    {
        "account",
        "accounts",
        "author",
        "authors",
        "cdn-cgi",
        "contact",
        "ethics",
        "feed",
        "img",
        "login",
        "people",
        "privacy",
        "profile",
        "profiles",
        "proposal",
        "robots.txt",
        "rss",
        "search",
        "sign-in",
        "signin",
        "sitemap.xml",
        "static",
        "wp-admin",
        "wp-login",
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
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_SITE_SUFFIXES = (
    " | NAVER LABS",
    " - NAVER LABS",
    " | NAVER Labs",
    " - NAVER Labs",
    " | 네이버랩스",
    " - 네이버랩스",
)
_SITE_PREFIXES = (
    "NAVER LABS - ",
    "NAVER LABS | ",
    "NAVER Labs - ",
    "NAVER Labs | ",
)
_GENERIC_TITLES = frozenset({"naver", "home", "top"})
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "cf-browser-verification",
    "attention required! | cloudflare",
    "verify you are human",
)
_ANYWHERE_MARKERS = (
    "sg-captcha",
    "sgcaptcha",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
    "/cdn-cgi/challenge",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "attention required! | cloudflare",
        "access denied",
    }
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
# Bare "MIT" and a university name are not the MIT licence.
_MIT_TEXT = re.compile(r"(?<!modified )(?:\bmit license\b|\blicensed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
# The comma in "Apache License, Version 2.0" is part of the licence name.
_APACHE_TEXT = re.compile(
    r"\bapache[\s-]*2\.0\b|\bapache license,?\s*(?:version\s+)?2(?:\.0)?\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
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
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|image|caption)\s+credits?\b|\bphoto\s*:")
_CREDIT_CLASS = re.compile(
    r"(?i)(?:photo[\s_-]*credit|image[\s_-]*credit|caption[\s_-]*credit|wp-caption)"
)
# Dots inside an href must not end the credit. A following licence sentence stays.
_CREDIT_SENTENCE = re.compile(
    r"(?i)(?:\b(?:photo|image|caption)\s+credits?\b|\bphoto\s*:)"
    r"(?:[^.<]|<(?!/?(?:p|figcaption|li)\b)[^>]*>){0,800}\."
)
_PASSWORD = re.compile(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]")
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
_NON_DATE_WORDS = ("updated", "update", "modified", "modification", "copyright")
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
_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,80}")


class CatalogError(ValueError):
    """A catalog row or page failed the NAVER Labs page rules."""


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
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog statement")
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
    if "<" in entry["title"] or ">" in entry["title"] or "\n" in entry["title"]:
        raise CatalogError("title must be plain text")
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
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public NAVER Labs page")
    if "%" in url:
        raise CatalogError(f"canonical URL must be a public NAVER Labs page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.port is not None
        or parsed.netloc.lower() != host
        or not is_official_host(host)
    ):
        raise CatalogError(f"canonical URL must be a public NAVER Labs page: {url}")
    path = _normalize_path(parsed.path or "/")
    if not _acceptable_path(path, parsed.query):
        raise CatalogError(f"canonical URL must be a public NAVER Labs page: {url}")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"https://{host}{path}{query}"


def is_official_host(hostname: str) -> bool:
    """True only for www.naverlabs.com and naverlabs.com."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is a Cloudflare, cookie, or captcha interstitial."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _ANYWHERE_MARKERS):
        return True
    head = lowered[:8000]
    if any(marker in head for marker in _HEAD_MARKERS):
        return True
    match = _TITLE.search(page_html[:8000])
    if match is None:
        return False
    title = _clean_text(match.group(1)).casefold()
    return title in _CHALLENGE_TITLES


def is_login_wall(page_html: str) -> bool:
    """True when the response is a sign-in form rather than a public page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if _PASSWORD.search(page_html):
        return True
    title_match = _TITLE.search(page_html[:8000])
    title = _clean_text(title_match.group(1)).casefold() if title_match else ""
    return any(token in title for token in ("log in", "login", "sign in", "sign-in"))


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows path.

    An HTML document or a challenge served in place of robots.txt does not
    allow a fetch. The longest matching Allow or Disallow pattern wins.
    Equal lengths allow. A comment-only file allows every path.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or "<!doctype" in sample or is_challenge_page(body[:8000]):
        return False
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
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


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or login wall."""

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
    if headers and _challenge_headers(headers):
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
    """Return metadata when one bounded GET stayed on a NAVER Labs host.

    A challenge, a captcha, a cookie interstitial, an authentication wall, a
    non-HTML body, an error status, a robots disallow, an HTML robots body,
    or an off-host hop is not stored.
    """

    target = final_url or page_url
    if hops and any(not _on_official_host(hop) for hop in hops):
        return None
    if not _on_official_host(target):
        return None
    parsed = urlparse(target)
    robots_path = (parsed.path or "/") + ("?" + parsed.query if parsed.query else "")
    if robots_txt is not None and not robots_allows(robots_txt, robots_path):
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


def rows_for_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
) -> list[dict]:
    """Return catalog rows for one response, or none when the response is unusable."""

    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        robots_txt=robots_txt,
        hops=hops,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a
    permissive mix of those is creative_commons. A sole restricted deed keeps
    its token. Two restricted deeds stay unknown. A permissive label on a
    restricted or public-domain mark URL stays unknown. A generic
    creativecommons.org/licenses/ URL is not a deed, and visible anchor text
    on it stays unknown. A photo, caption, or image credit does not count.
    A model or dataset licence does not establish page rights. Bare MIT stays
    unknown. Licensed under the MIT License is mit. A software licence beside
    any Creative Commons deed stays unknown. Two software licences stay
    unknown. A university name is not a software licence. uk_ogl requires the
    British phrase Open Government Licence. us_government_work comes only
    from an explicit rights field. Script, style, and comment text do not
    count.
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

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, and a year-only issue year are not publication dates. A date inside
    script, style, or a comment is not a publication date. A listing of other
    posts is not this page's publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    found: list[str] = []
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        _add_date(found, _iso_day(metas.get(key, "")))
    header = _ARTICLE_HEADER.search(visible)
    if header:
        _add_date(found, _header_date(header.group(0)))
    if len(found) == 1:
        return found[0]
    if found:
        return UNKNOWN_DATE
    return _published_prose(_plain_text(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    for pattern in (_ARTICLE_TITLE, _PUB_TITLE):
        match = pattern.search(visible)
        if match:
            title = _clean_title(match.group(1))
            if title and not _generic_title(title):
                return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title and not _generic_title(title):
            return title
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title and not _generic_title(title):
            return title
    for pattern in (_H2, _H1):
        for raw in pattern.findall(visible):
            title = _clean_title(raw)
            if title and not _generic_title(title):
                return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return NAVER Labs when the page names the organization.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    blob = _fold(_plain_text(visible))
    if "naver labs" in blob or "네이버랩스" in blob:
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
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
    validate_entry(record)
    return record


def _acceptable_path(path: str, query: str) -> bool:
    if not path.startswith("/") or "\\" in path or "//" in path or ".." in path:
        return False
    if query and _SEQ_QUERY.fullmatch(query) is None:
        return False
    raw = path[:-1] if path.endswith("/") and len(path) > 1 else path
    if raw != "/" and raw.endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in raw.split("/") if part]
    if any(part.casefold() in _EXCLUDED_SLUGS for part in parts):
        return False
    if not parts:
        return query == ""
    if parts[0] == "en":
        parts = parts[1:]
        if not parts:
            return query == ""
    if len(parts) != 1 or _SLUG.fullmatch(parts[0]) is None:
        return False
    slug = parts[0]
    if slug in _DETAIL_SLUGS:
        return query != ""
    return query == ""


def _normalize_path(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return is_official_host(host) and parsed.port is None and not parsed.username


def _header_date(header_html: str) -> str | None:
    """Use the article date span, not a date inside the title.

    A title such as "Updates (2023.06.12)" is not a modified-time field.
    Updated, modified, and copyright text inside the date span stays unknown.
    """

    found: list[str] = []
    for attrs, body in re.findall(r"(?is)<span\b([^>]*)>(.*?)</span>", header_html):
        parsed = _attrs(f"<span {attrs}>")
        classes = parsed.get("class", "").casefold().split()
        if "date" not in classes:
            continue
        if any(word in classes for word in ("updated", "modified", "copyright")):
            continue
        text = _plain_text(body).casefold()
        if any(word in text for word in _NON_DATE_WORDS):
            continue
        for year, month, day in _DOT_DATE.findall(text):
            _add_date(found, _ymd(int(year), int(month), int(day)))
        month_name = re.search(
            r"\b(january|february|march|april|may|june|july|august|september|"
            r"october|november|december)\s+(\d{1,2}),\s+(\d{4})\b",
            text,
        )
        if month_name:
            _add_date(
                found,
                _ymd(int(month_name.group(3)), _MONTHS[month_name.group(1)], int(month_name.group(2))),
            )
    if len(found) == 1:
        return found[0]
    return None


def _add_date(found: list[str], value: str | None) -> None:
    if value and value not in found:
        found.append(value)


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    page_text = _strip_artifact_licences(_strip_image_credits(page_text))
    page_text = _strip_generic_license_anchors(_strip_mark_anchors(page_text))
    visible = _visible_html(page_text)
    codes: set[str] = set()
    gov = False
    for value in _license_meta_texts(visible):
        codes |= _codes_in_string(value)
    for value in _rights_field_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    folded = _fold(_plain_text(visible))
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
    """Licence codes in one folded string. Longer text deeds win overlaps."""

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


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if "creativecommons.org/publicdomain/mark" in _fold(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    folded = _fold(href)
    if "creativecommons.org/licenses" not in folded:
        return False
    return not any(match.group("license") for match in _CC_URL.finditer(folded))


def _strip_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose URL is a generic creativecommons.org/licenses/ page."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


_ARTIFACT_SCOPE = re.compile(r"(?i)\b(?:datasets?|models?|software|source code)\b|Anny-One|데이터셋|모델")
_ARTIFACT_BLOCK = re.compile(r"(?is)<(p|li|figcaption|td|dd|figure|div|span)\b([^>]*)>(.*?)</\1>")


def _strip_artifact_licences(page_html: str) -> str:
    """An artifact's licence grants no rights to the page describing it."""

    def replace_block(match: re.Match[str]) -> str:
        body = match.group(3)
        if _ARTIFACT_SCOPE.search(_plain_text(body)) and _codes_in_string(body):
            return " "
        return match.group(0)

    stripped = _ARTIFACT_BLOCK.sub(replace_block, page_html)
    if "<" not in stripped and _ARTIFACT_SCOPE.search(stripped):
        return " "
    return stripped


def _strip_image_credits(page_html: str) -> str:
    """Drop photo, caption, and image credits that name someone else's licence."""

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if len(body) > 800:
            return match.group(0)
        if _CREDIT_CLASS.search(attrs) or _CREDIT_PHRASE.search(attrs):
            return " "
        if not _CREDIT_PHRASE.search(body):
            return match.group(0)
        cleaned = _CREDIT_SENTENCE.sub(" ", body)
        if _CREDIT_PHRASE.search(cleaned):
            phrase_at = _CREDIT_PHRASE.search(body)
            cleaned = body[: phrase_at.start()] + " " if phrase_at is not None else " "
        return f"<{match.group(1)}{attrs}>{cleaned}</{match.group(1)}>"

    stripped = _CREDIT_BLOCK.sub(replace_block, page_html)

    def replace_anchor(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    stripped = _FULL_ANCHOR.sub(replace_anchor, stripped)
    return _CREDIT_SENTENCE.sub(" ", stripped)


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    window = plain[max(0, match.start() - 40) : match.end()].casefold()
    if any(word in window for word in _NON_DATE_WORDS):
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
        for prefix in _SITE_PREFIXES:
            if text.startswith(prefix) and len(text) > len(prefix):
                text = text[len(prefix) :].strip()
                changed = True
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    if not text or len(text) > MAX_TEXT_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _generic_title(value: str) -> bool:
    return value.casefold() in _GENERIC_TITLES


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
    return _ymd(*_split_iso(match.group(1)))


def _split_iso(value: str) -> tuple[int, int, int]:
    year, month, day = value.split("-")
    return int(year), int(month), int(day)


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    return _ymd(int(year_text), month, int(day_text))


def _ymd(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


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


def _robots_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "^" + ".*".join(re.escape(chunk) for chunk in body.split("*"))
    if anchored:
        regex += "$"
    return re.search(regex, path) is not None


def _challenge_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "sg-captcha" or "sg-captcha" in text:
            return True
    return False
