"""Metadata catalog of public Atlantic Council pages about artificial intelligence.

Hosts are www.atlanticcouncil.org and atlanticcouncil.org. Each stored URL
was confirmed with one bounded GET that stayed on those hosts. A row keeps
the title, publisher, canonical URL, date, and rights label. Page text,
abstracts, PDFs, quotes, transcripts, and chart data are not stored. The
live URL is stored as confirmed; a different rel=canonical does not replace
it.

Unrelated Atlantic Council topics, login walls, and event registration are
not stored. A Cloudflare challenge, a captcha, an authentication wall, a
robots disallow, an HTTP 202, an Akamai 403, a non-HTML response, or a
redirect off those hosts is not stored. A blocked sitemap or listing
contributes no rows for that path.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means CC0, CC BY-SA, or a permissive mix of those.
``creative_commons_attribution`` means CC BY alone. One sole restricted deed
keeps ``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``, or ``cc_by_nc_nd``. Two
different restricted deeds stay unknown. A hyphen continues a deed, so CC BY
does not match CC BY-NC, and licenses/by does not match licenses/by-nc.
Public Domain Mark is not CC0. A generic creativecommons.org/licenses URL is
not a deed. Anchor text on it, including CC BY, CC BY 4.0, and CC BY-SA,
stays unknown, including a missing slash, http, a www host, and a query
string. A specific deed URL still counts. Text elsewhere on the page still
counts. Deceptive permissive anchor text on a restricted deed URL or on a
public-domain mark URL stays unknown. A CC0 anchor on a public-domain mark
URL stays unknown. ``uk_ogl`` requires the British phrase Open Government
Licence. ``us_government_work`` requires a rights metadata field. mit,
apache-2.0, and mpl-2.0 are one sole software licence. Apache License,
Version 2.0 is apache-2.0. A software licence beside any Creative Commons
deed stays unknown. Two software licences stay unknown. A photo credit,
caption credit, or image credit that names someone else's licence stays
unknown. Script, style, and comment text does not count.

Updated, modified, and copyright years are not publication dates. This
module does not fetch. It is not a belief collector, and runner_wired stays
false.
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

CATALOG_ID = "atlantic_ai_pages"
CATALOG_FILENAME = "atlantic_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Atlantic Council"
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
OFFICIAL_HOSTS = frozenset({"www.atlanticcouncil.org", "atlanticcouncil.org"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public Atlantic Council pages on artificial intelligence, machine learning, or AI policy. "
    "Hosts are www.atlanticcouncil.org and atlanticcouncil.org. Each URL was confirmed with one bounded GET. "
    "Off-host sitemaps were not fetched. A challenge, captcha, login wall, robots disallow, or event "
    "registration stores no row. On 2026-10-06 no on-host sitemap was skipped for those blocks. Rows are "
    "title, publisher, canonical URL, date, and rights. Page text, abstracts, PDFs, quotes, transcripts, and "
    "chart data are not stored. A missing date is unknown. Updated, modified, and copyright years are not "
    "publication dates. creative_commons is CC0, CC BY-SA, or a permissive mix of those. "
    "creative_commons_attribution is CC BY alone. Not a belief collector. runner_wired is false."
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
_LISTING_TYPES = _HTML_TYPES | frozenset({"text/xml", "application/xml", "application/rss+xml"})
_PUBLICATION_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_PAIR = re.compile(r"(?is)(<a\b[^>]*>)(.*?)(</a>)")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " — atlantic council",
    " – atlantic council",
    " - atlantic council",
    " | atlantic council",
)
_GENERIC_TITLES = frozenset({"atlantic council"})
_PUBLISHER_WORD = re.compile(r"\bAtlantic Council\b")
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".epub",
    ".mp3",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
    "are you a robot",
    "attention required",
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
# Longer deeds are listed first. A hyphen is a word boundary: (?!-) and
# (?![a-z0-9-]) stop CC BY and licenses/by from matching CC BY-NC. A version
# suffix such as -4.0 is consumed so CC BY-SA-4.0 still names CC BY-SA.
_VERSION = r"(?:[\s-]*\d+(?:\.\d+)?)?"
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd{_VERSION}(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa{_VERSION}(?![a-z0-9-])")),
    ("by-nc", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nc{_VERSION}(?![a-z0-9-])")),
    ("by-nd", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*nd{_VERSION}(?![a-z0-9-])")),
    ("by-sa", re.compile(rf"(?<![a-z0-9])cc[\s-]*by[\s-]*sa{_VERSION}(?![a-z0-9-])")),
    ("by", re.compile(rf"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b){_VERSION}(?![a-z0-9-])")),
    (
        "by-nc-nd",
        re.compile(
            r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"creative commons\s+attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
        ),
    ),
    ("by-nd", re.compile(r"creative commons\s+attribution[\s-]+no[\s-]*deriv")),
    (
        "by-sa",
        re.compile(
            r"creative commons\s+attribution[\s-]+share[\s-]*alike"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))"
        ),
    ),
    (
        "by",
        re.compile(
            r"creative commons\s+attribution(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|sa|nc|nd)\b)"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero(?![a-z])"
        ),
    ),
    ("mark", re.compile(r"\bpublic domain mark\b")),
)
_URL_CODES = {
    "by": "by",
    "by-sa": "by-sa",
    "by-nc": "by-nc",
    "by-nd": "by-nd",
    "by-nc-sa": "by-nc-sa",
    "by-nc-nd": "by-nc-nd",
    "zero": "zero",
    "mark": "mark",
}
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_US_GOV_WORK = re.compile(r"\b(?:united states|u\.s\.|us)\s+government\s+work\b")
_NEGATED_US_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+work\b"
)
_MIT = re.compile(r"\bmit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(
    r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b"
)
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_AI_PATH = re.compile(
    r"(?i)(?:"
    r"(?:^|[-/])ai(?:[-/]|$)"
    r"|artificial-intelligen"
    r"|machine-learning"
    r"|generative-ai"
    r"|(?:^|[-/])chatgpt(?:[-/]|$)"
    r"|(?:^|[-/])llms?(?:[-/]|$)"
    r"|large-language-model"
    r")"
)
_SKIPPED_PREFIXES = (
    "/sponsor/",
    "/wp-admin",
    "/wp-login",
    "/wp-json",
    "/wp-content/",
    "/xmlrpc.php",
    "/login",
    "/account",
    "/cart",
    "/checkout",
    "/feed",
)
_CREDIT_ELEMENT = re.compile(
    r"(?is)<(figcaption|p|li|span|small|cite|caption|dd|td|th)\b[^>]*>.*?</\1>"
)
_CREDIT_DIV = re.compile(
    r'(?is)<div\b[^>]*\bclass\s*=\s*["\'][^"\']*(?:caption|photo-credit|image-credit|wp-caption-text)[^"\']*["\'][^>]*>.*?</div>'
)
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|image|caption)\s+credits?\b")
_CREDIT_SENTENCE = re.compile(
    r"(?is)\b(?:photo|image|caption)\s+credits?\b(?:[^<.]|<[^>]+>){0,400}"
)
_LICENCE_HINT = re.compile(
    r"(?i)(?:"
    r"creativecommons|creative\s+commons|\bcc[\s-]*(?:by|0)\b|\bmit\s+licen|"
    r"\bapache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2\.0\b|\bmpl[\s-]*2\.0\b|"
    r"mozilla\s+public|open\s+government\s+licen"
    r")"
)
_REGISTRATION = re.compile(
    r"(?is)(?:"
    r"<h[1-3]\b[^>]*>\s*(?:event\s+registration|register\s+to\s+attend)\b"
    r"|<form\b[^>]{0,500}(?:\bregister\b|\brsvp\b)"
    r"|class\s*=\s*['\"][^'\"]*(?:event-registration|rsvp-form)[^'\"]*['\"]"
    r")"
)
_LOGIN_TITLE = re.compile(r"(?i)^(?:log[\s-]?in|sign[\s-]?in|sign[\s-]?up)$")
_PASSWORD_FORM = re.compile(
    r"(?is)<form\b[^>]*>.{0,1200}?type\s*=\s*['\"]password['\"]"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Atlantic Council page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for www.atlanticcouncil.org and atlanticcouncil.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_topic_path(path: str) -> bool:
    """True for an HTML path about artificial intelligence, machine learning, or AI policy."""

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    lowered = path.lower()
    if "ai-monitor" in lowered:
        return False
    if any(lowered.startswith(prefix) for prefix in _SKIPPED_PREFIXES):
        return False
    if re.search(r"/(?:register|rsvp|sign-in|signin)(?:/|$)", lowered):
        return False
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _AI_PATH.search(lowered) is not None


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html[:8000].casefold()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def is_login_wall(page_html: str) -> bool:
    """True when the page is an authentication form rather than a public article."""

    if not isinstance(page_html, str):
        return False
    visible = _without_hidden(page_html)
    title = ""
    match = _TITLE.search(visible)
    if match:
        title = _plain(match.group(1))
    if _LOGIN_TITLE.fullmatch(title):
        return True
    if _PASSWORD_FORM.search(visible) and not _H1.search(visible):
        return True
    return False


def is_event_registration(page_html: str, page_url: str = "") -> bool:
    """True for an event registration form. A public article is not one."""

    path = (urlparse(page_url).path or "").lower()
    if re.search(r"/(?:register|rsvp)(?:/|$)", path):
        return True
    if not isinstance(page_html, str):
        return False
    visible = _without_hidden(page_html)
    return _REGISTRATION.search(visible) is not None


def robots_blocks(robots_text: str, path: str) -> bool:
    """True when User-agent: * disallows path.

    An empty Disallow allows the path. The live Atlantic Council file has an
    empty Disallow. This does not fetch.
    """

    if not isinstance(robots_text, str):
        return False
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    rules: list[tuple[str, str]] = []
    agents: list[str] = []
    saw_rules = False
    for raw in robots_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if saw_rules:
                agents = []
                saw_rules = False
            agents.append(value.lower())
            continue
        if key in {"allow", "disallow"} and "*" in agents:
            saw_rules = True
            rules.append((key, value))
    if not rules:
        return False
    matched: tuple[int, str] | None = None
    for kind, prefix in rules:
        if prefix == "":
            if kind == "disallow":
                continue
            candidate = "/"
        else:
            candidate = prefix
        if target.startswith(candidate) and (matched is None or len(candidate) > matched[0]):
            matched = (len(candidate), kind)
    return matched is not None and matched[1] == "disallow"


def listing_is_blocked(
    *,
    status: object,
    content_type: object,
    body: object,
    robots_text: str = "",
    listing_path: str = "/",
    headers: Mapping[str, str] | None = None,
) -> bool:
    """True when a sitemap or listing must contribute an empty catalog.

    A Cloudflare challenge, a captcha, an authentication response, or a
    robots.txt disallow blocks that path. The caller moves on.
    """

    if robots_blocks(robots_text, listing_path):
        return True
    if isinstance(status, bool) or not isinstance(status, int):
        return True
    if status in {401, 403}:
        return True
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "www-authenticate":
                return True
            if name == "cf-mitigated" and "challenge" in token:
                return True
            if name == "sg-captcha":
                return True
    if status != 200 or not isinstance(body, str) or not body.strip():
        return True
    if is_challenge_page(body) or is_login_wall(body):
        return True
    if isinstance(content_type, str) and content_type.strip():
        base = content_type.split(";", 1)[0].strip().casefold()
        if base not in _LISTING_TYPES:
            return True
    return False


def listing_catalog_entries(
    *,
    status: object,
    content_type: object,
    body: object,
    robots_text: str = "",
    listing_path: str = "/",
    headers: Mapping[str, str] | None = None,
    pages: list[dict] | None = None,
) -> list[dict]:
    """Rows from one listing. A blocked listing contributes an empty list."""

    if listing_is_blocked(
        status=status,
        content_type=content_type,
        body=body,
        robots_text=robots_text,
        listing_path=listing_path,
        headers=headers,
    ):
        return []
    return list(pages or [])


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge or wall."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if is_login_wall(page_html) or is_event_registration(page_html, page_url):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
            if name == "www-authenticate":
                return False
            if name == "server" and "akamai" in token and status != 200:
                return False
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata when the response is an on-host AI page.

    A challenge, an HTTP 202, an Akamai 403, a login wall, event registration,
    a non-HTML body, or an off-host URL is not stored.
    """

    if headers:
        for key, value in headers.items():
            if str(key).casefold() == "server" and "akamai" in str(value).casefold() and status == 403:
                return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen continues a
    deed, so CC BY-NC is not CC BY and licenses/by does not match
    licenses/by-nc. Mixed restricted and permissive text stays unknown. A
    software licence beside any Creative Commons deed stays unknown. Two
    software licences stay unknown. Two different restricted deeds stay
    unknown. Public Domain Mark is not CC0. A generic
    creativecommons.org/licenses URL is not a deed. Anchor text on that URL
    does not count, including http, a www host, no trailing slash, and a
    query string. Text elsewhere on the page still counts. A specific deed
    URL still counts. Deceptive permissive anchor text on a restricted or
    public-domain mark URL stays unknown. A photo, caption, or image credit
    that names someone else's licence does not count. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    ld_values = _jsonld_rights_and_licenses(page_text)
    visible = _drop_other_work_credits(_without_hidden(page_text))
    visible = _drop_generic_cc_anchor_text(visible)
    plain = _plain(visible).casefold().translate(_DASHES)
    hrefs = [href for href in _hrefs(visible) if not _is_generic_cc_licenses_url(href)]
    blobs = [plain, *(_meta_values(visible, _LICENSE_META)), *ld_values, *hrefs]
    codes: set[str] = set()
    mit = False
    apache = False
    mpl = False
    for blob in blobs:
        folded = blob.casefold().translate(_DASHES)
        codes.update(_cc_codes(folded))
        mit = mit or bool(_MIT.search(folded) or _MIT_URL.search(folded))
        apache = apache or bool(_APACHE.search(folded) or _APACHE_URL.search(folded))
        mpl = mpl or bool(_MPL.search(folded) or _MPL_URL.search(folded))
    software = {name for name, present in (("mit", mit), ("apache", apache), ("mpl", mpl)) if present}
    ogl = _OGL_PHRASE.search(plain) is not None
    us_gov = _states_us_government_work(page_text, visible)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    other = bool(software or ogl or us_gov)
    if restricted and (permissive or other):
        return RIGHTS_UNKNOWN
    if permissive and other:
        return RIGHTS_UNKNOWN
    if len(software) > 1 or (software and (ogl or us_gov)) or (ogl and us_gov):
        return RIGHTS_UNKNOWN
    if restricted:
        named = restricted - {"mark"}
        if len(named) != 1:
            return RIGHTS_UNKNOWN
        if named == {"by-nc"}:
            return RIGHTS_CC_BY_NC
        if named == {"by-nd"}:
            return RIGHTS_CC_BY_ND
        if named == {"by-nc-nd"}:
            return RIGHTS_CC_BY_NC_ND
        if named == {"by-nc-sa"}:
            return RIGHTS_CC_BY_NC_SA
        return RIGHTS_UNKNOWN
    if permissive:
        if permissive <= {"by"}:
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


def publication_date_from_page(page_html: str, *, page_url: str | None = None) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    JSON-LD datePublished for this page and article:published_time are
    publication dates. dateModified, article:modified_time, og:updated_time,
    a copyright year, and dates of other posts are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    published = _jsonld_published(page_html)
    chosen: str | None = None
    if page_url:
        matched = {day for url, day in published if url and _same_page(url, page_url)}
        if len(matched) > 1:
            return UNKNOWN_DATE
        if len(matched) == 1:
            chosen = next(iter(matched))
    else:
        unique = {day for _url, day in published}
        if len(unique) > 1:
            return UNKNOWN_DATE
        if len(unique) == 1:
            chosen = next(iter(unique))
    metas = _metas(_without_hidden(page_html))
    meta_days = {day for key in _PUBLICATION_META if (day := _iso_day(metas.get(key, "")))}
    if len(meta_days) > 1:
        return UNKNOWN_DATE
    meta_day = next(iter(meta_days)) if meta_days else None
    if chosen and meta_day and meta_day != chosen:
        return UNKNOWN_DATE
    if chosen:
        return chosen
    if meta_day:
        return meta_day
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title and title.casefold() not in _GENERIC_TITLES:
            return title
    headings = []
    for inner in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", inner))
        if title:
            headings.append(title)
    if len(headings) == 1 and headings[0].casefold() not in _GENERIC_TITLES:
        return headings[0]
    if headings:
        return headings[0]
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Atlantic Council when the page names that publisher.

    A person named on the page is not the publisher. The hostname alone is
    not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    if _PUBLISHER_WORD.search(_plain(visible)):
        return PUBLISHER
    for name in _jsonld_values(page_html, "name"):
        if name.strip() == PUBLISHER:
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if is_login_wall(page_html):
        raise CatalogError("login wall is not stored")
    if is_event_registration(page_html, page_url):
        raise CatalogError("event registration is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html, page_url=page_url),
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
    if not isinstance(description, str) or not description.strip() or description != description.strip():
        raise CatalogError("description is required")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog description")
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
        raise CatalogError("rights must be a known label or unknown")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Atlantic Council AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or host not in OFFICIAL_HOSTS
        or parsed.netloc.lower() != host
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
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Atlantic Council AI page: {url}")
    return url


def _jsonld_published(page_html: str) -> list[tuple[str | None, str]]:
    found: list[tuple[str | None, str]] = []
    for block in _LDJSON.findall(_COMMENT.sub(" ", page_html)):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _collect_published(payload, None, found)
    return found


def _collect_published(payload: object, current_url: str | None, found: list[tuple[str | None, str]]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_published(item, current_url, found)
        return
    if not isinstance(payload, dict):
        return
    url = current_url
    for name, value in payload.items():
        if str(name).casefold() == "url" and isinstance(value, str):
            url = value.strip()
    for name, value in payload.items():
        if str(name).casefold() == "datepublished" and isinstance(value, str):
            day = _iso_day(value)
            if day:
                found.append((url, day))
    for name, value in payload.items():
        if str(name).casefold() in {"datemodified", "startdate", "enddate", "copyrightyear"}:
            continue
        if isinstance(value, (dict, list)):
            _collect_published(value, url, found)


def _same_page(left: str, right: str) -> bool:
    def norm(value: str) -> str:
        parsed = urlparse(value.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        path = parsed.path or ""
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        if host:
            return f"{host}{path}".casefold()
        text = value.strip()
        if len(text) > 1 and text.endswith("/"):
            text = text[:-1]
        return text.casefold()

    return norm(left) == norm(right)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for creativecommons.org/licenses with no deed in the path.

    http, a www host, a missing trailing slash, and a query string are still
    the generic licence index. licenses/by/4.0/ and the other deed paths are
    not generic.
    """

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(href.strip())
    scheme = (parsed.scheme or "").casefold()
    host = (parsed.hostname or "").casefold().rstrip(".")
    path = (parsed.path or "").casefold()
    if scheme not in {"http", "https"}:
        return False
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    return path in {"/licenses", "/licenses/"}


def _drop_generic_cc_anchor_text(visible_html: str) -> str:
    """Remove visible text of anchors that point at the generic licence index.

    That anchor text is not a licence statement. Text outside the anchor stays.
    A specific deed URL is unchanged.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(match.group(1)).get("href", "")
        if _is_generic_cc_licenses_url(href):
            return match.group(1) + match.group(3)
        return match.group(0)

    return _ANCHOR_PAIR.sub(replace, visible_html)


def _drop_other_work_credits(visible_html: str) -> str:
    """Drop a photo, image, or caption credit that names someone else's licence.

    A credit without a licence stays. A licence stated outside the credit stays.
    """

    def replace(match: re.Match[str]) -> str:
        element = match.group(0)
        plain = _plain(element)
        if not _CREDIT_PHRASE.search(plain):
            return element
        if len(plain) <= 500 and _names_a_licence(element):
            return " "
        return _CREDIT_SENTENCE.sub(_drop_licensed_credit, element)

    without_divs = _CREDIT_DIV.sub(replace, visible_html)
    return _CREDIT_ELEMENT.sub(replace, without_divs)


def _drop_licensed_credit(match: re.Match[str]) -> str:
    if _names_a_licence(match.group(0)):
        return " "
    return match.group(0)


def _names_a_licence(value: str) -> bool:
    folded = value.casefold().translate(_DASHES)
    if _LICENCE_HINT.search(folded):
        return True
    return _CC_URL.search(folded) is not None


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("code") or match.group("pd")
        if code:
            codes.add(_URL_CODES.get(code, code))
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _states_us_government_work(page_html: str, visible: str) -> bool:
    """True only when a rights field says the item is a US government work."""

    fields = list(_meta_values(visible, _RIGHTS_META))
    for value in _jsonld_values(page_html, "rights"):
        fields.append(value)
    for raw in fields:
        text = _plain(raw).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _jsonld_rights_and_licenses(page_html: str) -> list[str]:
    found: list[str] = []
    for key in ("license", "rights"):
        found.extend(_jsonld_values(page_html, key))
    return found


def _jsonld_values(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(_COMMENT.sub(" ", page_html)):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _collect_key(payload, key.casefold(), found)
    return found


def _collect_key(payload: object, key: str, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_key(item, key, found)
        return
    if not isinstance(payload, dict):
        return
    for name, value in payload.items():
        if str(name).casefold() == key and isinstance(value, str):
            found.append(value)
        elif isinstance(value, (dict, list)):
            _collect_key(value, key, found)


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


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        lowered = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    if text.casefold().startswith("tag:"):
        text = text.split(":", 1)[1].strip()
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, keys: frozenset[str] | tuple[str, ...]) -> list[str]:
    wanted = {key.lower() for key in keys}
    found: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in wanted and attrs.get("content"):
            found.append(attrs["content"])
    return found


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
