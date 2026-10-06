"""Metadata catalog of public Privacy International pages about AI and technology.

Hosts are privacyinternational.org and www.privacyinternational.org. A row is
stored only after one bounded GET that returns HTML, stays on those hosts,
and is allowed by robots.txt. On 2026-10-06 both hosts resolved. robots.txt
was text/plain, not an HTML document or a challenge, and disallowed admin,
search, login, core, and profile paths. A host that does not resolve, an
HTML or challenge robots.txt, a Cloudflare challenge, a cookie challenge, a
captcha, or a redirect off these hosts stores nothing. An empty catalog is
correct in those cases. This module does not bypass Cloudflare, captchas,
authentication, or robots. It blocks private, loopback, and metadata
addresses.

Pages in scope are public HTML about artificial intelligence or technology.
PDFs, downloads, login walls, and unrelated paths are omitted.

A row keeps the title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, PDFs, and chart data are
not stored. The live URL is stored as confirmed. A different rel=canonical
does not replace it. No p(doom) number is invented.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone.
``creative_commons`` is CC0, CC BY-SA, or a permissive mix of those. A sole
CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``,
``cc_by_nd``, ``cc_by_nc_sa``, or ``cc_by_nc_nd``. Two different restricted
deeds stay unknown. A software licence beside any Creative Commons deed stays
unknown. Two software licences stay unknown. ``mit``, ``apache-2.0``, and
``mpl-2.0`` are sole software licences. Bare MIT stays unknown. Licensed
under the MIT License is mit. Apache License, Version 2.0 is apache-2.0.
A hyphen is a word boundary, so CC BY does not match CC BY-NC and
licenses/by does not match licenses/by-nc. A generic
https://creativecommons.org/licenses/ URL is not a deed, and visible anchor
text on it stays unknown. That includes a missing slash, http, a www host,
and a query string. A specific deed URL still counts. Text elsewhere on the
page still counts. Deceptive permissive anchor text on a restricted deed URL
or a public-domain mark URL stays unknown. A CC0 anchor on a public-domain
mark URL stays unknown. A photo, image, or caption credit that names someone
else's licence stays unknown. ``uk_ogl`` requires the exact British phrase
Open Government Licence. The American spelling License stays unknown.
``us_government_work`` comes only from an explicit rights metadata field.

Updated, modified, and copyright years are not publication dates. Script,
style, and comment text does not count. A missing publication date stays
unknown. This module does not fetch and it does not import requests. It is
not a belief collector. ``runner_wired`` stays false. Belief collection stays
on RssCollector.
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

CATALOG_ID = "privacyint_pages"
CATALOG_FILENAME = "privacyint_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Privacy International"
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
OFFICIAL_HOSTS = frozenset({"privacyinternational.org", "www.privacyinternational.org"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 1400
CATALOG_DESCRIPTION = (
    "Metadata for public Privacy International pages about artificial intelligence and technology. "
    "Hosts are privacyinternational.org and www.privacyinternational.org. "
    "Each stored row follows one bounded robots-allowed HTML GET that stayed on those hosts. "
    "robots.txt disallows /admin/, /search/, /user/login, /core/, and /profiles/. "
    "A host that does not resolve, an HTML or challenge robots.txt, a Cloudflare, cookie, or captcha challenge, "
    "and a redirect off these hosts store nothing. An empty catalog is correct in those cases. "
    "PDFs and downloads are omitted. "
    "Rows keep a title, publisher, canonical URL, publication date, and rights. Page text is not stored. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix of those. "
    "A missing publication date is unknown. Updated, modified, and copyright years are not publication dates. "
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
_PUBLICATION_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.created",
        "dcterms.issued",
        "dc.date.issued",
        "datepublished",
    }
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dcterms.rights",
        "rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "twitter:title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_ELEMENT = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_TIME = re.compile(r"(?is)<time\b([^>]*)>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_POST_DATE_FIELD = re.compile(
    r"(?is)<div\b[^>]*\bfield__label\b[^>]*>\s*post date\s*</div>\s*"
    r"<div\b[^>]*\bfield__item\b[^>]*>\s*([^<]{0,80}?)\s*</div>"
)
_CREDIT_BLOCK = re.compile(
    r"(?is)<(p|li|figcaption|td|dd|small|cite|caption)\b([^>]*)>(.*?)</\1>"
)
_CITATION_BLOCK = re.compile(r"(?is)<(p|li|dd|figcaption)\b[^>]*>.*?</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
_EXCLUDED_PARTS = frozenset(
    {
        "admin",
        "advanced-search",
        "attachment",
        "cdn-cgi",
        "comment",
        "core",
        "feed",
        "filter",
        "index.php",
        "login",
        "log-in",
        "logout",
        "node",
        "password",
        "profiles",
        "register",
        "search",
        "sign-in",
        "signin",
        "sites",
        "user",
        "xmlrpc.php",
    }
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".gif",
    ".ico",
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
_TOPIC_TOKENS = frozenset(
    {
        "adtech",
        "ai",
        "algorithm",
        "algorithmic",
        "algorithms",
        "biometric",
        "biometrics",
        "chatbot",
        "chatbots",
        "deepfake",
        "deepfakes",
        "edtech",
        "fintech",
        "llm",
        "llms",
        "tech",
        "technologies",
        "technology",
    }
)
_TOPIC_PAIRS = frozenset(
    {
        ("artificial", "intelligence"),
        ("automated", "decision"),
        ("facial", "recognition"),
        ("generative", "ai"),
        ("large", "language"),
        ("machine", "learning"),
    }
)
_CHALLENGE_MARKERS = (
    "accept cookies to continue",
    "akamaighost",
    "cf-browser-verification",
    "cf-mitigated",
    "challenge-platform",
    "checking your browser",
    "consent interstitial",
    "cookie challenge",
    "enable javascript and cookies",
    "errors.edgesuite.net",
    "performing security verification",
    "please accept cookies to continue",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "/cdn-cgi/challenge-platform",
)
_CHALLENGE_TITLES = (
    "attention required",
    "checking your browser",
    "enable javascript and cookies",
    "just a moment",
    "please accept cookies",
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
# Longer deeds are listed first. (?!-) and (?![a-z0-9-]) keep CC BY and
# licenses/by from matching CC BY-NC and licenses/by-nc.
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"),
    ),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"),
    ),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    ("by-nc", re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-nd", re.compile(r"creative commons attribution[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]*share[\s-]*alike")),
    ("zero", re.compile(r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])")),
    ("zero", re.compile(r"creative commons(?:\s+public\s+domain)?[\s-]*zero(?![a-z])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![a-z0-9])")),
    ("by", re.compile(r"creative commons attribution(?![\s-]*(?:non|no[\s-]*deriv|share))")),
)
_URL_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"creativecommons\.org/licenses/by-nc-nd(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(r"creativecommons\.org/licenses/by-nc-sa(?![a-z0-9-])")),
    ("by-nc", re.compile(r"creativecommons\.org/licenses/by-nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"creativecommons\.org/licenses/by-nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"creativecommons\.org/licenses/by-sa(?![a-z0-9-])")),
    ("by", re.compile(r"creativecommons\.org/licenses/by(?!-)(?![a-z0-9])")),
    ("zero", re.compile(r"creativecommons\.org/publicdomain/zero(?![a-z0-9-])")),
    ("mark", re.compile(r"creativecommons\.org/publicdomain/mark(?![a-z0-9-])")),
)
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
}
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_US_GOV_WORK = re.compile(
    r"\b(?:united states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+(?:united states|u\.s\.|us)\s+government\b"
)
_NEGATED_US_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united states|u\.s\.|us)\s+government\b"
)
_MIT = re.compile(r"(?<!modified )(?:\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_CREDIT_PHRASE = re.compile(
    r"(?i)\b(?:photo|image|caption)\s+credits?\b|\b(?:photo|image|caption)\s*:"
)
_CREDIT_CLASS = re.compile(
    r"(?i)(?:photo|image|caption)[\s_-]*credits?|\bwp-caption\b|\bfield-credit\b"
)
_CREDIT_SENTENCE = re.compile(
    r"(?is)\b(?:photo|image|caption)\s+credits?\b.{0,500}?(?:\.(?=\s|<|$)|$)"
    r"|\b(?:photo|image|caption)\s*:.{0,500}?(?:\.(?=\s|<|$)|$)"
)
_PUBLISHED_PROSE = re.compile(
    r"\b(?:publication date|date published|published|posted|post date)\b(?:\s+on)?\s*:?\s*"
    r"(?:"
    r"(\d{4}-\d{2}-\d{2})"
    r"|([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"
    r"|(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})"
    r")",
    re.I,
)
_QUOTED = re.compile("“[^”]{0,400}”|„[^“]{0,400}“|" + '"[^"\\n]{0,400}"')
_SITE_SUFFIXES = (
    " | privacy international",
    " - privacy international",
    " – privacy international",
    " — privacy international",
    " | pi",
)
_JUNK_TITLES = frozenset(
    {
        "menu",
        "privacy international",
        "skip to content",
        "skip to main content",
    }
)
_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


class CatalogError(ValueError):
    """A catalog row or page failed the Privacy International page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for privacyinternational.org and www.privacyinternational.org only."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_topic_path(path: str) -> bool:
    """True for a public HTML path about artificial intelligence or technology.

    A token is a slash or hyphen piece. ``ai`` and ``tech`` match as their own
    tokens, so ``campaign`` and ``email`` do not. Login, search, admin, and
    download paths stay excluded.
    """

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    lowered = path.lower()
    if lowered != "/" and lowered.endswith("/"):
        lowered = lowered[:-1]
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    parts = [part for part in lowered.split("/") if part]
    if not parts or len(parts) > 6:
        return False
    if any(part in _EXCLUDED_PARTS for part in parts):
        return False
    if any(_SEGMENT.fullmatch(part) is None for part in parts):
        return False
    tokens: list[str] = []
    for part in parts:
        tokens.extend(part.split("-"))
    if any(token in _TOPIC_TOKENS for token in tokens):
        return True
    return any(pair in _TOPIC_PAIRS for pair in zip(tokens, tokens[1:], strict=False))


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is a Cloudflare, cookie, or captcha challenge."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    title = _TITLE.search(page_html[:12000])
    if title and any(marker in title.group(1).casefold() for marker in _CHALLENGE_TITLES):
        return True
    head = page_html[:8000].casefold()
    return any(marker in head for marker in _CHALLENGE_MARKERS)


def is_login_wall(page_html: str) -> bool:
    """True when the HTML is an authentication form rather than a public page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if is_challenge_page(page_html):
        return False
    visible = _without_hidden(page_html).casefold()
    if 'type="password"' not in visible and "type='password'" not in visible:
        return False
    return any(marker in visible for marker in ("sign in", "log in", "login", "authenticate"))


def robots_allows(body: str, path: str) -> bool:
    """True when the * group does not disallow ``path``.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. An empty User-agent group allows every path.
    """

    if not isinstance(body, str) or not isinstance(path, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or is_challenge_page(body[:8000]):
        return False
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    return not robots_disallows(body, target)


def robots_disallows(robots_txt: str, path: str) -> bool:
    """True when User-agent: * disallows ``path``.

    The longest matching Allow or Disallow wins. An empty Disallow does not
    block the site.
    """

    if not isinstance(robots_txt, str) or not isinstance(path, str) or not path.startswith("/"):
        return False
    rules = _star_rules(robots_txt)
    best_len = -1
    blocked = False
    for kind, value in rules:
        if not value:
            continue
        matched = path.startswith(value) or (value.endswith("/") and path == value[:-1])
        if not matched:
            continue
        length = len(value)
        if length > best_len:
            best_len = length
            blocked = kind == "disallow"
        elif length == best_len and kind == "allow":
            blocked = False
    return blocked


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or login wall."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if is_login_wall(page_html):
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
    final_url: str | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
    robots_txt: str | None = None,
    resolved: bool = True,
) -> dict | None:
    """Return metadata when one bounded response is on-host topic HTML.

    An unresolved host, a challenge, a cookie wall, a captcha, an
    authentication wall, a non-HTML body, an error status, a robots
    disallow, an HTML robots document, or an off-host redirect is not stored.
    """

    if not resolved:
        return None
    target = final_url or page_url
    if not _stayed_on_official_hosts(page_url, final_url, hops):
        return None
    parsed = urlparse(target)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not is_official_host(host):
        return None
    if robots_txt is not None and not robots_allows(robots_txt, parsed.path or "/"):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
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
    hops: tuple[str, ...] | list[str] | None = None,
    robots_txt: str | None = None,
    resolved: bool = True,
) -> list[dict]:
    """Return catalog rows for one response, or none when it must not be stored."""

    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        hops=hops,
        robots_txt=robots_txt,
        resolved=resolved,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a
    permissive mix of those is creative_commons. A sole restricted deed keeps
    its token. Two different restricted deeds stay unknown. A software licence
    beside any Creative Commons deed stays unknown. Two software licences stay
    unknown. Bare MIT stays unknown. Licensed under the MIT License is mit.
    Apache License, Version 2.0 is apache-2.0. A generic
    creativecommons.org/licenses URL is not a deed, and the visible text of
    that anchor does not count. Deceptive permissive anchor text on a
    restricted deed or public-domain mark URL stays unknown. A photo, image,
    or caption credit that names someone else's licence does not count.
    uk_ogl requires the British phrase Open Government Licence. American
    spelling License stays unknown. us_government_work requires a rights
    metadata field. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_mark_anchors(
        _without_generic_cc_license_anchors(_without_credit(_without_hidden(page_text)))
    )
    plain = _drop_quoted_licence_mentions(_plain(visible))
    folded = plain.casefold().translate(_DASHES)
    codes = _text_codes(folded)
    hrefs = [href for href in _hrefs(visible) if not _is_generic_cc_licenses_url(href)]
    for href in hrefs:
        codes |= _url_codes(href.casefold().translate(_DASHES))
    codes |= _url_codes(folded)
    licence_bits: list[str] = []
    for key, content in _meta_pairs(visible):
        if key not in _LICENSE_META:
            continue
        chunk = _plain(content).casefold().translate(_DASHES)
        licence_bits.append(chunk)
        codes |= _text_codes(chunk)
        codes |= _url_codes(chunk)
    if "mark" in codes:
        codes.discard("mark")
    scanned = " ".join([folded, *licence_bits, *(href.casefold() for href in hrefs)])
    mit = bool(_MIT.search(scanned) or any(_MIT_URL.search(href.casefold()) for href in hrefs))
    apache = bool(_APACHE.search(scanned) or any(_APACHE_URL.search(href.casefold()) for href in hrefs))
    mpl = bool(_MPL.search(scanned) or any(_MPL_URL.search(href.casefold()) for href in hrefs))
    return _label(
        codes,
        mit=mit,
        apache=apache,
        mpl=mpl,
        ogl=bool(_OGL_PHRASE.search(folded)),
        us_gov=_states_us_government_work(visible),
    )


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    A Drupal Post date is a publication date. article:modified_time,
    og:updated_time, a last-updated line, and a copyright year are not.
    Several different publication dates stay unknown. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    found: list[str] = []
    for key, content in _meta_pairs(visible):
        if key not in _PUBLICATION_META:
            continue
        parsed = _iso_day(content)
        if parsed and parsed not in found:
            found.append(parsed)
    for parsed in _time_publication_dates(visible):
        if parsed not in found:
            found.append(parsed)
    for parsed in _labeled_post_dates(visible):
        if parsed not in found:
            found.append(parsed)
    if found:
        return found[0] if len(found) == 1 else UNKNOWN_DATE
    prose = _published_prose_dates(_plain(visible))
    if len(prose) == 1:
        return prose[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Privacy International when the page states that name.

    A person named on the page is not the publisher. The hostname alone is
    not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher", "dcterms.publisher", "publisher"):
        if PUBLISHER.casefold() in _clean_text(metas.get(key, "")).casefold():
            return PUBLISHER
    title_tag = _TITLE.search(visible)
    title_text = title_tag.group(1) if title_tag else ""
    if PUBLISHER.casefold() in _plain(" ".join((title_text, visible))).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if is_login_wall(page_html):
        raise CatalogError("login wall is not stored")
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
    description = document.get("description")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog contract")
    if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_CHARS:
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
        raise CatalogError("canonical URL must be a public Privacy International AI or technology page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    normalized = f"https://{host}{path}"
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or url != normalized
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Privacy International AI or technology page: {url}")
    return normalized


def _label(
    codes: set[str],
    *,
    mit: bool,
    apache: bool,
    mpl: bool,
    ogl: bool,
    us_gov: bool,
) -> str:
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    families = [
        name
        for name, present in (
            ("restricted", bool(restricted)),
            ("permissive", bool(permissive)),
            ("mit", mit),
            ("apache", apache),
            ("mpl", mpl),
            ("ogl", ogl),
            ("us", us_gov),
        )
        if present
    ]
    if len(families) != 1:
        return RIGHTS_UNKNOWN
    if restricted:
        if len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive:
        if permissive == {"by"}:
            return RIGHTS_CC_ATTRIBUTION
        if permissive <= _PERMISSIVE and permissive & {"by-sa", "zero"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_UNKNOWN
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if ogl:
        return RIGHTS_UK_OGL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def _text_codes(folded: str) -> set[str]:
    found: list[tuple[int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            start, end = match.span()
            if any(start < prev_end and end > prev_start for prev_start, prev_end, _code in found):
                continue
            found.append((start, end, code))
    return {code for _start, _end, code in found}


def _url_codes(value: str) -> set[str]:
    found: set[str] = set()
    for code, pattern in _URL_DEEDS:
        if pattern.search(value):
            found.add(code)
    return found


def _states_us_government_work(visible_html: str) -> bool:
    """True only when a rights metadata field says the item is a US government work."""

    for key, content in _meta_pairs(visible_html):
        if key not in _RIGHTS_META:
            continue
        text = _plain(content).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _time_publication_dates(visible_html: str) -> list[str]:
    found: list[str] = []
    for attrs in _TIME.findall(visible_html):
        parsed_attrs = _attrs(f"<time {attrs}>")
        if parsed_attrs.get("itemprop", "").casefold() != "datepublished":
            continue
        parsed = _iso_day(parsed_attrs.get("datetime", ""))
        if parsed:
            found.append(parsed)
    return found


def _labeled_post_dates(visible_html: str) -> list[str]:
    found: list[str] = []
    for raw in _POST_DATE_FIELD.findall(visible_html):
        parsed = _prose_date_text(raw)
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def _published_prose_dates(plain: str) -> list[str]:
    found: list[str] = []
    for match in _PUBLISHED_PROSE.finditer(plain):
        parsed = _date_from_match(match)
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def _prose_date_text(value: str) -> str | None:
    text = _clean_text(value)
    iso = _iso_day(text)
    if iso:
        return iso
    match = re.search(
        r"(?:([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"
        r"|(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4}))",
        text,
        re.I,
    )
    if match is None:
        return None
    if match.group(3):
        return _calendar_date(match.group(1), match.group(2), match.group(3))
    return _calendar_date(match.group(5), match.group(4), match.group(6))


def _date_from_match(match: re.Match[str]) -> str | None:
    if match.group(1):
        return _iso_day(match.group(1))
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4))
    return _calendar_date(match.group(6), match.group(5), match.group(7))


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold().rstrip("."))
    if month is None:
        return None
    try:
        return date(int(year_text), month, int(day_text)).isoformat()
    except ValueError:
        return None


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} is too long to store")


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _JUNK_TITLES


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
    lowered = text.casefold()
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                lowered = text.casefold()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _without_credit(page_html: str) -> str:
    """Drop photo, image, and caption credits that name someone else's licence."""

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if len(body) > 800:
            return match.group(0)
        if _CREDIT_CLASS.search(attrs) or _CREDIT_PHRASE.search(attrs):
            return " "
        if not _CREDIT_PHRASE.search(body):
            return match.group(0)
        cleaned = _CREDIT_SENTENCE.sub(" ", body)
        if _CREDIT_PHRASE.search(cleaned):
            return " "
        return f"<{match.group(1)}{attrs}>{cleaned}</{match.group(1)}>"

    stripped = _CREDIT_BLOCK.sub(replace_block, page_html)

    def replace_anchor(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    stripped = _ANCHOR_ELEMENT.sub(replace_anchor, stripped)
    return _CREDIT_SENTENCE.sub(" ", stripped)


def _drop_quoted_licence_mentions(plain: str) -> str:
    """Drop a quoted title that names someone else's licence."""

    def replace(match: re.Match[str]) -> str:
        inner = match.group(0).casefold()
        if re.search(r"licen[cs]e|creative commons|cc[\s-]*by|mit licen", inner):
            return " "
        return match.group(0)

    return _QUOTED.sub(replace, plain)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for the Creative Commons licences index, not a deed."""

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(href.strip())
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in _GENERIC_CC_HOSTS:
        return False
    path = (parsed.path or "").casefold()
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _without_generic_cc_license_anchors(page_html: str) -> str:
    """Drop anchors whose href is only the generic licences index."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR_ELEMENT.sub(replace, page_html)


def _without_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "").casefold()
        if "creativecommons.org/publicdomain/mark" in href:
            return " "
        return match.group(0)

    return _ANCHOR_ELEMENT.sub(replace, page_html)


def _stayed_on_official_hosts(
    page_url: str,
    final_url: str | None,
    hops: tuple[str, ...] | list[str] | None,
) -> bool:
    chain = list(hops or [])
    if not chain:
        chain = [page_url]
        if final_url and final_url != page_url:
            chain.append(final_url)
    elif final_url and chain[-1] != final_url:
        chain.append(final_url)
    if not chain:
        return False
    for url in chain:
        host = (urlparse(url).hostname or "").lower().rstrip(".")
        if host not in OFFICIAL_HOSTS:
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
    return False


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _meta_pairs(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        if key and "content" in attrs:
            found.append((key, attrs["content"]))
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _star_rules(robots_txt: str) -> list[tuple[str, str]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().casefold()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value.casefold())
        elif key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    flush()
    selected: list[tuple[str, str]] = []
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            selected.extend(group_rules)
    return selected
