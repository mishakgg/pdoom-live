"""Metadata catalog of public Redwood Research pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights stay unknown unless the page states a reuse licence. creative_commons
means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. mit and apache-2.0 are recorded only when the page
states those licences. A public page, a copyright notice, and a terms link
are not licences. A page that does not state a publication date keeps the
date unknown. Updated, modified, last updated, and copyright years are not
publication dates. The live URL is stored as confirmed; a different
rel=canonical does not replace it. This module does not fetch and it is not
a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "redwood_pages"
CATALOG_FILENAME = "redwood_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Redwood Research"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
ALLOWED_RIGHTS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_MIT, RIGHTS_APACHE}
)
UNKNOWN_DATE = "unknown"
REDWOOD_HOST = "www.redwoodresearch.org"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
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
    "dc.date.issued",
)
_LICENSE_META_KEYS = frozenset(
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
_SITE_SUFFIXES = (
    " | Redwood Research",
    " — Redwood Research",
    " – Redwood Research",
    " - Redwood Research",
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
    ".ico",
    ".css",
    ".js",
    ".txt",
    ".mp3",
    ".mp4",
    ".woff",
    ".woff2",
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
# Negative lookaheads reject NonCommercial and NoDerivatives, so CC BY-NC,
# CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND are not creative_commons.
_CC_BY_PHRASE = re.compile(
    r"(?i)\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa|NonCommercial|NoDerivatives)\b)"
    r"|creative\s+commons\s+attribution\b(?![\s-]*(?:NonCommercial|NoDerivatives|share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?)\b)"
)
_CC_BY_SA_PHRASE = re.compile(
    r"(?i)\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd|NonCommercial|NoDerivatives)\b)"
    r"|creative\s+commons\s+attribution[\s-]*share[\s-]*alike\b(?![\s-]*(?:NonCommercial|NoDerivatives)\b)"
)
_CC0_PHRASE = re.compile(
    r"(?i)\bcc[\s-]*0\b|\bcc0\b|creative\s+commons(?:\s+public\s+domain)?[\s-]+zero\b"
)
_CC_COPYING_URL = re.compile(
    r"(?i)creativecommons\.org/publicdomain/zero/"
    r"|creativecommons\.org/licenses/by(?![\s-]*(?:nc|nd|NonCommercial|NoDerivatives)\b)(?:-sa)?/"
)
_CC_RESTRICTED = re.compile(
    r"(?i)\bcc[\s-]*by[\s-]*(?:nc|nd)\b"
    r"|creativecommons\.org/licenses/by-(?:nc|nd)\b"
    r"|attribution[\s-]*(?:NonCommercial|NoDerivatives|non[\s-]*commercial|no[\s-]*deriv)"
)
_MIT = re.compile(
    r"(?i)\bmit\s+licen[cs]e\b|\blicen[cs]ed under (?:the )?mit(?:\s+licen[cs]e)?\b"
)
_APACHE = re.compile(
    r"(?i)\bapache-2\.0\b"
    r"|\bapache\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
    r"|\blicen[cs]ed under (?:the )?apache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2\.0\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Redwood Research page rules."""


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
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
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
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be unknown, creative_commons, mit, or apache-2.0")


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
        raise CatalogError("canonical URL must be a public Redwood Research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != REDWOOD_HOST
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
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Redwood Research page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == REDWOOD_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label stated by the page.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. Negative lookaheads
    reject NonCommercial and NoDerivatives, so CC BY-NC, CC BY-ND, CC BY-NC-SA,
    CC BY-NC-ND, and a creativecommons.org/licenses/by-nc URL stay unknown.
    ``mit`` and ``apache-2.0`` are their own tokens when the page states those
    licences. A public page, a copyright notice, and a terms link are not
    licences. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    folded = _fold(_licence_text(page_text))
    if _APACHE.search(folded):
        return RIGHTS_APACHE
    if _MIT.search(folded):
        return RIGHTS_MIT
    if _CC_RESTRICTED.search(folded):
        return RIGHTS_UNKNOWN
    if any(
        pattern.search(folded)
        for pattern in (_CC0_PHRASE, _CC_BY_SA_PHRASE, _CC_BY_PHRASE, _CC_COPYING_URL)
    ):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, last updated, and copyright years are not publication
    dates. A date inside script or style text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            date.fromisoformat(match.group(1))
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    description = _clean_text(metas.get("og:description") or metas.get("description") or "")
    generic: str | None = None
    for key in _TITLE_KEYS:
        if not metas.get(key):
            continue
        title = _clean_title(metas[key])
        if not title:
            continue
        if title.casefold() != PUBLISHER.casefold():
            return title
        generic = generic or title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        # A site-wide og:title is not a page title. The first heading is, unless
        # it only repeats the page description.
        if title and title.casefold() not in {PUBLISHER.casefold(), description.casefold()}:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title and title.casefold() != PUBLISHER.casefold():
            return title
        generic = generic or title
    if generic:
        return generic
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    titled = " ".join(metas.get(key, "") for key in _TITLE_KEYS)
    if PUBLISHER in _clean_text(titled) or PUBLISHER in _plain(visible):
        return PUBLISHER
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


def _official_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/") or path.endswith("/"):
        return False
    lowered = path.lower()
    if lowered.startswith("/_next/") or "opengraph-image" in lowered:
        return False
    return not lowered.endswith(_DOWNLOAD_SUFFIXES)


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _licence_text(page_text: str) -> str:
    visible = _visible(page_text)
    parts = [_plain(visible)]
    metas = _metas(visible)
    for key, value in metas.items():
        if key in _LICENSE_META_KEYS and value:
            parts.append(value)
    for tag in _LINKISH.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold().replace("licence", "license")
        if "license" in rel.split():
            href = attrs.get("href", "")
            if href:
                parts.append(href)
    return " ".join(parts)


def _visible(page_html: str) -> str:
    return _HIDDEN.sub(" ", page_html)


def _plain(page_html: str) -> str:
    text = unescape(_TAG.sub(" ", page_html)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(value: str) -> str:
    return value.casefold().translate(_DASHES)


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


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
