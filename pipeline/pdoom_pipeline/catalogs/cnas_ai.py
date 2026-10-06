"""Metadata catalog of public Center for a New American Security pages on AI.

Hosts are www.cnas.org and cnas.org. cnas.org redirects to www.cnas.org.
robots.txt allows the public site and disallows /admin/ and /cache/. Each
stored URL was confirmed with one bounded GET that stayed on one of those
hosts. A row keeps the title, publisher, canonical URL, date, and rights
label. Page bodies, abstracts, PDFs, quotes, transcripts, and chart data are
not stored. The live URL is stored as confirmed; a different rel=canonical
does not replace it.

Pages are limited to artificial intelligence, machine learning, or AI policy:
the Artificial Intelligence research areas, the AI initiative pages, and the
publications, events, and on-host press pages listed there. Other center
topics, login walls, and donation pages are not stored. A sitemap or listing
blocked by a Cloudflare challenge, a captcha, authentication, or robots.txt
contributes no rows. This module does not bypass those controls.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means CC0, CC BY-SA, or a permissive mix of those,
including CC BY together with CC0 or CC BY-SA.
``creative_commons_attribution`` means CC BY alone. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps that token. A hyphen is a word boundary, so
CC BY does not match CC BY-NC and licenses/by does not match licenses/by-nc.
Two different restricted deeds stay unknown. A permissive anchor on a
restricted deed URL or on a public-domain mark URL stays unknown, and a CC0
anchor on a publicdomain/mark URL stays unknown. The Public Domain Mark is
not CC0. A generic creativecommons.org/licenses or /licenses/ URL is not a
deed. Anchor text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays
unknown, including a missing slash, http, a www host, and a query string. A
specific deed URL still counts. Text elsewhere on the page still counts. A
software licence beside any Creative Commons deed stays unknown. Two software
licences stay unknown. mit, apache-2.0, and mpl-2.0 are sole software
licences. Apache License, Version 2.0 is apache-2.0. ``uk_ogl`` is only the
British phrase Open Government Licence. ``us_government_work`` comes only
from an explicit rights metadata field. A photo credit, caption credit, or
image credit that names someone else's licence stays unknown, including
"Photo credit: UNDRR, CC BY-NC-ND 2.0."

A page that does not state a publication date keeps the date unknown.
Updated, modified, and copyright years are not publication dates. Script,
style, and comment text does not count. This module does not fetch. It is
not a belief collector, and runner_wired stays false.
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

CATALOG_ID = "cnas_ai_pages"
CATALOG_FILENAME = "cnas_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Center for a New American Security"
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
OFFICIAL_HOSTS = frozenset({"www.cnas.org", "cnas.org"})
MAX_TEXT_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
# Confirmed from https://www.cnas.org/robots.txt. These paths contribute no rows.
CONFIRMED_ROBOTS_TXT = (
    "Sitemap: https://www.cnas.org/sitemap.xml\n"
    "\n"
    "# Don't allow web crawlers to index Craft CMS\n"
    "User-agent: *\n"
    "Disallow: /admin/\n"
    "Disallow: /cache/\n"
)
# robots.txt disallows these paths, so each contributes an empty catalog.
# No sitemap or AI listing returned a challenge, a captcha, or an authentication wall.
SKIPPED_LISTING_PATHS: tuple[str, ...] = ("/admin/", "/cache/")
CATALOG_DESCRIPTION = (
    "Metadata for public Center for a New American Security pages on artificial intelligence, "
    "machine learning, or AI policy. Hosts are www.cnas.org and cnas.org. "
    "Each row was stored after one bounded GET that stayed on those hosts. "
    "robots.txt disallows /admin/ and /cache/. "
    "A Cloudflare challenge, a captcha, a login wall, a donation page, or an off-host redirect is not stored. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page bodies are not stored. "
    "Rights stay unknown unless the page states a reuse licence. "
    "creative_commons means CC0, CC BY-SA, or a permissive mix of those. "
    "creative_commons_attribution means CC BY alone. "
    "A missing date is unknown. Updated, modified, and copyright years are not publication dates. "
    "This catalog is not a belief collector and runner_wired is false."
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
_PUBLICATION_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset(
    {"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights", "rights"}
)
_TITLE_KEYS = ("og:title", "citation_title", "twitter:title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_ELEMENT = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_ATTRIBUTION_OPEN = re.compile(r"(?is)<div\b[^>]*\battribution-block\b[^>]*>")
_SITE_SUFFIXES = (
    " | center for a new american security",
    " - center for a new american security",
    " – center for a new american security",
    " — center for a new american security",
    " | cnas",
    " - cnas",
    " – cnas",
    " — cnas",
)
_PUBLISHER_WORD = re.compile(r"Center for a New American Security")
_CONTENT_PATH = re.compile(r"^/(?:publications|events|press)/[a-z0-9-]+(?:/[a-z0-9-]+)*$")
_TOP_AI_PATH = re.compile(
    r"^/(?:ai(?:-[a-z0-9]+)*|cnas-ai(?:-[a-z0-9]+)+|"
    r"artificial-intelligence(?:-[a-z0-9]+)*|machine-learning(?:-[a-z0-9]+)*)/?$"
)
_PAGINATION_SEGMENT = re.compile(r"^p\d+$")
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
_ROBOTS_DISALLOW_PREFIXES = ("/admin/", "/cache/")
_LOGIN_MARKERS = (
    "/login",
    "/log-in",
    "/signin",
    "/sign-in",
    "/account",
    "/wp-login",
    "/users/sign_in",
    "/admin",
)
_DONATION_MARKERS = (
    "/support-cnas",
    "/donate",
    "/donation",
    "/give",
    "/join",
    "/contribute",
)
_CHALLENGE_MARKERS = (
    "performing security verification",
    "challenge-platform",
    "cf-mitigated",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
)
_CHALLENGE_TITLES = (
    "just a moment",
    "attention required",
    "checking your browser",
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
_US_GOV_WORK = re.compile(r"\b(?:united states|u\.s\.|us)\s+government\s+work\b")
_NEGATED_US_GOV = re.compile(r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+work\b")
_MIT = re.compile(r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|image|caption)\s+credits?\b")
_CREDIT_SENTENCE = re.compile(
    r"(?is)\b(?:photo|image|caption)\s+credits?\b(?:[^<]{0,300}?)\."
)
_CREDIT_OPEN = re.compile(r"(?is)<(p|li|figcaption|button|span|div|figure|small|cite)\b[^>]*>")
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
_VISIBLE_DATE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
    r")\.?\s+(\d{1,2}),?\s+(\d{4})\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the CNAS AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for www.cnas.org and cnas.org only."""

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
    """True when the response is an interstitial challenge rather than the page.

    A phrase such as "just a moment" inside the article body is not a challenge.
    """

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    title = _TITLE.search(page_html[:12000])
    if title and any(marker in title.group(1).casefold() for marker in _CHALLENGE_TITLES):
        return True
    head = page_html[:6000].casefold()
    return any(marker in head for marker in _CHALLENGE_MARKERS)


def robots_disallows(robots_txt: str, path: str) -> bool:
    """True when User-agent: * disallows ``path``.

    The longest matching Allow or Disallow wins. An empty Disallow does not
    block the site. A sitemap line is not a disallow.
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
) -> bool:
    """True when a sitemap or listing must contribute an empty catalog.

    A Cloudflare challenge, a captcha, an authentication status, or a
    robots.txt disallow blocks that path. The caller moves on without
    bypassing the control.
    """

    if not isinstance(path, str) or not path.startswith("/"):
        return True
    if _robots_path_blocked(path):
        return True
    if robots_txt is not None and robots_disallows(robots_txt, path):
        return True
    if status in {401, 403, 202, 429}:
        return True
    if isinstance(page_html, str) and is_challenge_page(page_html):
        return True
    if status == 200 and page_html is not None and not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
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
) -> list[dict]:
    """Return no rows when a listing path is blocked.

    A readable listing is not itself a stored row. Child pages are recorded
    individually after their own GET.
    """

    if listing_is_blocked(
        path,
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        robots_txt=robots_txt,
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
    """A page is stored only from HTML that is not a challenge response.

    HTTP 202, a non-200 status, a Cloudflare or SiteGround challenge, and an
    Akamai block are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
            if name == "server" and "akamai" in token and status == 403:
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
) -> dict | None:
    """Return metadata when the response is AI-topic HTML on a CNAS host.

    A challenge, an HTTP 202, an Akamai block, a non-HTML body, a login page,
    a donation page, or an off-host URL is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY and licenses/by does not match
    licenses/by-nc. Mixed restricted and permissive text stays unknown. A
    software licence beside any Creative Commons deed stays unknown. Two
    software licences stay unknown. Two different restricted deeds stay
    unknown. A permissive anchor on a restricted or Public Domain Mark URL
    stays unknown. A CC0 anchor on a publicdomain/mark URL stays unknown.
    Public Domain Mark is not CC0. A generic creativecommons.org/licenses URL
    is not a deed, and the visible text of that anchor does not count. Text
    elsewhere on the page still counts. A specific deed URL still counts. A
    photo, image, or caption credit does not count. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _drop_citation_paragraphs(_without_credit(_without_hidden(page_text)))
    plain = _drop_quoted_licence_mentions(
        _plain(_without_generic_cc_license_anchors(visible))
    ).casefold().translate(_DASHES)
    codes = _text_codes(plain)
    hrefs = _hrefs(visible)
    for href in hrefs:
        if _is_generic_cc_licenses_url(href):
            continue
        codes |= _url_codes(href.casefold().translate(_DASHES))
    licence_bits: list[str] = []
    us_gov = _states_us_government_work(visible)
    for key, content in _meta_pairs(visible):
        if key not in _LICENSE_META:
            continue
        chunk = _plain(content).casefold().translate(_DASHES)
        licence_bits.append(chunk)
        codes |= _text_codes(chunk)
        codes |= _url_codes(chunk)
    scanned = " ".join([plain, *licence_bits, *(href.casefold() for href in hrefs)])
    mit = bool(_MIT.search(scanned) or any(_MIT_URL.search(href.casefold()) for href in hrefs))
    apache = bool(_APACHE.search(scanned) or any(_APACHE_URL.search(href.casefold()) for href in hrefs))
    mpl = bool(_MPL.search(scanned) or any(_MPL_URL.search(href.casefold()) for href in hrefs))
    return _label(
        codes,
        mit=mit,
        apache=apache,
        mpl=mpl,
        ogl=bool(_OGL_PHRASE.search(plain)),
        us_gov=us_gov,
    )


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    The article attribution date and publication meta tags count.
    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, an event schedule, and a date on a related card do not. A date
    inside script, style, or comment text does not count. Disagreeing
    publication dates stay unknown.
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
    found.extend(_attribution_dates(visible))
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
    """Return the Center's name when the page states it.

    A person named on the page is not the publisher. The hostname alone is
    not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    if _PUBLISHER_WORD.search(_plain(visible)):
        return PUBLISHER
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "publisher"):
        if _PUBLISHER_WORD.search(metas.get(key, "")):
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

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
    description = document.get("description")
    if not isinstance(description, str) or not description.strip() or description != description.strip():
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
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public CNAS AI page")
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
        or not _public_ai_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public CNAS AI page: {url}")
    return url


def _public_ai_path(path: str) -> bool:
    if not path.startswith("/") or ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    lowered = path.casefold()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if _robots_path_blocked(lowered):
        return False
    if any(marker in lowered for marker in _LOGIN_MARKERS):
        return False
    if any(lowered == marker or lowered.startswith(marker + "/") for marker in _DONATION_MARKERS):
        return False
    if lowered.startswith("/cdn-cgi") or lowered.startswith("/people") or lowered.startswith("/careers"):
        return False
    if _TOP_AI_PATH.fullmatch(lowered):
        return True
    if _ai_research_path(lowered):
        return True
    if _CONTENT_PATH.fullmatch(lowered) is None:
        return False
    segments = [segment for segment in lowered.split("/") if segment]
    if any(_PAGINATION_SEGMENT.fullmatch(segment) for segment in segments):
        return False
    if segments[0] == "events" and len(segments) == 1:
        return False
    if segments[0] == "press" and len(segments) < 2:
        return False
    return True


def _ai_research_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2 or parts[0] != "research":
        return False
    return any(
        part == "artificial-intelligence"
        or part.startswith("artificial-intelligence-")
        or part == "machine-learning"
        or part.startswith("machine-learning-")
        for part in parts
    )


def _robots_path_blocked(path: str) -> bool:
    for prefix in _ROBOTS_DISALLOW_PREFIXES:
        bare = prefix.rstrip("/")
        if path == bare or path.startswith(prefix) or path.startswith(bare + "/"):
            return True
    return False


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

    fields = [content for key, content in _meta_pairs(visible_html) if key in _RIGHTS_META]
    for raw in fields:
        text = _plain(raw).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _attribution_dates(visible_html: str) -> list[str]:
    match = _ATTRIBUTION_OPEN.search(visible_html)
    if match is None:
        return []
    chunk = visible_html[match.end() : match.end() + 1500]
    cut = re.search(r"(?is)<h1\b", chunk)
    if cut:
        chunk = chunk[: cut.start()]
    paragraph = re.search(r"(?is)<p\b[^>]*>\s*([^<]{0,80})\s*</p>", chunk)
    if paragraph is None:
        return []
    plain = _clean_text(paragraph.group(1))
    folded = plain.casefold()
    if not plain or _CREDIT_PHRASE.search(plain):
        return []
    if any(word in folded for word in ("updat", "modif", "copyright", "©")):
        return []
    return _visible_dates(plain)


def _visible_dates(plain: str) -> list[str]:
    found: list[str] = []
    for match in _VISIBLE_DATE.finditer(plain):
        parsed = _calendar_date(match.group(1), match.group(2), match.group(3))
        if parsed:
            found.append(parsed)
    return found


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold().rstrip("."))
    if month is None:
        return None
    try:
        value = date(int(year_text), month, int(day_text)).isoformat()
    except ValueError:
        return None
    return value


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


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    lowered = text.casefold()
    for suffix in _SITE_SUFFIXES:
        if lowered.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _without_credit(page_html: str) -> str:
    """Drop photo, image, and caption credits, including a licence they name."""

    html = _drop_credit_elements(page_html)
    return _CREDIT_SENTENCE.sub(" ", html)


def _drop_citation_paragraphs(page_html: str) -> str:
    """Drop a paragraph that cites another work's licence next to arXiv or a DOI.

    The paragraph is someone else's reuse terms. A licence stated elsewhere
    on the page is left in place.
    """

    def replace(match: re.Match[str]) -> str:
        folded = match.group(0).casefold()
        cites_elsewhere = "arxiv.org" in folded or "doi.org" in folded
        names_licence = (
            "creativecommons.org" in folded
            or "creative commons" in folded
            or "mit license" in folded
            or "mit licence" in folded
        )
        if cites_elsewhere and names_licence:
            return " "
        return match.group(0)

    return re.sub(r"(?is)<p\b[^>]*>.*?</p>", replace, page_html)


def _drop_quoted_licence_mentions(plain: str) -> str:
    """Drop a quoted title that names someone else's licence."""

    def replace(match: re.Match[str]) -> str:
        inner = match.group(0).casefold()
        if re.search(r"licen[cs]e|creative commons|cc[\s-]*by|mit licen", inner):
            return " "
        return match.group(0)

    quoted = re.compile("“[^”]{0,400}”|„[^“]{0,400}“|" + '"[^"\\n]{0,400}"')
    return quoted.sub(replace, plain)


def _drop_credit_elements(page_html: str) -> str:
    html = page_html
    changed = True
    while changed:
        changed = False
        for match in _CREDIT_OPEN.finditer(html):
            end = _matching_end(html, match)
            if end is None:
                continue
            inner = html[match.end() : end[0]]
            if re.search(rf"(?is)<{match.group(1)}\b", inner):
                continue
            text = _clean_text(inner)
            if _CREDIT_PHRASE.search(text) and len(text) <= 400:
                html = html[: match.start()] + " " + html[end[1] :]
                changed = True
                break
    return html


def _matching_end(html: str, open_match: re.Match[str]) -> tuple[int, int] | None:
    tag = open_match.group(1)
    token = re.compile(rf"(?is)</?{tag}\b[^>]*>")
    depth = 1
    for match in token.finditer(html, open_match.end()):
        piece = match.group(0)
        if piece[1] == "/":
            depth -= 1
            if depth == 0:
                return (match.start(), match.end())
        else:
            depth += 1
    return None


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
    """Drop anchors whose href is only the generic licences index.

    The visible text of that anchor is not a licence statement. Other text
    on the page is left in place.
    """

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
