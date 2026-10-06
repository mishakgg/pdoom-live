"""Metadata catalog of public NVIDIA artificial intelligence research pages.

Hosts are research.nvidia.com and the research blog on blogs.nvidia.com.
research.nvidia.com/ redirects to www.nvidia.com and is not stored. Person
profiles, PDFs, product marketing, login walls, and off-host redirects are
omitted. A Cloudflare challenge, a captcha, or an authentication wall is not
stored. Each stored URL was confirmed with one bounded GET that stayed on an
official host. robots.txt allows those paths.

A row keeps the title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, chart data, and PDFs are
not stored. The live URL is stored as confirmed. A different rel=canonical
does not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` means CC BY alone, including
https://creativecommons.org/licenses/by/4.0/. ``creative_commons`` means CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``,
or ``cc_by_nc_nd``. A hyphen is a word boundary, so CC BY does not match CC
BY-NC and licenses/by does not match licenses/by-nc. Two different restricted
deeds stay unknown. A permissive anchor on a restricted deed URL or on a
public-domain mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL
stays unknown. A generic https://creativecommons.org/licenses/ URL stays
unknown, including a missing slash, http, a www host, and a query string.
Anchor text on that generic URL stays unknown. A specific deed URL still
counts. A software licence beside any Creative Commons deed stays unknown.
Two software licences stay unknown. A sole MIT License is mit. A sole MPL-2.0
is mpl-2.0. Apache License, Version 2.0 is apache-2.0. A photo credit, caption
credit, or image credit that names someone else's licence stays unknown,
including "Photo credit: UNDRR, CC BY-NC-ND 2.0" and "Photo: UNDRR, CC
BY-NC-ND 2.0". ``uk_ogl`` requires the exact British phrase Open Government
Licence. Open Government License stays unknown. ``us_government_work`` comes
only from an explicit rights metadata field. Script, style, and comment text
does not count.

Publication dates only. Updated, modified, and copyright years stay unknown.
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

CATALOG_ID = "nvidia_ai_pages"
CATALOG_FILENAME = "nvidia_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "NVIDIA"
OFFICIAL_HOSTS = frozenset({"research.nvidia.com", "blogs.nvidia.com"})
RESEARCH_HOST = "research.nvidia.com"
BLOG_HOST = "blogs.nvidia.com"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
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
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
AI_RESEARCH_AREAS = frozenset(
    {
        "computer-vision",
        "generative-ai",
        "machine-learning-artificial-intelligence",
        "machine-translation",
        "natural-language-processing",
        "physical-ai",
        "robotics",
        "speech-processing",
        "world-simulation",
    }
)
AI_LABS = frozenset(
    {
        "adlr",
        "amri",
        "av-applied-research",
        "conv-ai",
        "cosmos-lab",
        "dair",
        "eai",
        "gear",
        "genair",
        "lpr",
        "nemotron",
        "sil",
        "toronto-ai",
    }
)
# The research host root leaves research.nvidia.com. It contributes no row.
OFF_HOST_ROOT = "https://research.nvidia.com/"
OGL_PHRASE = "open government licence"
MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public NVIDIA AI and machine learning research pages on research.nvidia.com "
    "and blogs.nvidia.com/blog/category/nvidia-research/. Publisher is NVIDIA. "
    "Each row is one bounded GET of HTML that stayed on those hosts. "
    "robots.txt disallows /admin/, /user/login, /search/, /core/, /profiles/, and blog page queries. "
    "research.nvidia.com/ redirects off host and is not stored. "
    "Person profiles, PDFs, product marketing, login walls, and off-host redirects are omitted. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "A missing date stays unknown. Updated and copyright years are not publication dates. "
    "Not a belief collector. runner_wired is false."
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
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "admin",
        "author",
        "authors",
        "cdn-cgi",
        "feed",
        "login",
        "people",
        "person",
        "profiles",
        "search",
        "sign-in",
        "signin",
        "user",
        "wp-admin",
        "wp-content",
        "wp-includes",
        "wp-json",
        "wp-login.php",
    }
)
_LAB_SKIP = frozenset(
    {
        "about",
        "author",
        "authors",
        "feed",
        "page",
        "people",
        "person",
        "projects",
        "publications",
        "tag",
        "tags",
    }
)
_PROJECT_ROOTS = frozenset({"neuralfields", "nglod", "sdf-explorer", "vbnf"})
_PRODUCT_BITS = ("dlss", "geforce", "/gaming", "/shop", "/store", "/buy/")
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
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
    ".txt",
    ".webp",
    ".xml",
    ".zip",
)
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
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PUB_SLUG = re.compile(r"_*[A-Za-z0-9][A-Za-z0-9_-]*")
_LAB_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_BLOG_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_PASSWORD = re.compile(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_PUB_TIME = re.compile(
    r"(?is)field-publication-date\b.{0,800}?<time\b[^>]*\bdatetime\s*=\s*[\"']([^\"']+)[\"']"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_GENERIC_LICENSES_URL = re.compile(
    r"(?i)^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:[?#]\S*)?$"
)
_MARK_URL = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
# Photo, caption, and image credits name someone else's licence. "Photo:" does too.
_CREDIT_CLAUSE = re.compile(
    r"(?is)(?:"
    r"\b(?:photo|caption|image)[\s-]+credits?\b"
    r"|\bphoto\s*:"
    r")"
    r"(?:[^<.]|<[^>]*>|\.(?=\d))*?"
    r"(?:\.(?=\s|<|$)|(?=</(?:p|figcaption|li|div|span|caption|td|dd|footer|figure|h[1-6])\b)|$)"
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dcterms.created",
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_SITE_SUFFIXES = (
    " | nvidia blog",
    " - nvidia blog",
    " – nvidia blog",
    " — nvidia blog",
    " | nvidia research",
    " - nvidia research",
    " | research",
    " - research",
    " | nvidia",
    " - nvidia",
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
# Longer deeds are listed first. `(?!-)` makes a hyphen a word boundary, so
# licenses/by and CC BY do not match licenses/by-nc or CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-))"
    r"(?![a-z0-9-])"
)
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("cc-by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)")),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("cc-by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("cc-by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    (
        "cc0",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    (
        "cc-by",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b)"),
    ),
    ("pd-mark", re.compile(r"\bpublic domain mark\b")),
)
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_RESTRICTED_TOKEN = {
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
}
_MIT = re.compile(
    r"(?<!modified )(?:"
    r"\bmit licen[cs]e\b"
    r"|\blicen[cs]ed under (?:the )?mit\b(?!-)"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
    r")"
)
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
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
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_WEEKDAY = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+"
_PUBLISHED_PROSE = re.compile(
    r"(?i)(?<!last )(?<!updated )(?<!modified )(?<!copyright )"
    r"\b(?:publication date|date published|published|posted)\b(?:\s+on)?\s*:?\s*"
    rf"(?:{_WEEKDAY})?"
    r"(?:(\d{4}-\d{2}-\d{2})"
    r"|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"
    r"|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))"
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


class CatalogError(ValueError):
    """A catalog row or page failed the NVIDIA AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for research.nvidia.com and blogs.nvidia.com."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def robots_allows(body: str, path: str) -> bool:
    """True when the * groups do not disallow path.

    ``path`` may include a query string. A challenge page or an HTML document
    served in place of robots.txt does not allow a fetch. ``*`` is a wildcard
    and ``$`` anchors the end. ``[?&]`` matches a question mark or ampersand,
    which is how the blog robots file writes query-parameter rules.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    rules = _star_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    best_len = -1
    best_kind = "allow"
    for kind, pattern in rules:
        if not pattern or not _rule_matches(pattern, target):
            continue
        length = len(pattern)
        if length > best_len or (length == best_len and kind == "allow"):
            best_len = length
            best_kind = kind
    if best_len < 0:
        return True
    return best_kind == "allow"


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

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
    headers: Mapping[str, str] | None = None,
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
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> dict | None:
    """Return metadata when one bounded GET confirmed an on-host AI research page.

    A challenge, a captcha, an HTTP error, a robots disallow, a non-HTML body,
    a login wall, or an off-host redirect is not stored.
    """

    target = final_url or page_url
    if robots_txt is not None and not _robots_allow_url(robots_txt, target):
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
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> list[dict]:
    """Return catalog rows for one response. A blocked path contributes none."""

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

    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
    mix of those is creative_commons. A sole restricted deed keeps its token.
    Mixed families, two restricted deeds, and two software licences stay
    unknown. A generic creativecommons.org/licenses URL is not a deed. A photo
    credit, caption credit, image credit, or "Photo:" credit stays unknown.
    Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, gov = _rights_signals(page_text)
    if "pd-mark" in cc_codes:
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
            {"us_government_work"} if gov else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive & {"cc0", "cc-by-sa"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated times, modified times, and copyright years are not publication dates.
    A date inside script, style, or comment text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    field = _PUB_TIME.search(visible)
    if field:
        parsed = _iso_day(field.group(1))
        if parsed:
            return parsed
    return _published_prose(_plain(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title and title.casefold() != PUBLISHER.casefold():
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
    """Return NVIDIA when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if _names_nvidia(metas.get(key, "")):
            return PUBLISHER
    if _names_nvidia(_plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed NVIDIA AI research page.

    The record does not include the document text. ``page_url`` is the live
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


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    if document.get("description") != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the NVIDIA AI catalog contract")
    if len(CATALOG_DESCRIPTION) > MAX_DESCRIPTION_CHARS:
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
    _require_text(entry.get("title"), "title")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError(f"canonical URL must be a public NVIDIA AI research page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != host
        or host not in OFFICIAL_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
        or hostname_is_blocked(host)
        or not _is_ai_research_path(host, path)
    ):
        raise CatalogError(f"canonical URL must be a public NVIDIA AI research page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    visible = _drop_generic_license_anchors(_drop_mark_anchors(_drop_credit_clauses(_visible(page_text))))
    cc_codes: set[str] = set()
    software: set[str] = set()
    gov = False
    for key, value in _metas(visible).items():
        if key in _LICENSE_META or key in _RIGHTS_META:
            cc_codes |= _cc_codes(value)
            software |= _software_codes(value)
        if key in _RIGHTS_META and _states_us_government_work(value):
            gov = True
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(visible):
        if not _is_rights_element(attrs):
            continue
        text = _plain(body)
        if text and len(text) <= MAX_FIELD_CHARS and _states_us_government_work(text):
            gov = True
    plain = _plain(visible)
    cc_codes |= _cc_codes(plain)
    software |= _software_codes(plain)
    for href in _hrefs(visible):
        cc_codes |= _cc_codes(href)
        software |= _software_codes(href)
    ogl = OGL_PHRASE in plain.casefold()
    return cc_codes, software, ogl, gov


def _drop_credit_clauses(page_html: str) -> str:
    """Remove photo, caption, and image credits, including a Photo: credit."""

    normalized = page_html.replace("&nbsp;", " ").replace("&#160;", " ").replace("\xa0", " ")
    return _CREDIT_CLAUSE.sub(" ", normalized)


def _drop_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _MARK_URL.search(_fold(href)):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _drop_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose URL is only the Creative Commons licences index."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _GENERIC_LICENSES_URL.fullmatch(_fold(href).strip()):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


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
            codes.add("pd-mark")
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
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


def _is_ai_research_path(host: str, path: str) -> bool:
    if ".." in path or "\\" in path or "//" in path:
        return False
    lowered_path = path.casefold()
    if any(bit in lowered_path for bit in _PRODUCT_BITS):
        return False
    if lowered_path.endswith(_DOWNLOAD_SUFFIXES):
        return False
    raw = path[:-1] if path.endswith("/") and len(path) > 1 else path
    parts = [part for part in raw.split("/") if part]
    if not parts:
        return False
    lowered = [part.casefold() for part in parts]
    if any(part in _BLOCKED_PARTS for part in lowered):
        return False
    if host == RESEARCH_HOST:
        return _research_path(parts, lowered)
    if host == BLOG_HOST:
        return _blog_path(parts, lowered)
    return False


def _research_path(parts: list[str], lowered: list[str]) -> bool:
    if lowered[0] == "publication" and len(parts) == 2 and _PUB_SLUG.fullmatch(parts[1]):
        return True
    if lowered[0] == "research-area" and len(parts) == 2 and lowered[1] in AI_RESEARCH_AREAS:
        return True
    if lowered[0] == "labs" and len(parts) in {2, 3} and lowered[1] in AI_LABS:
        if len(parts) == 2:
            return True
        if lowered[2] in _LAB_SKIP:
            return False
        return _LAB_SLUG.fullmatch(parts[2]) is not None
    if lowered[0] == "ai-security" and 1 <= len(parts) <= 2:
        return all(part == "ai-security" or _PUB_SLUG.fullmatch(part) for part in parts)
    if lowered[0] == "benchmarks" and 1 <= len(parts) <= 2:
        return all(_BLOG_SLUG.fullmatch(part) for part in lowered)
    return len(parts) == 1 and lowered[0] in _PROJECT_ROOTS


def _blog_path(parts: list[str], lowered: list[str]) -> bool:
    if lowered[0] != "blog" or len(parts) < 2:
        return False
    if lowered[1] == "category":
        if len(parts) == 3 and lowered[2] == "nvidia-research":
            return True
        return (
            len(parts) == 5
            and lowered[2] == "nvidia-research"
            and lowered[3] == "page"
            and parts[4].isdigit()
            and parts[4] != "0"
        )
    if len(parts) != 2 or lowered[1] in _BLOCKED_PARTS or lowered[1] == "category":
        return False
    return _BLOG_SLUG.fullmatch(parts[1]) is not None


def _robots_allow_url(robots_txt: str, url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return robots_allows(robots_txt, path)


def _rule_matches(pattern: str, path: str) -> bool:
    return _rule_regex(pattern).search(path) is not None


def _rule_regex(pattern: str) -> re.Pattern[str]:
    pieces: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            pieces.append(".*")
            index += 1
            continue
        if char == "$" and index == len(pattern) - 1:
            pieces.append("$")
            index += 1
            continue
        if char == "[":
            end = pattern.find("]", index + 1)
            if end > index + 1:
                pieces.append(_character_class(pattern[index + 1 : end]))
                index = end + 1
                continue
        pieces.append(re.escape(char))
        index += 1
    if not pattern.endswith("$"):
        pieces.append(".*")
    return re.compile("^" + "".join(pieces))


def _character_class(chars: str) -> str:
    body = chars.replace("\\", "\\\\").replace("]", "\\]")
    if body.startswith("^"):
        body = "\\" + body
    if "-" in body[1:]:
        body = body.replace("-", "") + "-"
    return "[" + body + "]"


def _star_rules(body: str) -> list[tuple[str, str]] | None:
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
    selected: list[tuple[str, str]] = []
    saw_star = False
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            saw_star = True
            selected.extend(group_rules)
    if not saw_star:
        return None
    return selected


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and is_official_host(parsed.hostname or "")


def _blocked_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name == "sg-captcha" or "sg-captcha" in token:
            return True
    return False


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    if match.group(1):
        return _iso_day(match.group(1)) or UNKNOWN_DATE
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4)) or UNKNOWN_DATE
    return _calendar_date(match.group(6), match.group(5), match.group(7)) or UNKNOWN_DATE


def _names_nvidia(value: str) -> bool:
    return re.search(r"\bnvidia\b", _clean_text(value).casefold()) is not None


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
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


def _iso_day(value: object) -> str | None:
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


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for match in _HREF.finditer(page_html):
        href = unescape(match.group(1) or match.group(2) or match.group(3) or "").strip()
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


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False
