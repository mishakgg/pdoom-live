"""Metadata catalog of public Center for Democracy and Technology AI pages.

Rows keep a title, publisher, canonical URL, date, and rights label. A row is
stored only when one bounded GET of cdt.org returns HTML. Response size,
redirects, and elapsed time are bounded. A Cloudflare challenge, a SiteGround
captcha, an HTTP 202 challenge, an Akamai interstitial, a robot interstitial,
or a redirect off cdt.org stores no row. Page bodies, abstracts, PDFs, chart
data, and quotes are not stored. A missing date is unknown. Updated, modified,
and copyright years are not publication dates. Rights stay unknown unless the
page states CC0, CC BY, or CC BY-SA, which are labeled creative_commons.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted
deed wins when it appears beside a permissive one. A public page, a copyright
notice, All rights reserved, or a terms link is not a licence. This catalog
does not fetch, it is not a belief collector, and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cdt_ai_pages"
CATALOG_FILENAME = "cdt_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "cdt.org"
PUBLISHER = "Center for Democracy and Technology"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
MAX_RESPONSE_BYTES = 1_000_000
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 15.0

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
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
        "dc.date.issued",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_URL_RE = re.compile(
    r"^(?P<scheme>https?)://"
    r"(?:(?P<userinfo>[^/@\s]+)@)?"
    r"(?P<host>\[[^\]]+\]|[^/:?#\s]+)"
    r"(?::(?P<port>\d+))?"
    r"(?P<path>/[^?#]*)?"
    r"(?:\?(?P<query>[^#]*))?"
    r"(?:#(?P<fragment>.*))?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"((?:\\.|[^"\\])*)"')
_LD_LICENSE_ID = re.compile(r'"license"\s*:\s*\{[^}]*"@id"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s*[|\-–—]\s*Center for Democracy (?:&|and) Technology\s*$"
)
# Hyphen is a word boundary, so a trailing \b would let "CC BY" match "CC BY-NC".
# Longer restricted deeds are listed first, and a deed cannot continue through
# another letter or hyphen. creativecommons.org/licenses/ is not itself a deed.
_CC_DEED_URL = re.compile(
    r"(?i)(?:www\.)?creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    ("by-nc-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    ("by-nc", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    ("by-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*share[\s-]*alike(?![a-z0-9])")),
    (
        "by",
        re.compile(
            r"(?i)(?<![a-z0-9])cc[\s-]*by"
            r"(?![\s-]*(?:nc(?:[\s-]*(?:sa|nd))?|nd|sa)(?![a-z0-9]))"
            r"(?![a-z0-9])"
        ),
    ),
    ("zero", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])")),
    ("zero", re.compile(r"(?i)creative\s+commons\s+(?:cc[\s-]*0|zero)\b")),
)
_ATTRIBUTION = re.compile(
    r"(?i)creative\s+commons\s+attribution"
    r"(?P<suffix>(?:[\s-]+(?:non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?|share[\s-]*alike))*)"
)
_PUBLIC_DOMAIN_MARK = re.compile(r"(?i)public\s+domain\s+mark")
_CHALLENGE_MARKERS = (
    "just a moment",
    "attention required! | cloudflare",
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "/cdn-cgi/styles/cf.errors.css",
    "cf-mitigated",
    "checking your browser",
    "enable javascript and cookies",
    "sgcaptcha",
    "siteground captcha",
    "powered by akamai",
    "akamai ghost",
    "edgesuite.net",
    "robot interstitial",
    "are you a robot",
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
_BLOCKED_PREFIXES = (
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/wp-login.php",
    "/xmlrpc.php",
    "/cdn-cgi",
    "/feed",
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


class CatalogError(ValueError):
    """A catalog row or page failed the Center for Democracy and Technology page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_cdt_host(hostname: str) -> bool:
    """True only for the official cdt.org host."""

    host = (hostname or "").strip().lower().rstrip(".")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _CHALLENGE_MARKERS):
        return True
    if "cloudflare" in lowered and "attention required" in lowered:
        return True
    if "akamai" in lowered and (
        "access denied" in lowered or "reference #" in lowered or "edgesuite" in lowered
    ):
        return True
    if "siteground" in lowered and "captcha" in lowered:
        return True
    if "robot" in lowered and "interstitial" in lowered:
        return True
    return False


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> bool:
    """A page is stored only from one bounded HTML GET of cdt.org.

    HTTP 202, a challenge interstitial, a non-HTML body, an oversized body,
    too many redirects, a timeout, or a final host other than cdt.org stores
    nothing.
    """

    if status != 200 or redirect_count > MAX_REDIRECTS:
        return False
    if elapsed_seconds is not None and elapsed_seconds > TIMEOUT_SECONDS:
        return False
    if not isinstance(page_html, str) or not is_html_content_type(content_type):
        return False
    if len(page_html.encode("utf-8")) > MAX_RESPONSE_BYTES:
        return False
    if is_challenge_page(page_html) or _challenge_headers(headers):
        return False
    stored_url = final_url if isinstance(final_url, str) and final_url else page_url
    try:
        validate_canonical_url(stored_url)
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
    final_url: str | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> dict | None:
    """Return metadata when the response is cdt.org HTML. Otherwise return None."""

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        redirect_count=redirect_count,
        elapsed_seconds=elapsed_seconds,
    ):
        return None
    assert isinstance(page_html, str)
    stored_url = final_url if isinstance(final_url, str) and final_url else page_url
    return metadata_from_page(page_html, page_url=stored_url)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons or unknown.

    creative_commons means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
    CC BY-NC-SA, and CC BY-NC-ND stay unknown, including when a permissive
    phrase appears beside them. A hyphen does not end a deed, so CC BY does
    not match CC BY-NC, and a licenses URL does not match every deed. A public
    domain mark is not CC0. Script and style text does not count. A copyright
    notice, All rights reserved, a public page, or a terms link is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    for blob in _LDJSON.findall(page_text):
        normalized = blob.replace("\\/", "/")
        for raw in _LD_LICENSE.findall(normalized):
            codes.update(_deeds_in(raw))
        for raw in _LD_LICENSE_ID.findall(normalized):
            codes.update(_deeds_in(raw))
    visible = _without_hidden(page_text)
    for href in _hrefs(visible):
        codes.update(_deeds_in(href))
    for content in _meta_values(visible, _LICENSE_META):
        codes.update(_deeds_in(content))
    codes.update(_deeds_in(_plain(visible)))
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    for raw in _meta_values(page_text, _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    site = _normalize_publisher(_metas(visible).get("og:site_name", ""))
    if site.casefold() == PUBLISHER.casefold():
        return PUBLISHER
    if site:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    if PUBLISHER.casefold() in _plain(visible).casefold():
        return PUBLISHER
    if "center for democracy & technology" in _plain(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    A challenge page is not stored.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    absolute = _resolve(live, href.strip())
    if absolute is None:
        return live
    try:
        declared = validate_canonical_url(absolute)
    except CatalogError:
        return live
    if _same_page(declared, live):
        return declared
    return live


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document["runner_wired"] is not False:
        raise CatalogError("runner_wired must be false")
    entries = document["entries"]
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
    _require_text(entry, "title")
    _require_text(entry, "publisher")
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https cdt.org page")
    parts = _parse_http_url(url)
    path = (parts or {}).get("path") or "/"
    host = (parts or {}).get("host") or ""
    if (
        parts is None
        or parts["scheme"] != "https"
        or parts["userinfo"]
        or parts["query"]
        or parts["fragment"]
        or parts["port"] is not None
        or host != OFFICIAL_HOST
        or not official_cdt_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _html_path(path)
    ):
        raise CatalogError(f"canonical URL must be an https cdt.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if "sgcaptcha" in name or "sgcaptcha" in text:
            return True
    return False


def _deeds_in(value: str) -> set[str]:
    folded = unescape(value).replace("\\/", "/").replace("\xa0", " ").casefold().translate(_DASHES)
    codes: set[str] = set()
    for match in _CC_DEED_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    codes.update(_attribution_codes(folded))
    if _PUBLIC_DOMAIN_MARK.search(folded):
        codes.add("mark")
    return codes


def _attribution_codes(text: str) -> set[str]:
    codes: set[str] = set()
    for match in _ATTRIBUTION.finditer(text):
        suffix = match.group("suffix").casefold()
        noncommercial = re.search(r"non[\s-]*commercial", suffix) is not None
        noderiv = re.search(r"no[\s-]*deriv", suffix) is not None
        share = re.search(r"share[\s-]*alike", suffix) is not None
        if noncommercial and noderiv:
            codes.add("by-nc-nd")
        elif noncommercial and share:
            codes.add("by-nc-sa")
        elif noncommercial:
            codes.add("by-nc")
        elif noderiv:
            codes.add("by-nd")
        elif share:
            codes.add("by-sa")
        else:
            codes.add("by")
    return codes


def _html_path(path: str) -> bool:
    if path == "/":
        return True
    if not path.startswith("/"):
        return False
    lowered = path.casefold()
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    if any(bare.endswith(suffix) for suffix in _DOWNLOAD_SUFFIXES):
        return False
    for prefix in _BLOCKED_PREFIXES:
        if bare == prefix or bare.startswith(prefix + "/"):
            return False
    return True


def _parse_http_url(url: str) -> dict[str, str | None] | None:
    match = _URL_RE.fullmatch(url)
    if match is None:
        return None
    return {
        "scheme": match.group("scheme").lower(),
        "userinfo": match.group("userinfo"),
        "host": match.group("host"),
        "port": match.group("port"),
        "path": match.group("path"),
        "query": match.group("query"),
        "fragment": match.group("fragment"),
    }


def _resolve(base: str, href: str) -> str | None:
    if href.startswith("https://") or href.startswith("http://"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        parts = _parse_http_url(base)
        if parts is None or not parts["host"]:
            return None
        return f"https://{parts['host']}{href}"
    return None


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value:
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


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _same_page(left: str, right: str) -> bool:
    a = _parse_http_url(left)
    b = _parse_http_url(right)
    if a is None or b is None:
        return False
    return (a["host"] or "").lower() == (b["host"] or "").lower() and (a["path"] or "/").rstrip(
        "/"
    ) == (b["path"] or "/").rstrip("/")


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() != PUBLISHER.casefold()


def _normalize_publisher(value: str) -> str:
    text = _clean_text(value)
    text = re.sub(r"\s*&\s*", " and ", text)
    return re.sub(r"\s+", " ", text).strip()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
