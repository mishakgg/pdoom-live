"""Metadata catalog of public OECD.AI Policy Observatory pages.

Each stored URL was confirmed with one bounded GET that returned HTML on
oecd.ai. A row keeps the title, publisher, canonical URL, date, and rights
label. Abstracts, chart data, indicator tables, and page bodies are not
stored. A Cloudflare challenge, a SiteGround captcha, an HTTP 202 challenge,
an Akamai 403, a robots disallow, a non-HTML response, or a redirect off-host
is not stored.

Rights stay unknown unless the page states a reuse licence. ``creative_commons``
means only CC0, CC BY, or CC BY-SA. ``creative_commons_attribution`` means CC BY
alone, without NC, ND, or SA. CC BY-NC, CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA
keep their own tokens. CC BY-NC-SA 3.0 IGO keeps ``cc_by_nc_sa_3_0_igo`` and is
not ``creative_commons``. A hyphen is a word boundary, so CC BY does not match
CC BY-NC. A restricted deed is recognized before a permissive one. A page that
states both stays unknown. The Public Domain Mark is not CC0. A copyright
notice, All rights reserved, a terms link, and the words Public or Disclosed
are not licences. ``eu_reuse_decision`` requires the text Decision 2011/833/EU.
``uk_ogl`` requires the British phrase "open government licence".
``us_government_work`` requires a rights field that says the item is a US
government work. MIT, Apache-2.0, and MPL-2.0 keep their own tokens. A missing
publication date stays unknown. Updated, modified, and copyright years are not
publication dates.

This module does not fetch. runner_wired stays false. It is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "oecd_ai_pages"
CATALOG_FILENAME = "oecd_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "OECD.AI"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_SA_3_0_IGO = "cc_by_nc_sa_3_0_igo"
RIGHTS_EU_REUSE = "eu_reuse_decision"
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
        RIGHTS_CC_BY_NC_SA_3_0_IGO,
        RIGHTS_EU_REUSE,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
OFFICIAL_HOST = "oecd.ai"
MAX_TEXT_CHARS = 400
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
        "indicator",
        "indicator_table",
        "indicators",
        "page",
        "page_text",
        "pdf",
        "pdoom",
        "p_doom",
        "probability",
        "quotation",
        "quote",
        "summary",
        "table",
        "text",
        "transcript",
        "transcript_text",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_LICENSE_META = frozenset(
    {
        "rights",
        "dc.rights",
        "dcterms.rights",
        "license",
        "licence",
        "dcterms.license",
    }
)
_US_GOV_FIELDS = frozenset({"rights", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_SUFFIXES = (
    " - OECD.AI",
    " | OECD.AI",
    " – OECD.AI",
    " — OECD.AI",
)
_SHELL_TITLE = "oecd ai policy observatory portal"
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "sgcaptcha",
    "sg-captcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
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
    ".js",
    ".css",
)
# Confirmed robots.txt prefixes for User-agent: *. A disallow stores no row.
_ROBOTS_DISALLOW_PREFIXES = (
    "/fr/community/",
    "/fr/catalogue/",
    "/fr/wonk/",
    "/fr/dashboards/",
    "/fr/data",
)
_BLOCKED_PREFIXES = (
    "/.well-known",
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
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
# Longer deeds are listed first. (?!-) keeps CC BY from matching inside CC BY-NC.
# licenses/by uses the same hyphen boundary so it does not match licenses/by-nc.
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "igo",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa[\s-]*3(?:\.0)?[\s-]*igo(?![a-z0-9])"
        ),
    ),
    (
        "igo",
        re.compile(
            r"attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike[\s-]*3(?:\.0)?[\s-]*igo(?![a-z0-9])"
        ),
    ),
    (
        "by-nc-nd",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])"),
    ),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])"),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    (
        "by-nc",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial"),
    ),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-nd", re.compile(r"creative commons attribution[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]*share[\s-]*alike")),
    (
        "zero",
        re.compile(r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])"),
    ),
    (
        "zero",
        re.compile(r"creative commons(?:\s+public\s+domain)?[\s-]*zero(?![a-z])"),
    ),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![a-z0-9])")),
    (
        "by",
        re.compile(
            r"creative commons attribution(?![\s-]*(?:non|no[\s-]*deriv|share))"
        ),
    ),
    ("mark", re.compile(r"public domain mark")),
)
_URL_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "igo",
        re.compile(r"creativecommons\.org/licenses/by-nc-sa/3\.0/igo(?![a-z0-9-])"),
    ),
    (
        "by-nc-nd",
        re.compile(r"creativecommons\.org/licenses/by-nc-nd(?![a-z0-9-])"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creativecommons\.org/licenses/by-nc-sa(?![a-z0-9-])"),
    ),
    ("by-nc", re.compile(r"creativecommons\.org/licenses/by-nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"creativecommons\.org/licenses/by-nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"creativecommons\.org/licenses/by-sa(?![a-z0-9-])")),
    ("by", re.compile(r"creativecommons\.org/licenses/by(?!-)(?![a-z0-9])")),
    ("zero", re.compile(r"creativecommons\.org/publicdomain/zero(?![a-z0-9-])")),
    ("mark", re.compile(r"creativecommons\.org/publicdomain/mark(?![a-z0-9-])")),
)
_RESTRICTED_TOKENS = {
    "igo": RIGHTS_CC_BY_NC_SA_3_0_IGO,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
}
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_MIT_PHRASE = re.compile(r"\bmit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_PHRASE = re.compile(r"\bapache-2\.0\b|\bapache licen[cs]e(?:\s+version)?\s*2\.0\b")
_APACHE_URL = re.compile(
    r"(?:www\.)?apache\.org/licenses/license-2\.0(?![a-z0-9])|spdx\.org/licenses/apache-2\.0(?![a-z0-9-])"
)
_MPL_PHRASE = re.compile(r"\bmpl-2\.0\b|\bmozilla public licen[cs]e(?:\s*2\.0)?\b")
_MPL_URL = re.compile(r"mozilla\.org/mpl/2\.0(?![a-z0-9])")
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_EU_REUSE = re.compile(r"\bdecision\s+2011/833/eu\b")
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the OECD.AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_oecd_ai_host(hostname: str) -> bool:
    """True only for the confirmed oecd.ai host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label stated by the page, or unknown.

    Restricted deeds are matched before permissive ones. CC BY-NC is not CC BY.
    A page that states both a restricted deed and a permissive deed stays
    unknown. ``creative_commons_attribution`` is CC BY with no NC, ND, or SA.
    ``creative_commons`` is CC0 or CC BY-SA, including a permissive mix of CC0,
    CC BY, and CC BY-SA. MIT, Apache-2.0, and MPL-2.0 are not folded into
    ``creative_commons``. Mixed MIT or Apache with a permissive Creative Commons
    deed stays unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    plain = _plain(visible)
    folded = plain.casefold().translate(_DASHES)
    codes = _text_codes(folded)
    hrefs = _hrefs(visible)
    for href in hrefs:
        codes |= _url_code(href.casefold().translate(_DASHES))
    licence_bits: list[str] = []
    us_gov = False
    for key, content in _meta_pairs(visible):
        if key not in _LICENSE_META:
            continue
        chunk = _plain(content).casefold().translate(_DASHES)
        licence_bits.append(chunk)
        codes |= _text_codes(chunk)
        codes |= _url_code(chunk)
        if key in _US_GOV_FIELDS and _states_us_government_work(chunk):
            us_gov = True
    scanned = " ".join([folded, *licence_bits, *(href.casefold() for href in hrefs)])
    mit = bool(_MIT_PHRASE.search(scanned) or any(_MIT_URL.search(href.casefold()) for href in hrefs))
    apache = bool(
        _APACHE_PHRASE.search(scanned) or any(_APACHE_URL.search(href.casefold()) for href in hrefs)
    )
    mpl = bool(_MPL_PHRASE.search(scanned) or any(_MPL_URL.search(href.casefold()) for href in hrefs))
    return _label(
        codes,
        mit=mit,
        apache=apache,
        mpl=mpl,
        ogl=bool(_OGL_PHRASE.search(folded)),
        eu=bool(_EU_REUSE.search(folded)),
        us_gov=us_gov,
    )


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, and copyright years are not publication dates. A date
    inside script or style text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_without_hidden(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    document_title = _clean_title(title_tag.group(1) if title_tag else "")
    if _usable_title(document_title):
        return document_title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title:
            return title
    if document_title:
        return document_title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return OECD.AI when the page states that name.

    A copyright line that only says OECD, and a terms link, do not invent a
    different publisher. The name is taken from visible page text.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if PUBLISHER.casefold() not in _plain(_without_hidden(page_html)).casefold():
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
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


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
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a robot or challenge response."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            if name == "sg-captcha":
                return False
            if name == "cf-mitigated" and "challenge" in str(value).casefold():
                return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict[str, str] | None = None,
) -> dict | None:
    """Return metadata when the bounded response is the page HTML.

    A Cloudflare challenge, a SiteGround captcha, an HTTP 202 challenge, an
    Akamai 403, or a non-HTML response is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
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
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if description != description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
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
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public oecd.ai page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not official_oecd_ai_host(host)
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public oecd.ai page: {url}")
    return url


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


def _label(
    codes: set[str],
    *,
    mit: bool,
    apache: bool,
    mpl: bool,
    ogl: bool,
    eu: bool,
    us_gov: bool,
) -> str:
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    restricted = codes & set(_RESTRICTED_TOKENS)
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
            ("eu", eu),
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
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    if eu:
        return RIGHTS_EU_REUSE
    if ogl:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def _states_us_government_work(field: str) -> bool:
    if _NEGATED_GOV_WORK.search(field):
        return False
    return _GOV_WORK.search(field) is not None


def _text_codes(folded: str) -> set[str]:
    found: list[tuple[int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            start, end = match.span()
            if any(start < prev_end and end > prev_start for prev_start, prev_end, _code in found):
                continue
            found.append((start, end, code))
    return {code for _start, _end, code in found}


def _url_code(value: str) -> set[str]:
    for code, pattern in _URL_DEEDS:
        if pattern.search(value):
            return {code}
    return set()


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/") or ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    lowered = path.casefold()
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if any(lowered.startswith(prefix) for prefix in _ROBOTS_DISALLOW_PREFIXES):
        return False
    return not any(bare.startswith(prefix) for prefix in _BLOCKED_PREFIXES)


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() != _SHELL_TITLE


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _iso_prefix(value: object) -> str | None:
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


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value:
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
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


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


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _hrefs(visible_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in [*_LINK.findall(visible_html), *_ANCHOR.findall(visible_html)]:
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _meta_pairs(visible_html: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for tag in _META.findall(visible_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs:
            pairs.append((key, attrs["content"]))
    return pairs


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
