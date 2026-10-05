"""Metadata catalog of US federal AI-safety and AI-risk publications.

Rows are US government works: NIST AI publications, GAO AI reports, and
congressional hearing records. The catalog stores identifiers and a hash of
a response header or snippet of at most 2048 bytes. It does not store the
documents.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "us_federal_ai_publications"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
MAX_HASHED_BYTES = 2048
CATALOG_FILENAME = "us_federal_ai_publications.json"

ENTRY_KINDS = frozenset({"nist_publication", "gao_report", "congressional_hearing"})
RETRIEVAL_METHODS = frozenset({"HEAD", "GET"})
HASH_BASES = frozenset({"response_headers", "snippet"})

# Hosts that publish the works in this catalog. Other .gov sites are not
# accepted, so a lookalike or unrelated host cannot be labeled as one of these works.
_HOST_SUFFIXES = ("nist.gov", "gao.gov", "govinfo.gov", "congress.gov", "senate.gov", "house.gov")
_KIND_SUFFIXES = {
    "nist_publication": ("nist.gov",),
    "gao_report": ("gao.gov", "govinfo.gov", "congress.gov", "senate.gov", "house.gov"),
    "congressional_hearing": ("govinfo.gov", "congress.gov", "senate.gov", "house.gov"),
}

_REQUIRED_FIELDS = (
    "id",
    "kind",
    "title",
    "publisher",
    "canonical_url",
    "publication_date",
    "rights",
    "final_url",
    "retrieved_at",
    "retrieval_method",
)
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


class CatalogError(ValueError):
    """A catalog row or URL violates the US federal publication rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def content_hash_for_small_payload(payload: bytes) -> str | None:
    """Hash a header block or snippet. Payloads over 2048 bytes are not hashed."""
    if not payload or len(payload) > MAX_HASHED_BYTES:
        return None
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_catalog(payload)


def validate_catalog(catalog: Mapping) -> dict:
    if not isinstance(catalog, dict):
        raise CatalogError("catalog must be an object")
    if catalog.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = catalog.get("description")
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    entries = catalog.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CatalogError(f"entries[{index}] must be an object")
        validate_entry(entry)
        entry_id = entry["id"]
        url = entry["canonical_url"]
        if entry_id in seen_ids:
            raise CatalogError(f"duplicate id: {entry_id}")
        if url in seen_urls:
            raise CatalogError(f"duplicate canonical_url: {url}")
        seen_ids.add(entry_id)
        seen_urls.add(url)
    return catalog


def validate_entry(entry: Mapping) -> dict:
    if not isinstance(entry, dict):
        raise CatalogError("entry must be an object")
    missing = [field for field in _REQUIRED_FIELDS if field not in entry]
    if missing:
        raise CatalogError("missing required fields: " + ", ".join(missing))
    _require_text(entry, "id")
    if not _ID.match(entry["id"]):
        raise CatalogError(f"id is not a lowercase slug: {entry['id']}")
    kind = entry["kind"]
    if kind not in ENTRY_KINDS:
        raise CatalogError(f"kind is not a federal publication kind: {kind}")
    _require_text(entry, "title", max_length=400)
    _require_text(entry, "publisher", max_length=200)
    if entry["rights"] != RIGHTS_US_GOVERNMENT_WORK:
        raise CatalogError(f"rights must be {RIGHTS_US_GOVERNMENT_WORK}")
    _require_publication_date(entry["publication_date"])
    _require_retrieved_at(entry["retrieved_at"])
    if entry["publication_date"] != "unknown":
        published = datetime.strptime(entry["publication_date"], "%Y-%m-%d").date()
        retrieved = datetime.strptime(entry["retrieved_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        if published > retrieved:
            raise CatalogError("publication_date is after retrieved_at")
    if entry["retrieval_method"] not in RETRIEVAL_METHODS:
        raise CatalogError("retrieval_method must be HEAD or GET")
    _require_federal_url(entry["canonical_url"], field="canonical_url", kind=kind)
    _require_federal_url(entry["final_url"], field="final_url", kind=kind)
    _require_small_content_hash(entry)
    return entry


def _require_text(entry: Mapping, field: str, *, max_length: int = 200) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long")


def _require_publication_date(value: object) -> None:
    if value == "unknown":
        return
    if not isinstance(value, str):
        raise CatalogError("publication_date must be YYYY-MM-DD or unknown")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise CatalogError("publication_date must be YYYY-MM-DD or unknown") from exc


def _require_retrieved_at(value: object) -> None:
    if not isinstance(value, str):
        raise CatalogError("retrieved_at must be a UTC timestamp")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise CatalogError("retrieved_at must be a UTC timestamp") from exc


def _require_federal_url(url: object, *, field: str, kind: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise CatalogError(f"{field} is a non-government URL")
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or not host
        or hostname_is_blocked(host)
        or _is_ip(host)
        or not _host_matches(host, _HOST_SUFFIXES)
    ):
        raise CatalogError(f"{field} is a non-government URL: {url}")
    if not _host_matches(host, _KIND_SUFFIXES[kind]):
        raise CatalogError(f"{field} does not match kind {kind}: {url}")
    return url


def _require_small_content_hash(entry: Mapping) -> None:
    content_hash = entry.get("content_hash")
    hashed_bytes = entry.get("hashed_bytes")
    basis = entry.get("content_hash_basis")
    if content_hash is None and hashed_bytes is None and basis is None:
        return
    if not isinstance(content_hash, str) or not _HASH.match(content_hash):
        raise CatalogError("content_hash must be a sha256 digest")
    if not isinstance(hashed_bytes, int) or isinstance(hashed_bytes, bool):
        raise CatalogError("hashed_bytes must be an integer")
    if hashed_bytes < 1 or hashed_bytes > MAX_HASHED_BYTES:
        raise CatalogError(f"content_hash is only stored for a header or snippet under {MAX_HASHED_BYTES} bytes")
    if basis not in HASH_BASES:
        raise CatalogError("content_hash_basis must be response_headers or snippet")


def _host_matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == suffix or host.endswith("." + suffix) for suffix in suffixes)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True
