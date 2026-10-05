"""Metadata catalog of public NIST AI RMF HTML pages.

Rows are the title, publisher, canonical URL, date, and rights for official
NIST HTML pages. This catalog is separate from the NIST PDF rows in the US
federal publications catalog. It does not store document bodies and it is not
a belief collector. A page that does not state a publication date keeps the
date unknown. Modification times are not publication dates.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

CATALOG_ID = "nist_ai_rmf_pages"
CATALOG_FILENAME = "nist_ai_rmf_pages.json"
RIGHTS = "us_government_work"
PUBLISHER = "National Institute of Standards and Technology"
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"www.nist.gov", "airc.nist.gov"})
ENTRY_FIELDS = ("title", "publisher", "canonical_url", "date", "rights")
MAX_TITLE_CHARS = 300
MAX_DESCRIPTION_CHARS = 800
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
SITE_SUFFIX = re.compile(r"(?i)\s+(?:\|\s*NIST|[-–—]\s*AIRC)\s*$")
TAG = re.compile(r"(?is)<[^>]+>")
META = re.compile(r"(?is)<meta\b[^>]*>")
LINK = re.compile(r"(?is)<link\b[^>]*>")
H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
PUBLICATION_DATE_KEYS = ("article:published_time", "dcterms.created", "dcterms.date")
TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")

_CONCEPT_NOTE = "/programs-projects/concept-note-ai-rmf-profile-trustworthy-ai-critical-infrastructure"


class CatalogError(ValueError):
    """A NIST AI RMF page row failed validation."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    if set(document) != {"catalog_id", "description", "entries"}:
        raise CatalogError("catalog fields must be catalog_id, description, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CatalogError(f"entries[{index}] must be an object")
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict) or set(entry) != set(ENTRY_FIELDS):
        raise CatalogError(
            "entry fields must be title, publisher, canonical URL, date, and rights"
        )
    _require_text(entry["title"], "title", MAX_TITLE_CHARS)
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] != RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an official NIST AI RMF HTML page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or host not in OFFICIAL_HOSTS
        or ".." in path
        or "\\" in path
        or not _ai_rmf_html_path(host, path)
    ):
        raise CatalogError(f"canonical URL must be an official NIST AI RMF HTML page: {url}")
    return url


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one NIST HTML page.

    The record does not include the document body. A page that does not state
    a publication date gets date unknown.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    record = {
        "title": title_from_page(page_html),
        "publisher": PUBLISHER,
        "canonical_url": canonical_url_from_page(page_html, page_url=page_url),
        "date": publication_date_from_page(page_html),
        "rights": RIGHTS,
    }
    return validate_entry(record)


def title_from_page(page_html: str) -> str:
    metas = _metas(page_html)
    for key in TITLE_KEYS:
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    heading = H1.search(page_html)
    if heading:
        title = _clean_title(TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = TITLE.search(page_html)
    if title_tag:
        title = _clean_title(TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time and og:updated_time are not publication dates.
    """

    metas = _metas(page_html)
    for key in PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def canonical_url_from_page(page_html: str, *, page_url: str) -> str:
    for tag in LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").lower().split()
        if "canonical" not in rel:
            continue
        href = attrs.get("href", "").strip()
        if href:
            return validate_canonical_url(urljoin(page_url, href))
    return validate_canonical_url(page_url)


def _ai_rmf_html_path(host: str, path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith(".pdf") or "/document/" in lowered:
        return False
    if host == "www.nist.gov":
        return lowered.startswith("/itl/ai-risk-management-framework") or lowered.startswith(_CONCEPT_NOTE)
    if host == "airc.nist.gov":
        return lowered.startswith("/airmf-resources/")
    return False


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long")


def _clean_title(value: str) -> str:
    text = unescape(TAG.sub(" ", value))
    text = re.sub(r"\s+", " ", text).strip()
    text = SITE_SUFFIX.sub("", text).strip()
    text = re.sub(r"^[^A-Za-z0-9]+", "", text).strip()
    return text


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
