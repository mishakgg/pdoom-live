"""Metadata catalog of public International Committee of the Red Cross pages about AI.

Hosts are www.icrc.org and icrc.org. icrc.org redirects to www.icrc.org, which
stays on these hosts. On 2026-10-06 robots.txt was text/plain and allowed
public HTML. It disallows profiles, login, admin, search, and a few parameter
paths. The sitemap was XML and was used only to find URLs. Each stored URL
was confirmed with one bounded GET: 12 second timeout, at most 3 redirects,
and at most 2000000 bytes. A Cloudflare challenge, a captcha, an HTML
document in place of robots.txt, a host that does not resolve, an HTTP error,
a non-HTML body, a robots disallow, or a redirect off these hosts is not
stored. An empty entries list is valid in those cases.

Stored pages are research and news HTML about artificial intelligence,
including military AI and autonomous weapon systems. Person profiles,
donation pages, login walls, PDFs, videos, events, and unrelated topics stay
out. Publisher is International Committee of the Red Cross.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
text, abstracts, quotes, transcripts, chart data, and PDFs are not stored.
The live URL is stored as confirmed. A different rel=canonical does not
replace it.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution is CC BY alone, including a specific
/licenses/by/4.0/ URL. creative_commons is CC0, CC BY-SA, or a permissive
mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps
cc_by_nc, cc_by_nd, cc_by_nc_sa, or cc_by_nc_nd. Text cc-by-nc maps to
cc_by_nc. A hyphen is a word boundary, so CC BY does not match CC BY-NC.
Two different restricted deeds stay unknown. A software licence beside any
Creative Commons deed stays unknown. Two software licences stay unknown.
mit, apache-2.0, and mpl-2.0 are sole software licences. Apache License,
Version 2.0 is apache-2.0. Bare MIT stays unknown. Licensed under the MIT
License is mit. uk_ogl is only the British phrase Open Government Licence.
Open Government License stays unknown. us_government_work comes only from an
explicit rights metadata field.

A generic creativecommons.org/licenses or /licenses URL is not a deed, and
anchor text on it stays unknown. That includes a missing slash, http, a www
host, and a query string. A specific deed URL still counts. Text elsewhere
on the page still counts. Deceptive permissive anchor text on a restricted
deed URL or a public-domain mark URL stays unknown. A CC0 anchor on a
publicdomain/mark URL stays unknown. Photo credit, caption credit, and image
credit that name someone else's licence stay unknown, including Photo credit:
UNDRR, CC BY-NC-ND 2.0 and Photo: UNDRR, CC BY-NC-ND 2.0. When the page
states its own CC BY licence and a separate photo credit names another
licence, the page stays creative_commons_attribution. Script, style, and
comment text does not count.

Publication dates only. Modified, updated, and copyright years stay unknown.
Several distinct publication dates stay unknown. This module does not fetch,
it does not import requests, and it is not a belief collector. runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "icrc_pages"
CATALOG_FILENAME = "icrc_pages.json"
RUNNER_WIRED = False
PUBLISHER = "International Committee of the Red Cross"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY = "creative_commons_attribution"
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
        RIGHTS_CC_BY,
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
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"www.icrc.org", "icrc.org"})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 1000
FETCH_TIMEOUT_SECONDS = 12
FETCH_MAX_REDIRECTS = 3
FETCH_MAX_BYTES = 2_000_000
CATALOG_DESCRIPTION = (
    "Metadata for public International Committee of the Red Cross research and news HTML "
    "about artificial intelligence on www.icrc.org and icrc.org. The apex host redirects to www. "
    "robots.txt allows these public paths and disallows profiles, login, admin, and search. "
    "Each stored URL was one bounded GET that returned HTML on these hosts. "
    "Rows store title, publisher, canonical URL, date, and rights. "
    "Page text, abstracts, PDFs, quotes, transcripts, and chart data are not stored. "
    "Person profiles, donation pages, login walls, and unrelated topics are omitted. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "A missing publication date is unknown. Updated, modified, and copyright years are not publication dates. "
    "Not a belief collector. runner_wired stays false."
)

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
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
        "auth",
        "biography",
        "biographies",
        "cart",
        "cdn-cgi",
        "checkout",
        "don",
        "donate",
        "donation",
        "donations",
        "donner",
        "feed",
        "give",
        "log-in",
        "login",
        "people",
        "person",
        "profile",
        "profiles",
        "search",
        "sign-in",
        "signin",
        "sign-up",
        "signup",
        "spende",
        "staff",
        "support-us",
        "user",
        "wp-admin",
        "wp-login.php",
        "xml",
    }
)
_SKIP_SECTIONS = frozenset(
    {
        "career",
        "careers",
        "event",
        "events",
        "job",
        "jobs",
        "podcast",
        "podcasts",
        "video",
        "videos",
    }
)
_CONTENT_SECTIONS = frozenset(
    {
        "article",
        "articles",
        "artikel",
        "artigo",
        "document",
        "documents",
        "droit-et-politique",
        "derecho-y-politicas",
        "direito-e-politicas",
        "law-and-policy",
        "news",
        "newsroom",
        "publication",
        "publications",
        "recht-und-politik",
        "research",
        "statement",
        "statements",
    }
)
_TOPIC_PAIRS = frozenset(
    {
        ("artificial", "intelligence"),
        ("autonomous", "weapon"),
        ("autonomous", "weapons"),
        ("deep", "learning"),
        ("generative", "ai"),
        ("inteligencia", "artificial"),
        ("intelligence", "artificielle"),
        ("künstliche", "intelligenz"),
        ("kuenstliche", "intelligenz"),
        ("kunstliche", "intelligenz"),
        ("large", "language"),
        ("lethal", "autonomous"),
        ("machine", "learning"),
        ("neural", "network"),
    }
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
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
)
_ANYWHERE_MARKERS = (
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "akamaighost",
    "errors.edgesuite.net",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"((?:\\.|[^"\\])*)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"((?:\\.|[^"\\])*)"', re.I)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
# Photo credit, caption credit, image credit, and a Photo: sentence name
# someone else's licence. Photo: UNDRR, CC BY-NC-ND 2.0 is that sentence.
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:(?:photo|image|caption)\s+credits?|photo\s*:)")
_BLOCK_BOUNDARY = re.compile(
    r"(?i)</(?:p|figcaption|li|dd|dt|h[1-6]|caption|blockquote|td|th|div)>"
)
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_SITE_SUFFIXES = (
    " | International Committee of the Red Cross",
    " - International Committee of the Red Cross",
    " – International Committee of the Red Cross",
    " — International Committee of the Red Cross",
    " | ICRC",
    " - ICRC",
    " – ICRC",
    " — ICRC",
    " | Comité international de la Croix-Rouge",
    " | Comité Internacional de la Cruz Roja",
    " | Internationales Komitee vom Roten Kreuz",
    " | 红十字国际委员会",
)
_ORG_NAMES = (
    "international committee of the red cross",
    "comité international de la croix-rouge",
    "comite international de la croix-rouge",
    "comité internacional de la cruz roja",
    "comite internacional de la cruz roja",
    "internationales komitee vom roten kreuz",
    "comité internacional da cruz vermelha",
    "comite internacional da cruz vermelha",
    "comitê internacional da cruz vermelha",
    "международный комитет красного креста",
    "اللجنة الدولية للصليب الأحمر",
    "红十字国际委员会",
    "紅十字國際委員會",
)
_WALL_TITLE = re.compile(r"(?i)^\s*(log[\s-]*in|sign[\s-]*in|donate|donation|support us)\s*$")
# A generic licences index is not a deed. A missing slash, http, a www host,
# and a query string are the same index. licenses/by remains a deed.
_GENERIC_LICENSES_URL = re.compile(
    r"(?i)^(?:(?:https?:)?//)?(?:www\.)?creativecommons\.org/licenses/?(?:[?#]\S*)?$"
)
_MARK_URL = re.compile(r"(?i)creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# A hyphen is a word boundary, so CC BY does not match CC BY-NC.
# Longer deeds are listed first. (?!-) keeps licenses/by from matching licenses/by-nc.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-)"
    r"|publicdomain/(?P<pd>zero|mark)(?!-))"
    r"(?![a-z0-9])"
)
_TEXT_DEEDS = (
    (
        "cc-by-nc-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc\b(?!-)"
            r"|creative commons attribution[\s-]*non[\s-]*commercial\b(?!-)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nd\b(?!-)"
            r"|creative commons attribution[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*sa\b(?!-)"
            r"|creative commons attribution[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc0",
        re.compile(r"\bcc[\s-]*0\b|\bcc0\b|\bcc[\s-]*zero\b|creative commons zero\b"),
    ),
    (
        "cc-by",
        re.compile(r"\bcc[\s-]*by\b(?!-)|creative commons attribution\b(?!-)"),
    ),
)
_PERMISSIVE = frozenset({"cc0", "cc-by", "cc-by-sa"})
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-nd", "cc-by-nc-sa"})
_RESTRICTED_TOKENS = {
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_MIT_TEXT = re.compile(r"(?<!modified )(?:\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
# The comma in "Apache License, Version 2.0" is part of the apache-2.0 statement.
_APACHE_TEXT = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:,)?(?:[\s,]+version)?[\s,]*2(?:\.0)?\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_TEXT = re.compile(r"\bmpl[\s-]*2\.0\b|\bmozilla public licen[cs]e(?:[\s,]+version)?[\s,]*2(?:\.0)?\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_SOFTWARE = (
    ("mit", _MIT_TEXT, _MIT_URL),
    ("apache-2.0", _APACHE_TEXT, _APACHE_URL),
    ("mpl-2.0", _MPL_TEXT, _MPL_URL),
)
_SOFTWARE_TOKENS = {
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_PUBLISHED_PROSE = re.compile(
    r"(?<!last )(?<!updated )(?<!modified )(?<!copyright )"
    r"\b(?:publication date|date published|published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})"
    r"|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"
    r"|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
    re.I,
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
_LANG = re.compile(r"^[a-z]{2}$")


class CatalogError(ValueError):
    """A catalog row or page failed the International Committee of the Red Cross page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document fields must be catalog_id, description, runner_wired, and entries")
    _reject_stored_body(document)
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the International Committee of the Red Cross catalog contract")
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
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _reject_stored_body(entry, path="entry")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public International Committee of the Red Cross AI page")
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
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not is_research_or_news_ai_path(path)
    ):
        raise CatalogError(
            f"canonical URL must be a public International Committee of the Red Cross research or news page: {url}"
        )
    return url


def is_official_host(hostname: str) -> bool:
    """True for www.icrc.org and icrc.org only."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_research_or_news_ai_path(path: str) -> bool:
    """True for research or news HTML about artificial intelligence.

    A language prefix is followed by an article, document, publication,
    statement, or law-and-policy section, or by one AI slug. Person profiles,
    donation pages, login walls, videos, events, and downloads stay out.
    ``ai`` matches as its own token, so ``campaign`` and ``airstrike`` do not.
    The pinyin sequence ``ai-bo-la`` (Ebola) is not an AI token.
    """

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    lowered = path.lower()
    if _is_download(lowered) or _has_blocked_part(lowered):
        return False
    parts = [part for part in lowered.split("/") if part]
    if len(parts) < 2 or _LANG.fullmatch(parts[0]) is None:
        return False
    section = parts[1]
    if section in _SKIP_SECTIONS or section in _BLOCKED_PARTS:
        return False
    if section in _CONTENT_SECTIONS:
        topic = "/".join(parts[2:])
        if not topic:
            return False
        return _is_ai_topic(topic)
    if len(parts) == 2:
        return _is_ai_topic(section)
    return False


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _ANYWHERE_MARKERS):
        return True
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    head = lowered[:2500]
    return any(marker in title or marker in head for marker in _HEAD_MARKERS)


def robots_allows(robots_text: str, path: str) -> bool:
    """True when robots.txt does not disallow ``path``.

    A challenge page or any HTML document served in place of robots.txt does
    not allow a fetch. ``*`` is a wildcard and ``$`` anchors the end. The
    longest matching Allow or Disallow wins. An empty Disallow allows the path.
    A group whose user-agent starts with ``pdoom`` overrides ``*``.
    """

    if not isinstance(robots_text, str) or not isinstance(path, str):
        return False
    sample = robots_text[:800].casefold()
    if "<html" in sample or any(marker in sample for marker in _ANYWHERE_MARKERS + _HEAD_MARKERS):
        return False
    rules = _wildcard_rules(robots_text)
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


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
    resolved: bool = True,
) -> bool:
    """A page is stored only from HTML that stayed on an official host."""

    if resolved is False:
        return False
    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers and _challenge_headers(headers):
        return False
    if not _stayed_on_official_hosts(page_url, final_url, hops):
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
    hops: tuple[str, ...] | list[str] | None = None,
    robots_text: str | None = None,
    resolved: bool = True,
) -> dict | None:
    """Return metadata when one bounded response is on-host AI research or news HTML.

    A Cloudflare challenge, a captcha, an authentication wall, an HTTP error,
    a non-HTML body, a robots disallow, HTML served as robots.txt, an unresolved
    host, an off-host redirect, a donation page, a login wall, a person profile,
    or an unrelated topic is not stored.
    """

    if resolved is False:
        return None
    target = final_url or page_url
    if robots_text is not None:
        parsed = urlparse(target)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        if not robots_allows(robots_text, path):
            return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        hops=hops,
        resolved=resolved,
    ):
        return None
    assert isinstance(page_html, str)
    if _is_login_or_donation(page_html, target):
        return None
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
    mix of those is creative_commons. A sole restricted deed keeps its own
    token. Text cc-by-nc maps to cc_by_nc. Two restricted deeds stay unknown.
    A software licence beside any Creative Commons deed stays unknown. Two
    software licences stay unknown. A generic creativecommons.org/licenses URL
    stays unknown, including when its anchor says CC BY, CC BY 4.0, or
    CC BY-SA, and including a missing slash, http, a www host, or a query
    string. A specific deed URL still counts. Text elsewhere on the page still
    counts. Deceptive permissive anchor text on a restricted or public-domain
    mark URL stays unknown. A CC0 anchor on a public-domain mark URL stays
    unknown. A photo credit, caption credit, image credit, or Photo: sentence
    stays unknown, including Photo credit: UNDRR, CC BY-NC-ND 2.0 and Photo:
    UNDRR, CC BY-NC-ND 2.0. A page licence outside that credit still counts.
    uk_ogl requires the British phrase Open Government Licence. us_government_work
    requires a rights field. Bare MIT stays unknown. Licensed under the MIT
    License is mit. Apache License, Version 2.0 is apache-2.0. Script, style,
    and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, gov = _licence_signals(page_text)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = codes & set(_SOFTWARE_TOKENS)
    ogl = "uk_ogl" in codes
    if restricted and (permissive or software or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if software and (permissive or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(software) == 1:
        return _SOFTWARE_TOKENS[next(iter(software))]
    if gov and (permissive or ogl):
        return RIGHTS_UNKNOWN
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    if ogl and permissive:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if permissive == frozenset({"cc-by"}):
        return RIGHTS_CC_BY
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, and copyright years are not publication dates. Script,
    style, and comment text does not count. Several different publication
    dates do not yield one date for the page.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    without_comments = _COMMENT.sub(" ", page_html)
    found: list[str] = []

    def add(raw: object) -> None:
        parsed = _iso_day(raw) if isinstance(raw, str) else None
        if parsed and parsed not in found:
            found.append(parsed)

    for raw in _DATE_PUBLISHED.findall(" ".join(_LDJSON.findall(without_comments))):
        add(raw)
    visible = _HIDDEN.sub(" ", without_comments)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        add(metas.get(key, ""))
    if len(found) == 1:
        return found[0]
    if found:
        return UNKNOWN_DATE
    return _published_prose(_plain_text(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return International Committee of the Red Cross when the page states that name.

    A person named on the page is not the publisher. The host name alone is
    not the publisher. Official names in other languages still store the
    English publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    titled = " ".join(_clean_text(metas.get(key, "")) for key in _PUBLISHER_KEYS)
    title_tag = _TITLE.search(visible)
    title_text = title_tag.group(1) if title_tag else ""
    blob = _fold(" ".join((titled, title_text, _plain_text(visible))))
    if not any(name in blob for name in _ORG_NAMES):
        raise CatalogError("publisher is required")
    return PUBLISHER


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed AI research or news page.

    The record does not include the document text. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if _is_login_or_donation(page_html, page_url):
        raise CatalogError("login and donation pages are not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _is_ai_topic(path: str) -> bool:
    tokens = _path_tokens(path)
    if _usable_ai_token(tokens):
        return True
    if any(token in {"llm", "llms", "chatgpt"} for token in tokens):
        return True
    for index in range(len(tokens) - 1):
        if (tokens[index], tokens[index + 1]) in _TOPIC_PAIRS:
            return True
    return False


def _usable_ai_token(tokens: list[str]) -> bool:
    """True when ``ai`` is a token and not the pinyin start of Ebola (ai-bo-la)."""

    for index, token in enumerate(tokens):
        if token != "ai":
            continue
        if index + 2 < len(tokens) and tokens[index + 1] == "bo" and tokens[index + 2] == "la":
            continue
        return True
    return False


def _is_login_or_donation(page_html: str, page_url: str) -> bool:
    path = (urlparse(page_url).path or "/").lower()
    if _has_blocked_part(path):
        return True
    try:
        title = title_from_page(page_html)
    except CatalogError:
        return False
    return _WALL_TITLE.fullmatch(title) is not None


def _path_tokens(path: str) -> list[str]:
    tokens: list[str] = []
    normalized = path.lower().replace("_", "-")
    for segment in normalized.split("/"):
        if not segment:
            continue
        tokens.extend(part for part in segment.split("-") if part)
    return tokens


def _has_blocked_part(path: str) -> bool:
    parts = [part for part in path.lower().split("/") if part]
    return any(part in _BLOCKED_PARTS for part in parts)


def _is_download(path: str) -> bool:
    bare = path[:-1] if path.endswith("/") else path
    return bare.endswith(_DOWNLOAD_SUFFIXES)


def _stayed_on_official_hosts(
    page_url: str,
    final_url: str | None,
    hops: tuple[str, ...] | list[str] | None,
) -> bool:
    chain = [url for url in (hops or []) if isinstance(url, str)]
    if not chain:
        chain = [page_url]
    if final_url and chain[-1] != final_url:
        chain.append(final_url)
    if not chain:
        return False
    for url in chain:
        if not is_official_host((urlparse(url).hostname or "").lower().rstrip(".")):
            return False
    return True


def _challenge_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "sg-captcha" or "sg-captcha" in text:
            return True
        if name == "www-authenticate":
            return True
        if name == "server" and "akamai" in text and "403" in text:
            return True
    return False


def _wildcard_rules(body: str) -> list[tuple[str, str]] | None:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, list(rules)))
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
    chosen: list[tuple[str, str]] | None = None
    wildcard: list[tuple[str, str]] | None = None
    for group_agents, group_rules in groups:
        for agent in group_agents:
            if agent == "*":
                wildcard = group_rules
            elif agent.startswith("pdoom"):
                chosen = group_rules
    if chosen is not None:
        return chosen
    return wildcard


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
        pieces.append(re.escape(char))
        index += 1
    if not pattern.endswith("$"):
        pieces.append(".*")
    return re.compile("^" + "".join(pieces))


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    without_comments = _COMMENT.sub(" ", page_text)
    codes: set[str] = set()
    gov = False
    for license_text, rights_text in _jsonld_rights(without_comments):
        codes |= _codes_in_string(license_text)
        codes |= _codes_in_string(rights_text)
        if _states_us_government_work(rights_text):
            gov = True
    visible = _HIDDEN.sub(" ", without_comments)
    for value in _license_meta_texts(visible):
        codes |= _codes_in_string(value)
    for key, value in _metas(visible).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            if _states_us_government_work(value):
                gov = True
            codes |= _codes_in_string(value)
    stripped = _strip_mark_anchors(_strip_generic_license_anchors(_strip_credit_spans(visible)))
    for value in _rights_element_texts(stripped):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    folded = _fold(_plain_text(stripped))
    codes |= _codes_in_folded(folded)
    if OGL_PHRASE in folded:
        codes.add("uk_ogl")
    for href in _hrefs(stripped):
        if _is_generic_cc_licenses_url(href) or _MARK_URL.search(_fold(href)):
            continue
        codes |= _codes_in_string(href)
    return codes, gov


def _codes_in_string(value: str) -> set[str]:
    if not value:
        return set()
    return _codes_in_folded(_fold(value))


def _codes_in_folded(folded: str) -> set[str]:
    """Licence codes in one folded string. Restricted deeds are matched first."""

    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            codes.add(f"cc-{license_code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
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
        codes.add(code)
    for code, text_pattern, url_pattern in _SOFTWARE:
        if text_pattern.search(folded) or url_pattern.search(folded):
            codes.add(code)
    return codes


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _fold(value))
    return _GOV_WORK.search(text) is not None


def _jsonld_rights(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for block in _LDJSON.findall(page_html):
        licenses = [item.replace("\\/", "/") for item in _LD_LICENSE.findall(block)]
        rights = [item.replace("\\/", "/") for item in _LD_RIGHTS.findall(block)]
        if not licenses and not rights:
            continue
        width = max(len(licenses), len(rights), 1)
        licenses.extend([""] * (width - len(licenses)))
        rights.extend([""] * (width - len(rights)))
        found.extend(zip(licenses, rights, strict=True))
    return found


def _license_meta_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key in {"license", "licence"} or key.endswith((".license", ".licence", ":license", ":licence")):
            found.append(value)
    return found


def _rights_element_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(page_html):
        if not _is_rights_element(attrs):
            continue
        text = _plain_text(body)
        if text and len(text) <= MAX_TEXT_CHARS:
            found.append(text)
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


def _is_generic_cc_licenses_url(href: str) -> bool:
    return _GENERIC_LICENSES_URL.fullmatch(_fold(href).strip()) is not None


def _strip_credit_spans(page_html: str) -> str:
    """Drop photo, image, and caption credits so someone else's licence does not count.

    ``Photo credit: UNDRR, CC BY-NC-ND 2.0`` and ``Photo: UNDRR, CC BY-NC-ND 2.0``
    are credits. A reuse licence stated outside that sentence still counts.
    """

    pieces: list[str] = []
    last = 0
    for match in _CREDIT_PHRASE.finditer(page_html):
        if match.start() < last or _inside_tag(page_html, match.start()):
            continue
        pieces.append(page_html[last : match.start()])
        window_end = min(len(page_html), match.end() + 500)
        last = match.end() + _credit_end(page_html[match.end() : window_end])
    pieces.append(page_html[last:])
    return "".join(pieces)


def _inside_tag(page_html: str, index: int) -> bool:
    last_open = page_html.rfind("<", 0, index)
    last_close = page_html.rfind(">", 0, index)
    return last_open > last_close


def _credit_end(window: str) -> int:
    stops = [len(window)]
    sentence = _sentence_end(window)
    if sentence is not None:
        stops.append(sentence)
    boundary = _BLOCK_BOUNDARY.search(window)
    if boundary:
        stops.append(boundary.start())
    return min(stops)


def _sentence_end(window: str) -> int | None:
    in_tag = False
    for index, char in enumerate(window):
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            continue
        if in_tag or char not in ".?!":
            continue
        if index + 1 == len(window) or window[index + 1] in " \t\n\r<":
            return index + 1
    return None


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _MARK_URL.search(_fold(href)):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _strip_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose URL is a generic creativecommons.org/licenses page.

    CC BY, CC BY 4.0, or CC BY-SA text on that URL is not a licence statement.
    A specific deed URL such as /licenses/by/4.0/ still counts.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _published_prose(plain: str) -> str:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        parsed = _prose_date(match)
        if parsed and parsed not in found:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def _prose_date(match: re.Match[str]) -> str | None:
    if match.group(1):
        return _iso_day(match.group(1))
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4))
    return _calendar_date(match.group(6), match.group(5), match.group(7))


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be plain text")


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
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible_html(page_text))


def _visible_html(page_text: str) -> str:
    return _HIDDEN.sub(" ", _COMMENT.sub(" ", page_text))


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _iso_day(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
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
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs in _ANCHOR.findall(page_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if href:
            found.append(href)
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
