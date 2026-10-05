"""Metadata catalog of public AI Impacts pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page bodies, essays, and
chart data are not stored. Rights stay unknown unless the page states a reuse
licence. ``creative_commons`` means only CC0, CC BY, or CC BY-SA. CC BY-NC,
CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A following
NonCommercial, NoDerivatives, or ShareAlike suffix is not plain CC BY.
A public page, a copyright notice, an all-rights-reserved line, or a terms
link is not a licence. Updated, modified, and copyright years are not
publication dates. A missing date stays unknown. The live URL is stored as
confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ai_impacts_pages"
CATALOG_FILENAME = "ai_impacts_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "aiimpacts.org"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_VERSION = re.compile(r"\d+\.\d+\Z")
_DEED = re.compile(r"(?:legalcode|deed)(?:[.-][a-z0-9]+)*\Z")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*(?:\"application/ld\+json\"|'application/ld\+json')[^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"license"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_ENTRY_H1 = re.compile(
    r"""(?is)<h1\b[^>]*class\s*=\s*(?:"[^"]*\b(?:entry-title|page-title)\b[^"]*"|'[^']*\b(?:entry-title|page-title)\b[^']*')[^>]*>(.*?)</h1>"""
)
_H1 = re.compile(r"(?is)<h1\b([^>]*)>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_CC_URL = re.compile(r"(?i)\bhttps?://(?:www\.)?creativecommons\.org/[^\s\"'<>]+")
_LICENCE_START = re.compile(
    r"(?i)(?<![a-z0-9])(?:cc[\s-]?0|cc[\s-]?by|creative[\s]+commons)(?![a-z0-9])"
)
_CC_KIND = re.compile(
    r"(?i)[\s]+(cc[\s-]?0|zero|public[\s]+domain|attribution|share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?)\b"
)
_PLAIN_TAIL = re.compile(
    r"""(?ix)
    ^(?:
        $
        | [.,;:)\]]
        | \s*$
        | \s*\d
        | \s*licen[cs]e\b
        | \s*international\b
        | \s*deed\b
    )
    """
)
_SUFFIX = re.compile(
    r"""(?ix)
    ^[\s,.:;|()/\-]{0,8}
    (
        nc | nd | sa
        | non[\s-]*commercial
        | no[\s-]*deriv(?:ative)?s?
        | share[\s-]*alike
    )
    \b
    """
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
    "dc.date.issued",
)
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_SITE_SUFFIXES = (
    " | AI Impacts",
    " - AI Impacts",
    " – AI Impacts",
    " — AI Impacts",
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
)
_BLOCKED_PREFIXES = (
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/xmlrpc.php",
    "/wp-login.php",
    "/feed",
    "/comments",
    "/category",
    "/tag",
    "/author",
)
_ALLOWED_URL_CODES = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_URL_CODES = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_RESTRICTIVE_SUFFIXES = frozenset({"nc", "nd", "noncommercial", "noderivatives"})
_SHARE_ALIKE_SUFFIXES = frozenset({"sa", "sharealike"})
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
    """A catalog row or page failed the AI Impacts page rules."""


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
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public AI Impacts page")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or not is_official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public AI Impacts page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons only for a stated CC0, CC BY, or CC BY-SA licence.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A following
    NonCommercial, NoDerivatives, or ShareAlike suffix is not read as plain
    CC BY. ShareAlike alone is CC BY-SA. Script and style text do not count.
    A copyright line, an all-rights-reserved line, or a terms link is not a
    licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    urls = _jsonld_license_urls(page_text)
    urls.extend(_meta_license_urls(visible))
    urls.extend(_link_license_urls(visible))
    visible, anchor_urls = _blank_cc_anchors(visible)
    urls.extend(anchor_urls)
    urls.extend(_CC_URL.findall(visible))
    if any(_cc_url_kind(url) == "allowed" for url in urls):
        return RIGHTS_CREATIVE_COMMONS
    prose = _CC_URL.sub(" ", _plain_text(visible))
    if _prose_has_allowed_licence(prose):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, and a copyright year are not
    publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        return match.group(1)
    for raw in _jsonld_dates(page_html):
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    heading = _ENTRY_H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    for attrs, inner in _H1.findall(visible):
        if _is_site_header(attrs):
            continue
        title = _clean_title(_TAG.sub(" ", inner))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_visible_html(page_html)).get("og:site_name", ""))
    if site and site.casefold() not in {"wordpress", "localhost"}:
        return site
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    Qualitative wording is not converted into a probability.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _official_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    lowered = path.lower()
    if not path.startswith("/"):
        return False
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    for prefix in _BLOCKED_PREFIXES:
        if bare == prefix or bare.startswith(prefix + "/"):
            return False
    if bare.endswith("/feed"):
        return False
    return True


def _prose_has_allowed_licence(text: str) -> bool:
    normalized = _normalize_licence_text(text)
    for match in _LICENCE_START.finditer(normalized):
        if _licence_at(normalized, match) == "allowed":
            return True
    return False


def _licence_at(text: str, match: re.Match[str]) -> str:
    token = match.group(0)
    rest = text[match.end() :]
    if re.fullmatch(r"(?i)cc[\s-]?0", token):
        if _suffixes(rest) & _RESTRICTIVE_SUFFIXES:
            return "restricted"
        return "allowed"
    if re.fullmatch(r"(?i)cc[\s-]?by", token):
        suffixes = _suffixes(rest)
        if suffixes & _RESTRICTIVE_SUFFIXES:
            return "restricted"
        if suffixes & _SHARE_ALIKE_SUFFIXES:
            return "allowed"
        if _PLAIN_TAIL.match(rest):
            return "allowed"
        return "none"
    kind = _CC_KIND.match(rest)
    if kind is None:
        return "none"
    name = re.sub(r"[\s-]+", "", kind.group(1).casefold())
    after = rest[kind.end() :]
    extra = _suffixes(after)
    if name == "attribution":
        return _family_from_suffixes(extra)
    if name.startswith("share"):
        if extra & _RESTRICTIVE_SUFFIXES:
            return "restricted"
        return "allowed"
    if name.startswith("non") or name.startswith("no"):
        return "restricted"
    if name == "publicdomain" and re.match(r"(?i)[\s-]*mark\b", after):
        return "none"
    if extra & _RESTRICTIVE_SUFFIXES:
        return "restricted"
    return "allowed"


def _suffixes(rest: str) -> set[str]:
    found: set[str] = set()
    while True:
        match = _SUFFIX.match(rest)
        if match is None:
            return found
        found.add(_normalize_suffix(match.group(1)))
        rest = rest[match.end() :]


def _family_from_suffixes(suffixes: set[str]) -> str:
    if suffixes & _RESTRICTIVE_SUFFIXES:
        return "restricted"
    if suffixes & _SHARE_ALIKE_SUFFIXES:
        return "allowed"
    return "allowed"


def _normalize_suffix(value: str) -> str:
    token = re.sub(r"[\s-]+", "", value.casefold())
    if token in {"nc", "nd", "sa"}:
        return token
    if token.startswith("non"):
        return "noncommercial"
    if token.startswith("no"):
        return "noderivatives"
    if token.startswith("share"):
        return "sharealike"
    return token


def _cc_url_kind(url: str) -> str | None:
    candidate = unescape(url).strip().rstrip(").,;\"'")
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif "://" not in candidate:
        return None
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if parsed.scheme.lower() not in {"http", "https"} or host != "creativecommons.org":
        return None
    parts = [part.casefold() for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "publicdomain" and parts[1] == "zero":
        if _deed_suffix_ok(parts[2:]):
            return "allowed"
        return None
    if len(parts) >= 2 and parts[0] == "licenses":
        code = parts[1]
        if code in _RESTRICTED_URL_CODES:
            return "restricted"
        if code in _ALLOWED_URL_CODES and _deed_suffix_ok(parts[2:]):
            return "allowed"
    return None


def _deed_suffix_ok(rest: list[str]) -> bool:
    if not rest:
        return True
    if _VERSION.fullmatch(rest[0]) is None:
        return False
    if len(rest) == 1:
        return True
    return len(rest) == 2 and _DEED.fullmatch(rest[1]) is not None


def _blank_cc_anchors(html: str) -> tuple[str, list[str]]:
    urls: list[str] = []

    def replace(match: re.Match[str]) -> str:
        href = _attr_href(match.group(1))
        if href and _cc_url_kind(href) is not None:
            urls.append(href)
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, html), urls


def _attr_href(attrs_text: str) -> str:
    attrs = _attrs(f"<a {attrs_text}>")
    return attrs.get("href", "")


def _jsonld_license_urls(page_html: str) -> list[str]:
    urls: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_LICENSE.findall(blob):
            urls.append(raw.replace("\\/", "/"))
    return urls


def _jsonld_dates(page_html: str) -> list[str]:
    dates: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in re.findall(r'"datePublished"\s*:\s*"([^"]+)"', blob):
            dates.append(raw)
    return dates


def _meta_license_urls(html: str) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in _LICENSE_META if metas.get(name)]


def _link_license_urls(html: str) -> list[str]:
    urls: list[str] = []
    for tag in _LINK.findall(html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        href = attrs.get("href", "")
        if href and ("license" in rel or _cc_url_kind(href) is not None):
            urls.append(href)
    return urls


def _visible_html(page_html: str) -> str:
    return _HIDDEN.sub(" ", _COMMENT.sub(" ", page_html))


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
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(page_text)


def _normalize_licence_text(value: str) -> str:
    return _plain_text(value).translate(_DASHES)


def _is_site_header(attrs: str) -> bool:
    classes = _attrs(f"<h1 {attrs}>").get("class", "")
    tokens = set(classes.casefold().split())
    return "mh-header-title" in tokens or "site-title" in tokens


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
