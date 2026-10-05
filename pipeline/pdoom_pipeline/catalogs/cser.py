"""Metadata catalog of public Centre for the Study of Existential Risk pages.

Each stored URL was confirmed with one bounded GET of www.cser.ac.uk. A row
keeps the title, publisher, canonical URL, date, and rights label. Page text
is not stored. A Cloudflare challenge, an HTTP 403, or any non-HTML response
is not a row. Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. ``uk_ogl`` is used only when the
page states the phrase "open government licence". This centre is not a UK
government publisher. Crown copyright, a copyright notice, a public page, and
a terms link are not licences. The American spelling "license" does not state
the Open Government Licence. A missing publication date stays unknown.
Updated, modified, last updated, and copyright years are not publication
dates. The live URL is stored as confirmed; a different rel=canonical does
not replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cser_pages"
CATALOG_FILENAME = "cser_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
CSER_HOST = "www.cser.ac.uk"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# A labeled publication date. Last updated, updated, and modified do not match.
_DATE_PUBLISHED = re.compile(
    r"(?<!last )(?<!updated )(?<!modified )\b(?:date published|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dcterms.created",
    "dc.date.issued",
)
_MODIFIED_DATE_KEYS = (
    "article:modified_time",
    "article:updated_time",
    "og:updated_time",
    "dcterms.modified",
    "dc.date.modified",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dc.publisher", "dcterms.publisher")
_SITE_SUFFIXES = (" - CSER", " | CSER", " – CSER", " — CSER")
_DOWNLOAD_SUFFIXES = (".pdf", ".zip", ".csv", ".json", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".webp")
_BLOCKED_PREFIXES = ("/wp-admin", "/wp-json", "/wp-content", "/wp-includes", "/wp-login.php", "/xmlrpc.php")
# creative_commons is only a copying licence: CC0, CC BY, or CC BY-SA.
# Negative lookaheads reject NonCommercial and NoDerivatives, so by-nc,
# by-nd, by-nc-sa, and by-nc-nd stay unknown. A URL containing
# creativecommons.org/licenses/by-nc stays unknown.
_NC_ND = r"(?:nc|nd|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?)"
_CC0_PHRASE = re.compile(r"\bcc[\s-]*0\b|creative commons(?:\s+public\s+domain)?[\s-]+zero\b")
_CC_BY_SA_PHRASE = re.compile(
    r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*" + _NC_ND + r"\b)"
    r"|creative commons\s+attribution[\s-]*(?:share[\s-]*alike|sa)\b(?![\s-]*" + _NC_ND + r"\b)"
)
_CC_BY_PHRASE = re.compile(
    r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?|share[\s-]*alike)\b)"
    r"|creative commons\s+attribution\b"
    r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?|sa|nc|nd)\b)"
)
_CC_COPYING_URL = re.compile(
    r"creativecommons\.org/(?:licenses/by(?!-(?:nc|nd)\b)(?:-sa)?/|publicdomain/zero/)"
)


class CatalogError(ValueError):
    """A catalog row or page failed the CSER page rules."""


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
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS}, {RIGHTS_UK_OGL}, or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public CSER page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != CSER_HOST
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
        or not _html_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public CSER page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == CSER_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label stated by the page.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA. Negative lookaheads
    reject NonCommercial and NoDerivatives, including a URL that contains
    creativecommons.org/licenses/by-nc. ``uk_ogl`` means the page states the
    phrase "open government licence". The American spelling "license" does
    not count. A public page, a copyright notice, Crown copyright, and a
    terms link stay unknown. Script and style text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    texts = [_plain(html).casefold()]
    texts.extend(_plain(item).casefold() for item in _meta_contents(html))
    if any(_states_creative_commons(item) for item in texts):
        return RIGHTS_CREATIVE_COMMONS
    if any(OGL_PHRASE in item for item in texts):
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, last updated, and copyright years are not publication
    dates. A date inside script or style text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    html = _without_hidden(page_html)
    metas = _metas(html)
    for key in _MODIFIED_DATE_KEYS:
        metas.pop(key, None)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    match = _DATE_PUBLISHED.search(_plain(html).casefold())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    html = _without_hidden(page_html)
    metas = _metas(html)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(html)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(html)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_without_hidden(page_html))
    for key in _PUBLISHER_KEYS:
        name = _clean_text(metas.get(key, ""))
        if name:
            return name
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
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


def _html_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    lowered = path.casefold()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return not any(lowered == prefix or lowered.startswith(prefix + "/") for prefix in _BLOCKED_PREFIXES)


def _states_creative_commons(plain: str) -> bool:
    text = _normalize_dashes(plain.casefold())
    return any(pattern.search(text) for pattern in (_CC0_PHRASE, _CC_BY_SA_PHRASE, _CC_BY_PHRASE, _CC_COPYING_URL))


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = _TAG.sub(" ", _without_hidden(page_text))
    return _clean_text(text)


def _normalize_dashes(text: str) -> str:
    return text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value))
    text = _normalize_dashes(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_contents(html: str) -> list[str]:
    contents: list[str] = []
    for tag in _META.findall(html):
        content = _attrs(tag).get("content", "")
        if content:
            contents.append(content)
    return contents


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
