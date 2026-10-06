"""Metadata catalog of public AI Objectives Institute research, publication, and program pages.

Each stored URL was confirmed with one bounded GET on ai.objectives.institute.
aiobjectives.org redirects off that host and is not stored. A row keeps the
title, publisher, canonical URL, date, and rights label. Page text is not
stored. A Cloudflare challenge, a captcha, an HTTP error, a non-HTML response,
a robots disallow, a login page, or an off-host redirect is not stored. An
empty entries list is valid.

``creative_commons`` means CC0, CC BY-SA, or a permissive mix of those.
``creative_commons_attribution`` means CC BY alone. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps its own token. Mixed restricted and
permissive text stays unknown. A software licence beside any Creative Commons
deed stays unknown, including MIT plus CC BY and Apache-2.0 plus CC BY-NC.
A CC BY or CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or
public-domain mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL
stays unknown. The Public Domain Mark, all rights reserved, a terms link, and
a host name are not licences. ``mit``, ``apache-2.0``, and ``mpl-2.0`` stay
their own tokens. Mixed software licences stay unknown. ``uk_ogl`` requires
the British phrase Open Government Licence. A generic
creativecommons.org/licenses/ URL is not a deed, with or without a trailing
slash, including http, a www host, and a query string. Anchor text on that
generic URL does not count. Text elsewhere on the page still counts, and a
specific deed URL such as creativecommons.org/licenses/by/4.0/ still counts.
A hyphen is part of the deed, so CC BY does not match CC BY-NC and
licenses/by does not match licenses/by-nc.

Updated, modified, and copyright years are not publication dates. A missing
date stays unknown. The live URL is stored as confirmed; a different
rel=canonical does not replace it. This module does not fetch and it is not
a belief collector. ``runner_wired`` stays false.
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

CATALOG_ID = "aio_pages"
CATALOG_FILENAME = "aio_pages.json"
RUNNER_WIRED = False
PUBLISHER = "AI Objectives Institute"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_ATTRIBUTION,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_UK_OGL,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "ai.objectives.institute"
OGL_PHRASE = re.compile(r"\bopen government licence\b")
MAX_TEXT_CHARS = 400
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
        "text",
        "transcript",
        "transcript_text",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "datepublished",
    "dcterms.created",
    "dcterms.issued",
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_SUFFIXES = (
    " — AI • Objectives • Institute",
    " – AI • Objectives • Institute",
    " - AI • Objectives • Institute",
    " | AI • Objectives • Institute",
    " — AI Objectives Institute",
    " – AI Objectives Institute",
    " - AI Objectives Institute",
    " | AI Objectives Institute",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "cf-browser-verification",
    "sgcaptcha",
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
    ".ico",
    ".css",
    ".js",
    ".webmanifest",
)
_BLOCKED_PREFIXES = (
    "/.well-known",
    "/account",
    "/api",
    "/cart",
    "/commerce",
    "/config",
    "/login",
    "/register",
    "/search",
    "/shop",
    "/sign-in",
    "/signin",
    "/static",
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-login.php",
)
_PATH = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$")
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
# Longer deeds are listed first. A hyphen is a word boundary, so CC BY must not
# match CC BY-NC. licenses/by does not match licenses/by-nc.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*non[\s-]*commercial\b")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)")),
    (
        "zero",
        re.compile(
            r"\bcc0\b|\bcc[\s-]*0\b|\bcc[\s-]*zero\b|"
            r"\bcreative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    (
        "by",
        re.compile(
            r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
            r"(?![\s-]*(?:non[\s-]*commercial\b|no[\s-]*deriv))"
        ),
    ),
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
            r"creative commons attribution[\s-]+non[\s-]*commercial\b"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
        ),
    ),
    ("by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    (
        "by-sa",
        re.compile(r"creative commons attribution[\s-]+share[\s-]*alike\b"),
    ),
    (
        "by",
        re.compile(
            r"creative commons attribution\b"
            r"(?![\s-]*(?:non[\s-]*commercial\b|no[\s-]*deriv|share[\s-]*alike\b|nc\b|nd\b|sa\b))"
        ),
    ),
    ("mark", re.compile(r"\bpublic domain mark\b")),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_MIT_PHRASE = re.compile(r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_PHRASE = re.compile(r"\bapache-2\.0\b|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b")
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_PHRASE = re.compile(r"\bmpl-2\.0\b|\bmozilla public licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")


class CatalogError(ValueError):
    """A catalog row or page failed the AI Objectives Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
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
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be a known label or unknown")
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
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public AI Objectives Institute page")
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
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public AI Objectives Institute page: {url}")
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
    plain = _plain_text(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from an HTML 200 that is not a challenge.

    HTTP 202, HTTP 403, a captcha, and a Cloudflare interstitial are not stored.
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
            if name in {"sg-captcha", "x-amzn-waf-action"} and token:
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

    A challenge page, an HTTP 202, an HTTP 403, or a non-HTML response is not
    stored.
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

    ``creative_commons`` is CC0, CC BY-SA, or a permissive mix of those.
    ``creative_commons_attribution`` is CC BY alone. A sole restricted deed
    keeps its own token. Mixed restricted and permissive text stays unknown.
    A software licence beside any Creative Commons deed stays unknown. A CC BY
    or CC BY-SA anchor on a restricted or public-domain mark URL stays unknown,
    and a CC0 anchor on a publicdomain/mark URL stays unknown. Anchor text on
    a generic creativecommons.org/licenses/ URL is not a licence statement.
    The Public Domain Mark is not CC0. ``uk_ogl`` requires the phrase Open
    Government Licence. Script and style text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, mit, apache, mpl = _licence_signals(page_text)
    ogl = _states_ogl(page_text)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = (mit, apache, mpl)
    if "mark" in codes and (permissive or restricted or any(software) or ogl):
        return RIGHTS_UNKNOWN
    if restricted and permissive:
        return RIGHTS_UNKNOWN
    if any(software) and (restricted or permissive):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        if any(software) or ogl:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if sum(bool(item) for item in software) > 1:
        return RIGHTS_UNKNOWN
    if any(software) and ogl:
        return RIGHTS_UNKNOWN
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if permissive and ogl:
        return RIGHTS_UNKNOWN
    if permissive:
        if permissive <= {"by"}:
            return RIGHTS_CC_ATTRIBUTION
        if permissive & {"zero", "by-sa"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dateModified, a last-updated line,
    and a copyright year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for blob in _LDJSON.findall(page_html):
        for raw in _DATE_PUBLISHED.findall(blob):
            found = _iso_prefix(raw)
            if found:
                return found
    metas = _metas(_visible(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
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


def publisher_from_page(page_html: str) -> str:
    """Return the AI Objectives Institute when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    site = _metas(visible).get("og:site_name", "")
    if site:
        if _is_publisher_name(site):
            return PUBLISHER
        raise CatalogError("publisher must be the AI Objectives Institute")
    if "ai objectives institute" in _plain_text(visible).casefold():
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
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/") or path.endswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if _PATH.fullmatch(path) is None:
        return False
    for prefix in _BLOCKED_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return False
    return True


def _licence_signals(page_text: str) -> tuple[set[str], bool, bool, bool]:
    codes: set[str] = set()
    mit = False
    apache = False
    mpl = False
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            codes.update(_cc_codes(raw.replace("\\/", "/")))
            mit, apache, mpl = _note_software(raw.replace("\\/", "/"), mit, apache, mpl)
    visible = _visible(page_text)
    hrefs = [href for href in _hrefs(visible) if not _is_generic_cc_licenses_url(href)]
    blobs = [
        _plain_text(_without_generic_cc_anchors(visible)),
        *hrefs,
        *_meta_values(visible, _LICENSE_META),
    ]
    for blob in blobs:
        codes.update(_cc_codes(blob))
        mit, apache, mpl = _note_software(blob, mit, apache, mpl)
    return codes, mit, apache, mpl


def _states_ogl(page_text: str) -> bool:
    visible = _without_generic_cc_anchors(_visible(page_text))
    blobs = [_plain_text(visible), *_meta_values(visible, _LICENSE_META)]
    for blob in _LDJSON.findall(page_text):
        blobs.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(blob))
    return any(OGL_PHRASE.search(_fold(blob)) for blob in blobs)


def _note_software(blob: str, mit: bool, apache: bool, mpl: bool) -> tuple[bool, bool, bool]:
    folded = _fold(blob)
    return (
        mit or bool(_MIT_PHRASE.search(folded) or _MIT_URL.search(folded)),
        apache or bool(_APACHE_PHRASE.search(folded) or _APACHE_URL.search(folded)),
        mpl or bool(_MPL_PHRASE.search(folded) or _MPL_URL.search(folded)),
    )


def _cc_codes(value: str) -> set[str]:
    folded = _fold(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            codes.add(license_code.casefold())
            continue
        pd = (match.group("pd") or "").casefold()
        if pd == "zero":
            codes.add("zero")
        elif pd == "mark":
            codes.add("mark")
    for code, pattern in _TEXT_CODES:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


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


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible(page_text))


def _visible(page_text: str) -> str:
    return _HIDDEN.sub(" ", _COMMENT.sub(" ", page_text))


def _iso_prefix(raw: str) -> str:
    if not isinstance(raw, str):
        return ""
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return ""
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return ""
    return match.group(1)


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(page_html)
    return [metas[name] for name in names if metas.get(name)]


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for creativecommons.org/licenses with no deed in the path.

    A trailing slash, http, a www host, a query string, and a fragment stay
    on that generic page. licenses/by and the other deed paths do not.
    """

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(unescape(href).strip().replace("\\/", "/"))
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"creativecommons.org", "www.creativecommons.org"}:
        return False
    path = (parsed.path or "").rstrip("/")
    return path.casefold() == "/licenses"


def _without_generic_cc_anchors(visible: str) -> str:
    """Drop the visible text of anchors that point at the generic licences URL."""

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, visible)


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINKISH.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _is_publisher_name(value: str) -> bool:
    text = _clean_text(value).casefold().replace("•", " ").replace("·", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text.startswith("the "):
        text = text[4:]
    return text == "ai objectives institute"
