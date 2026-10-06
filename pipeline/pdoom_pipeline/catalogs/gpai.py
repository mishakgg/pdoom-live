"""Metadata catalog of public Global Partnership on Artificial Intelligence pages.

The expected host is https://gpai.ai. A bounded GET of that host is a 301
off-host redirect to https://oecd.ai, so the committed catalog stores no rows.
www.gpai.ai redirects the same way. A Cloudflare challenge, a captcha, HTTP
202, an Akamai 403, a robots disallow, or any other off-host redirect is not
stored either.

A row would keep only the title, publisher, canonical URL, date, and rights
label from an on-host HTML page. Page text, reports, and PDFs are not stored.
creative_commons means only a stated CC0, CC BY, or CC BY-SA deed. CC BY-NC
and CC BY-NC-SA, including IGO variants, keep their own tokens and are never
folded into creative_commons. A restricted deed wins when a permissive deed
is also stated. The Public Domain Mark is not CC0. uk_ogl is used only when
the page text contains the British phrase "open government licence".
eu_reuse_decision is used only when the page states Decision 2011/833/EU.
A copyright notice, All rights reserved, a terms link, or a host name is not
a licence. Updated, modified, and copyright years are not publication dates.
A missing date stays unknown. The live URL is stored as confirmed; a different
rel=canonical does not replace it. This module does not fetch and it is not
a belief collector. runner_wired stays false.
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

CATALOG_ID = "gpai_pages"
CATALOG_FILENAME = "gpai_pages.json"
PUBLISHER = "Global Partnership on Artificial Intelligence"
RUNNER_WIRED = False
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_3_0_IGO = "cc_by_nc_3_0_igo"
RIGHTS_CC_BY_NC_SA_3_0_IGO = "cc_by_nc_sa_3_0_igo"
RIGHTS_EU_REUSE = "eu_reuse_decision"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_3_0_IGO,
        RIGHTS_CC_BY_NC_SA_3_0_IGO,
        RIGHTS_EU_REUSE,
        RIGHTS_UK_OGL,
        RIGHTS_UNKNOWN,
    }
)
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"gpai.ai", "www.gpai.ai"})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"license"\s*:\s*"([^"]*)"')
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_LABELED_PUBLISHED = re.compile(
    r"(?<![a-z])(?:date published|publication date|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_EU_REUSE = re.compile(r"\bdecision\s+2011/833/eu\b")
_SITE_SUFFIXES = (
    " | Global Partnership on Artificial Intelligence",
    " - Global Partnership on Artificial Intelligence",
    " – Global Partnership on Artificial Intelligence",
    " — Global Partnership on Artificial Intelligence",
    " | GPAI",
    " - GPAI",
    " – GPAI",
    " — GPAI",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "cf-turnstile",
    "/cdn-cgi/challenge",
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
# Longest deed first. licenses/by must not match licenses/by-nc: the by
# alternative is last, and the match has to end at a path boundary.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nd|by-nc|by-sa|by)"
    r"(?:/(?P<version>\d+(?:\.\d+)*))?"
    r"(?:/(?P<port>igo))?"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?=/|[?#]|$)"
)
# A hyphen is a word boundary, so \b after BY matches inside BY-NC.
# The CC BY pattern therefore refuses a following NC, ND, or SA token.
_TEXT_DEEDS = (
    (
        "cc-by-nc-sa-igo",
        re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa(?:[\s-]*3(?:\.0)?)?[\s-]*igo\b"),
    ),
    ("cc-by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    (
        "cc-by-nc-sa",
        re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b(?![\s-]*(?:3(?:\.0)?[\s-]*)?igo\b)"),
    ),
    (
        "cc-by-nc-igo",
        re.compile(r"\bcc[\s-]*by[\s-]*nc(?![\s-]*sa\b)(?:[\s-]*3(?:\.0)?)?[\s-]*igo\b"),
    ),
    ("cc-by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd|igo)\b)")),
    ("cc-by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("cc-by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd|igo)\b)")),
    (
        "cc0",
        re.compile(
            r"\bcc0\b|\bcc[\s-]*0\b|\bcc[\s-]*zero\b|"
            r"\bcreative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("cc-by", re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa|igo)\b)")),
)
_NAME_DEEDS = (
    (
        "cc-by-nc-sa-igo",
        re.compile(
            r"creative commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
            r"(?:[\s-]*3(?:\.0)?)?[\s-]*igo\b"
        ),
    ),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike\b"
            r"(?![\s-]*(?:3(?:\.0)?[\s-]*)?igo\b)"
        ),
    ),
    (
        "cc-by-nc-igo",
        re.compile(
            r"creative commons\s+attribution[\s-]*non[\s-]*commercial"
            r"(?![\s-]*share[\s-]*alike\b)(?:[\s-]*3(?:\.0)?)?[\s-]*igo\b"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons\s+attribution[\s-]*non[\s-]*commercial\b"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv|igo)\b)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(r"creative commons\s+attribution[\s-]*no[\s-]*deriv"),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"creative commons\s+attribution[\s-]*share[\s-]*alike\b"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|igo)\b)"
        ),
    ),
    (
        "cc-by",
        re.compile(
            r"creative commons\s+attribution\b"
            r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|nc|nd|sa|igo)\b)"
        ),
    ),
)
_PD_MARK = re.compile(r"public domain mark\b")
_TOKEN_FOR_RESTRICTED = (
    ("cc-by-nc-sa-igo", RIGHTS_CC_BY_NC_SA_3_0_IGO),
    ("cc-by-nc-igo", RIGHTS_CC_BY_NC_3_0_IGO),
    ("cc-by-nc-sa", RIGHTS_CC_BY_NC_SA),
    ("cc-by-nc", RIGHTS_CC_BY_NC),
)
_UNTOKENIZED_RESTRICTED = frozenset({"cc-by-nd", "cc-by-nc-nd", "pd-mark"})
_PERMISSIVE = frozenset({"cc0", "cc-by", "cc-by-sa"})


class CatalogError(ValueError):
    """A catalog row or page failed the Global Partnership page rules."""


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
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    # An empty list is valid: the live host redirects off-host, so no row is stored.
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
        raise CatalogError("rights must be a known label or unknown")


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
    if not isinstance(url, str) or not url or url != url.strip() or any(char in url for char in " \t\r\n"):
        raise CatalogError("canonical URL must be a public Global Partnership page")
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
        or not host
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Global Partnership page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


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
    plain = _plain(_visible_html(page_html)).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge or redirect."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return False
    if headers and _headers_block_storage(headers):
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
    """Return metadata when the response is on-host page HTML.

    HTTP 202, HTTP 403, a challenge, a non-HTML body, and an off-host redirect
    are not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=page_url)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    creative_commons means CC0, CC BY, or CC BY-SA only. CC BY-NC and
    CC BY-NC-SA, including IGO variants, keep their own tokens. CC BY-ND,
    CC BY-NC-ND, and the Public Domain Mark stay unknown. A restricted deed
    wins when a permissive deed is also stated. A hyphen is a word boundary,
    so CC BY does not match CC BY-NC, and licenses/by does not match
    licenses/by-nc. A generic creativecommons.org/licenses/ URL is not a
    permissive deed. uk_ogl requires the phrase open government licence.
    eu_reuse_decision requires Decision 2011/833/EU. Script and style text
    does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    licences = _jsonld_licences(page_text)
    visible = _visible_html(page_text)
    plain = _plain(visible)
    metas = _meta_values(visible, _LICENSE_META)
    stated = _fold("\n".join([plain, *metas, *licences]))
    corpus = _fold("\n".join([stated, *_hrefs(visible)]))
    return _rights_from_codes(_deed_codes(corpus), stated)


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, and a copyright
    year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for blob in _LDJSON.findall(page_html):
        for match in _DATE_PUBLISHED.finditer(blob):
            found = _iso_date(match.group(1))
            if found:
                return found
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    match = _LABELED_PUBLISHED.search(_fold(_plain(visible)))
    if match:
        found = _iso_date(match.group(1))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
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


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return the partnership name when the page states it.

    A person named on the page is not the publisher. The host name alone is
    not the publisher. The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _visible_html(page_html)
    site = _metas(visible).get("og:site_name", "")
    if PUBLISHER.casefold() in _clean_text(site).casefold():
        return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
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
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    lowered = path.lower()
    return not lowered.endswith(_DOWNLOAD_SUFFIXES)


def _headers_block_storage(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "location" and _location_is_off_host(str(value)):
            return True
    return False


def _location_is_off_host(location: str) -> bool:
    host = (urlparse(location.strip()).hostname or "").lower().rstrip(".")
    if not host:
        return False
    return not is_official_host(host)


def _rights_from_codes(codes: set[str], stated: str) -> str:
    if codes & _UNTOKENIZED_RESTRICTED:
        return RIGHTS_UNKNOWN
    for code, token in _TOKEN_FOR_RESTRICTED:
        if code in codes:
            return token
    if codes & _PERMISSIVE:
        return RIGHTS_CREATIVE_COMMONS
    if _EU_REUSE.search(stated):
        return RIGHTS_EU_REUSE
    if OGL_PHRASE in stated:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def _deed_codes(corpus: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(corpus):
        code = _code_from_url(match)
        if code:
            codes.add(code)
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(corpus):
            codes.add(code)
    for code, pattern in _NAME_DEEDS:
        if pattern.search(corpus):
            codes.add(code)
    if _PD_MARK.search(corpus):
        codes.add("pd-mark")
    return codes


def _code_from_url(match: re.Match[str]) -> str:
    public_domain = match.group("pd")
    if public_domain == "zero":
        return "cc0"
    if public_domain == "mark":
        return "pd-mark"
    license_slug = match.group("license") or ""
    port = match.group("port") or ""
    if license_slug == "by-nc-sa" and port == "igo":
        return "cc-by-nc-sa-igo"
    if license_slug == "by-nc" and port == "igo":
        return "cc-by-nc-igo"
    return {
        "by-nc-nd": "cc-by-nc-nd",
        "by-nc-sa": "cc-by-nc-sa",
        "by-nc": "cc-by-nc",
        "by-nd": "cc-by-nd",
        "by-sa": "cc-by-sa",
        "by": "cc-by",
    }.get(license_slug, "")


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
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\xa0", " ").casefold().translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


def _visible_html(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _jsonld_licences(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_LICENSE.findall(blob):
            found.append(raw.replace("\\/", "/"))
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(page_html)
    return [metas[name] for name in names if name in metas and metas[name]]


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


def _iso_date(value: str) -> str | None:
    if _DATE.fullmatch(value) is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    return _iso_date(match.group(1))
