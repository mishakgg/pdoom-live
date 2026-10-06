"""Metadata catalog of public Microsoft Research pages about artificial intelligence.

Preferred hosts are research.microsoft.com and www.research.microsoft.com when
a response stays on that host. research.microsoft.com redirects to
www.microsoft.com, so that URL is not stored. www.research.microsoft.com does
not present a certificate for that name, so that host contributes no rows.
The live research site is www.microsoft.com under /en-us/research/. Stored
pages are artificial-intelligence research-area, group, theme, collaboration,
project, and story HTML. Person profiles, product marketing, login walls,
PDFs, blogs, publication records, and unrelated topics stay out.

Each stored URL was confirmed with one bounded GET of public HTML that
robots.txt allowed. A challenge page, an HTML document in place of
robots.txt, a host that does not resolve, or a redirect off the catalogued
hosts is not stored. An empty catalog is correct in those cases. This module
does not fetch and it does not bypass Cloudflare, captchas, authentication,
or robots.

A row keeps the title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, PDFs, quotes, transcripts, and chart data are
not stored. The live URL is stored as confirmed; a different rel=canonical
does not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone, including a specific
/licenses/by/4.0/ URL. creative_commons means CC0, CC BY-SA, or a permissive
mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps
cc_by_nc, cc_by_nd, cc_by_nc_sa, or cc_by_nc_nd. Text cc-by-nc maps to
cc_by_nc. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
Two different restricted deeds stay unknown. A permissive anchor on a
restricted deed URL or a public-domain mark URL stays unknown. A CC0 anchor
on a publicdomain/mark URL stays unknown. A generic
creativecommons.org/licenses or /licenses URL is not a deed, including a
missing slash, http, www, or a query string, and anchor text on it stays
unknown. A specific deed URL still counts. A software licence beside any
Creative Commons deed stays unknown. Two software licences stay unknown.
Bare MIT stays unknown. Licensed under the MIT License is mit. Apache
License, Version 2.0 is apache-2.0. A sole MPL-2.0 is mpl-2.0. uk_ogl is
only the British phrase Open Government Licence. Open Government License
stays unknown. us_government_work comes only from an explicit rights
metadata field. Photo credit, caption credit, and image credit that name
someone else's licence stay unknown, including Photo credit: UNDRR, CC
BY-NC-ND 2.0 and Photo: UNDRR, CC BY-NC-ND 2.0. When the page states its own
CC BY licence and a separate photo credit names another licence, the page
stays creative_commons_attribution. Script, style, and comment text does not
count.

Publication dates only. Modified, updated, and copyright years stay unknown.
This module is not a belief collector. runner_wired stays false.
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

CATALOG_ID = "microsoft_research_pages"
CATALOG_FILENAME = "microsoft_research_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Microsoft Research"
UNKNOWN_DATE = "unknown"
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
PREFERRED_HOSTS = frozenset({"research.microsoft.com", "www.research.microsoft.com"})
LIVE_HOST = "www.microsoft.com"
OFFICIAL_HOSTS = frozenset({*PREFERRED_HOSTS, LIVE_HOST})
# Confirmed 2026-10-06: DNS resolves, then the certificate hostname does not match.
CERTIFICATE_MISMATCH_HOSTS = frozenset({"www.research.microsoft.com"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 900
MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 15.0
CATALOG_DESCRIPTION = (
    "Metadata for public Microsoft Research AI pages. "
    "research.microsoft.com redirects off-host and is not stored. "
    "www.research.microsoft.com has no matching certificate, so that host is empty. "
    "Live rows are www.microsoft.com under /en-us/research/ for AI areas, groups, themes, "
    "collaborations, projects, and stories. Each URL was one bounded GET that robots.txt allowed. "
    "Person profiles, product marketing, login walls, PDFs, blogs, publications, and unrelated topics "
    "are omitted. A challenge, HTML robots.txt, or an off-host redirect is not stored. "
    "Rows store a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "creative_commons_attribution means CC BY alone. creative_commons means CC0, CC BY-SA, or a "
    "permissive mix. A missing date is unknown. Updated, modified, and copyright years are not "
    "publication dates. This catalog is not a belief collector and runner_wired is false."
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
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_ELEMENT = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
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
    "aclanthology.org",
    "dl.acm.org",
)
_SITE_SUFFIXES = (
    " | microsoft research",
    " - microsoft research",
    " | microsoft ai",
    " - microsoft ai",
)
_SECTIONS = frozenset({"research-area", "group", "theme", "collaboration", "project", "story"})
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "admin",
        "author",
        "authors",
        "blog",
        "careers",
        "cdn-cgi",
        "event",
        "events",
        "feed",
        "login",
        "people",
        "person",
        "podcast",
        "product",
        "products",
        "profile",
        "profiles",
        "publication",
        "publications",
        "search",
        "sign-in",
        "signin",
        "staff",
        "wp-admin",
        "wp-content",
        "wp-includes",
        "wp-json",
        "wp-login.php",
    }
)
_LOGIN_PATHS = (
    "/login",
    "/log-in",
    "/signin",
    "/sign-in",
    "/account",
    "/wp-login",
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
_AI_PHRASES = (
    "artificial-intelligence",
    "machine-learning",
    "deep-learning",
    "reinforcement-learning",
    "natural-language",
    "human-language",
    "computer-vision",
    "foundation-model",
    "generative-ai",
    "responsible-ai",
    "machine-intelligence",
    "machine-translation",
    "language-model",
    "large-language",
    "neural-network",
    "deep-neural",
)
_AI_TOKENS = frozenset({"ai", "fate", "msai", "aiei", "codeai"})
_GENERIC_HEADINGS = frozenset(
    {
        "home",
        "menu",
        "microsoft",
        "microsoft research",
        "research",
        "search",
    }
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
# Longer deeds are listed first. (?!-) keeps CC BY from matching CC BY-NC.
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
_CREDIT_SENTENCE = re.compile(
    r"(?is)\b(?:photo|image|caption)\s+credits?\b.{0,500}?(?:\.(?=\s|<|$)|$)"
    r"|\b(?:photo|image|caption)\s*:.{0,500}?(?:\.(?=\s|<|$)|$)"
)
# "Posted :" is a job-board label on Microsoft Research listings, not a publication date.
_PUBLISHED_PROSE = re.compile(
    r"\b(?:published|publication date|date published|posted\s+on)\b(?:\s+on)?\s*:?\s*"
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
    """A catalog row or page failed the Microsoft Research page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for a catalogued Microsoft Research host."""

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
    certificate_mismatch: bool = False,
    html_robots: bool = False,
) -> bool:
    """True when that host contributes no rows.

    An unresolved host, a certificate hostname mismatch, a Cloudflare
    challenge, a captcha, an authentication wall, or an HTML document in
    place of robots.txt is an empty catalog. The caller does not bypass it.
    """

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or not resolved or host in CERTIFICATE_MISMATCH_HOSTS or certificate_mismatch:
        return True
    return bool(challenge or captcha or authentication_wall or html_robots)


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
    """True when the HTML is an authentication form rather than a public page.

    A header link that says Sign in is not a login wall.
    """

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
    not allow a fetch. An empty User-agent group allows every path. ``*`` in
    a rule matches any characters.
    """

    if not isinstance(body, str) or not isinstance(path, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or "<!doctype html" in sample or is_challenge_page(body[:8000]):
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
        if not value or not _robots_rule_matches(value, path):
            continue
        length = len(value)
        if length > best_len:
            best_len = length
            blocked = kind == "disallow"
        elif length == best_len and kind == "allow":
            blocked = False
    return blocked


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> bool:
    """A page is stored only from bounded HTML that is not a challenge or login wall."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if redirect_count > MAX_REDIRECTS:
        return False
    if elapsed_seconds is not None and elapsed_seconds > TIMEOUT_SECONDS:
        return False
    if len(page_html.encode("utf-8")) > MAX_RESPONSE_BYTES:
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


def confirmed_url(page_url: str, final_url: str) -> str | None:
    """Return the live URL when the response stayed on a catalogued host.

    A preferred host that redirects onto an in-scope www.microsoft.com research
    page is stored at that final URL. A redirect off the catalogued hosts, or
    a same-host redirect onto a different path, is not stored.
    """

    try:
        final = validate_canonical_url(final_url)
    except CatalogError:
        return None
    requested = urlparse(page_url)
    landed = urlparse(final)
    requested_host = (requested.hostname or "").lower().rstrip(".")
    final_host = (landed.hostname or "").lower().rstrip(".")
    if not is_official_host(requested_host) or not is_official_host(final_host):
        return None
    if requested_host == final_host:
        if (requested.path or "/") != (landed.path or "/"):
            return None
        try:
            return validate_canonical_url(page_url)
        except CatalogError:
            return None
    if requested_host in PREFERRED_HOSTS and final_host == LIVE_HOST:
        return final
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
    credit, image credit, or a Photo: credit does not count. Script, style,
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

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, and listing-card dates are not publication dates. Disagreeing
    publication dates stay unknown. Script, style, and comment text does not
    count.
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
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if title and title.casefold() not in _GENERIC_HEADINGS:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title and title.casefold() not in _GENERIC_HEADINGS:
            return title
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title and title.casefold() not in _GENERIC_HEADINGS:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Microsoft Research when the page states that name.

    A person named on the page is not the publisher. The hostname alone is
    not the publisher.
    """

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


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> dict | None:
    """Return metadata when one bounded response is on-host AI research HTML.

    A challenge, a captcha, an authentication wall, a non-HTML body, an error
    status, a robots disallow, a person profile, a product page, or a redirect
    off the catalogued hosts is not stored.
    """

    if not isinstance(page_url, str):
        return None
    landed = page_url if final_url is None else final_url
    target = confirmed_url(page_url, landed)
    if target is None:
        return None
    path = urlparse(target).path or "/"
    if robots_txt is not None and not robots_allows(robots_txt, path):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        redirect_count=redirect_count,
        elapsed_seconds=elapsed_seconds,
    ):
        return None
    if not isinstance(page_html, str):
        return None
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def build_catalog(entries: list[dict]) -> dict:
    """Validate and order metadata rows. This does not fetch."""

    ordered = sorted(entries, key=lambda entry: (_sort_date(entry["date"]), entry["canonical_url"]))
    document = {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": False,
        "entries": ordered,
    }
    return validate_catalog(document)


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
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Microsoft Research artificial-intelligence page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    normalized = f"https://{host}{path}"
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or host in CERTIFICATE_MISMATCH_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or url != normalized
        or not _in_scope_path(path)
    ):
        raise CatalogError(
            f"canonical URL is not a public Microsoft Research artificial-intelligence page: {url}"
        )
    return normalized


def _in_scope_path(path: str) -> bool:
    """True for one AI research-area, group, theme, collaboration, project, or story."""

    if not path.startswith("/en-us/research/") or path != path.lower() or not path.endswith("/"):
        return False
    if ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    if any(path == marker or path.startswith(marker + "/") for marker in _LOGIN_PATHS):
        return False
    parts = [part for part in path.split("/") if part]
    if len(parts) != 4 or parts[0] != "en-us" or parts[1] != "research":
        return False
    if any(part in _BLOCKED_PARTS for part in parts):
        return False
    section, slug = parts[2], parts[3]
    if section not in _SECTIONS or _SEGMENT.fullmatch(slug) is None:
        return False
    if slug.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _ai_topic(slug)


def _ai_topic(slug: str) -> bool:
    """True when the slug names an artificial-intelligence topic.

    Computer-vision syndrome is an eye condition, so that phrase is not an AI
    topic. A hyphen-separated ``ai`` token counts. Bare substrings such as
    the letters inside ``campaign`` do not.
    """

    checked = slug.replace("computer-vision-syndrome", " ")
    if any(phrase in checked for phrase in _AI_PHRASES):
        return True
    tokens = [token for token in checked.split("-") if token]
    return any(token in _AI_TOKENS for token in tokens)


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
            return RIGHTS_CC_BY
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
    found: list[str] = []
    for attrs in _TIME.findall(visible_html):
        parsed_attrs = _attrs(f"<time {attrs}>")
        if parsed_attrs.get("itemprop", "").casefold() != "datepublished":
            continue
        if "card__date" in parsed_attrs.get("class", "").casefold():
            continue
        parsed = _iso_day(parsed_attrs.get("datetime", ""))
        if parsed:
            found.append(parsed)
    return found


def _published_prose(plain: str) -> str:
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
    text = _clean_text(value).translate(_DASHES)
    lowered = text.casefold()
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip(" -|")
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
    """Drop photo, image, and caption credits, including a Photo: credit line."""

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if len(body) > 800:
            return match.group(0)
        if _CREDIT_CLASS.search(attrs) or _CREDIT_PHRASE.search(body) or _CREDIT_PHRASE.search(attrs):
            return " "
        return match.group(0)

    stripped = _CREDIT_BLOCK.sub(replace_block, page_html)

    def replace_anchor(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    stripped = _ANCHOR_ELEMENT.sub(replace_anchor, stripped)
    return _CREDIT_SENTENCE.sub(" ", stripped)


def _drop_foreign_licence_citations(page_html: str) -> str:
    """Drop a citation that names someone else's licence next to a paper host."""

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
    """True for the Creative Commons licences index, not a deed."""

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


def _robots_rule_matches(pattern: str, path: str) -> bool:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    pieces = []
    for char in body:
        if char == "*":
            pieces.append(".*")
        else:
            pieces.append(re.escape(char))
    expression = "".join(pieces)
    if anchored:
        expression += "$"
    return re.match(expression, path) is not None


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
