"""Metadata catalog of public UK AI Security Institute pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
Rights is ``uk_ogl`` only when the page states the Open Government Licence.
Otherwise rights is ``unknown``. A page that does not state a publication
date keeps the date unknown. Updated and modified times are not publication
dates. The live URL is stored as confirmed; a different rel=canonical does
not replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "uk_aisi_pages"
CATALOG_FILENAME = "uk_aisi_pages.json"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_UK_OGL, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
AISI_HOST = "www.aisi.gov.uk"
GOVUK_HOST = "www.gov.uk"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_TAG = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>|<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_FROM_BLOCK = re.compile(r"(?is)<dt\b[^>]*>\s*From:\s*</dt>\s*<dd\b[^>]*>(.*?)</dd>")
_ANCHOR = re.compile(r"""(?is)<a\b[^>]*href\s*=\s*(?:"([^"]*)"|'([^']*)')[^>]*>(.*?)</a>""")
_PUBLICATION_DATE_KEYS = (
    "govuk:first-published-at",
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_SITE_SUFFIXES = (
    " | The AI Security Institute (AISI)",
    " | The AI Security Institute",
    " | AISI Work",
    " - The AI Security Institute (AISI)",
    " - GOV.UK",
)
_DOWNLOAD_SUFFIXES = (".pdf", ".zip", ".csv", ".json", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".webp")
_GOVUK_PREFIXES = (
    "/government/organisations/ai-security-institute",
    "/government/organisations/ai-safety-institute",
    "/government/publications/ai-safety-institute",
    "/government/publications/ai-security-institute",
    "/government/publications/uk-ai-safety-institute",
)


class CatalogError(ValueError):
    """A catalog row or page failed the UK AISI page rules."""


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
        raise CatalogError(f"rights must be {RIGHTS_UK_OGL} or {RIGHTS_UNKNOWN}")


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
        raise CatalogError("canonical URL must be a public UK AISI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() not in {AISI_HOST, GOVUK_HOST}
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
        or not _official_path(host, path)
    ):
        raise CatalogError(f"canonical URL is not a public UK AISI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in {AISI_HOST, GOVUK_HOST} and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return uk_ogl when the page states the Open Government Licence.

    Script and style text does not count. Crown copyright alone, and the
    American spelling "license", do not state the Open Government Licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    if OGL_PHRASE in _plain_text(page_text).casefold():
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    govuk:updated-at, govuk:public-updated-at, article:modified_time, and
    og:updated_time are not publication dates.
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
    heading = _H1.search(page_html)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
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
    names: list[str] = []
    primary = _metas(page_html).get("govuk:primary-publishing-organisation", "").strip()
    if primary and primary.casefold() != "gov.uk":
        names.append(primary)
    for name in _from_organisations(page_html):
        if name not in names:
            names.append(name)
    if names:
        return "; ".join(names)
    host = (urlparse(page_url).hostname or "").lower()
    if host == AISI_HOST:
        site = _metas(page_html).get("og:site_name", "").strip()
        if site and site.casefold() != "gov.uk":
            return site
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


def _official_path(host: str, path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if host == AISI_HOST:
        return path in {"", "/"} or path.startswith("/")
    if host == GOVUK_HOST:
        bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
        for prefix in _GOVUK_PREFIXES:
            if bare == prefix or bare.startswith(prefix + "/") or bare.startswith(prefix + "-"):
                return True
    return False


def _from_organisations(page_html: str) -> list[str]:
    names: list[str] = []
    for block in _FROM_BLOCK.findall(page_html):
        for href_double, href_single, inner in _ANCHOR.findall(block):
            href = unescape(href_double or href_single).strip()
            if "/government/organisations/" not in href:
                continue
            name = _clean_text(inner)
            if name and name not in names:
                names.append(name)
    return names


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
