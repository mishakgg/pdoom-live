"""Metadata catalog of public LAION research, dataset, news, and project pages.

The official host is laion.ai. www.laion.ai redirects to laion.ai, so a
response that leaves www.laion.ai is not stored. robots.txt is an HTML 404,
which allows every path. Each stored URL was confirmed with one bounded GET
of HTML that stayed on laion.ai.

Stored pages are the blog and its posts, the notes and their posts, the
projects page, and the press page. Notes are on-site research and dataset
announcements. Press items link off-host and are not stored. /research/,
/datasets/, and /news/ do not resolve as pages and are not stored. Person
profiles on /team/, PDFs, login walls, and other hosts are omitted. A
Cloudflare challenge, a captcha, an authentication wall, an HTTP error, a
non-HTML body, a robots disallow, or an off-host redirect is not stored.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
text, abstracts, quotes, transcripts, dataset files, and chart data are not
stored. The live URL is stored as confirmed; a different rel=canonical does
not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone. creative_commons means CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. Mixed restricted and permissive text stays unknown. A CC BY or
CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or publicdomain/mark
URL stays unknown. A CC0 anchor on a publicdomain/mark URL stays unknown. A
generic https://creativecommons.org/licenses/ URL stays unknown even when
the anchor text says CC BY, CC BY 4.0, or CC BY-SA, including a missing
slash, http, www, or a query string. A specific deed URL such as
/licenses/by/4.0/ still counts. A software licence beside any Creative
Commons deed stays unknown. Two different software licences stay unknown.
Two different restricted deeds stay unknown. Apache License, Version 2.0,
including the comma, is apache-2.0. uk_ogl requires the British phrase Open
Government Licence. The American spelling Open Government License stays
unknown. us_government_work comes only from an explicit rights metadata
field. A photo credit, caption credit, or image credit that names someone
else's licence stays unknown, including Photo credit: UNDRR, CC BY-NC-ND 2.0
and Photo: UNDRR, CC BY-NC-ND 2.0. Public Domain Mark, all rights reserved,
terms, and the host name stay unknown. A hyphen is a word boundary, so CC BY
does not match CC BY-NC. Script, style, and comment text does not count.

A page that does not state a publication date keeps the date unknown.
Updated, modified, and copyright years are not publication dates. This
module does not fetch. It is not a belief collector, and runner_wired stays
false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "laion_pages"
CATALOG_FILENAME = "laion_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
PUBLISHER = "LAION"
OFFICIAL_HOST = "laion.ai"
OFFICIAL_HOSTS = frozenset({"laion.ai", "www.laion.ai"})

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
MAX_RESPONSE_BYTES = 1_000_000
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 15.0
CATALOG_DESCRIPTION = (
    "Metadata for public LAION research, dataset, news, blog, and project pages on laion.ai. "
    "www.laion.ai redirects to laion.ai and is not stored. robots.txt is an HTML 404, which allows /. "
    "Each row was confirmed with one bounded GET that stayed on laion.ai. "
    "Person profiles, PDFs, login walls, and off-host redirects are omitted. "
    "Press items leave the host and are not stored. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "A missing date is unknown. Updated, modified, and copyright years are not publication dates. "
    "creative_commons_attribution means CC BY alone. "
    "creative_commons means CC0, CC BY-SA, or a permissive mix of those. "
    "A sole restricted deed keeps its own token. "
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
    "dcterms.issued",
    "dc.date.issued",
)
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
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
)
_AUTH_MARKERS = (
    "authentication required",
    "please log in",
    "please sign in",
    "login required",
    "sign in to continue",
)
_OMITTED_PARTS = frozenset(
    {
        "about",
        "account",
        "auth",
        "cdn-cgi",
        "console",
        "dataset-requests",
        "donations",
        "faq",
        "gep-policy",
        "impressum",
        "log-in",
        "login",
        "privacy-policy",
        "sign-in",
        "signin",
        "team",
        "wp-admin",
        "wp-login.php",
    }
)
_SECTION_INDEXES = frozenset({"blog", "notes", "projects", "press"})
_POST_SECTIONS = frozenset({"blog", "notes"})
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
_SEGMENT = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_BYLINE_P = re.compile(r"(?is)<p\b[^>]*>\s*by:.*?</p>")
_RIGHTS_ELEMENT = re.compile(
    r"(?is)<([a-z0-9]+)\b([^>]*\bitemprop\s*=\s*['\"]rights['\"][^>]*)>(.*?)</\1>"
)
_OPEN_CREDIT = re.compile(
    r"(?is)<([a-z0-9]+)\b[^>]*\b(?:class|id)\s*=\s*(['\"])[^'\"]*(?:photo|image|caption)[\s_-]+credits?[^'\"]*\2[^>]*>"
)
_CREDIT_SPAN = re.compile(
    r"(?is)\b(?:(?:photo|image|caption)\s+credits?|photo\s*:)\s*(?:[^<.]|<[^>]*>|\.(?=\d)){0,500}"
)
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s*laion(?:\s+e\.v\.)?\s*$")
_OGL_PHRASE = re.compile(r"(?i)\bopen\s+government\s+licence\b")
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
# Longer restricted deeds are listed first. (?!-) keeps CC BY from matching
# CC BY-NC, and licenses/by from matching licenses/by-nc.
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
_GENERIC_CC_LICENSES = re.compile(
    r"(?i)^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:[?#].*)?$"
)
_CC_BARE = re.compile(r"(?i)\bcreative\s+commons\b")
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
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
_PUBLISHED_DMY = re.compile(rf"\bPublished\s+(\d{{1,2}})\s+({_MONTH_NAME})\.?,?\s+(\d{{4}})\b")
_PUBLISHED_MDY = re.compile(rf"\bPublished\s+({_MONTH_NAME})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b")
_BYLINE_DMY = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_NAME})\.?,?\s+(\d{{4}})\b")
_BYLINE_MDY = re.compile(rf"\b({_MONTH_NAME})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b")


class CatalogError(ValueError):
    """A catalog row or page failed the LAION page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_laion_host(hostname: str) -> bool:
    """True for laion.ai, and for www.laion.ai when that host is the response host."""

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
        lowered = page_html.casefold()
        if any(marker in lowered for marker in _CHALLENGE_MARKERS):
            return True
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name in {"cf-mitigated", "sg-captcha"} and "challenge" in token:
            return True
        if name == "server" and "akamaighost" in token:
            return True
    return False


def is_authentication_wall(page_html: str, *, status: object = None) -> bool:
    """True for an HTTP 401 or a page that demands a login."""

    if status in {401, 403}:
        return True
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    return any(marker in lowered for marker in _AUTH_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> bool:
    """A page is stored only from bounded HTML that is not a challenge or login wall.

    HTTP 202, HTTP 401, and HTTP 403, including an Akamai 403, are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if redirect_count > MAX_REDIRECTS:
        return False
    if elapsed_seconds is not None and elapsed_seconds > TIMEOUT_SECONDS:
        return False
    if len(page_html.encode("utf-8")) > MAX_RESPONSE_BYTES:
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers):
        return False
    if is_authentication_wall(page_html, status=status):
        return False
    return True


def confirmed_fetch_url(requested_url: str, final_url: str) -> str | None:
    """Return the URL when the GET stayed on that same official page.

    A redirect off-host, or a same-host redirect onto a different path, is
    not stored. www.laion.ai is stored only when the response stays there.
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

    An empty body or an HTML 404 allows the path. A Disallow rule blocks the
    longest matching prefix unless a longer Allow prefix wins. The observed
    laion.ai robots.txt is an HTML 404, so every public path is allowed.
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
    A hyphen is part of the deed token. Mixed restricted and permissive text
    stays unknown. A permissive anchor label on a restricted or public-domain
    mark URL stays unknown. Anchor text on a generic creativecommons.org/licenses/
    URL is not a licence statement. Public Domain Mark is not CC0. uk_ogl
    needs the British phrase Open Government Licence. us_government_work needs
    a rights field. mit, apache-2.0, and mpl-2.0 are not folded together.
    Photo, caption, and image credits do not count. Script, style, and comment
    text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _drop_non_licence_anchors(_drop_credit_licences(_visible(page_text)))
    pieces = [_plain(visible), *_hrefs(visible), *_meta_values(visible, _LICENSE_META)]
    folded = _fold("\n".join(pieces))
    restricted, permissive = _cc_codes(folded)
    software = _software_tokens(folded)
    # "Creative Commons" without a deed is not itself a stored token. Beside a
    # software licence it keeps the page unknown, because the deed was not named.
    bare_cc = _CC_BARE.search(folded) is not None and not restricted and not permissive
    ogl = _OGL_PHRASE.search(_plain(visible).translate(_DASHES)) is not None
    government = _us_government_work(visible)
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
        if ogl or government or bare_cc or len(software) != 1:
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

    A visible Published label or the byline date under the title is the
    publication date. The same date repeated is still that date.
    article:modified_time, og:updated_time, a last-updated line, and a
    copyright year are not publication dates. Script, style, and comment
    text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    found = _published_labels(visible) | _byline_dates(visible)
    if len(found) == 1:
        return next(iter(found))
    if len(found) > 1:
        return UNKNOWN_DATE
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_prefix(metas.get(key))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str, *, page_url: str | None = None) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    headings: list[str] = []
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title and title.casefold() != PUBLISHER.casefold():
            headings.append(title)
    meta_title = ""
    for key in ("og:title", "citation_title", "dcterms.title"):
        candidate = _clean_title(metas.get(key, ""))
        if candidate and candidate.casefold() != PUBLISHER.casefold():
            meta_title = candidate
            break
    section = _section_heading(page_url, headings)
    if section and meta_title.casefold() != section.casefold():
        return section
    if meta_title:
        return meta_title
    if headings:
        return headings[0]
    title_tag = _TITLE.search(visible)
    if title_tag:
        document_title = _clean_title(title_tag.group(1))
        if document_title and document_title.casefold() != PUBLISHER.casefold():
            return document_title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return LAION when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher", "og:title"):
        if _states_publisher(metas.get(key, "")):
            return PUBLISHER
    title_tag = _TITLE.search(visible)
    title_text = title_tag.group(1) if title_tag else ""
    if _states_publisher(_plain(visible)) or _states_publisher(_plain(title_text)):
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
    if is_authentication_wall(page_html):
        raise CatalogError("authentication wall is not stored")
    record = {
        "title": title_from_page(page_html, page_url=page_url),
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
    headers: dict | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> dict | None:
    """Return metadata when one bounded response is that page's HTML.

    A challenge, an authentication wall, an HTTP error, a non-HTML body, a
    robots disallow, or a redirect away from ``page_url`` is not stored.
    """

    if not isinstance(page_url, str):
        return None
    try:
        path = urlparse(page_url).path or "/"
    except ValueError:
        return None
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
        if not official_laion_host(urlparse(url).hostname or ""):
            raise CatalogError("canonical URL must stay on an official LAION host")
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
        raise CatalogError("canonical URL must be a public LAION research, dataset, news, or project page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc != host
        or not official_laion_host(host)
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
        or not path.startswith("/")
        or not path.endswith("/")
        or _omitted_path(path)
        or _is_download(path)
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public LAION research, dataset, news, or project page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _drop_credit_licences(visible_html: str) -> str:
    """Drop photo, caption, and image credits so someone else's licence does not count.

    ``Photo credit: UNDRR, CC BY-NC-ND 2.0`` and ``Photo: UNDRR, CC BY-NC-ND 2.0``
    are credits. A licence stated outside that credit still counts.
    """

    without_elements = _drop_credit_class_elements(visible_html)

    def replace(match: re.Match[str]) -> str:
        head = without_elements[: match.start()]
        if head.rfind("<") > head.rfind(">"):
            return match.group(0)
        return " "

    return _CREDIT_SPAN.sub(replace, without_elements)


def _drop_credit_class_elements(page_html: str) -> str:
    output: list[str] = []
    cursor = 0
    for match in _OPEN_CREDIT.finditer(page_html):
        if match.start() < cursor:
            continue
        end = _closing_tag_end(page_html, match.group(1), match.end())
        if end is None:
            continue
        output.append(page_html[cursor : match.start()])
        output.append(" ")
        cursor = end
    output.append(page_html[cursor:])
    return "".join(output)


def _closing_tag_end(page_html: str, tag: str, start: int) -> int | None:
    pattern = re.compile(rf"(?is)</?{re.escape(tag)}\b[^>]*>")
    depth = 1
    for match in pattern.finditer(page_html, start):
        token = match.group(0)
        if token.lower().startswith("</"):
            depth -= 1
            if depth == 0:
                return match.end()
        elif token.endswith("/>"):
            continue
        else:
            depth += 1
    return None


def _drop_non_licence_anchors(visible_html: str) -> str:
    """Drop anchors whose text must not be read as a licence.

    A generic creativecommons.org/licenses/ URL is not a deed, and its anchor
    text is not a licence statement. A publicdomain/mark URL is not CC0, and
    CC BY, CC BY-SA, or CC0 written on that URL stays unknown.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        folded = _fold(href).strip()
        if _GENERIC_CC_LICENSES.fullmatch(folded) or _CC_MARK_URL.search(folded):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, visible_html)


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
    fields = _meta_values(visible_html, _RIGHTS_META)
    for _tag, attrs, inner in _RIGHTS_ELEMENT.findall(visible_html):
        if _attrs(f"<x {attrs}>").get("itemprop", "").casefold() == "rights":
            fields.append(_plain(inner))
    text = _plain("\n".join(fields)).translate(_DASHES)
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


def _published_labels(visible_html: str) -> set[str]:
    found: set[str] = set()
    plain = _plain(visible_html)
    for match in _PUBLISHED_DMY.finditer(plain):
        parsed = _calendar_date(match.group(2), match.group(1), match.group(3))
        if parsed:
            found.add(parsed)
    for match in _PUBLISHED_MDY.finditer(plain):
        parsed = _calendar_date(match.group(1), match.group(2), match.group(3))
        if parsed:
            found.add(parsed)
    return found


def _byline_dates(visible_html: str) -> set[str]:
    found: set[str] = set()
    for element in _BYLINE_P.findall(visible_html):
        plain = _plain(element)
        for match in _BYLINE_DMY.finditer(plain):
            parsed = _calendar_date(match.group(2), match.group(1), match.group(3))
            if parsed:
                found.add(parsed)
        for match in _BYLINE_MDY.finditer(plain):
            parsed = _calendar_date(match.group(1), match.group(2), match.group(3))
            if parsed:
                found.add(parsed)
    return found


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold().rstrip("."))
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


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


def _section_heading(page_url: str | None, headings: list[str]) -> str | None:
    """Return the section name when the visible heading names that index.

    The notes index reuses the blog document title. Its h1 says NOTES, so the
    stored title is Notes. A document title that already names the section wins.
    """

    if not isinstance(page_url, str) or not headings:
        return None
    parts = [part for part in urlparse(page_url).path.split("/") if part]
    if len(parts) != 1 or parts[0] not in _SECTION_INDEXES:
        return None
    if headings[0].casefold() != parts[0]:
        return None
    return parts[0].capitalize()


def _public_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if len(parts) == 1 and parts[0] in _SECTION_INDEXES:
        return True
    if len(parts) == 2 and parts[0] in _POST_SECTIONS and _SEGMENT.fullmatch(parts[1]):
        return True
    return False


def _omitted_path(path: str) -> bool:
    parts = [part for part in path.casefold().split("/") if part]
    return any(part in _OMITTED_PARTS for part in parts)


def _is_download(path: str) -> bool:
    lowered = path.casefold()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _visible(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text))
    text = _TAG.sub(" ", text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(value: str) -> str:
    return unescape(value).replace("\\/", "/").translate(_DASHES).casefold()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _plain(value)).strip()


def _states_publisher(value: str) -> bool:
    return re.search(r"(?i)(?<![a-z0-9])laion(?![a-z0-9])", _plain(value)) is not None


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or "\n" in value or "\r" in value:
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
