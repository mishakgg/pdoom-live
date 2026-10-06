"""Metadata catalog of public ControlAI statement, research, news, and program pages.

The only hosts are controlai.com and www.controlai.com. controlai.org is a
different host and is not part of this catalog. Bounded GETs of the home page,
robots.txt, sitemap.xml, and the news, research, statements, and programs
listings on both hosts returned HTTP 301 to the same path on controlai.org.
Those responses left the catalog hosts, so each of those paths records an
empty catalog and the redirect is not followed. A Cloudflare challenge, a
captcha, an authentication wall, or a robots.txt disallow does the same. No
challenge, captcha, or authentication wall was returned.

A row is stored only when one bounded GET returns HTML on one of the two
hosts. Login walls, downloads, and unrelated hosts are omitted. Each row keeps
the title, publisher, canonical URL, date, and rights label. Page text,
abstracts, PDFs, quotes, transcripts, and chart data are not stored. The
publisher is ControlAI. The live URL is stored as confirmed. A different
rel=canonical does not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone. creative_commons means CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. Two different restricted deeds stay unknown. A CC BY, CC BY 4.0,
or CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or public-domain
mark URL stays unknown. A CC0 anchor on a public-domain mark URL stays
unknown. A generic creativecommons.org/licenses or /licenses/ URL is not a
deed, including a missing slash, http, a www host, and a query string. Anchor
text on that URL does not count. A specific deed URL still counts, and text
elsewhere on the page still counts. mit, apache-2.0, and mpl-2.0 are stored
only as one sole software licence. Apache License, Version 2.0, including the
comma, is apache-2.0. A software licence beside any Creative Commons deed
stays unknown. Two software licences stay unknown. uk_ogl requires the
British phrase Open Government Licence. us_government_work comes only from an
explicit rights metadata field. A photo credit, caption credit, or image
credit that names someone else's licence does not count. Script, style, and
comment text does not count. A hyphen is a word boundary, so CC BY does not
match CC BY-NC.

Updated, modified, and copyright years are not publication dates. A missing
date stays unknown. This module does not fetch. It is not a belief collector,
and runner_wired stays false.
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

CATALOG_ID = "controlai_pages"
CATALOG_FILENAME = "controlai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
PUBLISHER = "ControlAI"
APEX_HOST = "controlai.com"
WWW_HOST = "www.controlai.com"
OFFICIAL_HOSTS = frozenset({APEX_HOST, WWW_HOST})
OUTSIDE_HOST = "controlai.org"

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

MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public statement, research, news, and program HTML pages on "
    "controlai.com and www.controlai.com. Publisher is ControlAI. A row keeps a "
    "title, canonical URL, date, and rights. Page text, abstracts, PDFs, quotes, "
    "transcripts, and chart data are not stored. Bounded GETs of /, /robots.txt, "
    "/sitemap.xml, /news, /research, /statements, and /programs on both hosts "
    "returned HTTP 301 to controlai.org. That host is not catalogued, so those "
    "paths are empty and the redirect is not followed. A Cloudflare challenge, "
    "captcha, authentication wall, or robots disallow records an empty catalog "
    "for that path. No such challenge was returned. Missing dates stay unknown. "
    "Updated, modified, and copyright years are not publication dates. Not a "
    "belief collector and runner_wired stays false."
)

# Paths probed on both hosts. Each HTTP response was 301 to controlai.org.
REDIRECTED_LISTING_PATHS = (
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/news",
    "/research",
    "/statements",
    "/programs",
)
CHALLENGE_SKIPPED_PATHS: tuple[str, ...] = ()

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
        "summary",
        "text",
        "transcript",
        "transcript_text",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PAGE_PATH = re.compile(
    r"^/(?:statements?|research|news|programmes?|programs?)"
    r"(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*/?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
)
_LICENSE_META = frozenset(
    {"license", "licence", "dcterms.license", "dcterms.licence", "dc.rights", "dcterms.rights", "rights"}
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_LOGIN_PARTS = frozenset(
    {
        "account",
        "auth",
        "log-in",
        "login",
        "sign-in",
        "signin",
        "signup",
        "sign-up",
        "wp-admin",
        "wp-login.php",
    }
)
_LOGIN_TITLES = frozenset({"log in", "login", "sign in", "sign-in"})
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "akamaighost",
    "errors.edgesuite.net",
    "are you a robot",
)
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s*control\s*ai\s*$")
_NOT_PUBLICATION = re.compile(r"(?i)\b(?:updated|modified|copyright)\b|©|last\s+update")
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
    r"(?i)(?:\bmit\s+licen[cs]e\b|\blicen[cs]ed under (?:the\s+)?mit\s+licen[cs]e\b)"
)
_MIT_URL = re.compile(r"(?i)(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?i)(?<![a-z0-9])(?:"
    r"apache-2\.0(?![a-z0-9])"
    r"|apache\s+licen[cs]e(?:\s*,\s*version|\s+version)?\s*2\.0(?!\d)"
    r")"
)
_APACHE_URL = re.compile(
    r"(?i)(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(
    r"(?i)(?:\bmpl-2\.0\b|\bmozilla\s+public\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b)"
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
# Longer restricted deeds are listed first. (?!-) keeps CC BY and licenses/by
# from matching CC BY-NC and licenses/by-nc.
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
            r"|creative commons attribution[-\s]+non[-\s]?commercial[-\s]+no[-\s]?deriv"
            r")"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc[-\s]sa(?![a-z0-9-])"
            r"|creative commons attribution[-\s]+non[-\s]?commercial[-\s]+share[-\s]?alike"
            r")"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nc(?![a-z0-9-])"
            r"|creative commons attribution[-\s]+non[-\s]?commercial(?![-\s]*(?:share[-\s]?alike|no[-\s]?deriv))"
            r")"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:"
            r"cc[-\s]?by[-\s]nd(?![a-z0-9-])"
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
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|caption|image)\s+credit\b")
_CREDIT_OPEN = re.compile(
    r"(?is)<(p|figcaption|li|em|span|caption|figure|small|cite|dd|td|div)\b[^>]*>"
)
_CREDIT_CLOSE = re.compile(
    r"(?is)</(?:p|figcaption|li|em|span|caption|figure|small|cite|dd|td|div)\s*>"
)


class CatalogError(ValueError):
    """A catalog row or page failed the ControlAI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def empty_catalog() -> dict:
    """A catalog document with no rows."""

    return {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": False,
        "entries": [],
    }


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_controlai_host(hostname: str) -> bool:
    """True only for controlai.com or www.controlai.com."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: Mapping[str, str] | None = None) -> bool:
    """True for a Cloudflare, SiteGround, or Akamai interstitial."""

    if isinstance(page_html, str) and page_html.strip():
        sample = page_html[:12000].casefold()
        head = sample[:4000]
        title_match = _TITLE.search(page_html[:4000])
        title = _plain(title_match.group(1)).casefold() if title_match else ""
        blob = head + "\n" + title
        if any(marker in blob or marker in sample for marker in _CHALLENGE_MARKERS):
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
        if name == "www-authenticate":
            return True
    return False


def robots_allows(robots_body: str, path: str) -> bool:
    """True when robots.txt does not disallow ``path``.

    An empty body or an HTML 404 allows the path. A challenge body does not.
    A Disallow rule blocks the longest matching prefix unless a longer Allow
    prefix wins. A sitemap line alone does not disallow a path.
    """

    if not isinstance(robots_body, str):
        return False
    sample = robots_body.lstrip()[:2000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
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


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or login wall.

    HTTP errors, including 202, 401, and 403, are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers) or _is_login_wall(page_html):
        return False
    return True


def confirmed_fetch_url(requested_url: str, final_url: str) -> str | None:
    """Return the final URL when the GET stayed on an official host and path.

    A redirect to controlai.org, or onto a different path, is not stored.
    A redirect between controlai.com and www.controlai.com on the same path
    stays in the catalog.
    """

    requested = urlparse(requested_url)
    final = urlparse(final_url)
    if not official_controlai_host(requested.hostname or ""):
        return None
    if not official_controlai_host(final.hostname or ""):
        return None
    if _path_key(requested.path) != _path_key(final.path):
        return None
    try:
        return validate_canonical_url(final_url)
    except CatalogError:
        return None


def catalog_for_path(
    *,
    path: str,
    status: object,
    content_type: object,
    body: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_text: str | None = None,
) -> dict:
    """Return a catalog for one sitemap or listing path.

    A Cloudflare challenge, a captcha, an authentication status, a robots
    disallow, or a redirect off the two ControlAI hosts records an empty
    catalog for that path.
    """

    document = empty_catalog()
    if not isinstance(path, str) or not path.startswith("/"):
        return document
    if robots_text is not None and not robots_allows(robots_text, path):
        return document
    if status in {401, 403, 407} or _authentication_status(status, headers):
        return document
    if isinstance(body, str) and is_challenge_page(body, headers):
        return document
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=body,
        headers=headers,
    ):
        return document
    landed = page_url if final_url is None else final_url
    if confirmed_fetch_url(page_url, landed) is None:
        return document
    assert isinstance(body, str)
    try:
        document["entries"] = [page_record(body, page_url=landed)]
    except CatalogError:
        document["entries"] = []
    return document


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary. A permissive label on a restricted or public-domain mark URL
    stays unknown. Anchor text on a generic creativecommons.org/licenses URL
    is not a licence statement. A photo, caption, or image credit is not a
    licence for the page. uk_ogl needs the British phrase Open Government
    Licence. us_government_work needs a rights metadata field. mit,
    apache-2.0, and mpl-2.0 stay separate from each other and from any
    Creative Commons deed. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _drop_credit_licences(_visible(page_text))
    if _misleading_permissive_anchor(visible):
        return RIGHTS_UNKNOWN
    scanned = _blank_generic_license_anchors(visible)
    pieces = [_plain(scanned), *_hrefs(scanned), *_meta_values(scanned, _LICENSE_META)]
    folded = _fold("\n".join(pieces))
    restricted, permissive = _cc_codes(folded)
    software = _software_tokens(folded)
    ogl = _OGL_PHRASE.search(_plain(scanned).translate(_DASHES)) is not None
    government = _us_government_work(_visible(page_text))
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


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, and dates inside script, style, or comments are not publication
    dates. Several different publication dates stay unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    found: list[str] = []
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_prefix(metas.get(key))
        if parsed and parsed not in found:
            found.append(parsed)
    for attrs, inner in _TIME.findall(visible):
        parsed_attrs = _attrs(f"<time {attrs}>")
        blob = f"{parsed_attrs.get('class', '')} {_plain(inner)}"
        if _NOT_PUBLICATION.search(blob):
            continue
        parsed = _iso_prefix(parsed_attrs.get("datetime"))
        if parsed and parsed not in found:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(heading.group(1))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return ControlAI when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher"):
        if _names_controlai(metas.get(key, "")):
            return PUBLISHER
    if _names_controlai(_plain(visible)):
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
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded response is that page's HTML.

    A challenge, an HTTP error, a non-HTML body, a robots disallow, a login
    wall, or a redirect away from the two ControlAI hosts is not stored.
    """

    if robots_text is not None and not robots_allows(robots_text, urlparse(page_url).path or "/"):
        return None
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
    if description != description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
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
        if not official_controlai_host(urlparse(url).hostname or ""):
            raise CatalogError("canonical URL must stay on controlai.com or www.controlai.com")
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
    _require_text(entry.get("title"), "title", MAX_FIELD_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public ControlAI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or not official_controlai_host(host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or not _PAGE_PATH.fullmatch(path)
        or _login_path(path)
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be a public ControlAI page: {url}")
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


def _blank_generic_license_anchors(visible_html: str) -> str:
    """Drop anchor text on a generic creativecommons.org/licenses URL.

    That text is not a licence statement, even when it says CC BY, CC BY 4.0,
    or CC BY-SA. A missing slash, http, a www host, and a query string stay
    generic. A specific deed path is left in place.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_license_href(href):
            return f"<a {match.group(1)}></a>"
        return match.group(0)

    return _ANCHOR.sub(replace, visible_html)


def _is_generic_cc_license_href(href: str) -> bool:
    parsed = urlparse(href.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    path = (parsed.path or "/").lower()
    return path.rstrip("/") == "/licenses"


def _drop_credit_licences(html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names."""

    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(html):
        start_region = max(0, match.start() - 500)
        opens = list(_CREDIT_OPEN.finditer(html[start_region : match.start()]))
        removed = False
        if opens:
            last = opens[-1]
            abs_open = start_region + last.start()
            close = re.search(
                rf"(?is)</{last.group(1)}\s*>",
                html[match.end() : match.end() + 1500],
            )
            if close is not None:
                abs_end = match.end() + close.end()
                if abs_end - abs_open <= 2000:
                    spans.append((abs_open, abs_end))
                    removed = True
        if removed:
            continue
        close = _CREDIT_CLOSE.search(html[match.end() : match.end() + 1200])
        end = match.end() + close.end() if close is not None else min(match.end() + 800, len(html))
        spans.append((match.start(), end))
    if not spans:
        return html
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    pieces: list[str] = []
    cursor = 0
    for start, end in merged:
        pieces.append(html[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(html[cursor:])
    return "".join(pieces)


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


def _us_government_work(visible_html: str) -> bool:
    """True only when a rights metadata field states a US government work."""

    fields = _meta_values(visible_html, _RIGHTS_META)
    text = _plain("\n".join(fields)).translate(_DASHES)
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


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


def _authentication_status(status: object, headers: Mapping[str, str] | None) -> bool:
    if status in {401, 403, 407}:
        return True
    if not headers:
        return False
    return any(str(key).casefold() == "www-authenticate" for key in headers)


def _is_login_wall(page_html: str) -> bool:
    visible = _visible(page_html)
    title_match = _TITLE.search(visible)
    title = _plain(title_match.group(1)).casefold() if title_match else ""
    title = _SITE_SUFFIX.sub("", title).strip()
    return title in _LOGIN_TITLES


def _login_path(path: str) -> bool:
    return any(part in _LOGIN_PARTS for part in path.casefold().split("/") if part)


def _is_download(path: str) -> bool:
    bare = path[:-1] if path.endswith("/") else path
    return bare.casefold().endswith(_DOWNLOAD_SUFFIXES)


def _path_key(path: str) -> str:
    if path in {"", "/"}:
        return "/"
    return path[:-1] if path.endswith("/") else path


def _names_controlai(value: str) -> bool:
    folded = _plain(value).casefold()
    return "controlai" in folded.replace(" ", "")


def _visible(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text))
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(value: str) -> str:
    return unescape(value).replace("\\/", "/").translate(_DASHES).casefold()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _plain(value)).strip()


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
            if isinstance(item, (dict, list)):
                _reject_stored_body(item, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, (dict, list)):
                _reject_stored_body(item, path=f"{path}[{index}]")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    parsed = match.group(1)
    if not _iso_date(parsed):
        return None
    return parsed


def _iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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
    return [metas[name] for name in names if metas.get(name)]


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
