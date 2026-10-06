"""Metadata catalog of public Transluce pages.

Transluce is the interpretability research organization. Rows are page
metadata, not a product dump and not person records. Each stored URL was
confirmed with one bounded GET that returned HTML from an official Transluce
host. www.transluce.org redirects to transluce.org. A Cloudflare challenge, a
captcha, an HTTP 202, an Akamai 403, a consent interstitial, a non-HTML
response, or a redirect off the confirmed host is not stored.

A row keeps the title, publisher, canonical URL, date, and rights label.
Page bodies, abstracts, PDFs, quotes, transcripts, chart data, and model
outputs are not stored. A missing date stays unknown. Updated, modified, and
copyright years are not publication dates.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` is only CC0 or CC BY-SA. A page that states CC BY
together with CC0 or CC BY-SA may use ``creative_commons``.
``creative_commons_attribution`` is a CC BY deed that does not state NC, ND,
or SA. ``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_nd``, and ``cc_by_nc_sa`` stay
their own tokens. Longer deeds are checked first. A hyphen is a word
boundary: ``(?![a-z0-9-])`` stops the text CC BY from matching CC BY-NC and
stops ``licenses/by`` from matching ``licenses/by-nc``. A restricted deed
beside a permissive deed stays unknown. A CC BY anchor whose href is a
restricted or public-domain mark URL stays unknown. The Public Domain Mark
is not CC0. ``uk_ogl`` requires the British phrase open government licence.
``us_government_work`` requires a rights field. ``mit``, ``apache-2.0``, and
``mpl-2.0`` are their own tokens. Mixed software licences stay unknown. The
letters MIT inside a university or person name are not the MIT licence.

This module does not fetch. It is not a belief collector, and runner_wired
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

CATALOG_ID = "transluce_pages"
CATALOG_FILENAME = "transluce_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
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
PUBLISHER = "Transluce"
APEX_HOST = "transluce.org"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
OGL_PHRASE = "open government licence"
CATALOG_DESCRIPTION = (
    "Metadata for public pages of Transluce, the interpretability research organization. "
    "Each stored URL was confirmed with one bounded GET of HTML from an official Transluce host. "
    "www.transluce.org redirects to transluce.org. Challenges and redirects off the host are omitted. "
    "Rows store the title, publisher, canonical URL, date, and rights. "
    "Page bodies, PDFs, quotes, and model outputs are not stored. "
    "A missing date is unknown. Updated, modified, and copyright years are not publication dates. "
    "creative_commons is CC0 or CC BY-SA. creative_commons_attribution is CC BY alone. "
    "Restricted deeds keep their own tokens. A restricted deed with a permissive deed stays unknown. "
    "uk_ogl requires the phrase open government licence. runner_wired is false."
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
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dcterms.rights",
    }
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "checking your browser",
    "enable javascript and cookies",
    "sgcaptcha",
    "attention required! | cloudflare",
    "are you a robot",
    "are you human",
    "akamai bot manager",
    "errors.edgesuite.net",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4})[-/](\d{2})[-/](\d{2})")
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_RIGHTS = re.compile(r'"(?:license|licence|rights)"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
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
_PUBLISHED_ISO = re.compile(
    r"(?i)(?<![A-Za-z])published\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_PUBLISHED_MONTH = re.compile(
    r"(?i)(?<![A-Za-z])published\s*:\s*"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+(\d{4})\b"
)
_SITE_SUFFIXES = (
    " | Transluce AI",
    " - Transluce AI",
    " — Transluce AI",
    " – Transluce AI",
    " | Transluce Behavior Reports",
    " — Transluce Behavior Reports",
    " – Transluce Behavior Reports",
    " - Transluce Behavior Reports",
    " | Transluce",
    " — Transluce",
    " – Transluce",
    " - Transluce",
)
_SITE_PREFIXES = (
    "Transluce - ",
    "Transluce — ",
    "Transluce – ",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)
_BLOCKED_PREFIXES = ("/api", "/_next", "/cdn-cgi", "/wp-admin", "/wp-content", "/wp-includes")
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
# Longer deeds are first. (?![a-z0-9-]) makes a hyphen a boundary, so
# licenses/by does not match licenses/by-nc and CC BY does not match CC BY-NC.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<deed>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_PROSE_CODES = (
    (
        RIGHTS_CC_BY_NC_ND,
        re.compile(
            r"(?i)(?:"
            r"\bcc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9-])"
            r"|attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
            r")"
        ),
    ),
    (
        RIGHTS_CC_BY_NC_SA,
        re.compile(
            r"(?i)(?:"
            r"\bcc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9-])"
            r"|attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
            r")"
        ),
    ),
    (
        RIGHTS_CC_BY_NC,
        re.compile(
            r"(?i)(?:"
            r"\bcc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)(?![a-z0-9-])"
            r"|attribution[\s-]*non[\s-]*commercial(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
            r")"
        ),
    ),
    (
        RIGHTS_CC_BY_ND,
        re.compile(
            r"(?i)(?:"
            r"\bcc[\s-]*by[\s-]*nd(?![a-z0-9-])"
            r"|attribution[\s-]*no[\s-]*deriv"
            r")"
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"(?i)(?:"
            r"\bcc[\s-]*by[\s-]*sa(?![\s-]*(?:nc|nd)\b)(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution[\s-]*share[\s-]*alike(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))"
            r")"
        ),
    ),
    (
        "cc-by",
        re.compile(
            r"(?i)(?:"
            r"\bcc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|sa|nc|nd)\b)"
            r")"
        ),
    ),
    (
        "cc0",
        re.compile(
            r"(?i)(?:"
            r"(?<![a-z0-9])(?:cc0|cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9-])"
            r"|creative\s+commons(?:\s+public\s+domain)?[\s-]+(?:cc[\s-]*)?zero\b"
            r")"
        ),
    ),
)
_URL_DEED = {
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-sa": "cc-by-sa",
    "by": "cc-by",
    "zero": "cc0",
}
_PERMISSIVE = frozenset({"cc0", "cc-by", "cc-by-sa"})
_RESTRICTED = frozenset(
    {RIGHTS_CC_BY_NC, RIGHTS_CC_BY_ND, RIGHTS_CC_BY_NC_ND, RIGHTS_CC_BY_NC_SA}
)
_SOFTWARE = frozenset({RIGHTS_MIT, RIGHTS_APACHE, RIGHTS_MPL})
_PDM_PROSE = re.compile(r"(?i)\bpublic\s+domain\s+mark\b")
_MIT = re.compile(
    r"(?i)(?:"
    r"\bmit\s+licen[cs]e\b"
    r"|\blicen[cs]ed under (?:the )?mit\s+licen[cs]e\b"
    r"|\bspdx-licen[cs]e-identifier\s*:\s*mit(?![a-z0-9-])"
    r")"
)
_APACHE = re.compile(
    r"(?i)\bapache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2\.0\b"
)
_MPL = re.compile(
    r"(?i)(?:\bmpl[\s-]*2\.0\b|\bmozilla\s+public\s+licen[cs]e(?:\s+version)?\s*2\.0\b)"
)
_US_GOV_WORK = re.compile(
    r"(?i)(?:"
    r"\bus\s+government\s+works?\b"
    r"|\bu\.s\.\s+government\s+works?\b"
    r"|\bunited\s+states\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+united\s+states\s+government\b"
    r"|\bworks?\s+of\s+the\s+u\.s\.\s+government\b"
    r"|\bworks?\s+of\s+the\s+us\s+government\b"
    r")"
)
_US_GOV_NEGATED = re.compile(
    r"(?i)(?:"
    r"\bnot\s+(?:a\s+)?(?:us|u\.s\.|united\s+states)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r")"
)
_HOST_WORD = re.compile(r"(?i)\btransluce\.org\b")
_ORG_WORD = re.compile(r"(?i)\btransluce\b")


class CatalogError(ValueError):
    """A catalog row or page failed the Transluce page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_transluce_host(hostname: str) -> bool:
    """True for transluce.org and its public subdomains."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == APEX_HOST or host.endswith("." + APEX_HOST)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons`` is CC0 or CC BY-SA, including a page that also states
    CC BY. ``creative_commons_attribution`` is CC BY alone. Restricted deeds
    keep their own tokens. A hyphen is a boundary, so CC BY does not match
    CC BY-NC. A deceptive CC BY anchor on a restricted or public-domain mark
    URL stays unknown. Public Domain Mark is not CC0. A generic
    creativecommons.org/licenses/ URL stays unknown. ``uk_ogl`` requires the
    British spelling. ``us_government_work`` requires a rights field.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    pdm = False
    rights_fields = _rights_field_values(page_text)
    for value in rights_fields:
        found, found_pdm = _codes_in(value)
        codes.update(found)
        pdm = pdm or found_pdm
    visible = _visible(page_text)
    kept, anchor_codes, anchor_pdm = _take_anchors(visible)
    codes.update(anchor_codes)
    pdm = pdm or anchor_pdm
    for href in _license_hrefs(kept):
        found, found_pdm = _codes_in(href)
        codes.update(found)
        pdm = pdm or found_pdm
    plain = _plain(kept)
    found, found_pdm = _codes_in(plain)
    codes.update(found)
    pdm = pdm or found_pdm
    if OGL_PHRASE in plain.casefold():
        codes.add(RIGHTS_UK_OGL)
    if _states_us_government_work("\n".join(rights_fields)):
        codes.add(RIGHTS_US_GOVERNMENT_WORK)
    return _rights_label(codes, pdm)


def date_from_page(page_text: str) -> str:
    """Return a publication date, or unknown when the page does not state one.

    Updated, modified, and copyright years are not publication dates.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        found = _iso_from_text(metas.get(key, ""))
        if found:
            return found
    published = _DATE_PUBLISHED.findall(page_text)
    unique = []
    for raw in published:
        if raw not in unique and _iso_date(raw):
            unique.append(raw)
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        return UNKNOWN_DATE
    plain = _plain(visible)
    match = _PUBLISHED_ISO.search(plain)
    if match and _iso_date(match.group(1)):
        return match.group(1)
    month = _PUBLISHED_MONTH.search(plain)
    if month:
        found = _ymd(int(month.group(3)), _MONTHS[month.group(1).casefold()], int(month.group(2)))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "twitter:title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Transluce when the page states that organization name.

    A hostname ending in .org is not enough. A person named on the page is
    not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    titled = " ".join(metas.get(key, "") for key in ("og:site_name", "og:title", "citation_title"))
    title_tag = _TITLE.search(visible)
    title_text = title_tag.group(1) if title_tag else ""
    blob = " ".join((titled, title_text, _plain(visible)))
    if not _states_publisher(blob):
        raise CatalogError("publisher is required")
    return PUBLISHER


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    return content_type.split(";", 1)[0].strip().casefold() in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:8000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(_visible(page_html[:8000]))
    if match is None:
        return False
    title = _plain(match.group(1)).casefold()
    return title in {"just a moment...", "attention required! | cloudflare", "access denied"}


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
) -> bool:
    """A row requires HTTP 200 HTML on an official host, with no redirect hop."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html) or _challenge_headers(headers):
        return False
    if hops:
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
    hops: tuple[str, ...] | list[str] | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML. Otherwise return None."""

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        hops=hops,
    ):
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=page_url)


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


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Transluce page")
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
        or not official_transluce_host(host)
        or ".." in path
        or "\\" in url
        or "//" in path
        or "%" in path
        or _blocked_path(path)
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL is not a public Transluce page: {url}")
    return url


def _rights_label(codes: set[str], pdm: bool) -> str:
    if pdm:
        return RIGHTS_UNKNOWN
    permissive = codes & _PERMISSIVE
    restricted = codes & _RESTRICTED
    software = codes & _SOFTWARE
    other = codes - _PERMISSIVE - _RESTRICTED - _SOFTWARE
    if restricted and permissive:
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if software and (permissive or restricted or other):
        return RIGHTS_UNKNOWN
    if len(software) > 1:
        return RIGHTS_UNKNOWN
    if permissive and other:
        return RIGHTS_UNKNOWN
    if restricted and other:
        return RIGHTS_UNKNOWN
    if len(other) > 1:
        return RIGHTS_UNKNOWN
    if permissive:
        if "cc0" in permissive or "cc-by-sa" in permissive:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_CC_BY
    if len(restricted) == 1:
        return next(iter(restricted))
    if len(software) == 1:
        return next(iter(software))
    if other == {RIGHTS_UK_OGL}:
        return RIGHTS_UK_OGL
    if other == {RIGHTS_US_GOVERNMENT_WORK}:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def _codes_in(value: str) -> tuple[set[str], bool]:
    text = unescape(value or "").replace("\\/", "/").translate(_DASHES)
    codes: set[str] = set()
    pdm = False
    for match in _CC_URL.finditer(text):
        deed = (match.group("deed") or "").casefold()
        pd = (match.group("pd") or "").casefold()
        if deed in _URL_DEED:
            codes.add(_URL_DEED[deed])
        elif pd == "zero":
            codes.add("cc0")
        elif pd == "mark":
            pdm = True
    if _PDM_PROSE.search(text):
        pdm = True
    for label, pattern in _PROSE_CODES:
        if pattern.search(text):
            codes.add(label)
    if _MIT.search(text):
        codes.add(RIGHTS_MIT)
    if _APACHE.search(text):
        codes.add(RIGHTS_APACHE)
    if _MPL.search(text):
        codes.add(RIGHTS_MPL)
    return codes, pdm


def _take_anchors(html: str) -> tuple[str, set[str], bool]:
    """Drop deceptive anchors. Their text does not reclassify the href."""

    codes: set[str] = set()
    pdm = False

    def replace(match: re.Match[str]) -> str:
        nonlocal pdm
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        href_codes, href_pdm = _codes_in(href)
        text_codes, text_pdm = _codes_in(_plain(match.group(2)))
        deceptive = bool(text_codes & _PERMISSIVE) and (bool(href_codes & _RESTRICTED) or href_pdm)
        if "cc0" in text_codes and href_pdm:
            deceptive = True
        if deceptive:
            return " "
        codes.update(href_codes)
        codes.update(text_codes)
        pdm = pdm or href_pdm or text_pdm
        return " "

    return _ANCHOR.sub(replace, html), codes, pdm


def _rights_field_values(page_html: str) -> list[str]:
    visible = _visible(page_html)
    values = [value for value in _meta_values(visible, _LICENSE_META)]
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_RIGHTS.findall(blob):
            values.append(raw.replace("\\/", "/").replace("\\u002f", "/"))
    return values


def _states_us_government_work(value: str) -> bool:
    text = unescape(value or "").translate(_DASHES)
    if not text.strip() or _US_GOV_NEGATED.search(text):
        return False
    return _US_GOV_WORK.search(text) is not None


def _license_hrefs(html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(html):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold()
        href = attrs.get("href", "")
        if href and "license" in rel.split():
            hrefs.append(href)
    return hrefs


def _states_publisher(value: str) -> bool:
    without_host = _HOST_WORD.sub(" ", value or "")
    return _ORG_WORD.search(without_host) is not None


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value)
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    for prefix in _SITE_PREFIXES:
        if text.startswith(prefix) and len(text) > len(prefix):
            text = text[len(prefix) :].strip()
            break
    return text


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
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in keys and attrs.get("content"):
            values.append(attrs["content"])
    return values


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _iso_from_text(value: str) -> str | None:
    match = _DATE_PREFIX.match((value or "").strip())
    if match is None:
        return None
    return _ymd(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _iso_date(value: str) -> bool:
    return bool(value) and _DATE.fullmatch(value) is not None and _iso_from_text(value) == value


def _ymd(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _blocked_path(path: str) -> bool:
    lowered = path.lower()
    if lowered in {"", "/"}:
        return False
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    return any(bare == prefix or bare.startswith(prefix + "/") for prefix in _BLOCKED_PREFIXES)


def _is_download(path: str) -> bool:
    lowered = path.lower()
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    return bare.endswith(_DOWNLOAD_SUFFIXES)


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "server" and "akamai" in text and "403" in text:
            return True
    return False


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > MAX_FIELD_CHARS:
        raise CatalogError(f"{field} is too long to store")


def _reject_stored_body(document: dict, *, path: str = "catalog") -> None:
    for key in document:
        if str(key).casefold() in _FORBIDDEN_KEYS:
            raise CatalogError(f"{path} must not store page text")
