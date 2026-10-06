"""Metadata catalog of public AI Sweden research, program, news, and publication pages.

Hosts are www.ai.se and ai.se. ai.se redirects to www.ai.se. Each stored URL
was confirmed with one bounded GET that returned HTML on one of those hosts.
A row keeps the title, publisher, canonical URL, date, and rights label.
Page text, abstracts, PDFs, quotes, transcripts, and chart data are not
stored. A Cloudflare challenge, a captcha, an HTTP 202, an Akamai 403, an
access-denied or login wall, a robots disallow, a non-HTML response, or a
redirect off those hosts is not stored. An empty entries list is valid.

``creative_commons`` means CC0, CC BY-SA, or a permissive mix of those.
``creative_commons_attribution`` means CC BY alone. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps its own token. Two different restricted
deeds stay unknown. A software licence beside any Creative Commons deed stays
unknown. Two software licences stay unknown. A CC BY, CC BY-SA, or CC0 anchor
on a restricted deed URL or a public-domain mark URL stays unknown. The
Public Domain Mark is not CC0. A generic creativecommons.org/licenses or
/licenses/ URL is not a deed. Anchor text on it, including CC BY, CC BY 4.0,
and CC BY-SA, stays unknown. That includes a missing slash, http, a www host,
and a query string. A specific deed URL still counts. Text elsewhere on the
page still counts. A photo credit, caption credit, or image credit that names
someone else's licence stays unknown, including "Photo credit: UNDRR, CC
BY-NC-ND 2.0." ``uk_ogl`` requires the British phrase Open Government
Licence. ``us_government_work`` requires an explicit rights metadata field.
``mit``, ``apache-2.0``, and ``mpl-2.0`` stay their own tokens. Apache
License, Version 2.0 is apache-2.0. A hyphen is a word boundary, so CC BY
does not match CC BY-NC and licenses/by does not match licenses/by-nc.

Publication dates only. Updated, modified, and copyright years are not
publication dates. Script, style, and comment text does not count. The live
URL is stored as confirmed; a different rel=canonical does not replace it.
This module does not fetch and it is not a belief collector. ``runner_wired``
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

CATALOG_ID = "aisweden_pages"
CATALOG_FILENAME = "aisweden_pages.json"
RUNNER_WIRED = False
PUBLISHER = "AI Sweden"
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
OFFICIAL_HOSTS = frozenset({"www.ai.se", "ai.se"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
OGL_PHRASE = "open government licence"
CATALOG_DESCRIPTION = (
    "Metadata for public AI Sweden research, program, news, and publication pages on www.ai.se and ai.se. "
    "Each stored URL was confirmed with one bounded GET of HTML on those hosts. "
    "Login walls, access-denied listings, Cloudflare challenges, captchas, robots disallows, "
    "and off-host redirects are not stored. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page text is not stored. "
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
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_PAIR = re.compile(r"(?is)(<a\b[^>]*>)(.*?)(</a>)")
_IMG = re.compile(r"(?is)<img\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_ARTICLE_TIME = re.compile(
    r'(?is)<div\b[^>]*class="[^"]*\bcontent-simple__time\b[^"]*"[^>]*>\s*'
    r'<div\b[^>]*class="[^"]*\btext-field__content\b[^"]*"[^>]*>\s*'
    r"<div>(.*?)</div>"
)
_RESOURCE_DATE = re.compile(
    r'(?is)<div\b[^>]*class="[^"]*\bresource-full__meta\b[^"]*"[^>]*>\s*'
    r'<div\b[^>]*class="[^"]*\bfield-name-node-post-date\b[^"]*"[^>]*>\s*(.*?)\s*</div>'
)
_SITE_SUFFIXES = (
    " | ai sweden",
    " - ai sweden",
    " — ai sweden",
    " – ai sweden",
)
_GENERIC_TITLES = frozenset({"ai sweden"})
_PUBLISHER_WORD = re.compile(r"\bAI Sweden\b")
_ACCESS_WALL = re.compile(r"(?i)^(?:access denied|åtkomst nekad|log in|logga in)\b")
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
# User-agent: * disallows from https://www.ai.se/robots.txt. Research, program,
# news, and publication paths are not in this list.
_ROBOTS_DISALLOW = (
    "/core/",
    "/profiles/",
    "/admin/",
    "/comment/reply/",
    "/filter/tips",
    "/node/add/",
    "/search/",
    "/user/register/",
    "/user/password/",
    "/user/login/",
    "/user/logout/",
    "/index.php/admin/",
    "/index.php/comment/reply/",
    "/index.php/filter/tips",
    "/index.php/node/add/",
    "/index.php/search/",
    "/index.php/user/password/",
    "/index.php/user/register/",
    "/index.php/user/login/",
    "/index.php/user/logout/",
    "/readme.txt",
    "/web.config",
)
_CONTENT_PREFIXES = (
    "/en/news",
    "/sv/nyheter",
    "/en/resources",
    "/sv/resurser",
    "/en/project",
    "/sv/projekt",
    "/sv/project",
    "/en/research-innovation",
    "/sv/research-innovation",
    "/en/sector-initiatives",
    "/en/sector-initiatives-projects",
    "/en/sector-initiatives-and-applied-ai-projects",
    "/sv/sektorsinitiativ",
    "/sv/sektorsinitiativ-projekt",
    "/sv/sektorsinitiativ-och-tillampade-ai-projekt",
    "/en/public-policy",
    "/sv/public-policy",
    "/en/young-talent-program",
    "/sv/young-talent-program",
    "/en/ai-labs",
    "/sv/ai-labs",
    "/en/adoption",
    "/sv/tillampning",
    "/en/insights",
    "/sv/insights",
)
_EXTRA_PATHS = frozenset(
    {
        "/en/ai-sweden-leadership-report-2026",
        "/sv/ai-sweden-leadership-report-2026",
        "/en/svea-handbok",
        "/sv/svea-handbok",
        "/en/get-started-ai-online-course",
        "/sv/starta-din-ai-resa-onlinekurs",
        "/en/ai-adoption",
        "/sv/ai-adoption",
        "/sv/har-ar-de-14-scaleups-som-valts-ut-till-den-andra-omgangen-av-gsai-programmet",
    }
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
    "are you a robot",
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
# Longer deeds are listed first. A hyphen is a word boundary: (?!-) and
# (?![a-z0-9-]) stop CC BY and licenses/by from matching CC BY-NC. A version
# suffix such as -4.0 is consumed so CC BY-SA-4.0 still names CC BY-SA.
_VERSION = r"(?:[\s-]*\d+(?:\.\d+)?)?"
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd{_VERSION}(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa{_VERSION}(?![a-z0-9-])")),
    ("by-nc", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nc{_VERSION}(?![a-z0-9-])")),
    ("by-nd", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nd{_VERSION}(?![a-z0-9-])")),
    ("by-sa", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*sa{_VERSION}(?![a-z0-9-])")),
    ("by", re.compile(rf"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b){_VERSION}(?![a-z0-9-])")),
    (
        "by-nc-nd",
        re.compile(r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    ("by-nc", re.compile(r"creative commons\s+attribution[\s-]+non[\s-]*commercial")),
    ("by-nd", re.compile(r"creative commons\s+attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"creative commons\s+attribution[\s-]+share[\s-]*alike")),
    (
        "by",
        re.compile(
            r"creative commons\s+attribution(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|sa|nc|nd)\b)"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero(?![a-z])"
        ),
    ),
    ("mark", re.compile(r"\bpublic domain mark\b")),
)
_URL_CODES = {
    "by": "by",
    "by-sa": "by-sa",
    "by-nc": "by-nc",
    "by-nd": "by-nd",
    "by-nc-sa": "by-nc-sa",
    "by-nc-nd": "by-nc-nd",
    "zero": "zero",
    "mark": "mark",
}
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_US_GOV_WORK = re.compile(r"\b(?:united states|u\.s\.|us)\s+government\s+work\b")
_NEGATED_US_GOV = re.compile(r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+work\b")
_MIT = re.compile(r"\bmit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])")
_MPL = re.compile(r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|caption|image)\s+credits?\b")
_CREDIT_CLOSE = re.compile(r"(?is)^</(?:p|figcaption|li|caption|blockquote)\b")
_EN_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_SV_MONTHS = {
    "januari": 1,
    "februari": 2,
    "mars": 3,
    "april": 4,
    "maj": 5,
    "juni": 6,
    "juli": 7,
    "augusti": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}
_EN_DATE = re.compile(
    r"(?i)(?:(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*,\s*)?"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s*(\d{4})"
)
_SV_DATE = re.compile(
    r"(?i)(?:(?:måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag)\s*,\s*)?"
    r"(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)"
    r"\s+(\d{1,2}),?\s*(\d{4})"
)
_SV_DMY = re.compile(
    r"(?i)(\d{1,2})\s+"
    r"(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)"
    r"\s+(\d{4})"
)
_ISO_IN_TEXT = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


class CatalogError(ValueError):
    """A catalog row or page failed the AI Sweden page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for www.ai.se and ai.se."""

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
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:8000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(_without_hidden(page_html[:8000]))
    if match is None:
        return False
    title = _plain(match.group(1)).casefold()
    return title in {"just a moment...", "attention required! | cloudflare", "access denied"}


def is_access_wall(page_html: str) -> bool:
    """True when the page is a login or access-denied wall."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    match = _TITLE.search(_without_hidden(page_html[:12000]))
    if match is None:
        return False
    return _ACCESS_WALL.search(_plain(match.group(1))) is not None


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or access wall.

    HTTP 202, a non-200 status, a Cloudflare or captcha challenge, an Akamai
    403, and an access-denied title are not stored.
    """

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html) or is_access_wall(page_html):
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
    hops: tuple[str, ...] | list[str] | None = None,
) -> dict | None:
    """Return metadata when the response is a public AI Sweden content page.

    A challenge, an access wall, an HTTP 202, an Akamai 403, a non-HTML body,
    a robots disallow, or an off-host hop is not stored.
    """

    if hops and not _hops_stay_on_host(hops):
        return None
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

    Restricted deeds are checked before permissive ones. A hyphen continues a
    deed, so CC BY-NC is not CC BY and licenses/by does not match
    licenses/by-nc. Mixed restricted and permissive text stays unknown. A
    software licence beside any Creative Commons deed stays unknown. Two
    software licences stay unknown. Two different restricted deeds stay
    unknown. Public Domain Mark is not CC0. A generic
    creativecommons.org/licenses/ URL is not a deed. Anchor text on that URL
    does not count, including http, a www host, no trailing slash, and a
    query string. Text elsewhere on the page still counts. A specific deed
    URL still counts. A photo, caption, or image credit does not count.
    Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    ld_values = _jsonld_rights_and_licenses(page_text)
    visible = _prepare_visible(page_text)
    plain = _plain(visible).casefold().translate(_DASHES)
    hrefs = [href for href in _hrefs(visible) if not _is_generic_cc_licenses_url(href)]
    blobs = [plain, *(_meta_values(visible, _LICENSE_META)), *ld_values, *hrefs]
    codes: set[str] = set()
    pdm = False
    mit = False
    apache = False
    mpl = False
    for blob in blobs:
        folded = unescape(blob or "").casefold().translate(_DASHES)
        found, found_pdm = _cc_codes(folded)
        codes.update(found)
        pdm = pdm or found_pdm
        mit = mit or bool(_MIT.search(folded) or _MIT_URL.search(folded))
        apache = apache or bool(_APACHE.search(folded) or _APACHE_URL.search(folded))
        mpl = mpl or bool(_MPL.search(folded) or _MPL_URL.search(folded))
    software = {name for name, present in (("mit", mit), ("apache", apache), ("mpl", mpl)) if present}
    ogl = _OGL_PHRASE.search(plain) is not None
    us_gov = _states_us_government_work(page_text, visible)
    return _rights_label(codes, pdm, software, ogl, us_gov)


def publication_date_from_page(page_html: str, *, page_url: str | None = None) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    JSON-LD datePublished, article:published_time, and the page's own
    publication widget are publication dates. dateModified,
    article:modified_time, og:updated_time, a copyright year, dates of other
    posts, and dates in script, style, or comment text are not.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    widget = _widget_dates(visible)
    if widget is None:
        return UNKNOWN_DATE
    published = _jsonld_published(page_html)
    chosen: str | None = None
    if page_url:
        matched = {day for url, day in published if url and _same_page(url, page_url)}
        if len(matched) > 1:
            return UNKNOWN_DATE
        if len(matched) == 1:
            chosen = next(iter(matched))
    if chosen is None:
        unique = {day for _url, day in published}
        if len(unique) > 1:
            return UNKNOWN_DATE
        if len(unique) == 1:
            chosen = next(iter(unique))
    metas = _metas(visible)
    meta_days = {day for key in _PUBLICATION_META if (day := _iso_day(metas.get(key, "")))}
    if len(meta_days) > 1:
        return UNKNOWN_DATE
    meta_day = next(iter(meta_days)) if meta_days else None
    candidates = {day for day in (chosen, meta_day, widget) if day}
    if len(candidates) > 1:
        return UNKNOWN_DATE
    if len(candidates) == 1:
        return next(iter(candidates))
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    headings = []
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if title:
            headings.append(title)
    if len(headings) == 1 and headings[0].casefold() not in _GENERIC_TITLES:
        return headings[0]
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title and not (title.casefold() in _GENERIC_TITLES and headings):
            return title
    if headings:
        return headings[0]
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return AI Sweden when the page names that publisher.

    A person named on the page is not the publisher. The hostname alone is
    not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    if site:
        raise CatalogError("publisher must be AI Sweden")
    titled = " ".join(metas.get(key, "") for key in _TITLE_KEYS)
    title_tag = _TITLE.search(visible)
    title_text = title_tag.group(1) if title_tag else ""
    blob = " ".join((titled, title_text, _plain(visible)))
    if _PUBLISHER_WORD.search(blob):
        return PUBLISHER
    for name in _jsonld_values(page_html, "name"):
        if name.strip() == PUBLISHER:
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if is_access_wall(page_html):
        raise CatalogError("access wall is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html, page_url=page_url),
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
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog description")
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
        raise CatalogError("canonical URL must be a public AI Sweden page")
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
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public AI Sweden page: {url}")
    return url


def content_path(path: str) -> bool:
    """True for a research, program, news, or publication path on AI Sweden."""

    if path in _EXTRA_PATHS:
        return True
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _CONTENT_PREFIXES)


def _public_path(path: str) -> bool:
    if not content_path(path):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _robots_allows(lowered)


def _robots_allows(path: str) -> bool:
    """User-agent: * disallows from https://www.ai.se/robots.txt."""

    return not any(path == prefix or path.startswith(prefix) for prefix in _ROBOTS_DISALLOW)


def _hops_stay_on_host(hops: tuple[str, ...] | list[str]) -> bool:
    for hop in hops:
        if not isinstance(hop, str):
            return False
        host = (urlparse(hop).hostname or "").lower().rstrip(".")
        if not is_official_host(host):
            return False
    return True


def _rights_label(codes: set[str], pdm: bool, software: set[str], ogl: bool, us_gov: bool) -> str:
    if pdm and (codes or software or ogl or us_gov):
        return RIGHTS_UNKNOWN
    if pdm:
        return RIGHTS_UNKNOWN
    permissive = codes & _PERMISSIVE
    restricted = codes & _RESTRICTED
    other = bool(software or ogl or us_gov)
    if restricted and (permissive or other):
        return RIGHTS_UNKNOWN
    if permissive and other:
        return RIGHTS_UNKNOWN
    if len(software) > 1 or (software and (ogl or us_gov)) or (ogl and us_gov):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if restricted:
        if restricted == {"by-nc"}:
            return RIGHTS_CC_BY_NC
        if restricted == {"by-nd"}:
            return RIGHTS_CC_BY_ND
        if restricted == {"by-nc-nd"}:
            return RIGHTS_CC_BY_NC_ND
        if restricted == {"by-nc-sa"}:
            return RIGHTS_CC_BY_NC_SA
        return RIGHTS_UNKNOWN
    if permissive:
        if permissive <= {"by"}:
            return RIGHTS_CC_ATTRIBUTION
        if permissive & {"by-sa", "zero"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_UNKNOWN
    if len(software) == 1 and not ogl and not us_gov:
        only = next(iter(software))
        if only == "mit":
            return RIGHTS_MIT
        if only == "apache":
            return RIGHTS_APACHE
        if only == "mpl":
            return RIGHTS_MPL
    if ogl:
        return RIGHTS_UK_OGL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def _cc_codes(folded: str) -> tuple[set[str], bool]:
    codes: set[str] = set()
    pdm = False
    for match in _CC_URL.finditer(folded):
        code = match.group("code") or match.group("pd")
        mapped = _URL_CODES.get(code or "", code or "")
        if mapped == "mark":
            pdm = True
        elif mapped:
            codes.add(mapped)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            if code == "mark":
                pdm = True
            else:
                codes.add(code)
    return codes, pdm


def _prepare_visible(page_html: str) -> str:
    visible = _without_hidden(page_html)
    visible = _drop_image_credits(visible)
    visible = _drop_caption_elements(visible)
    visible = _drop_image_attribution_paragraphs(visible)
    visible = _strip_image_text(visible)
    return _drop_generic_cc_anchor_text(visible)


def _drop_image_credits(html: str) -> str:
    """Remove photo, caption, and image credits so their licences do not apply."""

    pieces: list[str] = []
    cursor = 0
    for match in _CREDIT_PHRASE.finditer(html):
        if match.start() < cursor or _inside_tag(html, match.start()):
            continue
        end = _credit_end(html, match.end())
        pieces.append(html[cursor:match.start()])
        pieces.append(" ")
        cursor = end
    pieces.append(html[cursor:])
    return "".join(pieces)


def _inside_tag(html: str, index: int) -> bool:
    last_lt = html.rfind("<", 0, index)
    last_gt = html.rfind(">", 0, index)
    return last_lt > last_gt


def _credit_end(html: str, start: int) -> int:
    """End a credit at the sentence period or the closing block tag."""

    index = start
    while index < len(html):
        if html[index] == "<":
            if _CREDIT_CLOSE.match(html[index:]):
                return index
            end = html.find(">", index)
            if end == -1:
                return len(html)
            index = end + 1
            continue
        if html[index] == ".":
            prev = html[index - 1] if index else ""
            nxt = html[index + 1] if index + 1 < len(html) else ""
            if prev.isdigit() and nxt.isdigit():
                index += 1
                continue
            if nxt == "" or nxt.isspace() or nxt == "<":
                return index + 1
        index += 1
    return len(html)


def _drop_caption_elements(html: str) -> str:
    """Drop caption elements. A caption credit is not a licence for the page."""

    pattern = re.compile(r"(?is)<(div|p|span|figcaption|figure|li)\b[^>]*>")
    pieces: list[str] = []
    cursor = 0
    for match in pattern.finditer(html):
        if match.start() < cursor:
            continue
        if not _class_has_caption(match.group(0)) and match.group(1).casefold() != "figcaption":
            continue
        end = _element_end(html, match.end(), match.group(1))
        pieces.append(html[cursor:match.start()])
        pieces.append(" ")
        cursor = end
    pieces.append(html[cursor:])
    return "".join(pieces)


def _class_has_caption(tag: str) -> bool:
    classes = re.split(r"[^a-z0-9]+", _attrs(tag).get("class", "").casefold())
    return "caption" in classes


def _element_end(html: str, start: int, tag: str) -> int:
    token = re.compile(rf"(?is)</?{re.escape(tag)}\b[^>]*>")
    depth = 1
    for match in token.finditer(html, start):
        if match.group(0).startswith("</") or match.group(0)[:2].casefold() == "</":
            depth -= 1
            if depth == 0:
                return match.end()
        else:
            depth += 1
    return len(html)


def _drop_image_attribution_paragraphs(html: str) -> str:
    """Drop a short paragraph that only credits someone else's image licence."""

    def replace(match: re.Match[str]) -> str:
        block = match.group(0)
        folded = unescape(block).casefold().translate(_DASHES)
        if len(_plain(block)) > 400:
            return block
        imageish = any(
            token in folded
            for token in (
                "photo credit",
                "caption credit",
                "image credit",
                "photo:",
                "foto:",
                "image:",
                "wikimedia.org",
            )
        )
        licensed = _CC_URL.search(folded) is not None or re.search(r"cc[\s-]*by", folded) is not None
        if imageish and licensed:
            return " "
        return block

    return re.sub(r"(?is)<p\b[^>]*>.*?</p>", replace, html)


def _strip_image_text(html: str) -> str:
    """Drop img alt and title text. A photo credit there is not a page licence."""

    def replace(match: re.Match[str]) -> str:
        return re.sub(
            r"""(?is)\s(?:alt|title)\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""",
            "",
            match.group(0),
        )

    return _IMG.sub(replace, html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for creativecommons.org/licenses with no deed in the path.

    http, a www host, a missing trailing slash, and a query string are still
    the generic licence index. licenses/by/4.0/ and the other deed paths are
    not generic.
    """

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(href.strip())
    scheme = (parsed.scheme or "").casefold()
    host = (parsed.hostname or "").casefold().rstrip(".")
    path = (parsed.path or "").casefold()
    if scheme not in {"http", "https"}:
        return False
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    return path in {"/licenses", "/licenses/"}


def _drop_generic_cc_anchor_text(visible_html: str) -> str:
    """Remove visible text of anchors that point at the generic licence index."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(match.group(1)).get("href", "")
        if _is_generic_cc_licenses_url(href):
            return match.group(1) + match.group(3)
        return match.group(0)

    return _ANCHOR_PAIR.sub(replace, visible_html)


def _states_us_government_work(page_html: str, visible: str) -> bool:
    """True only when a rights field says the item is a US government work."""

    fields = list(_meta_values(visible, _RIGHTS_META))
    for value in _jsonld_values(page_html, "rights"):
        fields.append(value)
    for raw in fields:
        text = _plain(raw).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _jsonld_rights_and_licenses(page_html: str) -> list[str]:
    found: list[str] = []
    for key in ("license", "rights"):
        found.extend(_jsonld_values(page_html, key))
    return found


def _jsonld_published(page_html: str) -> list[tuple[str | None, str]]:
    found: list[tuple[str | None, str]] = []
    for block in _LDJSON.findall(_COMMENT.sub(" ", page_html)):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _collect_published(payload, None, found)
    return found


def _collect_published(payload: object, current_url: str | None, found: list[tuple[str | None, str]]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_published(item, current_url, found)
        return
    if not isinstance(payload, dict):
        return
    url = current_url
    for name, value in payload.items():
        if str(name).casefold() == "url" and isinstance(value, str):
            url = value.strip()
    for name, value in payload.items():
        if str(name).casefold() == "datepublished" and isinstance(value, str):
            day = _iso_day(value)
            if day:
                found.append((url, day))
    for name, value in payload.items():
        if str(name).casefold() == "datemodified":
            continue
        if isinstance(value, (dict, list)):
            _collect_published(value, url, found)


def _jsonld_values(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(_COMMENT.sub(" ", page_html)):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _collect_key(payload, key.casefold(), found)
    return found


def _collect_key(payload: object, key: str, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_key(item, key, found)
        return
    if not isinstance(payload, dict):
        return
    for name, value in payload.items():
        if str(name).casefold() == key and isinstance(value, str):
            found.append(value)
        elif isinstance(value, (dict, list)):
            _collect_key(value, key, found)


def _widget_dates(visible_html: str) -> str | None:
    """Return the page's own publication widget date.

    None means the widgets disagree. An empty result is "" so the caller can
    fall through to metadata.
    """

    found: list[str] = []
    for raw in _ARTICLE_TIME.findall(visible_html) + _RESOURCE_DATE.findall(visible_html):
        parsed = _parse_display_date(_plain(raw))
        if parsed:
            found.append(parsed)
    unique = set(found)
    if len(unique) > 1:
        return None
    if len(unique) == 1:
        return next(iter(unique))
    return ""


def _parse_display_date(text: str) -> str | None:
    if not text:
        return None
    iso_days = {_iso_day(match) for match in _ISO_IN_TEXT.findall(text)}
    iso_days.discard(None)
    if len(iso_days) == 1 and not _EN_DATE.search(text) and not _SV_DATE.search(text):
        return next(iter(iso_days))
    if len(iso_days) > 1:
        return None
    parsed: set[str] = set()
    for match in _EN_DATE.finditer(text):
        day = _ymd(int(match.group(3)), _EN_MONTHS[match.group(1).casefold()], int(match.group(2)))
        if day:
            parsed.add(day)
    for match in _SV_DATE.finditer(text):
        day = _ymd(int(match.group(3)), _SV_MONTHS[match.group(1).casefold()], int(match.group(2)))
        if day:
            parsed.add(day)
    if not parsed:
        for match in _SV_DMY.finditer(text):
            day = _ymd(int(match.group(3)), _SV_MONTHS[match.group(2).casefold()], int(match.group(1)))
            if day:
                parsed.add(day)
    if iso_days:
        parsed.update(day for day in iso_days if day)
    if len(parsed) == 1:
        return next(iter(parsed))
    return None


def _same_page(left: str, right: str) -> bool:
    def norm(value: str) -> str:
        text = value.strip()
        if len(text) > 1 and text.endswith("/"):
            text = text[:-1]
        return text.casefold()

    return norm(left) == norm(right)


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    return _ymd_text(match.group(1))


def _ymd_text(value: str) -> str | None:
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _ymd(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


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
    changed = True
    while changed and text:
        changed = False
        lowered = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, keys: frozenset[str] | tuple[str, ...]) -> list[str]:
    wanted = {key.lower() for key in keys}
    found: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in wanted and attrs.get("content"):
            found.append(attrs["content"])
    return found


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


def _challenge_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name == "sg-captcha":
            return True
        if name == "server" and "akamai" in token:
            return True
    return False
