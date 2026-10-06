"""Metadata catalog of public Apple Machine Learning Research pages.

Scope is research and news HTML on machinelearning.apple.com: /research,
/updates, and one slug under either path. Each stored URL was confirmed with
one bounded GET: 15 second timeout, at most 3 redirects, and at most 3000000
bytes. The response stayed on machinelearning.apple.com. robots.txt allows
these paths. A Cloudflare challenge, a captcha, an authentication wall, an
HTTP error, a non-HTML body, a robots disallow, a login wall, a person
profile, a PDF, or an off-host redirect is not stored. An empty entries list
is valid when a path is blocked or does not resolve.

Rows keep a title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, chart data, and PDFs are
not stored. Publisher is Apple Machine Learning Research. The live URL is
stored as confirmed. A different rel=canonical does not replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone, including a
https://creativecommons.org/licenses/by/4.0/ URL. creative_commons means CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. A hyphen is a word boundary, so CC BY does not match CC BY-NC
and licenses/by does not match licenses/by-nc. Mixed restricted and
permissive text stays unknown. Two different restricted deeds stay unknown.
A software licence beside any Creative Commons deed stays unknown. Two
software licences stay unknown. A sole MIT License is mit. A sole MPL-2.0 is
mpl-2.0. Apache License, Version 2.0 is apache-2.0.

A generic https://creativecommons.org/licenses/ URL is not a deed. A missing
slash, http, a www host, or a query string stays on that generic URL. Anchor
text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays unknown. A
specific deed URL still counts. Text elsewhere on the page still counts.
Deceptive permissive anchor text on a restricted deed URL or on a
public-domain mark URL stays unknown. A CC0 anchor on a public-domain mark
URL stays unknown.

A photo credit, caption credit, or image credit that names someone else's
licence stays unknown. The sentence Photo credit: UNDRR, CC BY-NC-ND 2.0
stays unknown. The sentence Photo: UNDRR, CC BY-NC-ND 2.0 stays unknown. A
page that says Licensed under CC BY 4.0 and also has that photo credit stays
creative_commons_attribution. A sentence that names someone else's dataset
licence stays unknown. A page licence stated outside that sentence still
counts.

uk_ogl requires the exact British phrase Open Government Licence. Open
Government License stays unknown. us_government_work comes only from an
explicit rights metadata field. Script, style, and comment text does not
count. Publication dates only. Modified, updated, and copyright years stay
unknown. This module does not fetch. It is not a belief collector.
runner_wired stays false.
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

CATALOG_ID = "apple_ml_pages"
CATALOG_FILENAME = "apple_ml_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
PUBLISHER = "Apple Machine Learning Research"
OFFICIAL_HOST = "machinelearning.apple.com"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST})
SCOPE_ROOTS = frozenset({"research", "updates"})
FETCH_TIMEOUT_SECONDS = 15
FETCH_MAX_REDIRECTS = 3
FETCH_MAX_BYTES = 3_000_000

RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY = RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
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
_SOFTWARE_TOKENS = {
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}

MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public Apple Machine Learning Research research and news HTML pages "
    "on machinelearning.apple.com. Publisher is Apple Machine Learning Research. "
    "Each stored URL was one bounded GET that stayed on that host. robots.txt allows "
    "these paths. Person profiles, PDFs, login walls, and off-host redirects are omitted. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a "
    "permissive mix of those. A missing date is unknown. Updated, modified, and copyright "
    "years are not publication dates. This module does not fetch. It is not a belief "
    "collector, and runner_wired is false."
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
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dcterms.licence"})
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
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
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
    "cf-browser-verification",
    "cdn-cgi/challenge",
    "g-recaptcha",
    "hcaptcha",
    "cf-turnstile",
)
_OMITTED_PARTS = frozenset(
    {
        "account",
        "auth",
        "author",
        "authors",
        "cdn-cgi",
        "login",
        "log-in",
        "member",
        "members",
        "people",
        "person",
        "persons",
        "profile",
        "profiles",
        "sign-in",
        "signin",
        "sign-up",
        "signup",
        "staff",
        "team",
        "wp-admin",
        "wp-login.php",
    }
)
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
_ISO_IN_TEXT = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
_SEGMENT = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>(.*?)</time>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PASSWORD = re.compile(r"(?i)<input\b[^>]*type\s*=\s*['\"]password['\"]")
_SITE_SUFFIX = re.compile(
    r"(?i)\s*(?:\||[-–—])\s*apple machine learning research\s*$"
)
_GENERIC_TITLES = frozenset(
    {
        "apple machine learning research",
        "home",
        "machine learning research",
        "overview",
    }
)
_MONTH_NAMES = {
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
_MONTH_PATTERN = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec"
)
_PUBLISHED_PROSE = re.compile(
    r"(?i)\b(?:publication date|date published|published)\b(?:\s+on)?\s*:?\s*"
    r"(?:"
    rf"(?P<iso>\d{{4}}-\d{{2}}-\d{{2}})"
    rf"|(?P<month>{_MONTH_PATTERN})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<year>\d{{4}})"
    rf"|(?P<day2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month2>{_MONTH_PATTERN})\s+(?P<year2>\d{{4}})"
    r")"
)
_TEXT_DATE = re.compile(
    rf"(?i)\b(?:"
    rf"(?P<m1>{_MONTH_PATTERN})\s+(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?"
    rf"|"
    rf"(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m2>{_MONTH_PATTERN})"
    rf"),?\s+(?P<year>\d{{4}})\b"
)
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
    r"(?i)(?<!modified )(?:\bmit\s+licen[cs]e\b|\bmit-licen[cs]ed\b|"
    r"\blicen[cs]ed under (?:the\s+)?mit(?:\s+licen[cs]e)?\b(?!-))"
)
_APACHE = re.compile(
    r"(?i)(?<![a-z0-9])(?:"
    r"apache-2\.0(?![a-z0-9])"
    r"|apache\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0(?!\d)"
    r"|apache\s+2\.0(?!\d)"
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
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|image|caption)\s+credits?\b|\bphoto\s*:")
_DATASET_WORD = re.compile(r"(?i)\bdatasets?\b")
_LICENCE_HINT = re.compile(
    r"(?i)creativecommons|cc[\s-]*by|cc[\s-]*0|\bcc0\b|creative commons|"
    r"\bmit licen[cs]e\b|apache licen[cs]e|mpl-2\.0|open government licence"
)
_ABBREV_BEFORE_DOT = re.compile(
    r"(?i)(?:et\s+al|e\.g|i\.e|inc|ltd|corp|vs|fig|eq|vol|no|pp|dr|mr|mrs|ms|prof|st)\s*$"
)
_CREDIT_CLOSE = re.compile(
    r"(?is)</(?:p|figcaption|li|em|span|caption|figure|small|cite|dd|td|div)\s*>"
)
_LOGIN_TITLES = frozenset({"log in", "login", "sign in", "signin"})


class CatalogError(ValueError):
    """A catalog row or page failed the Apple Machine Learning Research page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for machinelearning.apple.com only."""

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
    """True for a Cloudflare, SiteGround, captcha, or Akamai interstitial."""

    if isinstance(page_html, str) and page_html.strip():
        sample = page_html[:8000].casefold()
        if any(marker in sample for marker in _CHALLENGE_MARKERS):
            return True
        match = _TITLE.search(_visible(page_html[:8000]))
        if match is not None:
            title = _plain(match.group(1)).casefold()
            if title in {"just a moment...", "attention required! | cloudflare", "access denied"}:
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


def is_login_wall(page_html: str) -> bool:
    """True when the response is a login form rather than a public page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    visible = _visible(page_html)
    match = _TITLE.search(visible)
    if match is not None and _plain(match.group(1)).casefold() in _LOGIN_TITLES:
        return True
    return _PASSWORD.search(visible) is not None


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or login wall.

    HTTP 202 and HTTP 403 are not stored.
    """

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers) or is_login_wall(page_html):
        return False
    return True


def confirmed_fetch_url(requested_url: str, final_url: str) -> str | None:
    """Return the final URL when the GET stayed on machinelearning.apple.com.

    An off-host redirect is not stored. A same-host redirect onto another
    research or news path, such as a trailing slash, is stored at the final
    URL.
    """

    requested = urlparse(requested_url)
    if not is_official_host(requested.hostname or ""):
        return None
    try:
        final = validate_canonical_url(final_url)
    except CatalogError:
        return None
    if urlparse(final).hostname != (requested.hostname or "").lower().rstrip("."):
        return None
    return final


def robots_allows(robots_body: str, path: str) -> bool:
    """True when the * group does not disallow path.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. Comment-only robots text allows every path. A longer
    Allow prefix wins over a shorter Disallow prefix.
    """

    if not isinstance(robots_body, str):
        return False
    sample = robots_body[:800].casefold()
    if "<html" in sample or is_challenge_page(robots_body[:8000]):
        return False
    rules = _wildcard_rules(robots_body)
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


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted Creative Commons deeds are detected before permissive ones.
    A hyphen is a word boundary, so CC BY does not match CC BY-NC. A generic
    creativecommons.org/licenses URL is not a deed, and anchor text on it does
    not count. A permissive label on a restricted or public-domain mark URL
    does not count. A CC0 label on a public-domain mark URL does not count.
    Photo credit, caption credit, image credit, and a Photo: credit do not
    count. A sentence that names someone else's dataset licence does not
    count. Public Domain Mark is not CC0. uk_ogl needs the British phrase
    Open Government Licence. us_government_work needs a rights metadata field.
    mit, apache-2.0, and mpl-2.0 are not folded together or into a Creative
    Commons deed. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _drop_deceptive_anchors(
        _strip_generic_license_anchors(
            _without_image_credits(_without_dataset_licence_sentences(_visible(page_text)))
        )
    )
    pieces = [_plain(visible), *_hrefs(visible), *_meta_values(visible, _LICENSE_META)]
    pieces.extend(_rights_meta_values(visible))
    folded = _fold("\n".join(pieces))
    restricted, permissive = _cc_codes(folded)
    software = _software_tokens(folded)
    ogl = _OGL_PHRASE.search(_plain(visible).translate(_DASHES)) is not None
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
        return _SOFTWARE_TOKENS[next(iter(software))]
    if ogl and government:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    A full calendar date in one time element is the publication date. Visible
    prose that says published, publication date, or date published is used
    when it names one full day. A month and year without a day stay unknown.
    article:modified_time, og:updated_time, a last-updated line, and a
    copyright year are not publication dates. Script, style, and comment text
    does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    found: list[str] = []
    for attrs, inner in _TIME.findall(visible):
        parsed_attrs = _attrs(f"<time {attrs}>")
        blob = f"{parsed_attrs.get('class', '')} {_plain(inner)}"
        if _NOT_PUBLICATION.search(blob):
            continue
        stated = _calendar_dates(_plain(inner))
        if stated:
            for parsed in stated:
                if parsed not in found:
                    found.append(parsed)
            continue
        parsed = _iso_prefix(parsed_attrs.get("datetime"))
        if parsed and parsed not in found:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        return UNKNOWN_DATE
    prose = _published_prose_dates(_plain(visible))
    if len(prose) == 1:
        return prose[0]
    if len(prose) > 1:
        return UNKNOWN_DATE
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_prefix(metas.get(key))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        document_title = _clean_title(title_tag.group(1))
        if _usable_title(document_title):
            return document_title
    headings = _H1.findall(visible)
    if headings:
        title = _clean_title(headings[0])
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Apple Machine Learning Research when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher"):
        if _states_publisher(metas.get(key, "")):
            return PUBLISHER
    if _states_publisher(_plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html) or is_login_wall(page_html):
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
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> dict | None:
    """Return metadata when one bounded response is that page's HTML.

    A challenge, an HTTP error, a non-HTML body, a login wall, a robots
    disallow, or an off-host redirect is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    landed = page_url if final_url is None else final_url
    confirmed = confirmed_fetch_url(page_url, landed)
    if confirmed is None:
        return None
    parsed = urlparse(confirmed)
    if robots_txt is not None and not robots_allows(robots_txt, parsed.path or "/"):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=confirmed)
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
    if not isinstance(description, str) or description != description.strip() or not description:
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the Apple Machine Learning Research catalog contract")
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
        if not is_official_host(urlparse(url).hostname or ""):
            raise CatalogError("canonical URL must stay on machinelearning.apple.com")
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
        raise CatalogError("canonical URL must be a public Apple Machine Learning Research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc != host
        or not is_official_host(host)
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
        or not _scoped_path(path)
        or _omitted_path(path)
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be a public Apple Machine Learning Research page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _drop_deceptive_anchors(visible_html: str) -> str:
    """Drop a permissive label on a restricted deed or public-domain mark URL.

    The anchor text does not reclassify the href. A CC0 label on a
    public-domain mark URL is not a licence. Text outside the anchor still
    counts.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if not href:
            return match.group(0)
        folded_href = _fold(href)
        restricted_url = _CC_RESTRICTED_URL.search(folded_href) is not None
        mark_url = _CC_MARK_URL.search(folded_href) is not None
        if not restricted_url and not mark_url:
            return match.group(0)
        restricted_text, permissive_text = _cc_codes(_fold(_plain(match.group(2))))
        if restricted_text:
            return match.group(0)
        if mark_url and "zero" in permissive_text:
            return " "
        if permissive_text & {"by", "by-sa"}:
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
        found.add("mit")
    if _APACHE.search(folded) or _APACHE_URL.search(folded):
        found.add("apache-2.0")
    if _MPL.search(folded) or _MPL_URL.search(folded):
        found.add("mpl-2.0")
    return found


def _us_government_work(page_text: str) -> bool:
    visible = _visible(page_text)
    fields = _rights_meta_values(visible)
    text = _plain("\n".join(fields)).translate(_DASHES)
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
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
    return None


def _scoped_path(path: str) -> bool:
    if not path.startswith("/") or "//" in path:
        return False
    raw = path[:-1] if path.endswith("/") and len(path) > 1 else path
    if raw.endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in raw.split("/") if part]
    if not parts or parts[0] not in SCOPE_ROOTS:
        return False
    if len(parts) == 1:
        return True
    if len(parts) != 2:
        return False
    return _SEGMENT.fullmatch(parts[1]) is not None


def _omitted_path(path: str) -> bool:
    parts = [part for part in path.casefold().split("/") if part]
    return any(part in _OMITTED_PARTS for part in parts)


def _is_download(path: str) -> bool:
    raw = path[:-1] if path.endswith("/") else path
    return raw.casefold().endswith(_DOWNLOAD_SUFFIXES)


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
    text = _clean_text(value)
    previous = None
    while text and text != previous:
        previous = text
        text = _SITE_SUFFIX.sub("", text).strip()
    return text


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _GENERIC_TITLES and len(title) <= MAX_FIELD_CHARS


def _states_publisher(value: str) -> bool:
    return PUBLISHER.casefold() in _clean_text(value).casefold()


def _published_prose_dates(plain: str) -> list[str]:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        if match.group("iso"):
            parsed = match.group("iso") if _iso_date(match.group("iso")) else None
        elif match.group("year"):
            parsed = _calendar_day(match.group("year"), match.group("month"), match.group("day"))
        else:
            parsed = _calendar_day(match.group("year2"), match.group("month2"), match.group("day2"))
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def _calendar_dates(text: str) -> list[str]:
    found: list[str] = []

    def add(year: str, month_name: str, day: str) -> None:
        parsed = _calendar_day(year, month_name, day)
        if parsed and parsed not in found:
            found.append(parsed)

    for match in _TEXT_DATE.finditer(text):
        year = match.group("year")
        if match.group("m1"):
            add(year, match.group("m1"), match.group("d1"))
        else:
            add(year, match.group("m2"), match.group("d2"))
    for match in _ISO_IN_TEXT.finditer(text):
        raw = match.group(1)
        if _iso_date(raw) and raw not in found:
            found.append(raw)
    return found


def _calendar_day(year: str, month_name: str, day: str) -> str | None:
    month = _MONTH_NAMES.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year), month, int(day))
    except ValueError:
        return None
    return parsed.isoformat()


def _strip_generic_license_anchors(visible_html: str) -> str:
    """Drop anchors whose href is only the generic Creative Commons licences URL.

    The anchor text is not a licence statement, even when it says CC BY,
    CC BY 4.0, or CC BY-SA. A missing slash, http, a www host, and a query
    string stay generic. A specific deed URL stays. Text outside the anchor
    still counts.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, visible_html)


def _generic_cc_licenses_url(href: str) -> bool:
    text = unescape(href or "").strip()
    if not text:
        return False
    if text.startswith("//"):
        text = "https:" + text
    elif "://" not in text:
        bare = text.lstrip("/")
        lowered = bare.casefold()
        if lowered.startswith("creativecommons.org") or lowered.startswith("www.creativecommons.org"):
            text = "https://" + bare
        else:
            return False
    parsed = urlparse(text)
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    path = (parsed.path or "").casefold()
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _without_image_credits(page_html: str) -> str:
    """Drop photo, caption, and image credits, including a Photo: credit.

    A credit such as ``Photo credit: UNDRR, CC BY-NC-ND 2.0.`` or
    ``Photo: UNDRR, CC BY-NC-ND 2.0.`` names someone else's image licence.
    A decimal in a version number does not end the sentence. A reuse licence
    stated outside that sentence still counts.
    """

    out: list[str] = []
    cursor = 0
    while cursor < len(page_html):
        match = _CREDIT_PHRASE.search(page_html, cursor)
        if match is None:
            out.append(page_html[cursor:])
            break
        previous_open = page_html.rfind("<", cursor, match.start())
        previous_close = page_html.rfind(">", cursor, match.start())
        if previous_open > previous_close:
            out.append(page_html[cursor:match.end()])
            cursor = match.end()
            continue
        out.append(page_html[cursor:match.start()])
        index = match.end()
        while index < len(page_html):
            if page_html[index] == "<":
                if _CREDIT_CLOSE.match(page_html, index) or re.match(r"(?i)<br\b", page_html[index:]):
                    break
                end = page_html.find(">", index)
                if end == -1:
                    index = len(page_html)
                    break
                index = end + 1
                continue
            if page_html[index] == ".":
                nxt = page_html[index + 1] if index + 1 < len(page_html) else ""
                if nxt.isdigit():
                    index += 1
                    continue
                index += 1
                break
            index += 1
        cursor = index
    return "".join(out)


def _without_dataset_licence_sentences(page_html: str) -> str:
    """Drop a sentence that assigns a licence to someone else's dataset.

    The Free Music Archive and NSynth notices name another party's licence.
    They are not a licence for the page. A licence stated in another sentence
    still counts. ``et al.`` and ``Inc.`` do not end the sentence.
    """

    spans: list[tuple[int, int]] = []
    for match in _DATASET_WORD.finditer(page_html):
        previous_open = page_html.rfind("<", 0, match.start())
        previous_close = page_html.rfind(">", 0, match.start())
        if previous_open > previous_close:
            continue
        start = _sentence_start(page_html, match.start())
        end = _sentence_end(page_html, match.end())
        sentence = page_html[start:end]
        if _LICENCE_HINT.search(sentence):
            spans.append((start, end))
    if not spans:
        return page_html
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
        pieces.append(page_html[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(page_html[cursor:])
    return "".join(pieces)


def _sentence_start(page_html: str, index: int) -> int:
    i = index
    while i > 0:
        if page_html[i - 1] == ">":
            tag_start = page_html.rfind("<", 0, i)
            if tag_start == -1:
                return 0
            tag = page_html[tag_start:i].casefold()
            if re.match(r"</(?:p|div|li|h\d|section|article|figcaption|blockquote|tr|td)\b", tag) or re.match(
                r"<(?:p|div|li|h\d|section|article|figcaption|blockquote|tr|td|br)\b", tag
            ):
                return i
            i = tag_start
            continue
        if page_html[i - 1] in ".!?":
            nxt = page_html[i] if i < len(page_html) else ""
            if page_html[i - 1] == "." and nxt.isdigit():
                i -= 1
                continue
            if page_html[i - 1] == "." and _ABBREV_BEFORE_DOT.search(page_html[max(0, i - 17) : i - 1]):
                i -= 1
                continue
            return i
        i -= 1
    return 0


def _sentence_end(page_html: str, index: int) -> int:
    i = index
    while i < len(page_html):
        if page_html[i] == "<":
            end = page_html.find(">", i)
            if end == -1:
                return len(page_html)
            tag = page_html[i : end + 1].casefold()
            if re.match(r"</(?:p|div|li|h\d|section|article|figcaption|blockquote|tr|td)\b", tag) or re.match(
                r"<br\b", tag
            ):
                return i
            i = end + 1
            continue
        if page_html[i] in ".!?":
            nxt = page_html[i + 1] if i + 1 < len(page_html) else ""
            if page_html[i] == "." and nxt.isdigit():
                i += 1
                continue
            if page_html[i] == "." and _ABBREV_BEFORE_DOT.search(page_html[max(0, i - 16) : i]):
                i += 1
                continue
            return i + 1
        i += 1
    return len(page_html)


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


def _rights_meta_values(html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(html).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.casefold(), unescape(raw).strip())
    return attrs
