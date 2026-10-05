"""Metadata catalog of public Epoch AI pages about AI trends and compute.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, chart series, and
datasets are not stored. Rights stay unknown unless that page states a reuse
licence that allows copying. A public page, a copyright notice, or a link to a
licence is not itself a licence. Updated and modified times are not
publication dates; a page that does not state a publication date keeps the
date unknown. This module does not fetch and it is not a belief collector.
runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "epoch_pages"
CATALOG_FILENAME = "epoch_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY = "creative_commons_attribution"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CC_BY})
PUBLISHER = "Epoch AI"
OFFICIAL_HOST = "epoch.ai"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "chart",
        "chart_data",
        "content",
        "csv",
        "dataset",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "quotation",
        "quote",
        "series",
        "text",
        "transcript",
        "transcript_text",
    }
)
_TOPIC_SLUGS = frozenset(
    {
        "capabilities",
        "chips",
        "data-centers",
        "energy",
        "future-of-ai",
        "scaling",
        "software-progress",
    }
)
_DATA_PATHS = frozenset(
    {
        "/data/ai-data-centers",
        "/data/ai-models",
        "/data/gpu-clusters",
        "/data/machine-learning-hardware",
    }
)
_MARKERS = frozenset(
    {
        "capacity",
        "chip",
        "chips",
        "cluster",
        "clusters",
        "compute",
        "computing",
        "energy",
        "flop",
        "flops",
        "gpu",
        "gpus",
        "hardware",
        "scaling",
        "supercomputer",
        "supercomputers",
        "training",
        "trend",
        "trends",
    }
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
)
_SITE_SUFFIXES = (" | Epoch AI", " - Epoch AI")
_PUBLICATION_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_GRANT = "free to use, distribute, and reproduce"
_LICENCE_NAMES = (
    "creative commons attribution",
    "creative commons by license",
    "creative commons by licence",
    "cc-by license",
    "cc-by licence",
)
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:$|[Tt\s])")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)


class CatalogError(ValueError):
    """A catalog row or page failed the Epoch AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_epoch_host(hostname: str) -> bool:
    """True only for the official epoch.ai host."""
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    The page must state a reuse licence and a grant to copy, distribute, or
    reproduce. Those two statements have to sit in the same notice. A copyright
    line, a terms link, or the licence name by itself stays unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    plain = _plain(page_text).casefold()
    start = 0
    while True:
        at = plain.find(_GRANT, start)
        if at < 0:
            return RIGHTS_UNKNOWN
        window = plain[max(0, at - 80) : at + len(_GRANT) + 320]
        if any(name in window for name in _LICENCE_NAMES):
            return RIGHTS_CC_BY
        start = at + len(_GRANT)


def date_from_page(page_text: str) -> str:
    """Return a publication date, or unknown when the page does not state one.

    pagefind:update_date, modified times, and dates inside chart tables are
    not publication dates.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    metas = _metas(page_text)
    for key in _PUBLICATION_META:
        parsed = _parse_date(metas.get(key, ""))
        if parsed:
            return parsed
    for raw in _meta_values(page_text, "pagefind:date"):
        parsed = _parse_date(raw)
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    if metas.get("og:title"):
        title = _clean_title(metas["og:title"])
        if title:
            return title
    visible = _visible_html(page_html)
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(heading.group(1))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _metas(page_html).get("og:site_name", "").strip()
    if not site:
        raise CatalogError("publisher is required")
    return site


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body, chart series, or dataset.
    ``page_url`` is the live URL that was fetched.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


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
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
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
        raise CatalogError("canonical URL must be an https epoch.ai trend or compute page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
        or parsed.port is not None
        or not official_epoch_host(host)
        or not _trend_or_compute_path(parsed.path or "")
    ):
        raise CatalogError(f"canonical URL must be an https epoch.ai trend or compute page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _trend_or_compute_path(path: str) -> bool:
    if not path or path != path.lower() or path.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if path.endswith("/") or ".." in path or "//" in path or "\\" in path:
        return False
    if path == "/data-insights":
        return True
    if path in _DATA_PATHS:
        return True
    parts = path.split("/")
    if len(parts) != 3 or not parts[2]:
        return False
    section, slug = parts[1], parts[2]
    if section == "topics":
        return slug in _TOPIC_SLUGS
    if section in {"data-insights", "publications"}:
        return _marked_slug(slug)
    return False


def _marked_slug(slug: str) -> bool:
    if _SLUG.fullmatch(slug) is None:
        return False
    if "data-center" in slug:
        return True
    return bool(set(slug.split("-")) & _MARKERS)


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


def _visible_html(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", _visible_html(page_text)))
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _meta_values(page_html: str, name: str) -> list[str]:
    return [content for key, content in _meta_pairs(page_html) if key == name]


def _meta_pairs(page_html: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for tag in _META.findall(_visible_html(page_html)):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs:
            pairs.append((key, attrs["content"]))
    return pairs


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        attrs.setdefault(name.lower(), unescape(double or single or bare).strip())
    return attrs


def _parse_date(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    iso = _ISO_PREFIX.match(text)
    if iso and _iso_date(iso.group(1)):
        return iso.group(1)
    head = text.split(" GMT", 1)[0].strip()
    try:
        parsed = datetime.strptime(head, "%a %b %d %Y %H:%M:%S").date()
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True
