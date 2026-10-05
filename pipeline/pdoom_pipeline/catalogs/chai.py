"""Metadata catalog of public Center for Human-Compatible AI pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights is ``creative_commons`` only when the page states CC0, CC BY, or CC
BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A match
on the substring "creative commons" or "cc-by" is not CC BY when
NonCommercial, NoDerivatives, or ShareAlike follows. A public page, a
copyright notice, an all-rights-reserved line, or a terms link is not a
licence. Updated times, modified times, and copyright years are not
publication dates. A page that does not state a publication date keeps the
date unknown. The live URL is stored as confirmed; a different rel=canonical
does not replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "chai_pages"
CATALOG_FILENAME = "chai_pages.json"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
CHAI_HOST = "humancompatible.ai"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>|<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_FOOTER = re.compile(r"(?is)<footer\b[^>]*>(.*?)</footer>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_COPYRIGHT_NAME = re.compile(
    r"(?is)(?:©|&copy;|&#169;)\s*(?:19|20)\d{2}\s+([^<]{2,200})"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_PUBLISHER_NAME = "Center for Human-Compatible Artificial Intelligence"
_SITE_SUFFIXES = (
    f" – {_PUBLISHER_NAME}",
    f" — {_PUBLISHER_NAME}",
    f" - {_PUBLISHER_NAME}",
    f" | {_PUBLISHER_NAME}",
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
    ".css",
    ".js",
    ".txt",
    ".ico",
)
_CC_ALLOWED = frozenset({"cc0", "cc-by", "cc-by-sa"})
_CC_DISALLOWED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_CC_URL = re.compile(
    r"(?:https?:)?//(?:www\.)?creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>[a-z0-9-]+)|licenses/(?P<code>[a-z0-9-]+))",
    re.I,
)
# Longer licences are removed before shorter ones so "cc-by" inside
# "cc-by-nc" or "cc-by-sa" is not read as CC BY.
_PROSE_LICENCES = (
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*derivatives\b"
            r"|cc[\s-]*by[\s-]*nc[\s-]*nd\b"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike\b"
            r"|cc[\s-]*by[\s-]*nc[\s-]*sa\b"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial\b(?![\s-]*(?:share[\s-]*alike|no[\s-]*derivatives)\b)"
            r"|cc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"creative commons attribution[\s-]+no[\s-]*derivatives\b"
            r"|cc[\s-]*by[\s-]*nd\b"
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"creative commons attribution[\s-]+share[\s-]*alike\b"
            r"|cc[\s-]*by[\s-]*sa\b"
        ),
    ),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution\b(?![\s-]+(?:non[\s-]*commercial|no[\s-]*derivatives|share[\s-]*alike)\b)"
            r"|cc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
        ),
    ),
    (
        "cc0",
        re.compile(
            r"\bcc[\s-]*0\b"
            r"|creative commons zero\b"
            r"|cc[\s-]*zero\b"
            r"|creative commons public domain dedication\b"
        ),
    ),
)
_URL_CODES = {
    "by-nc-nd": "cc-by-nc-nd",
    "by-nc-sa": "cc-by-nc-sa",
    "by-nc": "cc-by-nc",
    "by-nd": "cc-by-nd",
    "by-sa": "cc-by-sa",
    "by": "cc-by",
}


class CatalogError(ValueError):
    """A catalog row or page failed the CHAI page rules."""


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
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public CHAI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != CHAI_HOST
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
        raise CatalogError(f"canonical URL is not a public CHAI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == CHAI_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons only for a stated CC0, CC BY, or CC BY-SA licence.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A disallowed
    licence also keeps the page unknown when the text contains the shorter
    substring "creative commons" or "cc-by". Script, style, and comment text
    does not count. A copyright notice, an all-rights-reserved line, a terms
    link, or the bare words "creative commons" are not a reuse licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _HIDDEN.sub(" ", page_text)
    families = _licence_families(visible)
    if families & _CC_DISALLOWED:
        return RIGHTS_UNKNOWN
    if families & _CC_ALLOWED:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a "last updated" line, a copyright
    year, and dates on listed child entries are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
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
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    for heading in _H1.findall(page_html):
        title = _clean_title(_TAG.sub(" ", heading))
        if title:
            return title
    title_tag = _TITLE.search(page_html)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    metas = _metas(page_html)
    for key in ("og:site_name", "publisher", "application-name"):
        name = _clean_text(metas.get(key, ""))
        if name and name.casefold() not in {"wordpress", "kadence"}:
            return name
    holder = _copyright_holder(page_html)
    if holder:
        return holder
    titled = _publisher_from_title(page_html)
    if titled:
        return titled
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _official_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    lowered = path.lower()
    return not lowered.endswith(_DOWNLOAD_SUFFIXES)


def _licence_families(visible_html: str) -> set[str]:
    families: set[str] = set()
    for match in _CC_URL.finditer(visible_html):
        family = _family_from_cc_url(match.group("pd"), match.group("code"))
        if family:
            families.add(family)
    plain = _clean_text(visible_html).casefold().replace("–", "-").replace("—", "-")
    for family, pattern in _PROSE_LICENCES:
        if pattern.search(plain):
            families.add(family)
            plain = pattern.sub(" ", plain)
    return families


def _family_from_cc_url(public_domain: str | None, code: str | None) -> str | None:
    if public_domain:
        if public_domain.lower() == "zero":
            return "cc0"
        return None
    if not code:
        return None
    return _URL_CODES.get(code.lower())


def _copyright_holder(page_html: str) -> str:
    footer = _FOOTER.search(page_html)
    if footer is None:
        return ""
    block = _HIDDEN.sub(" ", footer.group(1))
    match = _COPYRIGHT_NAME.search(block)
    if match is None:
        return ""
    name = _clean_text(match.group(1))
    name = re.sub(r"(?i)\s*all rights reserved\.?$", "", name).strip(" .")
    if not name or name.casefold() == "all rights reserved":
        return ""
    if re.fullmatch(r"(?:19|20)\d{2}", name):
        return ""
    return name


def _publisher_from_title(page_html: str) -> str:
    title_tag = _TITLE.search(page_html)
    if title_tag is None:
        return ""
    text = _clean_text(_TAG.sub(" ", title_tag.group(1)))
    if text == _PUBLISHER_NAME:
        return text
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix):
            return suffix.lstrip(" –—-|").strip()
    return ""


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


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    visible = _HIDDEN.sub(" ", page_html)
    for tag in _META.findall(visible):
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
