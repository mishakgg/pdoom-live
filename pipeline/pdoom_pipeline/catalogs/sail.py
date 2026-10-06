"""Metadata catalog of public Stanford Artificial Intelligence Laboratory pages.

Hosts are ai.stanford.edu and www.ai.stanford.edu. www.ai.stanford.edu does
not resolve, so that host is an empty catalog. Stored pages are research and
news HTML: the research-groups page, news articles, and the SAIL research
blog. Person profiles, login walls, PDFs, and pages on other Stanford hosts
stay out. A Cloudflare challenge, a captcha, an authentication wall, a
non-HTML shell, an HTTP error, a robots disallow, or a redirect off these
hosts is not stored. An HTML document served in place of robots.txt does not
allow a fetch. An empty entries list is valid.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, abstracts, quotes,
transcripts, chart data, and PDFs are not stored. Publisher is Stanford
Artificial Intelligence Laboratory when the page names SAIL, Stanford AI Lab,
or that laboratory.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone, including a specific
/licenses/by/4.0/ URL. ``creative_commons`` is CC0, CC BY-SA, or a permissive
mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps
``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``, or ``cc_by_nc_nd``. Text
``cc-by-nc`` is ``cc_by_nc``. Two different restricted deeds stay unknown. A
software licence beside any Creative Commons deed stays unknown. Two software
licences stay unknown. ``mit``, ``apache-2.0``, and ``mpl-2.0`` are sole
software licences. Apache License, Version 2.0 is ``apache-2.0``. Bare MIT
stays unknown. Licensed under the MIT License is ``mit``. ``uk_ogl`` is only
the British phrase Open Government Licence. Open Government License stays
unknown. ``us_government_work`` comes only from an explicit rights metadata
field.

A generic creativecommons.org/licenses or /licenses URL is not a deed. Visible
anchor text on it stays unknown, including a missing slash, http, www, or a
query string. Text elsewhere on the page still counts. A specific deed URL
still counts. Deceptive permissive anchor text on a restricted deed URL or a
public-domain mark URL stays unknown. A CC0 anchor on a public-domain mark URL
stays unknown. A photo credit, caption credit, or image credit that names
someone else's licence stays unknown, including ``Photo credit: UNDRR, CC
BY-NC-ND 2.0`` and ``Photo: UNDRR, CC BY-NC-ND 2.0``. When the page states its
own CC BY licence and a separate photo credit names another licence, the page
stays ``creative_commons_attribution``. Script, style, and comment text does
not count.

Publication dates only are kept. Modified, updated, and copyright years stay
unknown. The live URL is stored as confirmed; a different rel=canonical does
not replace it. This module does not fetch. It is not a belief collector, and
runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "sail_pages"
CATALOG_FILENAME = "sail_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Stanford Artificial Intelligence Laboratory"
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "ai.stanford.edu"
WWW_HOST = "www.ai.stanford.edu"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, WWW_HOST})
CATALOG_DESCRIPTION = (
    "Metadata for public Stanford Artificial Intelligence Laboratory research and news "
    "HTML on ai.stanford.edu and www.ai.stanford.edu. www.ai.stanford.edu does not "
    "resolve, so that host is empty. Each stored URL was one bounded GET that robots.txt "
    "allowed and returned HTML on ai.stanford.edu. Person profiles, login walls, "
    "PDFs, challenges, captchas, HTML robots.txt, and off-host redirects are omitted. "
    "Rows store title, publisher, canonical URL, date, and rights. Page text, abstracts, "
    "quotes, transcripts, PDFs, and chart data are not stored. creative_commons_attribution "
    "is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. A sole "
    "restricted deed keeps its token. Updated, modified, and "
    "copyright years are not publication dates. Not a belief collector. runner_wired is false."
)

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
MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

# Research is the research-groups page. News is /news and its articles. The
# SAIL research blog is /blog and its posts. Topic filters, pagination, and
# utility pages are not articles.
_BLOG_UTILITY = frozenset(
    {
        "about",
        "assets",
        "conferences",
        "feed.xml",
        "index.html",
        "ml",
        "nlp",
        "page",
        "rl",
        "robotics",
        "subscribe",
        "tos",
        "tos_stanford_blog",
        "vision",
    }
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_PASSWORD = re.compile(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "datepublished",
        "dc.date.issued",
        "dcterms.issued",
    }
)
_PUBLISHED_TYPES = frozenset(
    {
        "article",
        "blogposting",
        "newsarticle",
        "report",
        "scholarlyarticle",
        "webpage",
    }
)
_LICENSE_META = frozenset(
    {
        "dc.rights",
        "dcterms.license",
        "dcterms.licence",
        "dcterms.rights",
        "licence",
        "license",
    }
)
_RIGHTS_META = frozenset({"dc.rights", "dcterms.rights", "rights"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
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
    "errors.edgesuite.net",
    "akamaighost",
    "are you a robot",
    "are you human",
)
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
    ".txt",
    ".webp",
    ".xml",
    ".zip",
)
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "admin",
        "api",
        "auth",
        "author",
        "authors",
        "category",
        "cdn-cgi",
        "comments",
        "faculty",
        "feed",
        "log-in",
        "login",
        "page",
        "people",
        "person",
        "persons",
        "postdoctoral-fellows",
        "postdoctoralfellows",
        "profile",
        "profiles",
        "search",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "static",
        "tag",
        "users",
        "wp-admin",
        "wp-content",
        "wp-json",
        "wp-login",
        "wp-login.php",
    }
)
_SITE_SUFFIXES = (
    " | stanford artificial intelligence laboratory",
    " - stanford artificial intelligence laboratory",
    " | the stanford ai lab blog",
    " - the stanford ai lab blog",
    " | stanford ai lab",
    " - stanford ai lab",
    " | sail blog",
    " - sail blog",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
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
# Longer deeds are listed first. `(?!-)` keeps licenses/by from matching
# licenses/by-nc, and CC BY from matching CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-)"
    r"|publicdomain/(?P<pd>zero|mark)(?!-))"
    r"(?![a-z0-9])"
)
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    (
        "cc-by-nc-nd",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    (
        "cc-by-nc-sa",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    ("cc-by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)")),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    ("cc-by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "cc0",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("cc-by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b)")),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("pd-mark", re.compile(r"\bpublic domain mark\b")),
)
_PD_MARK = "pd-mark"
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_RESTRICTED_TOKEN = {
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
}
_MIT = re.compile(
    r"\bmit licen[cs]e\b"
    r"|\blicen[cs]ed under (?:the )?mit licen[cs]e\b"
    r"|\blicen[cs]ed under (?:the )?mit\b(?!-)"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,\s*version|\s+version|\s*,)?\s*2\.0\b"
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
_OGL_PHRASE = "open government licence"
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GENERIC_LICENSES_URL = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:[?#]\S*)?$"
)
# Photo, caption, and image credits name someone else's licence. ``Photo:``
# and ``Image:`` are the same kind of credit. A figcaption is a caption.
# ``© Name`` is someone else's copyright line; ``© 2024`` is a year.
_FIGURE = re.compile(r"(?is)<figure\b[^>]*>.*?</figure>")
_FIGCAPTION = re.compile(r"(?is)<figcaption\b[^>]*>.*?</figcaption>")
_CREDIT_PHRASE = re.compile(
    r"(?i)(?:"
    r"\b(?:photo|caption|image)[\s-]+credits?\b"
    r"|(?<![-\w])(?:photo|image|kuva)(?:\s+[a-z]{2,12}){0,4}\s*:"
    r"|\(\s*credit\s*:"
    r"|©(?!\s*\d)"
    r")"
)
_CREDIT_BLOCK_CLOSE = re.compile(
    r"(?is)</(?:p|figcaption|li|caption|figure|blockquote|dd|div)\s*>"
)
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_PUBLISHED_PROSE = re.compile(
    r"(?<!last )(?<!updated )(?<!modified )(?<!copyright )"
    r"\b(?:publication date|date published|published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})"
    r"|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"
    r"|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
    re.I,
)


class CatalogError(ValueError):
    """A catalog row or page failed the SAIL page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for ai.stanford.edu and www.ai.stanford.edu."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_catalog_path(path: str) -> bool:
    """True for research-groups, news, or SAIL research-blog HTML.

    Person profiles, pagination, topic filters, login paths, and downloads
    are not catalog paths. Path case is preserved because the blog serves
    mixed-case slugs.
    """

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    bare = path[:-1] if path.endswith("/") and path != "/" else path
    if bare.lower().endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in bare.split("/") if part]
    if not parts:
        return False
    lowered = [part.casefold() for part in parts]
    if any(part in _BLOCKED_PARTS for part in lowered):
        return False
    if not all(_SEGMENT.fullmatch(part) for part in parts):
        return False
    if lowered == ["research-groups"]:
        return True
    if lowered[0] == "news" and len(parts) <= 2:
        return True
    if lowered[0] == "blog" and len(parts) == 1:
        return True
    if lowered[0] == "blog" and len(parts) == 2 and lowered[1] not in _BLOG_UTILITY:
        return True
    return False


def rows_for_unresolved_host(hostname: str) -> list[dict]:
    """A host that does not resolve stores no rows.

    ``hostname`` may be an official host. DNS failure is not a page.
    """

    if not isinstance(hostname, str):
        return []
    return []


def robots_allows(body: str, path: str) -> bool:
    """True when the * group does not disallow path.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or "<!doctype html" in sample:
        return False
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
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
    """True when the response is an interstitial rather than the page."""

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
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
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
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> dict | None:
    """Return metadata when one response is a confirmed on-host SAIL page."""

    target = final_url or page_url
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
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> list[dict]:
    """Return catalog rows for one response.

    A Cloudflare challenge, a captcha, an authentication wall, a non-HTML
    shell, a robots disallow, or an off-host redirect records no row.
    """

    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        robots_txt=robots_txt,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is
    CC0, CC BY-SA, or a permissive mix of CC0, CC BY, and CC BY-SA. A sole
    restricted deed keeps its token. Two different restricted deeds stay
    unknown. A software licence beside any Creative Commons deed stays
    unknown. Anchor text on a generic creativecommons.org/licenses URL does
    not count. A photo, caption, or image credit, including a ``Photo:``
    credit, does not count. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, government = _rights_signals(page_text)
    if _PD_MARK in cc_codes:
        return RIGHTS_UNKNOWN
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    families = [
        family
        for family in (
            restricted,
            permissive,
            software,
            {"uk_ogl"} if ogl else set(),
            {RIGHTS_US_GOVERNMENT_WORK} if government else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive == {"cc-by"}:
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, dateModified, a last-updated line, and a copyright
    year are not publication dates. A date inside script prose, style, or a
    comment does not count. One page publication date from metadata is kept
    when the body mentions another work's publication date. Several metadata
    publication dates stay unknown. With no metadata, several prose
    publication dates stay unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")

    def collect(values: list[str]) -> list[str]:
        found: list[str] = []
        for raw in values:
            parsed = _iso_day(raw)
            if parsed and parsed not in found:
                found.append(parsed)
        return found

    visible = _visible(page_html)
    metadata = collect(_jsonld_published_dates(page_html) + _published_meta_values(visible))
    if len(metadata) == 1:
        return metadata[0]
    if len(metadata) > 1:
        return UNKNOWN_DATE
    prose = collect(_published_prose_dates(_plain(visible)))
    if len(prose) == 1:
        return prose[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the laboratory when the page names SAIL or the laboratory."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if _names_sail(metas.get(key, "")):
            return PUBLISHER
    if _names_sail(_plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it.
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


def build_catalog(entries: list[dict]) -> dict:
    """Validate and order metadata rows. An empty list is a valid catalog."""

    ordered = sorted(entries, key=lambda entry: (_sort_date(entry["date"]), entry["canonical_url"]))
    document = {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": RUNNER_WIRED,
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
        raise CatalogError("description must match the SAIL catalog contract")
    if len(CATALOG_DESCRIPTION) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "runner_wired is false" not in CATALOG_DESCRIPTION:
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
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public SAIL page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or parsed.netloc != host
        or not is_official_host(host)
        or not is_catalog_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public SAIL page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    cc_codes: set[str] = set()
    software: set[str] = set()
    government = False
    for license_text, rights_text in _jsonld_rights(page_text):
        cc_codes |= _cc_codes(license_text)
        software |= _software_codes(license_text)
        cc_codes |= _cc_codes(rights_text)
        software |= _software_codes(rights_text)
        if _states_us_government_work(rights_text):
            government = True
    visible = _drop_credit_clauses(_visible(page_text))
    metas = _metas(visible)
    for key, value in metas.items():
        if key in _LICENSE_META or key in _RIGHTS_META:
            cc_codes |= _cc_codes(value)
            software |= _software_codes(value)
        if key in _RIGHTS_META and _states_us_government_work(value):
            government = True
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(visible):
        if not _is_rights_element(attrs):
            continue
        text = _plain(body)
        if text and len(text) <= MAX_FIELD_CHARS and _states_us_government_work(text):
            government = True
    plain_html = _without_generic_license_anchor_text(visible)
    plain = _plain(plain_html)
    cc_codes |= _cc_codes(plain)
    software |= _software_codes(plain)
    for href in _hrefs(visible):
        if _is_generic_cc_licenses_url(href):
            continue
        cc_codes |= _cc_codes(href)
        software |= _software_codes(href)
    ogl = _OGL_PHRASE in plain.casefold()
    return cc_codes, software, ogl, government


def _drop_credit_clauses(page_html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names.

    ``Photo: UNDRR, CC BY-NC-ND 2.0`` is a photo credit. A figure or
    figcaption is a caption. ``Image:`` and Finnish ``Kuva:`` are image
    credits. Text before the credit in the same element still counts.
    """

    normalized = (
        page_html.replace("&nbsp;", " ")
        .replace("&#160;", " ")
        .replace("\xa0", " ")
        .replace("&copy;", "©")
        .replace("&#169;", "©")
    )
    normalized = _FIGURE.sub(" ", normalized)
    normalized = _FIGCAPTION.sub(" ", normalized)
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(normalized):
        close = _CREDIT_BLOCK_CLOSE.search(normalized[match.end() : match.end() + 1200])
        end = match.end() + close.end() if close is not None else min(len(normalized), match.end() + 500)
        spans.append((match.start(), end))
    if not spans:
        return normalized
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
        pieces.append(normalized[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(normalized[cursor:])
    return "".join(pieces)


def _without_generic_license_anchor_text(page_html: str) -> str:
    """Drop anchors whose URL is the generic Creative Commons licences page.

    The anchor text is not a deed. A specific /licenses/by/4.0/ URL is kept.
    Text outside the anchor still counts.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    folded = _fold(href).split()
    if not folded:
        return False
    return _GENERIC_LICENSES_URL.fullmatch(folded[0]) is not None


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
        elif match.group("pd") == "mark":
            codes.add(_PD_MARK)
    for name, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(name)
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


def _jsonld_rights(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        license_text = ""
        rights_text = ""
        for key, value in node.items():
            folded = str(key).casefold()
            if folded in {"license", "licence"} and isinstance(value, str):
                license_text = value
            elif folded == "rights" and isinstance(value, str):
                rights_text = value
            elif isinstance(value, (dict, list)):
                walk(value)
        if license_text or rights_text:
            found.append((license_text, rights_text))

    for blob in _LDJSON.findall(page_html):
        try:
            walk(json.loads(blob))
        except json.JSONDecodeError:
            continue
    return found


def _jsonld_published_dates(page_html: str) -> list[str]:
    found: list[str] = []

    def add(raw: object) -> None:
        parsed = _iso_day(raw) if isinstance(raw, str) else None
        if parsed and parsed not in found:
            found.append(parsed)

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        types = node.get("@type")
        names: set[str] = set()
        if isinstance(types, str):
            names.add(types.casefold())
        elif isinstance(types, list):
            names.update(item.casefold() for item in types if isinstance(item, str))
        if names & _PUBLISHED_TYPES:
            add(node.get("datePublished"))
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for blob in _LDJSON.findall(page_html):
        try:
            walk(json.loads(blob))
        except json.JSONDecodeError:
            continue
    return found


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
    return is_official_host(parsed.hostname or "")


def _blocked_headers(headers: dict[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name in {"sg-captcha", "www-authenticate"}:
            return True
        if "sg-captcha" in token or "sgcaptcha" in token:
            return True
    return False


def _published_meta_values(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key in _PUBLISHED_META and attrs.get("content"):
            found.append(attrs["content"])
    return found


def _published_prose_dates(plain: str) -> list[str]:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        if match.group(1):
            parsed = _iso_day(match.group(1))
        elif match.group(4):
            parsed = _month_day(match.group(2), match.group(3), match.group(4))
        else:
            parsed = _month_day(match.group(6), match.group(5), match.group(7))
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def _names_sail(value: str) -> bool:
    folded = _fold(value)
    if "stanford artificial intelligence laboratory" in folded:
        return True
    if "stanford ai lab" in folded:
        return True
    return re.search(r"\bsail\b", folded) is not None


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    changed = True
    while changed and text:
        changed = False
        folded = text.translate(_DASHES).casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip(" -|–—")
                changed = True
                break
    if not text or text.casefold() in {
        "sail",
        "sail blog",
        "stanford ai lab",
        "the stanford ai lab blog",
        PUBLISHER.casefold(),
    }:
        return ""
    if len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
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


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)


def _month_day(month: str, day: str, year: str) -> str | None:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        return date(int(year), month_number, int(day)).isoformat()
    except ValueError:
        return None


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs, _body in _ANCHOR.findall(page_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if href:
            found.append(href)
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False
