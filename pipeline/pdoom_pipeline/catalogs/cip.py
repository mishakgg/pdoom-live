"""Metadata catalog of public Collective Intelligence Project pages.

Each stored URL was confirmed with one bounded HTML GET of www.cip.org.
The apex host cip.org redirects there and is not stored. A row keeps the
title, publisher, canonical URL, date, and rights label. Page text is not
stored. A Cloudflare challenge, a captcha, HTTP 202, an Akamai 403, a
robots-disallowed path, an oversized response, or an off-host redirect is
not stored.

``creative_commons`` means only a stated CC0, CC BY, or CC BY-SA deed.
CC BY-NC, CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA keep their own tokens and
are never folded into ``creative_commons``. A page that states both a
restricted deed and a permissive deed stays unknown. A hyphen is a word
boundary, so CC BY does not match CC BY-NC, and licenses/by does not match
licenses/by-nc. A generic
creativecommons.org/licenses/ URL is not a permissive deed. The Public
Domain Mark is not CC0. A copyright notice, All rights reserved, a terms
link, or a host name is not a licence. ``uk_ogl`` is used only when the page
text contains the British phrase open government licence. ``us_government_work``
is used only when a rights field says the item is a US government work.
``mit``, ``apache-2.0``, and ``mpl-2.0`` stay their own tokens.

A page that does not state a publication date keeps the date unknown.
Updated, modified, and copyright years are not publication dates. The live
URL is stored as confirmed; a different rel=canonical does not replace it.
This module does not fetch and it is not a belief collector. runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cip_pages"
CATALOG_FILENAME = "cip_pages.json"
RUNNER_WIRED = False
PUBLISHER = "The Collective Intelligence Project"
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
CIP_HOST = "www.cip.org"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
MAX_RESPONSE_BYTES = 1_000_000
MAX_REDIRECTS = 5
FETCH_TIMEOUT_SECONDS = 12

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_MARK_HREF = re.compile(r"creativecommons\.org/publicdomain/mark(?![a-z0-9-])")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
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
        "dc.rights.license",
        "dcterms.rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title", "twitter:title")
_SITE_SUFFIX = re.compile(
    r"(?i)\s*(?:\||[\-\u2010\u2011\u2012\u2013\u2014\u2212])\s*(?:the\s+)?collective intelligence project\s*$"
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "cf-browser-verification",
    "checking your browser",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
    "please verify you are a human",
    "verify you are human",
    "sorry, you have been blocked",
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
_ROBOTS_PREFIXES = (
    "/config",
    "/search",
    "/account",
    "/commerce/digital-download",
    "/static",
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
# Longer deeds are listed first. A hyphen is not a word boundary here: the
# character after "by" may be "-", so CC BY must not match inside CC BY-NC
# and licenses/by must not match licenses/by-nc.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<lic>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_TEXT_DEEDS = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9-])")),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9-])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?![a-z0-9-])")),
    (
        "by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial(?![\s-]*(?:share|no))"
        ),
    ),
    ("by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    (
        "by-sa",
        re.compile(
            r"creative commons attribution[\s-]+share[\s-]*alike(?![\s-]*(?:non|no))"
        ),
    ),
    (
        "by",
        re.compile(
            r"creative commons attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*derivatives?|share[\s-]*alike|nc|nd|sa)\b)"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:cc0|cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])"
            r"|creative commons(?: public domain)? zero(?![a-z])"
        ),
    ),
)
_PD_MARK = re.compile(r"public domain mark\b")
_EXPLICIT_ZERO = re.compile(
    r"(?<![a-z0-9])(?:cc0|cc[\s-]*zero)(?![a-z0-9])"
    r"|creativecommons\.org/publicdomain/zero(?![a-z0-9-])"
)
_MIT = re.compile(
    r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b"
)
_APACHE = re.compile(
    r"\bapache-2\.0\b"
    r"|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
    r"|\blicen[cs]ed under (?:the )?apache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_MPL = re.compile(
    r"\bmpl-2\.0\b"
    r"|\bmozilla public licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_OGL = re.compile(r"open government licence(?![a-z])")
_US_GOV = re.compile(
    r"\bu\.?\s*s\.?\s+government work\b"
    r"|\bunited states government work\b"
    r"|\bwork of the (?:u\.?\s*s\.?|united states) government\b"
)
_RESTRICTED_PRIORITY = (
    ("by-nc-nd", RIGHTS_CC_BY_NC_ND),
    ("by-nc-sa", RIGHTS_CC_BY_NC_SA),
    ("by-nc", RIGHTS_CC_BY_NC),
    ("by-nd", RIGHTS_CC_BY_ND),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
# A restricted token is not returned when one of these is also stated.
_BLOCKS_RESTRICTED = frozenset({"by", "by-sa", "zero", "mit", "apache-2.0", "mpl-2.0"})
_SOFTWARE = (
    ("apache-2.0", RIGHTS_APACHE),
    ("mpl-2.0", RIGHTS_MPL),
    ("mit", RIGHTS_MIT),
)
_URL_CODES = {
    "by": "by",
    "by-sa": "by-sa",
    "by-nc": "by-nc",
    "by-nd": "by-nd",
    "by-nc-sa": "by-nc-sa",
    "by-nc-nd": "by-nc-nd",
    "zero": "zero",
}


class CatalogError(ValueError):
    """A catalog row or page failed the Collective Intelligence Project page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must stay false")
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
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be a known token or unknown")


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
        raise CatalogError("canonical URL must be a public Collective Intelligence Project page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc != CIP_HOST
        or host != CIP_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Collective Intelligence Project page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == CIP_HOST and not hostname_is_blocked(host)


def redirect_stays_official(page_url: str, location: str) -> bool:
    """False when a redirect leaves www.cip.org."""

    if not isinstance(page_url, str) or not isinstance(location, str):
        return False
    host = (urlparse(urljoin(page_url, location)).hostname or "").lower().rstrip(".")
    return is_official_host(host)


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
) -> bool:
    """A page is stored only from HTML that is not a block or a challenge.

    HTTP 202, HTTP 403 (including an Akamai 403), a captcha, and a Cloudflare
    challenge are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "server" and ("akamaighost" in token or "edgesuite" in token):
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

    A challenge, HTTP 202, HTTP 403, a non-HTML body, an off-host URL, or a
    robots-disallowed path is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
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

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. A sole CC BY-NC,
    CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND deed keeps its own token. A restricted
    deed together with CC BY, CC BY-SA, CC0, MIT, or Apache-2.0 stays unknown.
    A hyphen is a word boundary, so CC BY does not match CC BY-NC and
    licenses/by does not match licenses/by-nc. An anchor whose text says CC BY,
    CC BY-SA, or CC0 while the href is a restricted deed or the Public Domain
    Mark stays unknown. The Public Domain Mark is not CC0. ``mit``,
    ``apache-2.0``, and ``mpl-2.0`` are not folded into ``creative_commons``.
    MIT together with CC BY stays unknown, and two software licences stay
    unknown. ``uk_ogl`` requires the phrase open government licence.
    ``us_government_work`` requires a rights field. A copyright notice, All
    rights reserved, a terms link, and a host name are not licences. Script
    and style text does not count, except a JSON-LD license or rights field.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    rights_fields = _rights_fields(page_text)
    for field in rights_fields:
        codes.update(_codes_in_fragment(field))
    visible = _drop_mark_anchors(_visible(page_text))
    for href in _hrefs(visible):
        codes.update(_codes_in_fragment(href))
    plain = _fold(_plain_text(visible))
    codes.update(_codes_in_fragment(plain))
    ogl = _OGL.search(plain) is not None or any(_OGL.search(_fold(field)) for field in rights_fields)
    us_gov = any(_US_GOV.search(_fold(field)) for field in rights_fields)
    return _label(codes, ogl=ogl, us_gov=us_gov)


def publication_date_from_page(page_html: str, *, page_url: str | None = None) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    JSON-LD datePublished counts only for the node whose URL is this page.
    article:modified_time, dateModified, og:updated_time, and a copyright
    year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if page_url:
        for raw in _matching_published_dates(page_html, page_url):
            found = _iso_day(raw)
            if found:
                return found
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_day(metas.get(key, ""))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str, *, page_url: str | None = None) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if page_url:
        for headline in _matching_headlines(page_html, page_url):
            title = _clean_title(headline)
            if title:
                return title
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
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


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return the project name when the page states it.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible(page_html)
    site = _metas(visible).get("og:site_name", "")
    if PUBLISHER.casefold() in _clean_text(site).casefold():
        return PUBLISHER
    if PUBLISHER.casefold() in _plain_text(visible).casefold():
        return PUBLISHER
    for name in _organization_names(page_html):
        if PUBLISHER.casefold() in name.casefold():
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
        "title": title_from_page(page_html, page_url=page_url),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html, page_url=page_url),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    decoded = unquote(path)
    if ".." in path or ".." in decoded or "\\" in path or "\\" in decoded or "//" in path or "//" in decoded:
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    if bare == "/api" or bare.startswith("/api/"):
        return bare == "/api/ui-extensions" or bare.startswith("/api/ui-extensions/")
    return not any(bare == prefix or bare.startswith(prefix + "/") for prefix in _ROBOTS_PREFIXES)


def _label(codes: set[str], *, ogl: bool, us_gov: bool) -> str:
    restricted = [token for code, token in _RESTRICTED_PRIORITY if code in codes]
    permissive = bool(codes & _PERMISSIVE)
    software = [token for code, token in _SOFTWARE if code in codes]
    if restricted and (codes & _BLOCKS_RESTRICTED):
        return RIGHTS_UNKNOWN
    if restricted:
        return restricted[0]
    if len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(software) == 1 and permissive:
        return RIGHTS_UNKNOWN
    if len(software) == 1:
        return software[0]
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    if ogl:
        return RIGHTS_UK_OGL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def _codes_in_fragment(fragment: str) -> set[str]:
    folded = _fold(fragment).replace("\\/", "/")
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        kind = (match.group("lic") or match.group("pd") or "").lower()
        code = _URL_CODES.get(kind)
        if code:
            codes.add(code)
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    if _MIT.search(folded):
        codes.add("mit")
    if _APACHE.search(folded):
        codes.add("apache-2.0")
    if _MPL.search(folded):
        codes.add("mpl-2.0")
    # A Public Domain Mark is not CC0. Drop a zero code when the fragment has
    # no separate CC0 or publicdomain/zero deed.
    if "zero" in codes and _PD_MARK.search(folded) and _EXPLICIT_ZERO.search(folded) is None:
        codes.discard("zero")
    return codes


def _drop_mark_anchors(page_html: str) -> str:
    """Drop anchors whose href is the Public Domain Mark.

    The visible text of that anchor is not a CC0, CC BY, or CC BY-SA deed.
    """

    def replace(match: re.Match[str]) -> str:
        href = _fold(_attrs("<a " + match.group(1) + ">").get("href", "")).replace("\\/", "/")
        if _MARK_HREF.search(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, page_html)


def _rights_fields(page_html: str) -> list[str]:
    fields: list[str] = []
    visible = _visible(page_html)
    for tag in _META.findall(visible):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in _RIGHTS_META and attrs.get("content"):
            fields.append(attrs["content"])
    for tag in _LINKISH.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").lower().split()
        if "license" in rel and attrs.get("href"):
            fields.append(attrs["href"])
    for node in _json_nodes(page_html):
        for key in ("license", "licence", "rights"):
            if key in node:
                text = _flat_text(node[key])
                if text:
                    fields.append(text)
    return fields


def _matching_published_dates(page_html: str, page_url: str) -> list[str]:
    found: list[str] = []
    for node in _json_nodes(page_html):
        if not _node_matches_page(node, page_url):
            continue
        text = _flat_text(node.get("datePublished"))
        if text:
            found.append(text)
    return found


def _matching_headlines(page_html: str, page_url: str) -> list[str]:
    found: list[str] = []
    for node in _json_nodes(page_html):
        if not _node_matches_page(node, page_url):
            continue
        text = _flat_text(node.get("headline"))
        if text:
            found.append(text)
    return found


def _organization_names(page_html: str) -> list[str]:
    names: list[str] = []
    for node in _json_nodes(page_html):
        publisher = node.get("publisher")
        if isinstance(publisher, dict):
            text = _flat_text(publisher.get("name"))
            if text:
                names.append(text)
        elif isinstance(publisher, str):
            names.append(publisher)
        if str(node.get("@type", "")).casefold() in {"organization", "website"}:
            text = _flat_text(node.get("name"))
            if text:
                names.append(text)
    return names


def _json_nodes(page_html: str) -> list[dict]:
    nodes: list[dict] = []
    for blob in _LDJSON.findall(page_html):
        try:
            payload = json.loads(unescape(blob).strip())
        except json.JSONDecodeError:
            continue
        _gather_dicts(payload, nodes)
    return nodes


def _gather_dicts(payload: object, nodes: list[dict]) -> None:
    if isinstance(payload, dict):
        nodes.append(payload)
        for value in payload.values():
            _gather_dicts(value, nodes)
        return
    if isinstance(payload, list):
        for item in payload:
            _gather_dicts(item, nodes)


def _node_matches_page(node: dict, page_url: str) -> bool:
    for key in ("url", "@id", "mainEntityOfPage"):
        value = node.get(key)
        if isinstance(value, str) and _same_page(value, page_url):
            return True
        if isinstance(value, dict):
            for inner in ("@id", "url"):
                raw = value.get(inner)
                if isinstance(raw, str) and _same_page(raw, page_url):
                    return True
    return False


def _same_page(left: str, right: str) -> bool:
    try:
        a, b = urlparse(left.strip()), urlparse(right.strip())
    except ValueError:
        return False
    if a.scheme not in {"http", "https"} or b.scheme not in {"http", "https"}:
        return False
    host_a = (a.hostname or "").lower().rstrip(".")
    host_b = (b.hostname or "").lower().rstrip(".")
    path_a = a.path.rstrip("/") or "/"
    path_b = b.path.rstrip("/") or "/"
    return host_a == host_b and path_a == path_b and a.query == b.query


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


def _flat_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        raw = value.get("@value") or value.get("url") or value.get("@id")
        if isinstance(raw, str):
            return raw.strip()
        return ""
    if isinstance(value, list):
        parts = [_flat_text(item) for item in value]
        return " ".join(part for part in parts if part)
    return ""


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
    stripped = _SITE_SUFFIX.sub("", text).strip()
    return stripped or text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _visible(page_text: str) -> str:
    return _HIDDEN.sub(" ", page_text)


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible(page_text))


def _fold(value: str) -> str:
    return value.casefold().translate(_DASHES)


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINKISH.findall(page_html):
        href = _attrs(tag).get("href", "")
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
