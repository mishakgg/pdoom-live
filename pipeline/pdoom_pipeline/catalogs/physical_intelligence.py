"""Metadata catalog of public Physical Intelligence pages.

Hosts are www.physicalintelligence.company and physicalintelligence.company.
No other host is fetched. On 2026-10-06 both names resolved to public
addresses. One bounded GET of https://www.physicalintelligence.company/robots.txt
returned HTTP 429, content type text/html, title Vercel Security Checkpoint,
and header X-Vercel-Mitigated: challenge. The same status came back for
https://physicalintelligence.company/robots.txt and for both homepages.
That robots document is HTML and a challenge, so it does not allow a fetch.
Nothing from those responses is stored. The checkpoint was not bypassed.
An empty catalog is correct.

A row is stored only after one bounded robots-allowed HTML GET that stays on
these hosts. A Cloudflare challenge, a cookie challenge, a captcha, an
authentication wall, an HTTP error, a non-HTML body, an HTML or challenge
robots.txt, a host that does not resolve, or a redirect off these hosts
contributes nothing. Private, loopback, link-local, and metadata addresses
are blocked.

Each row keeps a title, publisher, canonical URL, publication date, and
rights label. Page text, abstracts, quotes, transcripts, chart data, and
PDFs are not stored. Publisher is Physical Intelligence. The live URL is
stored as confirmed. A different rel=canonical does not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution is CC BY alone. creative_commons is CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
Two different restricted deeds stay unknown. A software licence beside any
Creative Commons deed stays unknown. Two software licences stay unknown.
mit, apache-2.0, and mpl-2.0 are sole software licences. Bare MIT stays
unknown. Licensed under the MIT License is mit. Apache License, Version 2.0
is apache-2.0. The organization's own model-release licence stated on the
page may be that page's rights token. A permissive anchor on a restricted
deed URL or a public-domain mark URL stays unknown. A CC0 anchor on a
publicdomain/mark URL stays unknown. A generic
https://creativecommons.org/licenses/ URL is not a deed, and visible anchor
text on it stays unknown. A photo credit, image credit, or caption credit
that names someone else's licence stays unknown. uk_ogl requires the exact
British phrase Open Government Licence. Open Government License stays
unknown. us_government_work comes only from an explicit rights metadata
field.

Publication dates only. Updated, modified, and copyright years stay unknown.
A year-only date stays unknown. Script, style, and comment text does not
count. This module does not fetch. The requests library is not used.
It is not a belief collector. runner_wired stays false. RssCollector stays
the only belief collector.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "physical_intelligence_pages"
CATALOG_FILENAME = "physical_intelligence_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Physical Intelligence"
OFFICIAL_HOST = "www.physicalintelligence.company"
APEX_HOST = "physicalintelligence.company"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, APEX_HOST})
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
# Probed on 2026-10-06. Each response was HTTP 429. The www robots body was
# an HTML Vercel Security Checkpoint. Those URLs are not catalog rows.
CHALLENGED_URLS = (
    "https://www.physicalintelligence.company/robots.txt",
    "https://physicalintelligence.company/robots.txt",
    "https://www.physicalintelligence.company/",
    "https://physicalintelligence.company/",
)
OGL_PHRASE = "open government licence"
MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 1200
CATALOG_DESCRIPTION = (
    "Metadata for public Physical Intelligence pages on www.physicalintelligence.company "
    "and physicalintelligence.company. Both hosts resolve. On 2026-10-06, "
    "www.physicalintelligence.company/robots.txt was HTML titled Vercel Security "
    "Checkpoint with X-Vercel-Mitigated: challenge, so it does not allow a fetch. "
    "The apex robots.txt and both homepages returned HTTP 429 and were not stored. "
    "The checkpoint was not bypassed. An unresolved host, HTML or challenge robots.txt, "
    "a Cloudflare, cookie, or captcha challenge, or a redirect off these hosts is an "
    "empty catalog. Rows store a title, publisher, canonical URL, date, and rights. "
    "Page text is not stored. creative_commons_attribution is CC BY alone. "
    "creative_commons is CC0, CC BY-SA, or a permissive mix. A stated model-release "
    "licence may be that page's rights token. A missing date stays unknown. Updated, "
    "modified, copyright years, and year-only dates are not publication dates. "
    "Not a belief collector. runner_wired is false."
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
_PUBLIC_SECTIONS = frozenset(
    {"about", "blog", "news", "papers", "posts", "publications", "research"}
)
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "admin",
        "api",
        "assets",
        "atom",
        "auth",
        "careers",
        "cart",
        "cdn-cgi",
        "checkout",
        "feed",
        "jobs",
        "join",
        "log-in",
        "login",
        "rss",
        "search",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "static",
        "user",
        "users",
        "wp-admin",
        "wp-content",
        "wp-includes",
        "wp-json",
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
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".txt",
    ".webm",
    ".webp",
    ".xml",
    ".zip",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "cf-browser-verification",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "vercel security checkpoint",
    "x-vercel-mitigated",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_YEAR_ONLY = re.compile(r"^(?:19|20)\d{2}$")
_SEGMENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_TYPE = re.compile(r'"@type"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_PASSWORD = re.compile(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_LICENSE_META = frozenset(
    {"license", "licence", "dcterms.license", "dcterms.licence", "dc.license"}
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_ARTICLE_TYPES = frozenset(
    {"article", "blogposting", "newsarticle", "scholarlyarticle", "report"}
)
_SITE_SUFFIXES = (
    " | physical intelligence",
    " - physical intelligence",
    " – physical intelligence",
    " — physical intelligence",
    " · physical intelligence",
    " • physical intelligence",
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
    r"|\blicen[cs]ed under (?:the )?mit\b(?!-)"
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
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|image|caption)(?:[\s-]+credits?\b|\s*:)")
_CREDIT_DEED = re.compile(
    r"(?is)"
    r"cc[\s-]*by[\s-]*nc[\s-]*nd"
    r"|cc[\s-]*by[\s-]*nc[\s-]*sa"
    r"|cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd))"
    r"|cc[\s-]*by[\s-]*nd"
    r"|cc[\s-]*by[\s-]*sa"
    r"|cc[\s-]*by(?![\s-]*(?:nc|nd|sa))"
    r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv\w*"
    r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
    r"|creative commons attribution[\s-]*non[\s-]*commercial"
    r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
    r"|creative commons attribution[\s-]*no[\s-]*deriv\w*"
    r"|creative commons attribution[\s-]*share[\s-]*alike"
    r"|creative commons attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
    r"|creative commons zero"
    r"|(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
    r"|(?<![a-z0-9])cc0(?![a-z0-9])"
    r"|mit licen[cs]e"
    r"|apache licen[cs]e\s*,?\s*(?:version\s*)?2(?:\.0)?"
    r"|apache-2\.0"
    r"|mpl[\s-]*2\.0"
    r"|mozilla public licen[cs]e(?:\s*,?\s*version)?\s*2(?:\.0)?"
    r"|creativecommons\.org/(?:licenses/(?:by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-)"
    r"|publicdomain/zero)[^\"'\s<]*"
)
_VERSION_TAIL = re.compile(r"\s*\d+(?:\.\d+)?")
_BLOCK_BOUNDARY = re.compile(
    r"(?i)</(?:p|figcaption|li|div|td|dd|figure|blockquote|section|article|footer|caption|h[1-6])\b"
)
_UPDATED_WORD = re.compile(r"(?i)\b(?:updated|update|modified|modification|copyright)\b")
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
    """A catalog row or page failed the Physical Intelligence page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the two Physical Intelligence hosts, and never for a blocked address."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def empty_catalog_for_host(
    hostname: str,
    *,
    resolved: bool = True,
    challenge: bool = False,
    captcha: bool = False,
    cookie_challenge: bool = False,
    authentication_wall: bool = False,
    robots_html: bool = False,
    off_host_redirect: bool = False,
) -> bool:
    """True when that host contributes no rows.

    An unresolved host, a Cloudflare, cookie, or captcha challenge, an
    authentication wall, an HTML document in place of robots.txt, or a
    redirect off these hosts is an empty catalog. The caller does not bypass
    those controls.
    """

    host = (hostname or "").strip().lower().rstrip(".")
    if not resolved or not is_official_host(host):
        return True
    return bool(
        challenge
        or captcha
        or cookie_challenge
        or authentication_wall
        or robots_html
        or off_host_redirect
    )


def robots_allows(body: str, path: str) -> bool:
    """True when the * group does not disallow path.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. Comment-only robots text allows every path.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    if is_challenge_page(body[:8000]):
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
    """True when the response is a Cloudflare, cookie, captcha, or checkpoint page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    return any(marker in title for marker in _CHALLENGE_MARKERS)


def is_login_wall(page_html: str) -> bool:
    """True when the response asks for a password."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    return _PASSWORD.search(page_html) is not None


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
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
    redirects: Sequence[str] | None = None,
    robots_txt: str | None = None,
    resolved: bool = True,
) -> dict | None:
    """Return metadata when one allowed HTML response stayed on these hosts.

    A challenge, a captcha, a cookie interstitial, an authentication wall, an
    HTTP error, a robots disallow, HTML in place of robots.txt, an unresolved
    host, a non-HTML body, or a redirect off these hosts is not stored.
    """

    if resolved is not True:
        return None
    target = final_url or page_url
    if not _chain_stays(page_url, target, redirects):
        return None
    if robots_txt is not None and not robots_allows(robots_txt, urlparse(target).path or "/"):
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
    redirects: Sequence[str] | None = None,
    robots_txt: str | None = None,
    hostname: str | None = None,
    resolved: bool = True,
) -> list[dict]:
    """Return catalog rows for one response, or none when the response cannot be stored."""

    target = final_url or page_url
    if hostname is not None and empty_catalog_for_host(
        hostname,
        resolved=resolved,
        challenge=isinstance(page_html, str) and is_challenge_page(page_html),
        captcha=isinstance(page_html, str) and _is_captcha(page_html),
        cookie_challenge=isinstance(page_html, str) and _is_cookie_challenge(page_html),
        authentication_wall=_asks_for_login(status, page_html),
        robots_html=_robots_document_is_html(robots_txt),
        off_host_redirect=not _chain_stays(page_url, target, redirects),
    ):
        return []
    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        redirects=redirects,
        robots_txt=robots_txt,
        resolved=resolved,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    The organization's own model-release licence counts. A photo, image, or
    caption credit that names someone else's licence does not. Script, style,
    and comment text does not count. Bare MIT stays unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, gov = _rights_signals(page_text)
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
        return RIGHTS_CC_BY
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown.

    Updated, modified, and copyright years are not publication dates. A
    year-only value stays unknown. A date inside ordinary script, style, or
    comment text does not count. Two structured publication dates that
    disagree stay unknown. A time element is used only when the page states
    no structured publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found = _structured_publication_dates(page_html)
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        return UNKNOWN_DATE
    times = _time_publication_dates(_visible(page_html))
    if len(times) == 1:
        return times[0]
    if len(times) > 1:
        return UNKNOWN_DATE
    return _published_prose(_plain(_visible(page_html)))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    candidates: list[str] = []
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            candidates.append(title)
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            candidates.append(title)
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            candidates.append(title)
    for title in candidates:
        if not _generic_title(title):
            return title
    if candidates:
        return candidates[0]
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Physical Intelligence when the page states that name.

    A person named on the page is not the publisher. The hostname is not the
    publisher. The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site and not _names_publisher(site):
        raise CatalogError("publisher must be Physical Intelligence")
    for key in _PUBLISHER_KEYS:
        if _names_publisher(metas.get(key, "")):
            return PUBLISHER
    if _names_publisher(_plain(visible)):
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
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    if document.get("description") != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the Physical Intelligence catalog contract")
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
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError(f"canonical URL must be a public Physical Intelligence page: {url}")
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
        or not _is_public_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public Physical Intelligence page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if (
        not isinstance(value, str)
        or _YEAR_ONLY.fullmatch(value) is not None
        or _DATE.fullmatch(value) is None
        or _iso_day(value) is None
    ):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    visible = _visible(page_text)
    cc_codes: set[str] = set()
    software: set[str] = set()
    gov = False
    for key, value in _metas(visible).items():
        cleaned = _plain(_without_credit_regions(value))
        if key in _LICENSE_META or key in _RIGHTS_META:
            cc_codes |= _cc_codes(cleaned)
            software |= _software_codes(cleaned)
        if key in _RIGHTS_META and _states_us_government_work(cleaned):
            gov = True
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(visible):
        if not _is_rights_element(attrs):
            continue
        text = _plain(_without_credit_regions(body))
        if text and len(text) <= MAX_FIELD_CHARS and _states_us_government_work(text):
            gov = True
    kept = _strip_ignored_anchors(_without_credit_regions(visible))
    plain = _plain(kept)
    cc_codes |= _cc_codes(plain)
    software |= _software_codes(plain)
    for href in _hrefs(kept):
        if _is_generic_cc_licenses_url(href) or _is_public_domain_mark_url(href):
            continue
        cc_codes |= _cc_codes(href)
        software |= _software_codes(href)
    ogl = OGL_PHRASE in plain.casefold()
    return cc_codes, software, ogl, gov


def _structured_publication_dates(page_html: str) -> list[str]:
    found: list[str] = []
    without_comments = _COMMENT.sub(" ", page_html)
    for blob in _LDJSON.findall(without_comments):
        types = {match.group(1).casefold() for match in _LD_TYPE.finditer(blob)}
        if not types & _ARTICLE_TYPES:
            continue
        for raw in _DATE_PUBLISHED.findall(blob):
            _add_full_day(found, raw)
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        _add_full_day(found, metas.get(key, ""))
    return found


def _time_publication_dates(visible_html: str) -> list[str]:
    found: list[str] = []
    for attrs, body in _TIME.findall(visible_html):
        blob = f"{attrs} {body}"
        if _UPDATED_WORD.search(blob):
            continue
        raw = _attrs(f"<time {attrs}>").get("datetime", "")
        _add_full_day(found, raw)
    return found


def _add_full_day(found: list[str], value: object) -> None:
    if isinstance(value, str) and _YEAR_ONLY.fullmatch(value.strip()):
        return
    parsed = _iso_day(value)
    if parsed and parsed not in found:
        found.append(parsed)


def _without_credit_regions(page_html: str) -> str:
    """Drop a photo, image, or caption credit, including a Photo: sentence.

    A credit that names someone else's licence is not a licence for the page.
    A model-release licence stated outside that credit still counts.
    """

    normalized = page_html.replace("&nbsp;", " ").replace("&#160;", " ").replace("\xa0", " ")
    parts: list[str] = []
    cursor = 0
    for match in _CREDIT_PHRASE.finditer(normalized):
        if match.start() < cursor or _inside_tag(normalized, match.start()):
            continue
        parts.append(normalized[cursor : match.start()])
        window = normalized[match.end() : match.end() + 500]
        parts.append(" ")
        cursor = match.end() + _credit_end(window)
    parts.append(normalized[cursor:])
    return "".join(parts)


def _inside_tag(page_html: str, index: int) -> bool:
    last_open = page_html.rfind("<", 0, index)
    last_close = page_html.rfind(">", 0, index)
    return last_open > last_close


def _credit_end(window: str) -> int:
    limit = len(window)
    sentence = _sentence_end(window)
    if sentence is not None:
        limit = min(limit, sentence)
    boundary = _BLOCK_BOUNDARY.search(window)
    if boundary:
        limit = min(limit, boundary.start())
    deed = _CREDIT_DEED.search(window[:limit])
    if deed is None:
        return limit
    end = _extend_through_anchor(window, deed.end())
    version = _VERSION_TAIL.match(window, end)
    if version and version.start() <= limit:
        end = version.end()
        end = _extend_through_anchor(window, end)
    if end < limit:
        return end
    close = window.casefold().find("</a>", limit)
    if close != -1 and close < end:
        return end
    return limit


def _extend_through_anchor(window: str, end: int) -> int:
    lowered = window.casefold()
    open_rel = lowered.rfind("<a", 0, end)
    if open_rel == -1:
        return end
    close_before = lowered.rfind("</a>", 0, end)
    if close_before > open_rel:
        return end
    close = lowered.find("</a>", end)
    if close == -1 or close - end > 300:
        return end
    return close + len("</a>")


def _sentence_end(window: str) -> int | None:
    in_tag = False
    for index, char in enumerate(window):
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            continue
        if in_tag or char != ".":
            continue
        if index + 1 == len(window) or window[index + 1] in " \t\n\r<":
            return index + 1
    return None


def _strip_ignored_anchors(page_html: str) -> str:
    """Drop anchors whose URL is not a specific deed.

    A generic creativecommons.org/licenses URL is not a licence. A
    public-domain mark URL is not CC0. Anchor text on those URLs does not
    count. A specific deed URL keeps its text.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href) or _is_public_domain_mark_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for the Creative Commons licences index, not a deed."""

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(unescape(href).strip())
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in _GENERIC_CC_HOSTS:
        return False
    path = (parsed.path or "").casefold()
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _is_public_domain_mark_url(href: str) -> bool:
    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(unescape(href).strip())
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in _GENERIC_CC_HOSTS:
        return False
    path = (parsed.path or "").casefold()
    return path.startswith("/publicdomain/mark")


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


def _chain_stays(page_url: str, final_url: str | None, redirects: Sequence[str] | None) -> bool:
    urls = [page_url]
    if final_url:
        urls.append(final_url)
    if redirects:
        urls.extend(redirects)
    return all(_on_official_host(url) for url in urls)


def _is_public_path(path: str) -> bool:
    """True for the homepage and public editorial HTML on these hosts.

    Login, account, admin, careers, search, and downloads are not stored.
    """

    if not isinstance(path, str) or path != path.lower():
        return False
    if ".." in path or "\\" in path or "//" in path:
        return False
    raw = path[:-1] if path.endswith("/") and len(path) > 1 else path
    if raw.lower().endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in raw.split("/") if part]
    if not parts:
        return True
    if any(part in _BLOCKED_PARTS for part in parts):
        return False
    if not all(_SEGMENT.fullmatch(part) for part in parts):
        return False
    return parts[0] in _PUBLIC_SECTIONS


def _blocked_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name in {"cf-mitigated", "x-vercel-mitigated"} and "challenge" in token:
            return True
        if "captcha" in name or "sg-captcha" in token:
            return True
    return False


def _is_captcha(page_html: str) -> bool:
    sample = page_html.casefold()
    return "sg-captcha" in sample or "sgcaptcha" in sample


def _is_cookie_challenge(page_html: str) -> bool:
    return "enable javascript and cookies" in page_html.casefold()


def _asks_for_login(status: object, page_html: object) -> bool:
    if isinstance(page_html, str) and is_login_wall(page_html):
        return True
    return status in {401, 403} and not isinstance(page_html, str)


def _robots_document_is_html(body: object) -> bool:
    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    return "<html" in sample or is_challenge_page(body[:8000])


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    if match.group(1):
        return _iso_day(match.group(1)) or UNKNOWN_DATE
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4)) or UNKNOWN_DATE
    return _calendar_date(match.group(6), match.group(5), match.group(7)) or UNKNOWN_DATE


def _names_publisher(value: str) -> bool:
    return "physical intelligence" in _clean_text(value).casefold()


def _generic_title(value: str) -> bool:
    return value.casefold() in {PUBLISHER.casefold()}


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
                text = text[: -len(suffix)].strip()
                changed = True
                break
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
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
    text = value.strip()
    if _YEAR_ONLY.fullmatch(text):
        return None
    match = _DATE_PREFIX.match(text)
    if match is None:
        return None
    try:
        date.fromisoformat(match.group(1))
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
