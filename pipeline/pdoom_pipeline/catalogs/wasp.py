"""Metadata catalog of public WASP research, program, and news pages.

Hosts are wasp-sweden.org and www.wasp-sweden.org. www.wasp-sweden.org
redirects to wasp-sweden.org, so a response is stored at the final URL only
when that URL stays on one of these hosts. robots.txt on wasp-sweden.org
allows the public site. Each stored URL was confirmed with one bounded GET
of HTML.

Pages are research, program, and news HTML. Person profiles, job boards,
event listings, login walls, PDFs, and off-host pages are omitted. A
Cloudflare challenge, a captcha, an authentication wall, an HTML document
served in place of robots.txt, a host that does not resolve, or a redirect
off these hosts contributes nothing. An empty catalog is correct in those
cases. This module does not bypass those controls.

A row keeps the title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, chart data, and PDFs are
not stored. The live URL is stored as confirmed; a different rel=canonical
does not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` means CC BY alone, including a
https://creativecommons.org/licenses/by/4.0/ URL. ``creative_commons`` means
CC0, CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``,
``cc_by_nc_sa``, or ``cc_by_nc_nd``. Text cc-by-nc maps to ``cc_by_nc``. A
hyphen is a word boundary, so CC BY does not match CC BY-NC and licenses/by
does not match licenses/by-nc. Two different restricted deeds stay unknown.
A permissive anchor on a restricted deed URL or a public-domain mark URL
stays unknown. A CC0 anchor on a publicdomain/mark URL stays unknown. A
generic https://creativecommons.org/licenses/ URL stays unknown, including a
missing slash, http, a www host, or a query string. Anchor text on that
generic URL stays unknown. A specific deed URL still counts. A software
licence beside any Creative Commons deed stays unknown. Two software
licences stay unknown. A sole MIT License, including "Licensed under the MIT
License", is mit. Bare MIT stays unknown. A sole MPL-2.0 is mpl-2.0. Apache
License, Version 2.0 is apache-2.0. ``uk_ogl`` requires the exact British
phrase Open Government Licence. Open Government License stays unknown.
``us_government_work`` comes only from an explicit rights metadata field. A
photo credit, caption credit, or image credit that names someone else's
licence stays unknown, including "Photo credit: UNDRR, CC BY-NC-ND 2.0" and
"Photo: UNDRR, CC BY-NC-ND 2.0". A page licence stated outside that credit
still counts, including when the page states CC BY and a separate photo
credit names another licence.

Updated, modified, and copyright years are not publication dates. Script,
style, and comment text does not count. A missing publication date stays
unknown. This module does not fetch. It is not a belief collector.
``runner_wired`` stays false. Belief collection stays on RssCollector.
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

CATALOG_ID = "wasp_pages"
CATALOG_FILENAME = "wasp_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Wallenberg AI, Autonomous Systems and Software Program"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CC_ATTRIBUTION,
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
OFFICIAL_HOST = "wasp-sweden.org"
WWW_HOST = "www.wasp-sweden.org"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, WWW_HOST})
# Both hosts resolved on 2026-10-06. An unresolved lookup is still empty.
UNRESOLVED_HOSTS: frozenset[str] = frozenset()
# Confirmed from https://wasp-sweden.org/robots.txt. The * group allows the site.
CONFIRMED_ROBOTS_TXT = (
    "# START YOAST BLOCK\n"
    "# ---------------------------\n"
    "User-agent: *\n"
    "Disallow:\n"
    "\n"
    "Sitemap: https://wasp-sweden.org/sitemap_index.xml\n"
    "# ---------------------------\n"
    "# END YOAST BLOCK\n"
)
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 1200
CATALOG_DESCRIPTION = (
    "Metadata for public Wallenberg AI, Autonomous Systems and Software Program "
    "research, program, and news pages. Hosts are wasp-sweden.org and "
    "www.wasp-sweden.org. www.wasp-sweden.org redirects to wasp-sweden.org, so a "
    "response is stored only at a final URL that stays on one of these hosts. "
    "Each stored URL was confirmed with one bounded GET of HTML that robots.txt "
    "allows. Person profiles, PDFs, login walls, and off-host pages are omitted. "
    "A challenge page, an HTML document in place of robots.txt, an unresolved "
    "host, or a redirect off these hosts is not stored. Rows store a title, "
    "publisher, canonical URL, publication date, and rights. Page text is not "
    "stored. creative_commons_attribution means CC BY alone. creative_commons "
    "means CC0, CC BY-SA, or a permissive mix of those. A missing publication "
    "date is unknown. Updated, modified, and copyright years are not publication "
    "dates. This catalog is not a belief collector and runner_wired is false."
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
        "dcterms.created",
        "dcterms.issued",
        "dc.date.issued",
        "datepublished",
    }
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dcterms.rights",
        "rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "twitter:title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_PAGINATION = re.compile(r"page-?\d+")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_ELEMENT = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RELATED = re.compile(r"(?is)class\s*=\s*['\"][^'\"]*(?:news-related|related-posts)")
_CREDIT_BLOCK = re.compile(
    r"(?is)<(p|li|figcaption|td|dd|small|cite|caption)\b([^>]*)>(.*?)</\1>"
)
_CITATION_BLOCK = re.compile(r"(?is)<(p|li|dd|figcaption)\b[^>]*>.*?</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
_SCHOLARLY_HOSTS = (
    "arxiv.org",
    "doi.org",
    "dx.doi.org",
    "openreview.net",
    "proceedings.neurips.cc",
    "proceedings.mlr.press",
    "aclanthology.org",
    "ieeexplore.ieee.org",
    "link.springer.com",
    "nature.com",
    "biorxiv.org",
    "openaccess.thecvf.com",
    "papers.nips.cc",
    "dl.acm.org",
)
_SITE_SUFFIXES = (
    " | wallenberg ai, autonomous systems and software program",
    " - wallenberg ai, autonomous systems and software program",
    " – wallenberg ai, autonomous systems and software program",
    " — wallenberg ai, autonomous systems and software program",
    " | wasp",
    " - wasp",
    " – wasp",
    " — wasp",
)
_PROGRAM_ROOTS = frozenset(
    {
        "about-us",
        "funded-projects",
        "graduate-school",
        "opportunities",
        "wasp-alumni",
        "wasp-postdoc",
    }
)
_RESEARCH_ROOTS = frozenset(
    {
        "publications",
        "publications-bibl",
        "reports",
        "research",
        "theses",
        "wasp-publications-2015-2024",
    }
)
_NAMED_RESEARCH_SLUGS = frozenset(
    {
        "multi-dimensional-alignment-and-integration",
        "sting-synthesis-and-analysis-with-transducers-and-invertible-neural-generators",
    }
)
_EXCLUDED_ROOTS = frozenset(
    {
        "9-2",
        "calls",
        "lorem-ipsum-1",
        "newsletter-subscription",
        "old-event",
        "old-events",
        "positions",
        "submit-an-event",
    }
)
_EXCLUDED_SEGMENTS = frozenset(
    {
        "account",
        "admin",
        "alumni",
        "amp",
        "attachment",
        "author",
        "authors",
        "cdn-cgi",
        "contact",
        "embed",
        "event",
        "events",
        "faculty",
        "feed",
        "kontakta-oss",
        "log-in",
        "login",
        "member",
        "members",
        "newsletter-subscription",
        "page",
        "people",
        "person",
        "persons",
        "privacy",
        "privacy-policy",
        "profile",
        "profiles",
        "scientist",
        "scientists",
        "search",
        "sign-in",
        "signin",
        "staff",
        "student",
        "students",
        "submit-an-event",
        "team",
        "wp-admin",
        "wp-content",
        "wp-json",
        "wp-login",
        "xmlrpc",
    }
)
_EXCLUDED_SV_SLUGS = frozenset({"miltton-test-se", "wasp"})
_LOGIN_PATHS = (
    "/login",
    "/log-in",
    "/signin",
    "/sign-in",
    "/account",
    "/wp-login",
    "/wp-admin",
    "/users/sign_in",
    "/admin",
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
_CHALLENGE_MARKERS = (
    "performing security verification",
    "challenge-platform",
    "cf-mitigated",
    "cf-browser-verification",
    "sg-captcha",
    "sgcaptcha",
    "/cdn-cgi/challenge-platform",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
)
_CHALLENGE_TITLES = (
    "just a moment",
    "attention required",
    "checking your browser",
    "enable javascript and cookies",
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
# Longer deeds are listed first. (?!-) and (?![a-z0-9-]) keep CC BY and
# licenses/by from matching CC BY-NC and licenses/by-nc.
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"),
    ),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"),
    ),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    ("by-nc", re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-nd", re.compile(r"creative commons attribution[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]*share[\s-]*alike")),
    ("zero", re.compile(r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])")),
    ("zero", re.compile(r"creative commons(?:\s+public\s+domain)?[\s-]*zero(?![a-z])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![a-z0-9])")),
    ("by", re.compile(r"creative commons attribution(?![\s-]*(?:non|no[\s-]*deriv|share))")),
    ("mark", re.compile(r"public domain mark")),
)
_URL_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"creativecommons\.org/licenses/by-nc-nd(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(r"creativecommons\.org/licenses/by-nc-sa(?![a-z0-9-])")),
    ("by-nc", re.compile(r"creativecommons\.org/licenses/by-nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"creativecommons\.org/licenses/by-nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"creativecommons\.org/licenses/by-sa(?![a-z0-9-])")),
    ("by", re.compile(r"creativecommons\.org/licenses/by(?!-)(?![a-z0-9])")),
    ("zero", re.compile(r"creativecommons\.org/publicdomain/zero(?![a-z0-9-])")),
    ("mark", re.compile(r"creativecommons\.org/publicdomain/mark(?![a-z0-9-])")),
)
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
}
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_US_GOV_WORK = re.compile(
    r"\b(?:united states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+(?:united states|u\.s\.|us)\s+government\b"
)
_NEGATED_US_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united states|u\.s\.|us)\s+government\b"
)
_MIT = re.compile(r"(?<!modified )(?:\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_CREDIT_PHRASE = re.compile(
    r"(?i)\b(?:photo|image|caption)\s+credits?\b|\b(?:photo|image|caption)\s*:"
)
_CREDIT_CLASS = re.compile(
    r"(?i)(?:photo|image|caption)[\s_-]*credits?|\bwp-caption\b|\bfield-credit\b"
)
# Cross tags so "Photo: UNDRR, <a ...>CC BY-NC-ND 2.0</a>" drops the deed URL.
# A period inside 2.0 is not a sentence end. A later licence sentence stays.
_CREDIT_SENTENCE = re.compile(
    r"(?is)\b(?:photo|image|caption)\s+credits?\b.{0,500}?(?:\.(?=\s|<|$)|$)"
    r"|\b(?:photo|image|caption)\s*:.{0,500}?(?:\.(?=\s|<|$)|$)"
)
_PUBLISHED_PROSE = re.compile(
    r"\b(?:published|publication date|date published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
    re.I,
)
_QUOTED = re.compile("“[^”]{0,400}”|„[^“]{0,400}“|" + '"[^"\\n]{0,400}"')
_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


class CatalogError(ValueError):
    """A catalog row or page failed the WASP page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for wasp-sweden.org and www.wasp-sweden.org."""

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
    authentication_wall: bool = False,
) -> bool:
    """True when that host contributes no rows.

    An unresolved host, a Cloudflare challenge, a captcha, or an
    authentication wall is an empty catalog. The caller does not bypass it.
    """

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or host in UNRESOLVED_HOSTS or not resolved:
        return True
    return bool(challenge or captcha or authentication_wall)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    title = _TITLE.search(page_html[:12000])
    if title and any(marker in title.group(1).casefold() for marker in _CHALLENGE_TITLES):
        return True
    head = page_html[:8000].casefold()
    return any(marker in head for marker in _CHALLENGE_MARKERS)


def is_login_wall(page_html: str) -> bool:
    """True when the HTML is an authentication form rather than a public page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if is_challenge_page(page_html):
        return False
    visible = _without_hidden(page_html).casefold()
    if 'type="password"' not in visible and "type='password'" not in visible:
        return False
    return any(marker in visible for marker in ("sign in", "log in", "login", "authenticate"))


def robots_allows(body: str, path: str) -> bool:
    """True when the * group does not disallow ``path``.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. An empty User-agent group allows every path.
    """

    if not isinstance(body, str) or not isinstance(path, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or is_challenge_page(body[:8000]):
        return False
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    return not robots_disallows(body, target)


def robots_disallows(robots_txt: str, path: str) -> bool:
    """True when User-agent: * disallows ``path``.

    The longest matching Allow or Disallow wins. An empty Disallow does not
    block the site.
    """

    if not isinstance(robots_txt, str) or not isinstance(path, str) or not path.startswith("/"):
        return False
    rules = _star_rules(robots_txt)
    best_len = -1
    blocked = False
    for kind, value in rules:
        if not value:
            continue
        matched = path.startswith(value) or (value.endswith("/") and path == value[:-1])
        if not matched:
            continue
        length = len(value)
        if length > best_len:
            best_len = length
            blocked = kind == "disallow"
        elif length == best_len and kind == "allow":
            blocked = False
    return blocked


def listing_is_blocked(
    path: str,
    *,
    status: object = None,
    content_type: object = None,
    page_html: object = None,
    headers: Mapping[str, str] | None = None,
    robots_txt: str | None = None,
    hostname: str | None = None,
    resolved: bool = True,
) -> bool:
    """True when a listing must contribute an empty catalog for that host or path."""

    if hostname and empty_catalog_for_host(
        hostname,
        resolved=resolved,
        challenge=isinstance(page_html, str) and is_challenge_page(page_html),
        authentication_wall=status in {401, 403},
    ):
        return True
    if not isinstance(path, str) or not path.startswith("/"):
        return True
    if robots_txt is not None and not robots_allows(robots_txt, path):
        return True
    if status in {401, 403, 202, 429}:
        return True
    if isinstance(page_html, str) and (is_challenge_page(page_html) or is_login_wall(page_html)):
        return True
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return True
            if name == "sg-captcha":
                return True
            if name == "www-authenticate":
                return True
    return False


def rows_for_listing(
    path: str,
    *,
    status: object = None,
    content_type: object = None,
    page_html: object = None,
    headers: Mapping[str, str] | None = None,
    robots_txt: str | None = None,
    hostname: str | None = None,
    resolved: bool = True,
) -> list[dict]:
    """Return no rows when a listing is blocked.

    A readable listing is not itself stored by this helper. Child pages are
    recorded individually after their own GET.
    """

    if listing_is_blocked(
        path,
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        robots_txt=robots_txt,
        hostname=hostname,
        resolved=resolved,
    ):
        return []
    return []


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or login wall."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if is_login_wall(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
            if name == "www-authenticate":
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
    """Return metadata when one bounded response is on-host research, program, or news HTML.

    A challenge, a captcha, an authentication wall, a non-HTML body, an error
    status, a robots disallow, a person profile, or an off-host URL is not
    stored. www.wasp-sweden.org is stored only when the final response stays
    on an official host.
    """

    target = final_url or page_url
    parsed = urlparse(target)
    host = parsed.hostname or ""
    if not is_official_host(host) or host.lower().rstrip(".") in UNRESOLVED_HOSTS:
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

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY. Mixed restricted and permissive text
    stays unknown. A software licence beside any Creative Commons deed stays
    unknown. Two software licences stay unknown. Two different restricted
    deeds stay unknown. A permissive anchor on a restricted or Public Domain
    Mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL stays
    unknown. A generic creativecommons.org/licenses URL is not a deed, and
    the visible text of that anchor does not count. A photo credit, caption
    credit, image credit, or a "Photo:" credit does not count. Script, style,
    and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _drop_foreign_licence_citations(_without_credit(_without_hidden(page_text)))
    plain = _drop_quoted_licence_mentions(_plain(_without_generic_cc_license_anchors(visible)))
    folded = plain.casefold().translate(_DASHES)
    codes = _text_codes(folded)
    hrefs = [href for href in _hrefs(visible) if not _is_generic_cc_licenses_url(href)]
    for href in hrefs:
        codes |= _url_codes(href.casefold().translate(_DASHES))
    licence_bits: list[str] = []
    for key, content in _meta_pairs(visible):
        if key not in _LICENSE_META:
            continue
        chunk = _plain(content).casefold().translate(_DASHES)
        licence_bits.append(chunk)
        codes |= _text_codes(chunk)
        codes |= _url_codes(chunk)
    scanned = " ".join([folded, *licence_bits, *(href.casefold() for href in hrefs)])
    mit = bool(_MIT.search(scanned) or any(_MIT_URL.search(href.casefold()) for href in hrefs))
    apache = bool(_APACHE.search(scanned) or any(_APACHE_URL.search(href.casefold()) for href in hrefs))
    mpl = bool(_MPL.search(scanned) or any(_MPL_URL.search(href.casefold()) for href in hrefs))
    return _label(
        codes,
        mit=mit,
        apache=apache,
        mpl=mpl,
        ogl=bool(_OGL_PHRASE.search(folded)),
        us_gov=_states_us_government_work(visible),
    )


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, and a copyright
    year are not publication dates. Disagreeing publication dates stay unknown.
    Script, style, and comment text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    found: list[str] = []
    for key, content in _meta_pairs(visible):
        if key not in _PUBLICATION_META:
            continue
        parsed = _iso_day(content)
        if parsed:
            found.append(parsed)
    found.extend(_time_publication_dates(visible))
    distinct = set(found)
    if len(distinct) == 1:
        return found[0]
    if distinct:
        return UNKNOWN_DATE
    return _published_prose(_plain(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
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
    """Return the program name when the page states WASP or that name.

    A person named on the page is not the publisher. The hostname alone is
    not the publisher. The site name WASP on these pages is this program.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher", "publisher"):
        value = _clean_text(metas.get(key, ""))
        folded = value.casefold()
        if folded == "wasp" or PUBLISHER.casefold() in folded:
            return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
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
    if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "runner_wired is false" not in description:
        raise CatalogError("description must state that runner_wired is false")
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
        raise CatalogError("canonical URL must be a public WASP research, program, or news page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    normalized = f"https://{host}{path}"
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or host in UNRESOLVED_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or url != normalized
        or not _in_scope_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public WASP research, program, or news page: {url}")
    return normalized


def _in_scope_path(path: str) -> bool:
    """True for research, program, and news HTML on the official hosts.

    Person profiles, job boards, events, login walls, PDFs, pagination, and
    the bare homepage stay out. News articles use a single WordPress slug.
    Swedish news uses /sv/{slug}/. Research and program pages keep their
    section prefix.
    """

    if not path.startswith("/") or ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    if path != path.lower() or path == "/" or not path.endswith("/"):
        return False
    bare = path[:-1]
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if any(bare == marker or bare.startswith(marker + "/") for marker in _LOGIN_PATHS):
        return False
    parts = [part for part in bare.split("/") if part]
    if not parts or any(not _SEGMENT.fullmatch(part) for part in parts):
        return False
    if any(part in _EXCLUDED_SEGMENTS or _PAGINATION.fullmatch(part) for part in parts):
        return False
    if parts[0] in _EXCLUDED_ROOTS or parts[0].startswith("wallenberg-advanced-scientific-forum"):
        return False
    if parts[0].startswith("lorem-ipsum"):
        return False
    if parts[0] == "news":
        return len(parts) <= 2
    if parts[0] == "research":
        return len(parts) <= 5
    if parts[0] in _PROGRAM_ROOTS:
        return len(parts) <= 4
    if parts[0] in _RESEARCH_ROOTS:
        return len(parts) <= 3
    if parts[0].startswith("nest-project-") or parts[0] in _NAMED_RESEARCH_SLUGS:
        return len(parts) == 1
    if parts[0] == "sv":
        return _swedish_scope(parts)
    return len(parts) == 1


def _swedish_scope(parts: list[str]) -> bool:
    if len(parts) < 2 or parts[1] in _EXCLUDED_SV_SLUGS or parts[1].startswith("lorem-ipsum"):
        return False
    if parts[1] == "om-wasp":
        return len(parts) <= 5
    if parts[1] == "nyheter":
        return len(parts) <= 3
    if parts[1] == "ai-autonoma-system-och-mjukvara":
        return len(parts) == 2
    return len(parts) == 2


def _label(
    codes: set[str],
    *,
    mit: bool,
    apache: bool,
    mpl: bool,
    ogl: bool,
    us_gov: bool,
) -> str:
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    families = [
        name
        for name, present in (
            ("restricted", bool(restricted)),
            ("permissive", bool(permissive)),
            ("mit", mit),
            ("apache", apache),
            ("mpl", mpl),
            ("ogl", ogl),
            ("us", us_gov),
        )
        if present
    ]
    if len(families) != 1:
        return RIGHTS_UNKNOWN
    if restricted:
        if len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive:
        if permissive == {"by"}:
            return RIGHTS_CC_ATTRIBUTION
        if permissive <= _PERMISSIVE and permissive & {"by-sa", "zero"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_UNKNOWN
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if ogl:
        return RIGHTS_UK_OGL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def _text_codes(folded: str) -> set[str]:
    found: list[tuple[int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            start, end = match.span()
            if any(start < prev_end and end > prev_start for prev_start, prev_end, _code in found):
                continue
            found.append((start, end, code))
    return {code for _start, _end, code in found}


def _url_codes(value: str) -> set[str]:
    found: set[str] = set()
    for code, pattern in _URL_DEEDS:
        if pattern.search(value):
            found.add(code)
    return found


def _states_us_government_work(visible_html: str) -> bool:
    """True only when a rights metadata field says the item is a US government work."""

    for key, content in _meta_pairs(visible_html):
        if key not in _RIGHTS_META:
            continue
        text = _plain(content).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _time_publication_dates(visible_html: str) -> list[str]:
    cut = _RELATED.search(visible_html)
    scope = visible_html[: cut.start()] if cut else visible_html
    found: list[str] = []
    for attrs in _TIME.findall(scope):
        parsed_attrs = _attrs(f"<time {attrs}>")
        if parsed_attrs.get("itemprop", "").casefold() != "datepublished":
            continue
        parsed = _iso_day(parsed_attrs.get("datetime", ""))
        if parsed:
            found.append(parsed)
    return found


def _published_prose(plain: str) -> str:
    """Return one prose publication date, or unknown when the page states several.

    A listing that says "Decision published" for more than one day does not
    have a single page publication date. Updated and copyright lines are not
    matched by the publication pattern.
    """

    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        if match.group(1):
            parsed = _iso_day(match.group(1))
        elif match.group(4):
            parsed = _calendar_date(match.group(2), match.group(3), match.group(4))
        else:
            parsed = _calendar_date(match.group(6), match.group(5), match.group(7))
        if parsed:
            found.append(parsed)
    distinct = set(found)
    if len(distinct) == 1:
        return found[0]
    return UNKNOWN_DATE


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold().rstrip("."))
    if month is None:
        return None
    try:
        return date(int(year_text), month, int(day_text)).isoformat()
    except ValueError:
        return None


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} is too long to store")


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
    lowered = text.casefold()
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                lowered = text.casefold()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _without_credit(page_html: str) -> str:
    """Drop photo, image, and caption credits, including a Photo: credit line.

    A reuse sentence in the same paragraph stays. The credit sentence does not.
    """

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if len(body) > 800:
            return match.group(0)
        if _CREDIT_CLASS.search(attrs) or _CREDIT_PHRASE.search(attrs):
            return " "
        if _CREDIT_PHRASE.search(body):
            return _CREDIT_SENTENCE.sub(" ", body)
        return match.group(0)

    stripped = _CREDIT_BLOCK.sub(replace_block, page_html)

    def replace_anchor(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    stripped = _ANCHOR_ELEMENT.sub(replace_anchor, stripped)
    return _CREDIT_SENTENCE.sub(" ", stripped)


def _drop_foreign_licence_citations(page_html: str) -> str:
    """Drop a citation that names someone else's licence next to a paper host.

    A licence stated elsewhere on the page is left in place.
    """

    def replace(match: re.Match[str]) -> str:
        folded = match.group(0).casefold()
        foreign = any(host in folded for host in _SCHOLARLY_HOSTS)
        names_licence = (
            "creativecommons.org" in folded
            or "creative commons" in folded
            or "cc by" in folded
            or "cc-by" in folded
            or "mit license" in folded
            or "mit licence" in folded
            or "apache license" in folded
            or "mpl-2.0" in folded
        )
        if foreign and names_licence:
            return " "
        return match.group(0)

    return _CITATION_BLOCK.sub(replace, page_html)


def _drop_quoted_licence_mentions(plain: str) -> str:
    """Drop a quoted title that names someone else's licence."""

    def replace(match: re.Match[str]) -> str:
        inner = match.group(0).casefold()
        if re.search(r"licen[cs]e|creative commons|cc[\s-]*by|mit licen", inner):
            return " "
        return match.group(0)

    return _QUOTED.sub(replace, plain)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for the Creative Commons licences index, not a deed.

    http and https, a www host, a missing trailing slash, and a query string
    stay on that generic path. A deed such as /licenses/by/4.0/ does not.
    """

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(href.strip())
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in _GENERIC_CC_HOSTS:
        return False
    path = (parsed.path or "").casefold()
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _without_generic_cc_license_anchors(page_html: str) -> str:
    """Drop anchors whose href is only the generic licences index."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR_ELEMENT.sub(replace, page_html)


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _meta_pairs(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        if key and "content" in attrs:
            found.append((key, attrs["content"]))
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _star_rules(robots_txt: str) -> list[tuple[str, str]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().casefold()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value.casefold())
        elif key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    flush()
    selected: list[tuple[str, str]] = []
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            selected.extend(group_rules)
    return selected
