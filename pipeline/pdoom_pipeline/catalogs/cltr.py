"""Metadata catalog of public Centre for Long-Term Resilience pages.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies are not stored. The official host is www.longtermresilience.org. A
date the page does not state stays unknown. Updated, modified, and copyright
years are not publication dates.

Rights stay unknown unless the page states a reuse licence that allows
copying. ``creative_commons`` means CC0, CC BY, or CC BY-SA, and only when
the page does not also state a restricted deed. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen is part of the deed, so
the text CC BY does not match CC BY-NC. A creativecommons.org/licenses/ URL
is not ``creative_commons`` unless its deed is CC0, CC BY, or CC BY-SA. The
Public Domain Mark is not CC0. ``uk_ogl`` means the page text states the
phrase Open Government Licence. Crown copyright alone does not count, and
the American spelling license does not count. A public page, a copyright
notice, All rights reserved, or a terms link is not a licence.

The Centre is not a UK government publisher. A challenge page is not stored.
This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cltr_pages"
CATALOG_FILENAME = "cltr_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL})
OFFICIAL_HOST = "www.longtermresilience.org"
PUBLISHER = "Centre for Long-Term Resilience"
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
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_PUBLISHER_NAMES = frozenset(
    {
        "centre for long-term resilience",
        "the centre for long-term resilience",
    }
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
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
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s*(?:\||[-–—])\s*(?:the\s+)?centre for long-term resilience\s*$"
)
_CLTR_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s*cltr\s*$")
_GENERIC_TITLES = frozenset({"home", "news", "menu", "search"})
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
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
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".mp3",
    ".mp4",
)
_BLOCKED_PREFIXES = (
    "/.well-known",
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/xmlrpc.php",
)
# Longer deeds are listed first. The character after "by" may be a hyphen, and
# a hyphen is not a word boundary here: CC BY must not match inside CC BY-NC.
_CC_TEXT = (
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nc[-\s]?sa(?![a-z0-9])")),
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nc[-\s]?nd(?![a-z0-9])")),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nc(?![a-z0-9])")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nd(?![a-z0-9])")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?sa(?![a-z0-9])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[-\s]?by(?![a-z0-9-])")),
    (
        "by-nc-sa",
        re.compile(
            r"creative commons attribution[-\s]+non[-\s]?commercial[-\s]+share[-\s]?alike"
        ),
    ),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[-\s]+non[-\s]?commercial[-\s]+no[-\s]?deriv"),
    ),
    (
        "by-nc",
        re.compile(r"creative commons attribution[-\s]+non[-\s]?commercial"),
    ),
    ("by-nd", re.compile(r"creative commons attribution[-\s]+no[-\s]?deriv")),
    ("by-sa", re.compile(r"creative commons attribution[-\s]+share[-\s]?alike")),
    (
        "by",
        re.compile(
            r"creative commons attribution(?![-\s]+(?:non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike))"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:cc[-\s]?0|cc[-\s]?zero)(?![a-z0-9])"
            r"|creative commons(?: public domain)? zero(?![a-z])"
        ),
    ),
)
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<lic>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by|zero))"
    r"(?![a-z0-9-])"
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


class CatalogError(ValueError):
    """A catalog row or page failed the Centre for Long-Term Resilience page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_cltr_host(hostname: str) -> bool:
    """True only for the official www.longtermresilience.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA. A restricted deed
    on the same page stays unknown, including when anchor text says CC BY and
    the URL is CC BY-NC. The Public Domain Mark is not CC0. ``uk_ogl`` requires
    the phrase Open Government Licence in the page text.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            codes.update(_codes_in_fragment(raw.replace("\\/", "/")))
    visible = _without_hidden(page_text)
    for content in _meta_values(visible, _LICENSE_META):
        codes.update(_codes_in_fragment(content))
    for tag in _LINK.findall(visible):
        codes.update(_url_codes(_attrs(tag).get("href", "")))
    reduced, anchor_codes = _take_creativecommons_anchors(visible)
    codes.update(anchor_codes)
    codes.update(_codes_in_fragment(_plain(reduced)))
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    if _OGL_PHRASE.search(_plain(visible).casefold()):
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    for raw in _meta_values(_without_hidden(page_text), _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the Centre. A missing site name is not a UK government publisher."""
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if site and site.casefold() not in _PUBLISHER_NAMES:
        raise CatalogError("publisher must be the Centre for Long-Term Resilience")
    return PUBLISHER


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was confirmed. A rel=canonical on another path is not substituted.
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
    try:
        declared = validate_canonical_url(_join_url(live, href.strip()))
    except CatalogError:
        return live
    if _same_page(declared, live):
        return declared
    return live


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
    """A page is stored only from HTML that is not a robot or Cloudflare challenge."""
    if status != 200 or not isinstance(page_html, str) or not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name in {"cf-mitigated", "sg-captcha"} and "challenge" in token:
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
    """Return metadata when the response is the page HTML.

    A Cloudflare challenge, a robot block, an error status, or a non-HTML
    response is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    return metadata_from_page(page_html, page_url=page_url)


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
        raise CatalogError("canonical URL must be an https www.longtermresilience.org page")
    parts = _split_url(url)
    host = "" if parts is None else parts["host"].lower().rstrip(".")
    path = "" if parts is None else parts["path"]
    if (
        parts is None
        or parts["userinfo"]
        or parts["query"]
        or parts["fragment"]
        or parts["port"] not in ("", "443")
        or not official_cltr_host(host)
        or not _public_page_path(path)
    ):
        raise CatalogError(f"canonical URL must be an https www.longtermresilience.org page: {url}")
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


def _split_url(url: str) -> dict[str, str] | None:
    if not isinstance(url, str) or not url.startswith("https://") or url != url.strip():
        return None
    if any(char.isspace() or char == "\\" for char in url):
        return None
    rest = url[len("https://") :]
    fragment = ""
    query = ""
    if "#" in rest:
        rest, fragment = rest.split("#", 1)
    if "?" in rest:
        rest, query = rest.split("?", 1)
    if "/" in rest:
        authority, path = rest.split("/", 1)
        path = "/" + path
    else:
        authority, path = rest, ""
    userinfo = ""
    if "@" in authority:
        userinfo, authority = authority.rsplit("@", 1)
    if not authority or authority.startswith("["):
        return None
    port = ""
    host = authority
    if host.count(":") > 1:
        return None
    if ":" in host:
        host, port = host.rsplit(":", 1)
        if not port.isdigit():
            return None
    if not host:
        return None
    return {
        "userinfo": userinfo,
        "host": host,
        "port": port,
        "path": path,
        "query": query,
        "fragment": fragment,
    }


def _public_page_path(path: str) -> bool:
    if path == "":
        return True
    if not path.startswith("/") or ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    lowered = path.casefold()
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return not lowered.startswith(_BLOCKED_PREFIXES)


def _same_page(left: str, right: str) -> bool:
    one = _split_url(left)
    other = _split_url(right)
    if one is None or other is None:
        return False
    return one["host"].lower().rstrip(".") == other["host"].lower().rstrip(".") and one["path"].rstrip(
        "/"
    ) == other["path"].rstrip("/")


def _join_url(base: str, href: str) -> str:
    target = unescape(href).strip()
    if not target or target.startswith("#"):
        return base
    if target.startswith("https://") or target.startswith("http://"):
        return target
    if target.startswith("//"):
        return "https:" + target
    parts = _split_url(base)
    if parts is None:
        return target
    if target.startswith("/"):
        path = target
    else:
        directory = parts["path"].rsplit("/", 1)[0]
        path = directory + "/" + target
    return "https://" + parts["host"] + _normalize_path(path)


def _normalize_path(path: str) -> str:
    query = ""
    fragment = ""
    if "#" in path:
        path, fragment = path.split("#", 1)
        fragment = "#" + fragment
    if "?" in path:
        path, query = path.split("?", 1)
        query = "?" + query
    trailing = path.endswith("/")
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    normalized = "/" + "/".join(parts)
    if trailing and normalized != "/":
        normalized += "/"
    return normalized + query + fragment


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    title = _clean_text(value)
    changed = True
    while changed and title:
        changed = False
        for pattern in (_SITE_SUFFIX, _CLTR_SUFFIX):
            updated = pattern.sub("", title).strip()
            if updated != title:
                title = updated
                changed = True
    return title


def _usable_title(title: str) -> bool:
    if not title or title.casefold() in _PUBLISHER_NAMES or title.casefold() == "cltr":
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


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    visible = _without_hidden(page_html) if isinstance(page_html, str) else ""
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _fold_cc(value: str) -> str:
    return unescape(value).casefold().translate(_DASHES)


def _url_codes(value: str) -> set[str]:
    found: set[str] = set()
    for match in _CC_URL.finditer(_fold_cc(value)):
        kind = match.group("pd")
        licence = match.group("lic")
        if kind == "zero":
            found.add("zero")
        elif licence:
            found.add(licence)
    return found


def _text_codes(value: str) -> set[str]:
    folded = _fold_cc(value)
    found: set[str] = set()
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            found.add(code)
    return found


def _codes_in_fragment(value: str) -> set[str]:
    return _url_codes(value) | _text_codes(value)


def _take_creativecommons_anchors(visible: str) -> tuple[str, set[str]]:
    codes: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "")
        if "creativecommons.org" not in href.casefold():
            return match.group(0)
        codes.update(_url_codes(href))
        return " "

    return _ANCHOR.sub(replace, visible), codes


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
