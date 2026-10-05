"""Metadata catalog of public BlueDot Impact pages.

The official host is bluedot.org. www.bluedot.org, bluedotimpact.org, and
www.bluedotimpact.org redirect there, and the site robots.txt names
https://bluedot.org. Rows keep a title, publisher, canonical URL, date, and
rights label. Page bodies, abstracts, and PDFs are not stored. A date the
page does not state stays unknown. Updated times, modified times, and
copyright years are not publication dates. Rights stay unknown unless the
page states CC0, CC BY, or CC BY-SA and does not also state a restricted
deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen
continues a deed token, so CC BY does not match CC BY-NC. A public page, a
copyright notice, or a terms link is not a licence. This catalog is not a
collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "bluedot_pages"
CATALOG_FILENAME = "bluedot_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "bluedot.org"
PUBLISHER = "BlueDot Impact"
MAX_FIELD_CHARS = 400
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
        "dataset",
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
_PUBLISHED_META = ("article:published_time", "citation_publication_date")
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
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
)
_ROBOTS_PREFIXES = ("/admin", "/api", "/profile", "/settings", "/_next")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLUG_PATH = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$")
_URL = re.compile(
    r"^(?P<scheme>https)://(?P<authority>[^/?#]+)(?P<path>/[^?#]*)?(?P<query>\?[^#]*)?(?P<fragment>#.*)?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b([^>]*)>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_SITE_SUFFIX = re.compile(r"(?i)\s*[|\u2013\u2014-]\s*bluedot impact\s*$")
_SITE_PREFIX = re.compile(r"(?i)^bluedot impact\s*[|\u2013\u2014-]\s*")
_GENERIC_TITLES = frozenset({"loading", "loading...", "loading…"})
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
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
# Longer deeds are listed first. A hyphen continues the token, so "by" does
# not match inside "by-nc" and "CC BY" does not match inside "CC BY-NC".
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_TEXT_DEED = re.compile(
    r"(?i)(?:"
    r"(?P<zero>\bcc0\b|\bcc\s+0\b|creative commons zero\b|\bcc\s+zero\b)"
    r"|(?P<by_nc_nd>\bcc[\s-]+by[\s-]+nc[\s-]+nd(?![a-z0-9-])"
    r"|creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
    r"|attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv)"
    r"|(?P<by_nc_sa>\bcc[\s-]+by[\s-]+nc[\s-]+sa(?![a-z0-9-])"
    r"|creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
    r"|attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike)"
    r"|(?P<by_nc>\bcc[\s-]+by[\s-]+nc(?![a-z0-9-])"
    r"|creative commons attribution[\s-]+non[\s-]*commercial(?![a-z0-9-])"
    r"|attribution[\s-]+non[\s-]*commercial(?![a-z0-9-]))"
    r"|(?P<by_nd>\bcc[\s-]+by[\s-]+nd(?![a-z0-9-])"
    r"|creative commons attribution[\s-]+no[\s-]*deriv"
    r"|attribution[\s-]+no[\s-]*deriv)"
    r"|(?P<by_sa>\bcc[\s-]+by[\s-]+sa(?![a-z0-9-])"
    r"|creative commons attribution[\s-]+share[\s-]*alike"
    r"|attribution[\s-]+share[\s-]*alike)"
    r"|(?P<by>\bcc[\s-]+by(?![a-z0-9-])(?![\s-]*(?:nc|nd)(?![a-z0-9-]))"
    r"|creative commons attribution(?![a-z0-9-])"
    r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike)))"
    r"|(?P<mark>public domain mark\b)"
    r")"
)
_DEED_GROUPS = (
    ("zero", "zero"),
    ("by_nc_nd", "by-nc-nd"),
    ("by_nc_sa", "by-nc-sa"),
    ("by_nc", "by-nc"),
    ("by_nd", "by-nd"),
    ("by_sa", "by-sa"),
    ("by", "by"),
    ("mark", "mark"),
)
_PERMISSIVE = frozenset({"zero", "by", "by-sa"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})


class CatalogError(ValueError):
    """A catalog row or page failed the BlueDot Impact page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_bluedot_host(hostname: str) -> bool:
    """True only for the official bluedot.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is a Cloudflare or robot interstitial."""
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND.
    A hyphen is part of the deed token. Public Domain Mark is not CC0. A bare
    creativecommons.org/licenses/ URL is not a licence to copy.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            codes.update(_deed_codes(raw.replace("\\/", "/")))
    visible = _visible(page_text)
    codes.update(_deed_codes(visible))
    codes.update(_deed_codes(_plain(visible)))
    for content in _meta_values(visible, _LICENSE_META):
        codes.update(_deed_codes(content))
    if codes & _RESTRICTED:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE:
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
    for attrs, inner in _H1.findall(page_html):
        if "site-name" in attrs.casefold():
            continue
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    metas = _metas(page_html)
    for key in ("og:title", "twitter:title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(page_html)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    publisher = _clean_text(_metas(page_html).get("og:site_name", ""))
    if publisher != PUBLISHER:
        raise CatalogError("publisher is required")
    return publisher


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    return {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }


def metadata_from_response(
    *,
    status: int,
    content_type: object,
    page_html: str,
    page_url: str,
    headers: dict | None = None,
) -> dict | None:
    """Return metadata when one bounded response is public HTML, else None.

    A Cloudflare challenge, a robot block, or a non-HTML body is omitted.
    """
    if status != 200 or not is_html_content_type(content_type):
        return None
    if _challenge_headers(headers) or not isinstance(page_html, str) or is_challenge_page(page_html):
        return None
    try:
        return metadata_from_page(page_html, page_url=page_url)
    except CatalogError:
        return None


def confirmed_url(page_html: str, page_url: str) -> str:
    """Return the fetched URL. A different rel=canonical does not replace it."""
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    declared = _resolve(live, href)
    if declared == live:
        return live
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
        raise CatalogError("canonical URL must be an https bluedot.org page")
    match = _URL.fullmatch(url)
    if match is None:
        raise CatalogError(f"canonical URL must be an https bluedot.org page: {url}")
    authority = match.group("authority")
    path = match.group("path") or ""
    if (
        match.group("scheme") != "https"
        or authority != OFFICIAL_HOST
        or not official_bluedot_host(authority)
        or match.group("query")
        or match.group("fragment")
        or ".." in path
        or "\\" in path
        or "//" in path
        or _robots_disallowed(path)
        or _is_download(path)
        or not (path == "/" or _SLUG_PATH.fullmatch(path))
    ):
        raise CatalogError(f"canonical URL must be an https bluedot.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


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


def _robots_disallowed(path: str) -> bool:
    lowered = path.casefold()
    for prefix in _ROBOTS_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return True
    return False


def _is_download(path: str) -> bool:
    lowered = path.casefold()
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _visible(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    title = _SITE_SUFFIX.sub("", _clean_text(value)).strip()
    title = _SITE_PREFIX.sub("", title).strip()
    return title


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    return title.casefold() not in _GENERIC_TITLES


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


def _meta_values(html: str, names: frozenset[str] | tuple[str, ...]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _resolve(base: str, href: str) -> str:
    candidate = unescape(href).strip()
    lowered = candidate.casefold()
    if lowered.startswith("https://") or lowered.startswith("http://"):
        return candidate
    if not candidate.startswith("/"):
        return candidate
    match = _URL.fullmatch(base)
    if match is None:
        return candidate
    return f"https://{match.group('authority')}{candidate}"


def _prepare_licence_text(value: str) -> str:
    return unescape(value).replace("\\/", "/").translate(_DASHES)


def _deed_codes(value: str) -> set[str]:
    text = _prepare_licence_text(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(text):
        code = (match.group("license") or match.group("pd") or "").casefold()
        if code:
            codes.add(code)
    for match in _TEXT_DEED.finditer(text):
        for group, code in _DEED_GROUPS:
            if match.group(group):
                codes.add(code)
                break
    return codes


def _challenge_headers(headers: dict | None) -> bool:
    if not isinstance(headers, dict):
        return False
    for key, value in headers.items():
        if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
            return True
    return False


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
