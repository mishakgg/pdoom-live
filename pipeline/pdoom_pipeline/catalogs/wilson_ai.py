"""Metadata catalog of public Wilson Center pages about artificial intelligence.

Hosts are www.wilsoncenter.org and wilsoncenter.org. wilsoncenter.org redirects
to www.wilsoncenter.org. A row is stored only when one bounded GET returns
HTML that stays on those hosts. Pages are limited to artificial intelligence,
machine learning, and AI policy. Other issues, person pages, login walls, and
downloads are omitted.

robots.txt allows the public site and disallows Drupal admin paths, /search/,
/user/login, and any URL whose query string contains '='. A robots disallow
is not fetched. Sitemap page queries and listing pagers use that query form,
so they are not fetched. An HTML document or a challenge page served in place
of robots.txt does not allow a fetch. A Cloudflare challenge, a captcha, an
authentication wall, a non-HTML shell, or a redirect off these hosts stores
no row.

Each row keeps the title, publisher, canonical URL, date, and rights label.
Page text, abstracts, quotes, transcripts, PDFs, and chart data are not
stored. Publisher is Wilson Center. The live URL is stored as confirmed. A
different rel=canonical does not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone, including a specific
/licenses/by/4.0/ URL. ``creative_commons`` is CC0, CC BY-SA, or a permissive
mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps
``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``, or ``cc_by_nc_nd``. Two different
restricted deeds stay unknown. A software licence beside any Creative Commons
deed stays unknown. Two software licences stay unknown. ``mit``,
``apache-2.0``, and ``mpl-2.0`` are sole software licences. Apache License,
Version 2.0 is ``apache-2.0``. Bare MIT stays unknown. Licensed under the MIT
License is ``mit``. ``uk_ogl`` is only the British phrase Open Government
Licence. American spelling License stays unknown. ``us_government_work``
comes only from an explicit rights metadata field.

A generic creativecommons.org/licenses or /licenses URL is not a deed.
Anchor text on it stays unknown, including a missing slash, http, a www host,
and a query string. Text elsewhere on the page still counts. A specific deed
URL still counts. Deceptive permissive anchor text on a restricted deed URL
or a public-domain mark URL stays unknown. A CC0 anchor on a public-domain
mark URL stays unknown. A photo credit, caption credit, or image credit that
names someone else's licence stays unknown, including "Photo credit: UNDRR,
CC BY-NC-ND 2.0" and "Photo: UNDRR, CC BY-NC-ND 2.0". A page licence stated
outside that credit still counts.

Publication dates only are kept. A posted time on the article is a
publication date. Modified, updated, and copyright years stay unknown.
Script, style, and comment text does not count. This module does not fetch.
It is not a belief collector, and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "wilson_ai_pages"
CATALOG_FILENAME = "wilson_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Wilson Center"
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"www.wilsoncenter.org", "wilsoncenter.org"})
CATALOG_DESCRIPTION = (
    "Public Wilson Center AI, machine-learning, and AI-policy pages. "
    "Hosts are www.wilsoncenter.org and wilsoncenter.org. "
    "Each stored URL was one bounded GET of HTML on those hosts. "
    "robots.txt disallows /admin/, /search/, /user/login, and query-string URLs. "
    "Sitemap queries were not fetched. "
    "Challenges, captchas, login walls, and off-host redirects are omitted. "
    "Rows store title, publisher, canonical URL, date, and rights. "
    "Page text, abstracts, PDFs, quotes, and transcripts are not stored. "
    "Publisher is Wilson Center. creative_commons_attribution is CC BY alone. "
    "creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "uk_ogl is the British Open Government Licence. "
    "Missing dates stay unknown. Updated, modified, and copyright years are not dates. "
    "Not a belief collector. runner_wired is false."
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
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_PUBLISHED_TYPES = frozenset(
    {
        "aboutpage",
        "article",
        "blogposting",
        "collectionpage",
        "newsarticle",
        "report",
        "scholarlyarticle",
        "webpage",
    }
)
_RIGHTS_META = frozenset(
    {
        "dc.rights",
        "dcterms.license",
        "dcterms.licence",
        "dcterms.rights",
        "licence",
        "license",
        "rights",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "performing security verification",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "cf-mitigated",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "akamaighost",
    "errors.edgesuite.net",
    "hcaptcha",
    "g-recaptcha",
    "are you a robot",
    "are you human",
)
_CHALLENGE_TITLES = (
    "just a moment",
    "attention required",
    "checking your browser",
    "access denied",
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
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "admin",
        "auth",
        "cdn-cgi",
        "comment",
        "core",
        "donate",
        "donation",
        "log-in",
        "login",
        "profiles",
        "search",
        "sign-in",
        "signin",
        "user",
        "wp-admin",
        "wp-login.php",
    }
)
_INSIGHT_TYPES = (
    "article",
    "audio",
    "blog-post",
    "book",
    "event",
    "events",
    "podcast",
    "publication",
    "report",
    "video",
)
_INSIGHT_PATH = re.compile(
    r"^/(?:" + "|".join(re.escape(kind) for kind in _INSIGHT_TYPES) + r")/[a-z0-9-]+$"
)
_AI_ISSUE_PATHS = frozenset({"/issue/artificial-intelligence", "/issue/machine-learning"})
_AI_TOKENS = frozenset({"ai", "ais", "genai", "chatgpt", "llm", "llms", "deepfake", "deepfakes"})
_AI_PHRASES = (
    "artificial-intelligence",
    "machine-learning",
    "deep-learning",
    "generative-ai",
    "ai-policy",
    "ai-governance",
    "ai-safety",
    "inteligencia-artificial",
    "large-language",
)
_SITE_SUFFIXES = (
    " | the wilson center",
    " - the wilson center",
    " – the wilson center",
    " — the wilson center",
    " | wilson center",
    " - wilson center",
    " – wilson center",
    " — wilson center",
)
_BANNER_PREFIX = "explore more than 27,000 insights"
_MONTHS = {
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
_PUBLISHED_ISO = re.compile(r"(?i)(?<![a-z])published\s*:\s*(\d{4}-\d{2}-\d{2})\b")
_PUBLISHED_MONTH = re.compile(
    r"(?i)(?<![a-z])published\s*:\s*"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+(\d{1,2}),\s+(\d{4})\b"
)
_ARTICLE_META_CHUNK = re.compile(
    r'(?is)<div\b[^>]*\bclass="[^"]*\barticle-meta\b[^"]*"[^>]*>(.{0,3000})'
)
_PUBLISHED_INFO = re.compile(
    r'(?is)<div\b[^>]*\bclass="[^"]*\bpublished-info\b[^"]*"[^>]*>'
)
_POSTED_TIME = re.compile(
    r'(?is)posted date/time:.{0,500}?<time\b[^>]*\bdatetime\s*=\s*["\']([^"\']+)["\']'
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
# Longer deeds are listed first. (?![-a-z0-9]) keeps licenses/by from matching
# licenses/by-nc, and the text patterns refuse a following NC, ND, or SA.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![-a-z0-9])"
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
    ("cc-by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)")),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_PD_MARK = re.compile(r"public domain mark\b")
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
    r"|\bmozilla public licen[cs]e(?:\s*2\.0)?\b"
)
_OGL_PHRASE = "open government licence"
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_HREF_ATTR = re.compile(
    r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# A deed path such as /licenses/by/4.0/ is not generic. Optional slash, query,
# http, and a www host still leave the URL generic.
_GENERIC_CC_LICENSES = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:\?[^#]*)?(?:#.*)?$"
)
# Photo, caption, and image credits name someone else's licence. "Photo:" is
# the same kind of credit as "Photo credit:". A parenthetical "(Credit: ...)"
# on a figure is too.
_CREDIT_PHRASE = re.compile(
    r"(?i)(?:\b(?:photo|caption|image)\s+credits?\b"
    r"|\b(?:photo|caption|image)\s*:"
    r"|\(\s*credit\s*:)"
)
_CREDIT_BLOCK_CLOSE = re.compile(
    r"(?is)</(?:p|figcaption|li|caption|figure|blockquote|dd|div)\s*>"
)
_TAG_ANCHOR = re.compile(r"(?is)<a\b([^>]*\btags-item\b[^>]*)>(.*?)</a>")
_TITLE_AI = re.compile(
    r"(?i)\b(?:artificial intelligence|machine learning|deep learning|generative ai|"
    r"ai policy|ai governance|ai safety|inteligencia artificial|large language models?|"
    r"deepfakes?)\b|(?<![A-Za-z])AI(?![A-Za-z])"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Wilson Center page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for www.wilsoncenter.org and wilsoncenter.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_catalog_path(path: str) -> bool:
    """True for an on-site HTML path the catalog is allowed to store.

    Insight URLs still have to be about artificial intelligence, machine
    learning, or AI policy. ``page_is_about_ai`` applies that check.
    """

    bare = _bare_path(path)
    if bare is None:
        return False
    parts = [part for part in bare.split("/") if part]
    if any(part in _BLOCKED_PARTS for part in parts):
        return False
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if bare in _AI_ISSUE_PATHS:
        return True
    if bare.startswith("/collection/") or bare.startswith("/program/"):
        slug = parts[-1] if parts else ""
        return _slug_is_ai(slug)
    return _INSIGHT_PATH.fullmatch(bare) is not None


def page_is_about_ai(page_html: str, path: str) -> bool:
    """True when the page is an AI, machine-learning, or AI-policy page."""

    if not isinstance(page_html, str):
        return False
    bare = _bare_path(path) or ""
    if bare in _AI_ISSUE_PATHS or _slug_is_ai(bare.rsplit("/", 1)[-1]):
        return True
    if _has_ai_topic_tag(page_html):
        return True
    try:
        title = title_from_page(page_html)
    except CatalogError:
        return False
    return _TITLE_AI.search(title) is not None


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows ``path``.

    ``path`` may include a query string. A challenge or captcha in place of
    robots.txt does not allow a fetch. An HTML document served in place of
    robots.txt does not allow a fetch. The longest matching Allow or Disallow
    wins. An empty Disallow does not block the path.
    """

    if not isinstance(body, str) or not isinstance(path, str):
        return False
    sample = body[:4000]
    folded = sample.casefold()
    stripped = folded.lstrip()
    if (
        stripped.startswith("<!doctype html")
        or stripped.startswith("<html")
        or "<html" in folded[:800]
    ):
        return False
    if any(marker in folded for marker in _CHALLENGE_MARKERS):
        return False
    if any(marker in folded for marker in _CHALLENGE_TITLES):
        return False
    rules = _star_rules(body)
    if rules is None:
        return True
    target = path or "/"
    best = -1
    allowed = True
    matched = False
    for kind, pattern in rules:
        if not pattern or not _rule_matches(pattern, target):
            continue
        length = len(pattern)
        if length > best or (length == best and kind == "allow"):
            best = length
            allowed = kind == "allow"
            matched = True
    if not matched:
        return True
    return allowed


def robots_path_allowed(url: str, robots_txt: str | None = None) -> bool:
    """A missing robots document does not block. A disallow blocks the URL."""

    if not _on_official_host(url):
        return False
    if robots_txt is None:
        return True
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return robots_allows(robots_txt, path)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page.

    A phrase such as "just a moment" inside the article body is not a challenge.
    """

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:6000]
    title = _TITLE.search(head)
    if title and any(marker in title.group(1).casefold() for marker in _CHALLENGE_TITLES):
        return True
    folded = head.casefold()
    return any(marker in folded for marker in _CHALLENGE_MARKERS)


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
    lowered = page_html[:12000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name in {"sg-captcha", "www-authenticate"}:
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
    """Return metadata when the response is a confirmed on-host AI page."""

    target = final_url or page_url
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=target,
    ):
        return None
    if robots_txt is not None and not robots_path_allowed(target, robots_txt):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is
    CC0, CC BY-SA, or a permissive mix of CC0, CC BY, and CC BY-SA. A sole
    restricted deed keeps its token. Two different restricted deeds stay
    unknown. A software licence beside any Creative Commons deed stays
    unknown. Anchor text on a generic creativecommons.org/licenses URL does
    not count. A photo, caption, or image credit, including a "Photo:" credit,
    does not count. Script, style, and comment text does not count.
    ``us_government_work`` comes only from a rights metadata field.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl = _rights_signals(page_text)
    if "pd-mark" in cc_codes:
        return RIGHTS_UNKNOWN
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    government = _us_government_work(page_text)
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

    article:modified_time, og:updated_time, a last-updated line, and a
    copyright year are not publication dates. A posted time in the article
    header is a publication date. Related-card times are not. A date inside
    script prose, style, or a comment does not count. A JSON-LD datePublished
    on the page itself does.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found: list[str] = []

    def add(raw: object) -> None:
        parsed = _iso_day(raw) if isinstance(raw, str) else None
        if parsed and parsed not in found:
            found.append(parsed)

    for parsed in _jsonld_published_dates(page_html):
        add(parsed)
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        add(metas.get(key, ""))
    add(_posted_time(visible))
    plain = _plain(visible).casefold()
    iso = _PUBLISHED_ISO.search(plain)
    if iso:
        add(iso.group(1))
    month = _PUBLISHED_MONTH.search(plain)
    if month:
        parsed = _month_day(month.group(1), month.group(2), month.group(3))
        if parsed:
            add(parsed)
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
        if title and not _is_banner(title):
            return title
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if title and not _is_banner(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title and not _is_banner(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Wilson Center when the page names that publisher."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site.casefold() in {"wilson center", "the wilson center"}:
        return PUBLISHER
    blob = f"{_plain(visible)}"
    if re.search(r"(?i)\bwilson center\b", blob):
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
    canonical = validate_canonical_url(page_url)
    path = urlparse(canonical).path
    if not page_is_about_ai(page_html, path):
        raise CatalogError("page is not an artificial-intelligence topic")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": canonical,
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
    if not isinstance(description, str) or description != description.strip() or not description:
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
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
        raise CatalogError("canonical URL must be a public Wilson Center AI page")
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
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or ".." in path
        or "\\" in url
        or "//" in path
        or "%" in path
        or path != path.casefold()
        or not is_catalog_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Wilson Center AI page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _bare_path(path: str) -> str | None:
    if not isinstance(path, str) or not path.startswith("/"):
        return None
    if ".." in path or "//" in path or "\\" in path or "%" in path:
        return None
    bare = path[:-1] if path.endswith("/") and path != "/" else path
    if bare != bare.casefold():
        return None
    return bare


def _slug_is_ai(slug: str) -> bool:
    parts = set(slug.casefold().split("-"))
    if parts & _AI_TOKENS:
        return True
    blob = slug.casefold()
    return any(phrase in blob for phrase in _AI_PHRASES)


def _has_ai_topic_tag(page_html: str) -> bool:
    visible = _visible(page_html)
    for attrs, inner in _TAG_ANCHOR.findall(visible):
        href_match = _HREF_ATTR.search(attrs)
        href = ""
        if href_match is not None:
            href = href_match.group(1) or href_match.group(2) or href_match.group(3) or ""
        text = _clean_text(inner).casefold()
        path = _bare_path(urlparse(href).path or "") or ""
        if path in _AI_ISSUE_PATHS:
            return True
        if text in {
            "ai",
            "artificial intelligence",
            "machine learning",
            "generative ai",
            "ai policy",
            "inteligencia artificial",
        }:
            return True
    return False


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool]:
    visible = _drop_generic_cc_anchors(_drop_credit_licences(_visible(page_text)))
    return _cc_codes(visible), _software_codes(visible), _states_ogl(visible)


def _drop_generic_cc_anchors(html: str) -> str:
    """Remove anchors that point at the generic Creative Commons licences URL.

    The anchor text is not a deed. Text outside the anchor still is.
    """

    def replace(match: re.Match[str]) -> str:
        href_match = _HREF_ATTR.search(match.group(1))
        if href_match is None:
            return match.group(0)
        href = href_match.group(1) or href_match.group(2) or href_match.group(3) or ""
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    folded = _fold(href).split()
    if not folded:
        return False
    return _GENERIC_CC_LICENSES.fullmatch(folded[0]) is not None


def _drop_credit_attribute_tags(html: str) -> str:
    """Drop a tag whose attributes name a photo, caption, or image credit."""

    def replace(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    return re.sub(r"(?is)<[^>]+>", replace, html)


def _drop_credit_licences(html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names.

    Text before the credit phrase in the same element still counts. A credit
    inside a tag attribute is dropped with that tag.
    """

    html = _drop_credit_attribute_tags(html)
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(html):
        if _inside_tag(html, match.start()):
            continue
        close = _CREDIT_BLOCK_CLOSE.search(html[match.end() : match.end() + 1000])
        end = match.end() + close.end() if close is not None else min(len(html), match.end() + 500)
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


def _inside_tag(html: str, index: int) -> bool:
    last_open = html.rfind("<", 0, index)
    last_close = html.rfind(">", 0, index)
    return last_open > last_close


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
    for name, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(name)
    if _PD_MARK.search(folded):
        codes.add("pd-mark")
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


def _states_ogl(visible_html: str) -> bool:
    text = _plain(visible_html).replace("\xa0", " ")
    folded = re.sub(r"\s+", " ", text).casefold()
    return _OGL_PHRASE in folded


def _us_government_work(page_text: str) -> bool:
    """True only when a rights metadata field says the item is a US government work.

    Prose, script, style, and comments do not count. The field has to be a
    meta element, not a JSON-LD script.
    """

    fields = _meta_values(_visible(page_text), _RIGHTS_META)
    text = _plain("\n".join(fields)).casefold().translate(_DASHES)
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


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


def _star_rules(body: str) -> list[tuple[str, str]] | None:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    started = False

    def flush() -> None:
        nonlocal agents, rules, started
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []
        started = False

    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if started:
                flush()
            agents.append(value.lower())
            continue
        if agents and key in {"allow", "disallow", "crawl-delay"}:
            started = True
            if key in {"allow", "disallow"}:
                rules.append((key, value))
    flush()
    merged: list[tuple[str, str]] = []
    saw_star = False
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            saw_star = True
            merged.extend(group_rules)
    if not saw_star:
        return None
    return merged


def _rule_matches(pattern: str, target: str) -> bool:
    end = False
    if pattern.endswith("$"):
        pattern = pattern[:-1]
        end = True
    pieces = ["^"]
    for char in pattern:
        pieces.append(".*" if char == "*" else re.escape(char))
    if end:
        pieces.append("$")
    return re.match("".join(pieces), target) is not None


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    return is_official_host(parsed.hostname or "")


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _posted_time(visible_html: str) -> str | None:
    """Return the page's own posted time, not a related-card time.

    Article headers use article-meta. Publication headers use published-info
    directly. A published-info block that follows a card link is related content.
    """

    chunk = _ARTICLE_META_CHUNK.search(visible_html)
    if chunk is not None:
        posted = _POSTED_TIME.search(chunk.group(1))
        if posted is not None:
            return posted.group(1)
    for match in _PUBLISHED_INFO.finditer(visible_html):
        window = visible_html[max(0, match.start() - 500) : match.start()]
        if "js-link-event-link" in window:
            continue
        posted = _POSTED_TIME.search(visible_html[match.start() : match.start() + 800])
        if posted is not None:
            return posted.group(1)
    return None


def _is_banner(title: str) -> bool:
    return title.casefold().startswith(_BANNER_PREFIX)


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    folded = text.casefold()
    for suffix in _SITE_SUFFIXES:
        if folded.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            folded = text.casefold()
            break
    if not text or folded in {"wilson center", "the wilson center"}:
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


def _month_day(month: str, day: str, year: str) -> str | None:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        return date(int(year), month_number, int(day)).isoformat()
    except ValueError:
        return None


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, keys: frozenset[str]) -> list[str]:
    values: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key in keys and attrs.get("content"):
            values.append(attrs["content"])
    return values


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found
