"""Metadata catalog of official EU AI Act pages.

Rows are EUR-Lex or European Commission pages. Each stored URL was confirmed
with one bounded GET. The catalog keeps a title, publisher, canonical URL,
date, and rights label. It does not store the regulation text. A page that
does not state a reuse licence keeps the rights label ``unknown``.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "eu_ai_act"
CATALOG_FILENAME = "eu_ai_act.json"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY_4_0 = "cc_by_4_0"
ALLOWED_RIGHTS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CC_BY_4_0})
UNKNOWN_DATE = "unknown"
MAX_TEXT_CHARS = 500

_EUR_LEX_HOST = "eur-lex.europa.eu"
_COMMISSION_SUFFIXES = ("ec.europa.eu", "commission.europa.eu")
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_TAG = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>|<[^>]+>")
_CC_BY_4_0 = re.compile(
    r"(?i)(?:"
    r"creative commons attribution 4\.0(?: international)?"
    r"|cc[-\s]by[-\s]4\.0"
    r"|creativecommons\.org/licenses/by/4\.0"
    r")"
)


class CatalogError(ValueError):
    """A catalog row or URL violates the EU AI Act page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def is_official_host(hostname: str) -> bool:
    """True for EUR-Lex or a European Commission host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    if host == _EUR_LEX_HOST:
        return True
    return any(host == suffix or host.endswith("." + suffix) for suffix in _COMMISSION_SUFFIXES)


def validate_canonical_url(url: str) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an official EUR-Lex or European Commission URL")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not host
        or not is_official_host(host)
        or parsed.path in {"", "/"}
    ):
        raise CatalogError(f"canonical URL is not an official EUR-Lex or European Commission page: {url}")
    return url


def rights_from_page(page_text: str) -> str:
    """Return a reuse-licence label stated by the page, or unknown.

    A copyright symbol, a mention of copyright law, or an open-source licence
    inside the regulation is not a reuse licence for the page.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    if _CC_BY_4_0.search(_plain_text(page_text)):
        return RIGHTS_CC_BY_4_0
    return RIGHTS_UNKNOWN


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description")
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
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    validate_canonical_url(entry.get("canonical_url"))
    _require_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > MAX_TEXT_CHARS:
        raise CatalogError(f"{field} is too long to store")


def _require_date(value: object) -> None:
    if value == UNKNOWN_DATE:
        return
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc


def _plain_text(page_text: str) -> str:
    text = _TAG.sub(" ", page_text)
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()
