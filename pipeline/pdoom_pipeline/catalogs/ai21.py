"""Metadata catalog of public AI21 Labs research and news pages.

The official host is ai21.com. www.ai21.com is included only when the response
stays on that host. https://ai21.com/research/ redirects to www.ai21.com, so
the stored pages are the www URLs that stayed there. robots.txt on both hosts
allows these paths (``Disallow`` is empty). Each stored URL was confirmed with
one bounded GET of HTML.

Product console, playground, API docs, login, PDFs, and other hosts are not
stored. A Cloudflare challenge, a captcha, an HTTP error, a non-HTML body, a
robots disallow, or an off-host redirect is not stored. An empty entries list
is valid. The live URL is stored as confirmed; a different rel=canonical does
not replace it.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
text, abstracts, quotes, transcripts, chart data, and PDFs are not stored.
Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` means CC BY alone. ``creative_commons`` means
CC0, CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``,
or ``cc_by_nc_nd``. Mixed restricted and permissive text stays unknown. A CC
BY or CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or
publicdomain/mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL
stays unknown. A generic https://creativecommons.org/licenses/ URL stays
unknown even when the anchor text says CC BY, CC BY 4.0, or CC BY-SA. That
anchor text is not a licence statement. A specific deed URL such as
``/licenses/by/4.0/`` still counts. A software licence beside any Creative
Commons deed stays unknown. Two different software licences stay unknown. Two
different restricted deeds stay unknown. Apache License, Version 2.0,
including the comma, is ``apache-2.0``. ``uk_ogl`` requires the exact British
phrase Open Government Licence. ``us_government_work`` comes only from an
explicit rights metadata field. Public Domain Mark, all rights reserved,
terms, and the host name stay unknown. A hyphen is a word boundary, so CC BY
does not match CC BY-NC. Script, style, and comment text does not count.

A publication date is stored only. Updated, modified, and copyright years stay
unknown. This module does not fetch. It is not a belief collector, and
``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ai21_pages"
CATALOG_FILENAME = "ai21_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
PUBLISHER = "AI21 Labs"
OFFICIAL_HOSTS = frozenset({"ai21.com", "www.ai21.com"})

RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
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
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
}

MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public AI21 Labs research and news pages on www.ai21.com. "
    "ai21.com redirects there. Each stored URL was confirmed with one bounded GET that stayed on www.ai21.com. "
    "robots.txt allows these paths. Console, playground, API docs, login, PDFs, and other hosts are omitted. "
    "A challenge, HTTP error, non-HTML body, robots disallow, or off-host redirect is not stored. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "creative_commons_attribution means CC BY alone. creative_commons means CC0, CC BY-SA, or a permissive mix of those. "
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
        "dataset",
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
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dcterms.licence"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "citation_date",
    "dcterms.issued",
    "dc.date.issued",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "cf-browser-verification",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
    "hcaptcha",
    "g-recaptcha",
    "are you a robot",
)
_OMITTED_PARTS = frozenset(
    {
        "account",
        "api",
        "auth",
        "cdn-cgi",
        "console",
        "docs",
        "log-in",
        "login",
        "playground",
        "sign-in",
        "signin",
        "studio",
        "wp-admin",
        "wp-content",
        "wp-includes",
        "wp-json",
        "wp-login.php",
        "xmlrpc.php",
    }
)
_BLOG_SKIP = frozenset({"author", "category", "feed", "page", "tag"})
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".css",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".js",
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PAGE_NUMBER = re.compile(r"^[1-9][0-9]*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"', re.I)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_IMG = re.compile(r"(?is)<img\b[^>]*>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s*AI21(?:\s+Labs)?\s*$")
_NOT_PUBLICATION = re.compile(r"(?i)\b(?:updated|modified|copyright)\b|©|last\s+update")
_PUBLISHER_PHRASE = re.compile(r"AI21\s+Labs")
_OGL_PHRASE = re.compile(r"(?i)open\s+government\s+licence(?![a-z])")
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_MIT = re.compile(
    r"(?i)(?:\bmit\s+licen[cs]e\b|\bmit-licen[cs]ed\b|\blicen[cs]ed under (?:the\s+)?mit(?:\s+licen[cs]e)?\b)"
)
_APACHE = re.compile(
    r"(?i)(?<![a-z0-9])(?:"
    r"apache-2\.0(?![a-z0-9])"
    r"|apache\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0(?!\d)"
    r"|apache\s+2\.0(?!\d)"
    r"|licen[cs]ed under (?:the\s+)?apache(?:\s+licen[cs]e)?\b"
    r")"
)
_MPL = re.compile(
    r"(?i)(?:\bmpl-2\.0\b|\bmozilla\s+public\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b)"
)
_MIT_URL = re.compile(r"(?i)(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_URL = re.compile(
    r"(?i)(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_URL = re.compile(r"(?i)(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
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
# A hyphen is a word boundary. (?!-) keeps CC BY from matching CC BY-NC, and
# licenses/by from matching licenses/by-nc.
_CC_RESTRICTED_URL = re.compile(
    r"(?i)creativecommons\.org/licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd)(?!-)"
)
_CC_PERMISSIVE_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<by>by(?!-))(?![a-z0-9])"
    r"|licenses/(?P<sa>by-sa)(?![a-z0-9-])"
    r"|publicdomain/(?P<zero>zero)(?![a-z0-9-]))"
)
_CC_MARK_URL = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
_CC_CONTINUATION = r"(?:nc|nd|sa|non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike)(?![a-z0-9])"
_CC_RESTRICTED_TEXT = (
    (
        "by-nc-nd",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc[-\s]nd(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]non[-\s]?commercial[-\s]no[-\s]?deriv"
            r"|creative commons attribution[-\s]+non[-\s]?commercial[-\s]+no[-\s]?deriv"
            r")"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc[-\s]sa(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]non[-\s]?commercial[-\s]share[-\s]?alike"
            r"|creative commons attribution[-\s]+non[-\s]?commercial[-\s]+share[-\s]?alike"
            r")"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]non[-\s]?commercial(?![-\s]*(?:share[-\s]?alike|no[-\s]?deriv))"
            r"|creative commons attribution[-\s]+non[-\s]?commercial(?![-\s]*(?:share[-\s]?alike|no[-\s]?deriv))"
            r")"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nd(?![a-z0-9-])"
            r"|cc[-\s]?by[-\s]no[-\s]?deriv"
            r"|creative commons attribution[-\s]+no[-\s]?deriv"
            r")"
        ),
    ),
)
_CC_PERMISSIVE_TEXT = (
    (
        "by-sa",
        re.compile(
            r"(?i)(?<![a-z0-9])cc[-\s]?by[-\s]sa(?![a-z0-9-])"
            r"|creative commons attribution[-\s]+share[-\s]?alike"
        ),
    ),
    (
        "by",
        re.compile(
            r"(?i)(?<![a-z0-9])cc[-\s]?by(?![\s-]*" + _CC_CONTINUATION + r")"
            r"|creative commons attribution(?![-\s]*(?:non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike))"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:cc[-\s]?0|cc[-\s]?zero)(?![a-z0-9])"
            r"|creative commons(?:\s+public\s+domain)?\s+zero(?![a-z])"
        ),
    ),
)


class CatalogError(ValueError):
    """A catalog row or page failed the AI21 Labs page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_ai21_host(hostname: str) -> bool:
    """True for ai21.com, and for www.ai21.com when that host is the response host."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: dict | None = None) -> bool:
    """True for a Cloudflare, captcha, SiteGround, or Akamai interstitial.

    A normal article that only loads Cloudflare's ``/cdn-cgi/challenge-platform``
    script is the page, not a block page. A block page has no article heading.
    """

    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name in {"cf-mitigated", "sg-captcha"} and "challenge" in token:
                return True
            if name == "server" and "akamaighost" in token:
                return True
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _CHALLENGE_MARKERS):
        return True
    if "challenge-platform" in lowered and not re.search(r"(?is)<h1\b", page_html):
        return True
    return False


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge.

    An HTTP error, including 202 and 403, a non-HTML body, and a challenge
    page are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers):
        return False
    return True


def confirmed_fetch_url(requested_url: str, final_url: str) -> str | None:
    """Return the URL when the GET stayed on that same research or news page.

    A redirect off-host, or a same-host redirect onto a different path, is
    not stored. www.ai21.com is stored only when the response stays there.
    """

    try:
        requested = validate_canonical_url(requested_url)
        final = validate_canonical_url(final_url)
    except CatalogError:
        return None
    if requested != final:
        return None
    return final


def robots_allows(robots_body: str, path: str) -> bool:
    """True when robots.txt does not disallow ``path``.

    An empty body or an HTML error page allows the path. An empty Disallow
    value allows the path. A Disallow rule blocks the longest matching prefix
    unless a longer Allow prefix wins.
    """

    if not isinstance(robots_body, str):
        return False
    sample = robots_body.lstrip()[:500].casefold()
    if not sample or sample.startswith("<!doctype html") or sample.startswith("<html") or "<html" in sample:
        return True
    rules = _robots_star_rules(robots_body)
    target = path or "/"
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix:
            continue
        if target.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted Creative Commons deeds are detected before permissive ones.
    A hyphen is a word boundary, so CC BY does not match CC BY-NC. Mixed
    restricted and permissive text stays unknown. A permissive anchor label on
    a restricted or public-domain mark URL stays unknown. Anchor text on a
    generic creativecommons.org/licenses/ URL is not a licence statement.
    Public Domain Mark is not CC0. uk_ogl needs the British phrase Open
    Government Licence. us_government_work needs a rights field. mit,
    apache-2.0, and mpl-2.0 are not folded together or into a Creative Commons
    deed.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    if _misleading_permissive_anchor(visible):
        return RIGHTS_UNKNOWN
    scanned = _drop_generic_cc_license_anchors(visible)
    pieces = [_plain(scanned), *_licence_hrefs(visible), *_meta_values(visible, _LICENSE_META)]
    for blob in _LDJSON.findall(_COMMENT.sub(" ", page_text)):
        pieces.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(blob))
    folded = _fold("\n".join(pieces))
    restricted, permissive = _cc_codes(folded)
    software = _software_tokens(folded)
    ogl = _OGL_PHRASE.search(_plain(scanned).translate(_DASHES)) is not None
    government = _us_government_work(page_text)
    if restricted:
        if permissive or software or ogl or government or len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive:
        if software or ogl or government:
            return RIGHTS_UNKNOWN
        if permissive <= {"by"}:
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if software:
        if ogl or government or len(software) != 1:
            return RIGHTS_UNKNOWN
        return next(iter(software))
    if ogl and government:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str, *, page_url: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    ``datePublished`` counts when its URL is this page. ``article:published_time``
    counts. Updated, modified, and copyright years do not. Several different
    publication dates stay unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible(page_html)
    times: list[str] = []
    for attrs, inner in _TIME.findall(visible):
        parsed_attrs = _attrs(f"<time {attrs}>")
        blob = f"{parsed_attrs.get('class', '')} {_plain(inner)}"
        if _NOT_PUBLICATION.search(blob):
            continue
        parsed = _iso_prefix(parsed_attrs.get("datetime"))
        if parsed and parsed not in times:
            times.append(parsed)
    if len(times) > 1:
        return UNKNOWN_DATE
    meta_dates: list[str] = []
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_prefix(metas.get(key))
        if parsed and parsed not in meta_dates:
            meta_dates.append(parsed)
    json_dates = _jsonld_publication_dates(page_html, page_url)
    found: list[str] = []
    for value in [*times, *meta_dates, *json_dates]:
        if value not in found:
            found.append(value)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title and title.casefold() not in {"ai21", "ai21 labs"}:
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title and title.casefold() not in {"ai21", "ai21 labs"}:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title and title.casefold() not in {"ai21", "ai21 labs"}:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return AI21 Labs when the page states that name.

    A person named on the page is not the publisher. The hostname is not the
    publisher. The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible(page_html)
    if _PUBLISHER_PHRASE.search(_plain(visible)):
        return PUBLISHER
    for tag in _IMG.findall(visible):
        alt = _attrs(tag).get("alt", "")
        if _PUBLISHER_PHRASE.search(alt):
            return PUBLISHER
    metas = _metas(visible)
    for key in ("citation_publisher", "dcterms.publisher", "og:site_name"):
        if _PUBLISHER_PHRASE.search(metas.get(key, "")):
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html, page_url=page_url),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict | None = None,
    final_url: str | None = None,
) -> dict | None:
    """Return metadata when one bounded response is that page's HTML.

    A challenge, an HTTP error, a non-HTML body, a robots-ineligible URL, or
    a redirect away from ``page_url`` is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    landed = page_url if final_url is None else final_url
    if confirmed_fetch_url(page_url, landed) is None:
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=landed)
    except CatalogError:
        return None


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
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
        if not official_ai21_host(urlparse(url).hostname or ""):
            raise CatalogError("canonical URL must stay on ai21.com or www.ai21.com")
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
    _require_text(entry, "title")
    _require_text(entry, "publisher")
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public AI21 Labs research or news page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc != host
        or host not in OFFICIAL_HOSTS
        or not official_ai21_host(host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or not path.startswith("/")
        or not path.endswith("/")
        or _omitted_path(path)
        or _is_download(path)
        or not _research_or_news_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public AI21 Labs research or news page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _misleading_permissive_anchor(visible_html: str) -> bool:
    """True when a permissive label points at a restricted or mark URL.

    CC BY or CC BY-SA on by-nc, by-nd, by-nc-sa, by-nc-nd, or a public-domain
    mark URL is not that permissive deed. CC0 on a publicdomain/mark URL is
    not CC0.
    """

    for attrs, inner in _ANCHOR.findall(visible_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if not href:
            continue
        folded_href = _fold(href)
        restricted_url = _CC_RESTRICTED_URL.search(folded_href) is not None
        mark_url = _CC_MARK_URL.search(folded_href) is not None
        if not restricted_url and not mark_url:
            continue
        restricted_text, permissive_text = _cc_codes(_fold(_plain(inner)))
        if restricted_text:
            continue
        if mark_url and "zero" in permissive_text:
            return True
        if permissive_text & {"by", "by-sa"}:
            return True
    return False


def _drop_generic_cc_license_anchors(visible_html: str) -> str:
    """Remove anchors whose href is the generic Creative Commons licences URL.

    The anchor text on that path is not a licence statement, even when it
    says CC BY, CC BY 4.0, or CC BY-SA.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, visible_html)


def _generic_cc_licenses_url(href: str) -> bool:
    parsed = urlparse(_fold(href).strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    return (parsed.path or "") in {"/licenses", "/licenses/"}


def _cc_codes(folded: str) -> tuple[set[str], set[str]]:
    restricted: set[str] = set()
    permissive: set[str] = set()
    for match in _CC_RESTRICTED_URL.finditer(folded):
        restricted.add(match.group("code").casefold())
    for code, pattern in _CC_RESTRICTED_TEXT:
        if pattern.search(folded):
            restricted.add(code)
    for match in _CC_PERMISSIVE_URL.finditer(folded):
        if match.group("by"):
            permissive.add("by")
        elif match.group("sa"):
            permissive.add("by-sa")
        elif match.group("zero"):
            permissive.add("zero")
    for code, pattern in _CC_PERMISSIVE_TEXT:
        if pattern.search(folded):
            permissive.add(code)
    return restricted, permissive


def _software_tokens(folded: str) -> set[str]:
    found: set[str] = set()
    if _MIT.search(folded) or _MIT_URL.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded) or _APACHE_URL.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded) or _MPL_URL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _us_government_work(page_text: str) -> bool:
    """True only when a rights field says the item is a US government work."""

    visible = _visible(page_text)
    fields = _meta_values(visible, _RIGHTS_META)
    for blob in _LDJSON.findall(_COMMENT.sub(" ", page_text)):
        fields.extend(raw.replace("\\/", "/") for raw in _LD_RIGHTS.findall(blob))
    text = _plain("\n".join(fields)).translate(_DASHES)
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


def _jsonld_publication_dates(page_html: str, page_url: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(_COMMENT.sub(" ", page_html)):
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            continue
        for node in _iter_nodes(payload):
            published = node.get("datePublished")
            node_url = node.get("url")
            if not isinstance(published, str) or not isinstance(node_url, str):
                continue
            if not _same_page(node_url, page_url):
                continue
            parsed = _iso_prefix(published)
            if parsed and parsed not in found:
                found.append(parsed)
    return found


def _iter_nodes(payload: object) -> list[dict]:
    found: list[dict] = []

    def walk(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        found.append(value)
        for item in value.values():
            if isinstance(item, (dict, list)):
                walk(item)

    walk(payload)
    return found


def _same_page(left: str, right: str) -> bool:
    def norm(value: str) -> tuple[str, str] | None:
        parsed = urlparse(value.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in {"http", "https"} or not host:
            return None
        path = parsed.path or "/"
        if not path.endswith("/"):
            path += "/"
        return host, path

    return norm(left) == norm(right) and norm(left) is not None


def _robots_star_rules(robots_body: str) -> list[tuple[str, str]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in robots_body.splitlines():
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
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            return group_rules
    return []


def _research_or_news_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if not parts or not all(_SEGMENT.fullmatch(part) or _PAGE_NUMBER.fullmatch(part) for part in parts):
        return False
    if parts[0] == "research":
        if len(parts) == 1:
            return True
        if len(parts) == 2 and _SEGMENT.fullmatch(parts[1]):
            return True
        return len(parts) == 3 and parts[1] == "page" and _PAGE_NUMBER.fullmatch(parts[2]) is not None
    if parts[0] == "newsroom":
        if len(parts) == 1:
            return True
        return len(parts) == 3 and parts[1] == "page" and _PAGE_NUMBER.fullmatch(parts[2]) is not None
    if parts[0] == "blog" and len(parts) == 2 and parts[1] not in _BLOG_SKIP and _SEGMENT.fullmatch(parts[1]):
        return True
    return False


def _omitted_path(path: str) -> bool:
    parts = [part for part in path.casefold().split("/") if part]
    return any(part in _OMITTED_PARTS for part in parts)


def _is_download(path: str) -> bool:
    bare = path[:-1] if path.endswith("/") else path
    return bare.casefold().endswith(_DOWNLOAD_SUFFIXES)


def _visible(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text))
    text = _TAG.sub(" ", text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(value: str) -> str:
    return unescape(value).replace("\\/", "/").translate(_DASHES).casefold()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
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


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _licence_hrefs(visible_html: str) -> list[str]:
    found: list[str] = []
    for href in _hrefs(visible_html):
        if _generic_cc_licenses_url(href):
            continue
        found.append(href)
    return found


def _hrefs(visible_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(visible_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs, _inner in _ANCHOR.findall(visible_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
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


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.casefold(), unescape(raw).strip())
    return attrs
