"""Metadata catalog of public Mistral AI research and news pages.

Each stored URL was confirmed with one bounded GET that returned the page
HTML. The official host is mistral.ai. www.mistral.ai redirects there and is
not stored. Console, docs, API reference, and login pages are omitted, as are
other hosts. A Cloudflare challenge, a captcha, a non-HTML response, a robots
disallow, or a redirect off mistral.ai is not stored. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, abstracts,
quotes, transcripts, and chart data are not stored.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` means only CC BY. ``creative_commons`` means
CC0, CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps its own token. Mixed restricted and
permissive text stays unknown. A CC BY or CC BY-SA anchor on a by-nc, by-nd,
by-nc-sa, by-nc-nd, or public-domain mark URL stays unknown. A CC0 anchor on
a public-domain mark URL stays unknown. The Public Domain Mark, all rights
reserved, terms, and the host name stay unknown. MIT, Apache-2.0, and
MPL-2.0 keep their own tokens. Mixed software licences stay unknown.
``uk_ogl`` requires the British phrase Open Government Licence. A generic
creativecommons.org/licenses/ URL stays unknown. A hyphen is a word
boundary, so CC BY does not match CC BY-NC. Updated, modified, and copyright
years are not publication dates. A missing date stays unknown. The live URL
is stored as confirmed; a different rel=canonical does not replace it. This
module does not fetch and it is not a belief collector. ``runner_wired``
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

CATALOG_ID = "mistral_ai_pages"
CATALOG_FILENAME = "mistral_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Mistral AI"
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
OFFICIAL_HOST = "mistral.ai"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_RESEARCH_NEWS_PATH = re.compile(
    r"^/(?:(?:fr|it)/)?(?:news|research)(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*/?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"', re.I)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_SITE_SUFFIXES = (
    " | Mistral AI",
    " - Mistral AI",
    " – Mistral AI",
    " — Mistral AI",
    " | Mistral",
    " - Mistral",
    " – Mistral",
    " — Mistral",
)
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
)
_EXCLUDED_PARTS = frozenset(
    {
        "account",
        "api",
        "atom",
        "auth",
        "cdn-cgi",
        "console",
        "doc",
        "docs",
        "feed",
        "login",
        "rss",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "wp-admin",
        "wp-content",
        "wp-includes",
        "wp-json",
        "xmlrpc.php",
    }
)
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "cf-browser-verification",
    "attention required! | cloudflare",
)
_ANYWHERE_MARKERS = (
    "sg-captcha",
    "sgcaptcha",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
)
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
# Longer deeds are listed first. (?!-) makes a hyphen a token boundary, so
# CC BY does not match CC BY-NC and licenses/by does not match licenses/by-nc.
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
            r"|\bcc[\s-]*by[\s-]*non[\s-]*commercial\b(?!-)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nd\b(?!-)"
            r"|creative commons attribution[\s-]*no[\s-]*deriv"
            r"|\bcc[\s-]*by[\s-]*noderiv"
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
        re.compile(
            r"\bcc[\s-]*by\b(?!-)"
            r"|creative commons attribution\b(?!-)"
        ),
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
# "modified MIT" is not the MIT licence. The lookbehind is applied after casefold.
_MIT_TEXT = re.compile(r"(?<!modified )(?:\bmit license\b|\blicensed under (?:the )?mit\b(?!-))")
_OTHER_SOFTWARE = re.compile(r"\bmnpl\b|\bnon[\s-]*production licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_TEXT = re.compile(r"\bapache[\s-]*2\.0\b|\bapache license(?:[\s-]*version)?[\s-]*2(?:\.0)?\b")
_APACHE_URL = re.compile(r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])")
_MPL_TEXT = re.compile(r"\bmpl[\s-]*2\.0\b|\bmozilla public license(?:[\s-]*version)?[\s-]*2(?:\.0)?\b")
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
    r"\b(?:published|publication date|date published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))",
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


class CatalogError(ValueError):
    """A catalog row or page failed the Mistral AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    _require_text(document.get("description"), "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if len(order) > 1 and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public Mistral AI research or news page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or host != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _research_or_news_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Mistral AI research or news page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


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
    head = lowered[:8000]
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    blob = head + "\n" + title
    return any(marker in blob for marker in _HEAD_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or off-host block."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            text = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in text:
                return False
            if name == "sg-captcha" or "sg-captcha" in text:
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
    """Return metadata when the response is on-host research or news HTML.

    A challenge page, a non-HTML body, an error status, or an off-host URL is
    not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    parsed = urlparse(page_url)
    if not is_official_host(parsed.hostname or ""):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token.
    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
    mix of those is creative_commons. Mixed restricted and permissive text
    stays unknown. A CC BY or CC BY-SA anchor on a restricted or public-domain
    mark URL stays unknown. A CC0 anchor on a public-domain mark URL stays
    unknown. The Public Domain Mark, all rights reserved, terms, and a host
    name are not licences.     MIT, Apache-2.0, and MPL-2.0 keep their own tokens. A modified MIT licence
    is not MIT. The Mistral non-production licence (MNPL), alone or beside
    Apache 2.0, stays unknown. Mixed software licences stay unknown. uk_ogl
    requires the British phrase Open Government Licence. A generic
    creativecommons.org/licenses/ URL stays unknown. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, gov = _licence_signals(page_text)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = codes & set(_SOFTWARE_TOKENS)
    other_software = "other_software" in codes
    ogl = "uk_ogl" in codes
    if restricted and (permissive or software or other_software or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if software and (permissive or other_software or ogl or gov):
        return RIGHTS_UNKNOWN
    if other_software:
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

    article:modified_time, og:updated_time, a last-updated line, and a copyright
    year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    without_comments = _COMMENT.sub(" ", page_html)
    for raw in _DATE_PUBLISHED.findall(" ".join(_LDJSON.findall(without_comments))):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    visible = _HIDDEN.sub(" ", without_comments)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    return _published_prose(_plain_text(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
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
    """Return Mistral AI when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if PUBLISHER.casefold() in _clean_text(metas.get(key, "")).casefold():
            return PUBLISHER
    if PUBLISHER.casefold() in _plain_text(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _research_or_news_path(path: str) -> bool:
    if _RESEARCH_NEWS_PATH.fullmatch(path) is None:
        return False
    lowered = path.lower()
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return not any(part in _EXCLUDED_PARTS for part in lowered.split("/"))


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text.

    A CC0, CC BY, or CC BY-SA label on that URL is not a licence statement.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        folded = _fold(href)
        if "creativecommons.org/publicdomain/mark" in folded:
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    page_text = _strip_mark_anchors(page_text)
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
    for value in _rights_field_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    plain = _plain_text(visible)
    folded = _fold(plain)
    codes |= _codes_in_folded(folded)
    if OGL_PHRASE in folded:
        codes.add("uk_ogl")
    for href in _hrefs(visible):
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
    if _OTHER_SOFTWARE.search(folded):
        codes.add("other_software")
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


def _rights_field_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
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


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    if match.group(1):
        return _iso_day(match.group(1)) or UNKNOWN_DATE
    if match.group(4):
        return _calendar_date(match.group(2), match.group(3), match.group(4)) or UNKNOWN_DATE
    return _calendar_date(match.group(6), match.group(5), match.group(7)) or UNKNOWN_DATE


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
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
