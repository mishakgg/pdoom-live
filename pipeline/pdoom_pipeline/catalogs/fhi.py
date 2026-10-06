"""Metadata catalog of public Future of Humanity Institute pages.

The official host is fhi.ox.ac.uk. www.fhi.ox.ac.uk is an official host only
when the response stays on that host. The institute has closed. A bounded GET
of https://fhi.ox.ac.uk/robots.txt, https://www.fhi.ox.ac.uk/robots.txt, and
both home pages failed before a response: neither name resolves. The catalog
is empty. No block page is stored.

A row would be stored only from one bounded GET of on-host HTML for a public
research, publication, or news page that robots.txt allows. A challenge, an
HTTP error, a non-HTML body, a robots disallow, or an off-host redirect is
not stored. Other Oxford hosts, PDFs, and downloads are omitted.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, quotes, transcripts, chart data, and PDFs are not stored.
The live URL is stored as confirmed; a different rel=canonical does not
replace it. A missing publication date stays unknown. Updated, modified, and
copyright years are not publication dates.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone. creative_commons means CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. Mixed restricted and permissive text stays unknown. A CC BY or
CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or publicdomain/mark
URL stays unknown. A CC0 anchor on a publicdomain/mark URL stays unknown. A
generic https://creativecommons.org/licenses/ URL stays unknown, and the
anchor text on that generic path is not a licence statement. A specific deed
URL such as /licenses/by/4.0/ still counts. A software licence beside any
Creative Commons deed stays unknown. Two different software licences stay
unknown. Two different restricted deeds stay unknown. Apache License,
Version 2.0 is apache-2.0. uk_ogl requires the British phrase Open Government
Licence. us_government_work comes only from an explicit rights metadata
field. Public Domain Mark, all rights reserved, terms, and the host name stay
unknown. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
Script, style, and comment text does not count.

This module does not fetch. It is not a belief collector, and runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "fhi_pages"
CATALOG_FILENAME = "fhi_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Future of Humanity Institute"
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"fhi.ox.ac.uk", "www.fhi.ox.ac.uk"})
OMITTED_HOSTS = frozenset(
    {
        "ox.ac.uk",
        "www.ox.ac.uk",
        "philosophy.ox.ac.uk",
        "www.philosophy.ox.ac.uk",
    }
)
SECTION_ROOTS = frozenset({"research", "publication", "publications", "news"})

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
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_SOFTWARE_TOKENS = {
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})

MAX_TEXT_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public Future of Humanity Institute research, publication, and news pages. "
    "The official host is fhi.ox.ac.uk. www.fhi.ox.ac.uk counts only when a response stays on that host. "
    "The institute has closed. Neither name resolves, so robots.txt was not retrieved and this catalog is empty. "
    "No block page is stored. Other Oxford hosts, PDFs, and downloads are omitted. "
    "Rows store a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "Rights stay unknown unless the page states a reuse licence. "
    "creative_commons_attribution means CC BY alone. "
    "creative_commons means CC0, CC BY-SA, or a permissive mix of those. "
    "A missing publication date stays unknown. "
    "This catalog is not a belief collector and runner_wired stays false."
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
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dcterms.licence", "dc.rights"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dc.date.issued",
    "dcterms.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher", "dc.publisher")
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
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
)
_SECTION_ROOTS = SECTION_ROOTS
_LOGIN_PARTS = frozenset(
    {
        "account",
        "auth",
        "log-in",
        "login",
        "sign-in",
        "signin",
        "sign-up",
        "signup",
        "wp-login.php",
    }
)
_BLOCKED_PARTS = frozenset(
    {"cdn-cgi", "feed", "wp-admin", "wp-content", "wp-includes", "wp-json", "xmlrpc.php"}
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"', re.I)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR_BLOCK = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " | Future of Humanity Institute",
    " - Future of Humanity Institute",
    " – Future of Humanity Institute",
    " — Future of Humanity Institute",
)
_NOT_PUBLICATION = re.compile(r"(?i)\b(?:updated|modified|copyright)\b|©|last\s+update")
_OGL_PHRASE = re.compile(r"(?<![a-z])open\s+government\s+licence(?![a-z])")
_MARK_HREF = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
# Longer deeds are listed first. A hyphen is a word boundary, so licenses/by
# does not match licenses/by-nc and CC BY does not match CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?![a-z0-9-])"
    r"|publicdomain/(?P<pd>zero|mark)(?![a-z0-9-]))"
)
_CC_CONTINUATION = r"(?:nc|nd|sa|non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike)"
_TEXT_DEEDS = (
    (
        "by-nc-nd",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*by[\s-]*nc[\s-]*nd"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*derivatives?"
            r")(?![a-z0-9])"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*by[\s-]*nc[\s-]*sa"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
            r")(?![a-z0-9])"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)(?![a-z0-9]))"
            r"|cc[\s-]*by[\s-]*non[\s-]*commercial(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
            r"|creative commons attribution[\s-]*non[\s-]*commercial(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
            r")(?![a-z0-9])"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*by[\s-]*nd"
            r"|cc[\s-]*by[\s-]*no[\s-]*derivatives?"
            r"|creative commons attribution[\s-]*no[\s-]*derivatives?"
            r")(?![a-z0-9])"
        ),
    ),
    (
        "by-sa",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*by[\s-]*sa(?![\s-]*(?:nc|nd)(?![a-z0-9]))"
            r"|creative commons attribution[\s-]*share[\s-]*alike"
            r")(?![a-z0-9])"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*0|cc0|cc[\s-]*zero"
            r"|creative commons(?:\s+public\s+domain)?\s+zero"
            r")(?![a-z0-9])"
        ),
    ),
    (
        "by",
        re.compile(
            r"(?<![a-z0-9])(?:"
            r"cc[\s-]*by(?![\s-]*" + _CC_CONTINUATION + r"(?![a-z0-9]))"
            r"|creative commons attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
            r")(?![a-z0-9-])"
        ),
    ),
)
_MIT_TEXT = re.compile(
    r"(?<![a-z0-9])(?:mit\s+licen[cs]e|licen[cs]ed\s+under\s+(?:the\s+)?mit)(?![a-z0-9-])"
)
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_TEXT = re.compile(
    r"(?<![a-z0-9])(?:"
    r"apache-2\.0"
    r"|apache\s+licen[cs]e\s*,\s*version\s*2\.0"
    r"|apache\s+licen[cs]e(?:\s+version)?\s*2\.0"
    r"|apache\s+2\.0"
    r")(?!\d)"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_TEXT = re.compile(
    r"(?<![a-z0-9])(?:"
    r"mpl-2\.0"
    r"|mozilla\s+public\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0"
    r")(?!\d)"
)
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bus\s+government\s+work\b"
)
_PUBLISHED_PROSE = re.compile(
    r"\b(?:date published|publication date|published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})"
    r"|([a-z]+)\s+(\d{1,2}),\s+(\d{4})"
    r"|(\d{1,2})\s+([a-z]+)\s+(\d{4}))"
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
_PIECE_GAP = "\n\u241e\n"
_COLLECTOR_AGENT = "pdoom.live-collector"


class CatalogError(ValueError):
    """A catalog row or page failed the Future of Humanity Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_fhi_host(hostname: str) -> bool:
    """True for fhi.ox.ac.uk and www.fhi.ox.ac.uk.

    www.fhi.ox.ac.uk is stored only when the fetched response stays on that
    host. Other Oxford hosts are not official.
    """

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
    """True for a Cloudflare, SiteGround, or Akamai interstitial."""

    if isinstance(page_html, str) and page_html.strip():
        sample = page_html[:12000].casefold()
        if any(marker in sample for marker in _CHALLENGE_MARKERS):
            return True
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name in {"cf-mitigated", "sg-captcha"} and token:
            return True
        if name == "server" and "akamaighost" in token:
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

    An HTTP error, a non-HTML body, and a block page are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if page_html.lstrip().startswith("%PDF"):
        return False
    if is_challenge_page(page_html, headers):
        return False
    return True


def robots_allows(robots_body: str, path: str) -> bool:
    """True when robots.txt does not disallow ``path`` for this collector.

    A challenge served in place of robots.txt does not allow a fetch. An
    empty body or an HTML error page has no disallow rule. The longest
    matching Allow prefix wins over a shorter Disallow prefix.
    """

    if not isinstance(robots_body, str) or not isinstance(path, str):
        raise CatalogError("robots text and path must be strings")
    if is_challenge_page(robots_body):
        return False
    sample = robots_body.lstrip()[:800].casefold()
    if sample.startswith("<!doctype") or sample.startswith("<html") or "<html" in sample[:500]:
        return True
    target = path if path.startswith("/") else f"/{path}"
    allowed = 0
    disallowed = 0
    for kind, prefix in _robots_rules(robots_body):
        if prefix and target.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A hyphen is a word boundary. Mixed restricted and permissive text stays
    unknown. Anchor text on a generic creativecommons.org/licenses/ URL is
    not a licence statement. Public Domain Mark is not CC0. uk_ogl requires
    the British phrase Open Government Licence. us_government_work requires
    a rights field. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    restricted, permissive, software, ogl, government = _licence_signals(page_text)
    if restricted and (permissive or software or ogl or government or len(restricted) != 1):
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if software and (permissive or ogl or government or len(software) != 1):
        return RIGHTS_UNKNOWN
    if len(software) == 1:
        return next(iter(software))
    if government and (permissive or ogl):
        return RIGHTS_UNKNOWN
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    if ogl and permissive:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if permissive <= {"by"} and permissive:
        return RIGHTS_CC_ATTRIBUTION
    if permissive & {"zero", "by-sa"}:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return one YYYY-MM-DD publication date, or unknown.

    Updated times, modified times, and copyright years are not publication
    dates. Several different publication dates stay unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    without_comments = _COMMENT.sub(" ", page_html)
    json_dates = _unique_iso_dates(_DATE_PUBLISHED.findall(" ".join(_LDJSON.findall(without_comments))))
    if json_dates is None:
        return UNKNOWN_DATE
    if json_dates:
        return json_dates[0]
    visible = _SCRIPT_STYLE.sub(" ", without_comments)
    metas = _metas(visible)
    meta_dates: list[str] = []
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key, ""))
        if parsed and parsed not in meta_dates:
            meta_dates.append(parsed)
    if len(meta_dates) > 1:
        return UNKNOWN_DATE
    if len(meta_dates) == 1:
        return meta_dates[0]
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
    if len(times) == 1:
        return times[0]
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
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Future of Humanity Institute when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if PUBLISHER.casefold() in _clean_text(metas.get(key, "")).casefold():
            return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
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
    headers: dict | None = None,
    final_url: str | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded response is that page's HTML.

    A challenge, an HTTP error, a non-HTML body, a robots disallow, or a
    redirect off the requested host is not stored. www.fhi.ox.ac.uk is stored
    only when the response stays on www.fhi.ox.ac.uk.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    landed = page_url if final_url is None else final_url
    if not _same_confirmed_url(page_url, landed):
        return None
    if robots_text is not None and not robots_allows(robots_text, urlparse(landed).path or "/"):
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
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the Future of Humanity Institute catalog note")
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
        host = urlparse(url).hostname or ""
        if not official_fhi_host(host):
            raise CatalogError("canonical URL must stay on the Future of Humanity Institute host")
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
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError("rights must be a known label or unknown")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Future of Humanity Institute page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != host
        or not official_fhi_host(host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or _blocked_path(path)
        or not _content_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public Future of Humanity Institute page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_prefix(value) != value:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def stored_hosts(document: dict | None = None) -> list[str]:
    """Hosts present on stored rows. The live catalog has none."""

    catalog = load_catalog() if document is None else document
    hosts: list[str] = []
    for entry in catalog["entries"]:
        host = (urlparse(entry["canonical_url"]).hostname or "").lower()
        if host and host not in hosts:
            hosts.append(host)
    return hosts


def _licence_signals(page_text: str) -> tuple[set[str], set[str], set[str], bool, bool]:
    without_comments = _COMMENT.sub(" ", page_text)
    license_fields: list[str] = []
    rights_fields: list[str] = []
    for blob in _LDJSON.findall(without_comments):
        license_fields.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(blob))
        rights_fields.extend(raw.replace("\\/", "/") for raw in _LD_RIGHTS.findall(blob))
    visible = _drop_non_deed_anchors(_SCRIPT_STYLE.sub(" ", without_comments))
    metas = _metas(visible)
    for key, value in metas.items():
        if key in _LICENSE_META or key.endswith((".license", ".licence", ":license", ":licence")):
            license_fields.append(value)
        if key in _RIGHTS_META or key == "rights" or key.endswith((".rights", ":rights")):
            rights_fields.append(value)
    rights_fields.extend(_rights_element_texts(visible))
    pieces = [_plain(visible), *license_fields, *_hrefs(visible)]
    folded = _fold(_PIECE_GAP.join(pieces))
    restricted, permissive = _cc_codes(folded)
    software = _software_tokens(folded)
    ogl_blob = _fold(_PIECE_GAP.join([_plain(visible), *license_fields, *rights_fields]))
    ogl = _OGL_PHRASE.search(ogl_blob) is not None
    government = any(_states_us_government_work(field) for field in rights_fields)
    return restricted, permissive, software, ogl, government


def _drop_non_deed_anchors(page_html: str) -> str:
    """Drop anchors whose text must not be read as a licence.

    Anchor text on a generic creativecommons.org/licenses/ URL is not a
    licence statement. CC0, CC BY, or CC BY-SA on a publicdomain/mark URL is
    not a dedication or a permissive licence.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _generic_license_href(href) or _MARK_HREF.search(_fold(href)):
            return " "
        return match.group(0)

    return _ANCHOR_BLOCK.sub(replace, page_html)


def _generic_license_href(href: str) -> bool:
    """True for a creativecommons.org/licenses/ URL that names no deed."""

    folded = _fold(href).strip()
    if not folded:
        return False
    if folded.startswith("//"):
        folded = f"https:{folded}"
    parsed = urlparse(folded if "://" in folded else f"https://{folded}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    return (parsed.path or "").rstrip("/") == "/licenses"


def _cc_codes(folded: str) -> tuple[set[str], set[str]]:
    restricted: set[str] = set()
    permissive: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            code = license_code.casefold()
            if code in _RESTRICTED:
                restricted.add(code)
            elif code in _PERMISSIVE:
                permissive.add(code)
            continue
        if match.group("pd") == "zero":
            permissive.add("zero")
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
        if code in _RESTRICTED:
            restricted.add(code)
        elif code in _PERMISSIVE:
            permissive.add(code)
    return restricted, permissive


def _software_tokens(folded: str) -> set[str]:
    found: set[str] = set()
    if _MIT_TEXT.search(folded) or _MIT_URL.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE_TEXT.search(folded) or _APACHE_URL.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL_TEXT.search(folded) or _MPL_URL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _fold(value))
    return _GOV_WORK.search(text) is not None


def _rights_element_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(page_html):
        parsed = _attrs(f"<x {attrs}>")
        itemprop = parsed.get("itemprop", "").casefold()
        tokens = []
        for key in ("id", "class"):
            tokens.extend(part.casefold() for part in parsed.get(key, "").split())
        if itemprop != "rights" and not any(token in {"rights", "dc.rights", "dcterms.rights"} for token in tokens):
            continue
        text = _plain(body)
        if text and len(text) <= MAX_TEXT_CHARS:
            found.append(text)
    return found


def _robots_rules(robots_body: str) -> list[tuple[str, str]]:
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
    best: list[tuple[str, str]] | None = None
    best_len = -1
    wildcard: list[tuple[str, str]] | None = None
    for group_agents, group_rules in groups:
        for agent in group_agents:
            if agent == "*":
                wildcard = group_rules
            elif _COLLECTOR_AGENT.startswith(agent) and len(agent) > best_len:
                best = group_rules
                best_len = len(agent)
    if best is not None:
        return best
    return wildcard or []


def _content_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if not parts or parts[0] not in _SECTION_ROOTS:
        return False
    return all(_SEGMENT.fullmatch(part) is not None for part in parts)


def _blocked_path(path: str) -> bool:
    lowered = path.casefold()
    if any(part in _LOGIN_PARTS or part in _BLOCKED_PARTS for part in lowered.split("/")):
        return True
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    return bare.endswith(_DOWNLOAD_SUFFIXES)


def _same_confirmed_url(requested: str, final: str) -> bool:
    try:
        return validate_canonical_url(requested) == validate_canonical_url(final)
    except CatalogError:
        return False


def _unique_iso_dates(values: list[str]) -> list[str] | None:
    found: list[str] = []
    for raw in values:
        parsed = _iso_prefix(raw)
        if parsed and parsed not in found:
            found.append(parsed)
    if len(found) > 1:
        return None
    return found


def _published_prose(plain: str) -> str:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(_fold(plain)):
        if match.group(1):
            parsed = _iso_prefix(match.group(1))
        elif match.group(4):
            parsed = _calendar_date(match.group(2), match.group(3), match.group(4))
        else:
            parsed = _calendar_date(match.group(6), match.group(5), match.group(7))
        if parsed and parsed not in found:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        return date(int(year_text), month, int(day_text)).isoformat()
    except ValueError:
        return None


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
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
        return
    if isinstance(value, str):
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    if text.casefold() == PUBLISHER.casefold():
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _visible(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs, _inner in _ANCHOR_BLOCK.findall(page_html):
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


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.casefold(), unescape(raw).strip())
    return attrs
