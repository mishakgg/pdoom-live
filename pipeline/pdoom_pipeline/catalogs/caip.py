"""Metadata catalog of public Center for AI Policy pages.

Each stored URL was confirmed with one bounded GET on www.centeraipolicy.org.
A row keeps the title, publisher, canonical URL, date, and rights label. Page
text, abstracts, and PDFs are not stored. A Cloudflare challenge, a captcha,
an HTTP 202, an Akamai 403, a robots disallow, a non-HTML response, or an
off-host redirect is not stored. The apex host and aipolicy.us redirect away
from a page on those hosts, so they are not stored.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means only a stated CC0, CC BY, or CC BY-SA deed.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND are their own tokens and are
never folded into ``creative_commons``. A page that states both a restricted
deed and a permissive deed stays unknown. A hyphen is a word boundary, so CC BY does
not match CC BY-NC, and licenses/by does not match licenses/by-nc. A generic
creativecommons.org/licenses/ URL is not a permissive deed. The Public
Domain Mark is not CC0. ``uk_ogl`` is used only when the page text states the
British phrase open government licence. ``us_government_work`` is used only
when a rights field says the item is a US government work. ``mit``,
``apache-2.0``, and ``mpl-2.0`` stay their own tokens. A copyright notice,
All rights reserved, a terms link, and a .org host are not licences.

A page that does not state a publication date keeps the date unknown.
Updated, modified, and copyright years are not publication dates. The live
URL is stored as confirmed; a different rel=canonical does not replace it.
This module does not fetch and it is not a belief collector. runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "caip_pages"
CATALOG_FILENAME = "caip_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Center for AI Policy"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
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
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "www.centeraipolicy.org"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

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
# robots.txt on the official host lists a sitemap and no Disallow rule.
_ROBOTS_DISALLOW: tuple[str, ...] = ()
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_RIGHTS = re.compile(r'"(?:license|rights)"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|October|November|December"
)
_HEADER_DATE = re.compile(
    r"(?is)<div\b[^>]*\bclass\s*=\s*(?:\"[^\"]*\bflex-grow\b[^\"]*\"|'[^']*\bflex-grow\b[^']*')[^>]*>"
    rf"\s*({_MONTH_NAME})\s+(\d{{1,2}}),\s+(\d{{4}})\s*</div>"
)
_DATELINE = re.compile(
    rf"(?is)<div\b([^>]*)>\s*({_MONTH_NAME})\s+(\d{{1,2}}),\s+(\d{{4}})\s*</div>"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_RIGHTS_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dcterms.rights",
        "dc.rights.license",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title", "twitter:title")
_SITE_SUFFIXES = (
    " | Center for AI Policy | CAIP",
    " | Center for AI Policy (CAIP)",
    " | The Center for AI Policy",
    " | Center for AI Policy",
    " | CAIP",
    " - Center for AI Policy (CAIP)",
    " - Center for AI Policy",
    " – Center for AI Policy",
    " — Center for AI Policy",
    " at Center for AI Policy",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-browser-verification",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
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
# A hyphen is a word boundary in \b, so the deed must continue through the
# hyphen. licenses/by must not match licenses/by-nc. Longer deeds are first.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9-])")),
    ("by-nc", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9-])")),
    ("by", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)(?![a-z0-9-]))(?![a-z0-9-])")),
    (
        "zero",
        re.compile(
            r"(?i)(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9-])"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero(?![a-z])"
        ),
    ),
    ("mark", re.compile(r"(?i)\bpublic domain mark\b")),
)
_PROSE_CODES = (
    ("by-nc-nd", re.compile(r"(?i)attribution[-\s]+non[-\s]?commercial[-\s]+no[-\s]?deriv")),
    ("by-nc-sa", re.compile(r"(?i)attribution[-\s]+non[-\s]?commercial[-\s]+share[-\s]?alike")),
    ("by-nc", re.compile(r"(?i)attribution[-\s]+non[-\s]?commercial(?![-\s]+(?:share|no[-\s]?deriv))")),
    ("by-nd", re.compile(r"(?i)attribution[-\s]+no[-\s]?deriv")),
    ("by-sa", re.compile(r"(?i)attribution[-\s]+share[-\s]?alike")),
    (
        "by",
        re.compile(
            r"(?i)attribution(?![-\s]+(?:non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike))"
        ),
    ),
)
_RESTRICTED_CC = {
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
}
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_OGL_PHRASE = re.compile(r"(?i)open government licence(?![a-z])")
_US_GOV_WORK = re.compile(
    r"(?i)\b(?:u\.?\s*s\.?|united states)\s+government\s+work\b"
    r"|\bwork of the (?:u\.?\s*s\.?|united states)\s+government\b"
)
_MIT_PHRASE = re.compile(
    r"(?i)\bmit licen[cs]e\b|licen[cs]ed under (?:the )?mit licen[cs]e\b"
)
_MIT_URL = re.compile(r"(?i)(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_PHRASE = re.compile(
    r"(?i)(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?i)(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_PHRASE = re.compile(
    r"(?i)(?<![a-z0-9])mpl-2\.0(?![a-z0-9])"
    r"|\bmpl\s+2\.0\b"
    r"|\bmozilla public licen[cs]e\s+2\.0\b"
)
_MPL_URL = re.compile(r"(?i)(?:mozilla\.org/MPL/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")


class CatalogError(ValueError):
    """A catalog row or page failed the Center for AI Policy page rules."""


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
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
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
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Center for AI Policy page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or host != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or not is_official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _public_path(path)
        or robots_disallow(path)
    ):
        raise CatalogError(f"canonical URL is not a public Center for AI Policy page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def robots_disallow(path: str) -> bool:
    """True when robots.txt Disallow covers this path. The live file has none."""

    bare = path or "/"
    if not bare.startswith("/"):
        bare = "/" + bare
    for prefix in _ROBOTS_DISALLOW:
        if not prefix:
            continue
        if bare == prefix or bare.startswith(prefix if prefix.endswith("/") else prefix + "/"):
            return True
        if prefix != "/" and bare.startswith(prefix):
            return True
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
    plain = _plain_text(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
    page_url: str | None = None,
) -> bool:
    """A page is stored only from HTML that is not a block, challenge, or captcha."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if page_url is not None:
        try:
            validate_canonical_url(_live_url(page_url))
        except CatalogError:
            return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name in {"cf-mitigated", "sg-captcha"} and "challenge" in token:
                return False
            if name == "server" and "akamai" in token and status == 403:
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
    """Return metadata when the response is the page HTML.

    An HTTP 202, an Akamai 403, a Cloudflare or captcha challenge, a robots
    disallow, an off-host URL, or a non-HTML response is not stored.
    """

    if status == 202 or _akamai_block(status, headers):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        page_url=page_url,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. A sole CC BY-NC,
    CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND deed stays its own token. A page that
    also states CC BY, CC BY-SA, CC0, MIT, or Apache-2.0 stays unknown, including
    a CC BY or CC BY-SA anchor whose href is a restricted or Public Domain Mark
    URL. A CC0 anchor on a publicdomain/mark URL stays unknown. A hyphen
    continues the token, so CC BY does not match CC BY-NC and licenses/by does
    not match licenses/by-nc. The Public Domain Mark is not CC0. ``uk_ogl``
    requires the British phrase in the page text. ``us_government_work``
    requires a rights field. ``mit``, ``apache-2.0``, and ``mpl-2.0`` are not
    folded into ``creative_commons``. A copyright notice, All rights reserved,
    a terms link, and a .org host are not licences.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _HIDDEN.sub(" ", page_text)
    plain = _plain_text(visible).translate(_DASHES)
    blobs = [plain, *_hrefs(visible), *_meta_values(visible, _RIGHTS_META)]
    for blob in _LDJSON.findall(page_text):
        blobs.extend(raw.replace("\\/", "/") for raw in _LD_RIGHTS.findall(blob))
    codes: set[str] = set()
    for blob in blobs:
        codes.update(_cc_codes(blob))
    joined = "\n".join(blobs)
    restricted = [code for code in ("by-nc-nd", "by-nc-sa", "by-nc", "by-nd") if code in codes]
    permissive_also = bool(codes & _PERMISSIVE_CC) or _states_mit(joined) or _states_apache(joined)
    if restricted and permissive_also:
        return RIGHTS_UNKNOWN
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    if restricted:
        return _RESTRICTED_CC[restricted[0]]
    named: set[str] = set()
    if codes & _PERMISSIVE_CC:
        named.add(RIGHTS_CREATIVE_COMMONS)
    if _OGL_PHRASE.search(plain):
        named.add(RIGHTS_UK_OGL)
    if _rights_field_says_us_government_work(page_text):
        named.add(RIGHTS_US_GOVERNMENT_WORK)
    if _states_mit(joined):
        named.add(RIGHTS_MIT)
    if _states_apache(joined):
        named.add(RIGHTS_APACHE)
    if _states_mpl(joined):
        named.add(RIGHTS_MPL)
    if len(named) == 1:
        return next(iter(named))
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, a hidden listing date, and another item's date are not publication
    dates. The article header date is the flex-grow line on a work page.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for blob in _LDJSON.findall(page_html):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    header = _unique_date(_header_dates(visible))
    if header:
        return header
    dateline = _unique_date(_dateline_dates(visible))
    if dateline:
        return dateline
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return the Center for AI Policy when the page states that name.

    A person named on the page is not the publisher. A .org host is not a
    publisher. The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(_live_url(page_url))
    visible = _HIDDEN.sub(" ", page_html)
    site = _metas(visible).get("og:site_name", "")
    if PUBLISHER.casefold() in _clean_text(site).casefold():
        return PUBLISHER
    if PUBLISHER.casefold() in _plain_text(visible).casefold():
        return PUBLISHER
    for blob in _LDJSON.findall(page_html):
        if PUBLISHER.casefold() in blob.casefold():
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": _confirmed_url(page_html, page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(_live_url(page_url))
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_live_url(urljoin(live, href.strip())))
    except CatalogError:
        return live
    if declared == live:
        return declared
    return live


def _live_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if path == "/":
        path = ""
    host = (parsed.hostname or "").lower().rstrip(".")
    return f"https://{host}{path}"


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/") or path.endswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    segments = lowered[1:].split("/")
    return all(re.fullmatch(r"[a-z0-9]+(?:-{1,3}[a-z0-9]+)*", segment) for segment in segments)


def _akamai_block(status: object, headers: Mapping[str, str] | None) -> bool:
    if status != 403 or not headers:
        return False
    for key, value in headers.items():
        if str(key).casefold() == "server" and "akamai" in str(value).casefold():
            return True
    return False


def _rights_field_says_us_government_work(page_text: str) -> bool:
    fields: list[str] = []
    visible = _HIDDEN.sub(" ", page_text)
    fields.extend(_meta_values(visible, _RIGHTS_META))
    for tag in _LINKISH.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold().split()
        if "license" in rel or "licence" in rel:
            fields.append(attrs.get("href", ""))
    for attrs, inner in (( _attrs(raw), inner) for raw, inner in _anchor_parts(visible)):
        rel = attrs.get("rel", "").casefold().split()
        if "license" in rel or "licence" in rel:
            fields.append(_plain_text(inner))
    for blob in _LDJSON.findall(page_text):
        fields.extend(raw.replace("\\/", "/") for raw in _LD_RIGHTS.findall(blob))
    return any(_US_GOV_WORK.search(_normalize(field)) for field in fields)


def _cc_codes(value: str) -> set[str]:
    text = _normalize(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(text):
        code = match.group("code") or match.group("pd")
        if code:
            codes.add(code.casefold())
    for code, pattern in _CC_TEXT:
        if pattern.search(text):
            codes.add(code)
    if "creative commons" in text.casefold():
        for code, pattern in _PROSE_CODES:
            if pattern.search(text):
                codes.add(code)
    return codes


def _states_mit(value: str) -> bool:
    text = _normalize(value)
    if text.strip() in {"mit", "mit-license", "mit-licence"}:
        return True
    return _MIT_URL.search(text) is not None or _MIT_PHRASE.search(text) is not None


def _states_apache(value: str) -> bool:
    text = _normalize(value)
    if text.strip() in {"apache-2.0", "apache-2"}:
        return True
    return _APACHE_URL.search(text) is not None or _APACHE_PHRASE.search(text) is not None


def _states_mpl(value: str) -> bool:
    text = _normalize(value)
    if text.strip() in {"mpl-2.0", "mpl 2.0"}:
        return True
    return _MPL_URL.search(text) is not None or _MPL_PHRASE.search(text) is not None


def _normalize(value: str) -> str:
    text = unescape(value).casefold().replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text)


def _header_dates(visible_html: str) -> list[str]:
    found: list[str] = []
    for month, day, year in _HEADER_DATE.findall(visible_html):
        parsed = _long_date(month, day, year)
        if parsed:
            found.append(parsed)
    return found


def _dateline_dates(visible_html: str) -> list[str]:
    """A letter dateline is one text-size-sm div whose only text is a date.

    Listing dates use a filter field. Last updated, modified, and copyright
    lines are not datelines.
    """

    found: list[str] = []
    for attrs, month, day, year in _DATELINE.findall(visible_html):
        classes = set(re.findall(r"[a-z0-9-]+", attrs.casefold()))
        if "text-size-sm" not in classes or "hide" in classes:
            continue
        if "fs-cmsfilter-field" in attrs.casefold():
            continue
        window = attrs.casefold()
        if any(word in window for word in ("updated", "modified", "copyright")):
            continue
        parsed = _long_date(month, day, year)
        if parsed:
            found.append(parsed)
    return found


def _unique_date(found: list[str]) -> str | None:
    unique = set(found)
    if len(unique) == 1:
        return next(iter(unique))
    return None


def _long_date(month: str, day: str, year: str) -> str | None:
    try:
        parsed = date(int(year), _MONTHS[month.casefold()], int(day))
    except (KeyError, ValueError):
        return None
    return parsed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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
    text = _clean_text(value).translate(_DASHES)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix.casefold()) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(_HIDDEN.sub(" ", page_text))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, keys: frozenset[str]) -> list[str]:
    values: list[str] = []
    for key, content in _metas(page_html).items():
        if key in keys and content:
            values.append(content)
    return values


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINKISH.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _canonical_href(page_html: str) -> str:
    visible = _HIDDEN.sub(" ", page_html)
    for tag in _LINKISH.findall(visible):
        attrs = _attrs(tag)
        if "canonical" in attrs.get("rel", "").lower().split() and attrs.get("href"):
            return attrs["href"]
    return ""


def _anchor_parts(page_html: str) -> list[tuple[str, str]]:
    return [(raw, inner) for raw, inner in _ANCHOR.findall(page_html)]


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
