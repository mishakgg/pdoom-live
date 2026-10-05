"""Zenodo public record metadata.

Reads one record from the public REST API at https://zenodo.org/api/records.
The body is JSON metadata. File content, archive, and preview URLs are not
requested, and file bytes are not stored.

Each creator stays a separate name. A missing license id stays ``unknown``.
Open access, a license URL, or a missing license is not treated as CC0 or
CC-BY. This module is not wired into belief collection.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "zenodo-metadata-0.1.0"
API_ORIGIN = "https://zenodo.org"
RECORDS_PATH = "/api/records"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_CREATORS = 200
MAX_CREATOR_NAME_CHARS = 300
MAX_LICENSE_CHARS = 80

_RECORD_ID = re.compile(r"^[1-9][0-9]{0,11}$")
_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
_DOI = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
_LICENSE_ID = re.compile(rf"^[A-Za-z0-9][A-Za-z0-9.+_-]{{0,{MAX_LICENSE_CHARS - 1}}}$")
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)
_RECORD_HOSTS = frozenset({"zenodo.org", "www.zenodo.org"})


@dataclass(frozen=True)
class ZenodoRecord:
    """Metadata fields taken from one public Zenodo record."""

    record_id: str
    title: str
    creators: tuple[str, ...]
    publication_date: str
    doi: str | None
    license: str
    canonical_url: str

    def as_dict(self) -> dict[str, object]:
        record: dict[str, object] = {
            "record_id": self.record_id,
            "title": self.title,
            "creators": list(self.creators),
            "publication_date": self.publication_date,
            "license": self.license,
            "canonical_url": self.canonical_url,
        }
        if self.doi is not None:
            record["doi"] = self.doi
        return record


class ZenodoCollector:
    """Retrieve one public record. The default fetcher makes a single attempt."""

    collector = "zenodo"
    platform = "zenodo"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, record_id: str) -> ZenodoRecord:
        """Fetch one record's JSON metadata. Does not follow file links."""
        url = record_request_url(record_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if not _is_metadata_url(hop):
                raise CollectorFailure("blocked_by_policy", "zenodo file downloads are not requested")
        if _looks_like_file_bytes(result.body):
            raise CollectorFailure("blocked_by_policy", "zenodo file bytes are not metadata")
        record = self.parse(result.body)
        if record.record_id != record_id.strip():
            raise CollectorFailure("invalid_content", "zenodo record id mismatch")
        return record

    def parse(self, payload: bytes) -> ZenodoRecord:
        """Parse one records API body. Performs no I/O."""
        return parse_zenodo_record(payload)


def record_request_url(record_id: str) -> str:
    """JSON URL for one record. The path is ``/api/records/{id}``, never a file."""
    cleaned = _require_request_id(record_id)
    url = f"{API_ORIGIN}{RECORDS_PATH}/{cleaned}"
    if not _is_metadata_url(url):
        raise CollectorFailure("blocked_by_policy", "zenodo file downloads are not requested")
    return url


def parse_zenodo_record(payload: bytes) -> ZenodoRecord:
    """Return one record, or fail when the payload is empty or not a record.

    An empty object, an empty search hit list, and a body with no id and title
    do not become a record.
    """
    if _looks_like_file_bytes(payload):
        raise CollectorFailure("blocked_by_policy", "zenodo file bytes are not metadata")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "zenodo payload exceeds limit")
    if not payload.strip():
        raise CollectorFailure("invalid_content", "empty zenodo payload")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed zenodo payload: {exc}") from exc
    record = _extract_record(data)
    if record is None:
        raise CollectorFailure("invalid_content", "empty zenodo payload")
    return record


def _extract_record(data: object) -> ZenodoRecord | None:
    if data is None or data == {}:
        return None
    if isinstance(data, list):
        if not data:
            return None
        raise CollectorFailure("invalid_content", "zenodo payload is not one record")
    if not isinstance(data, dict):
        return None
    if _is_search_envelope(data):
        hits_obj = data.get("hits")
        hits = hits_obj.get("hits") if isinstance(hits_obj, dict) else None
        if not isinstance(hits, list) or not hits:
            return None
        if len(hits) != 1 or not isinstance(hits[0], dict):
            raise CollectorFailure("invalid_content", "expected one zenodo record")
        return _from_record_object(hits[0])
    return _from_record_object(data)


def _is_search_envelope(data: dict) -> bool:
    return "hits" in data and "id" not in data and "metadata" not in data


def _from_record_object(data: dict) -> ZenodoRecord | None:
    if not data:
        return None
    record_id = _record_id(data.get("id"))
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    title_value = metadata.get("title") if isinstance(metadata.get("title"), str) else data.get("title")
    title = _clean_title(title_value)
    if record_id is None or title is None:
        return None
    return ZenodoRecord(
        record_id=record_id,
        title=title,
        creators=_creators(metadata),
        publication_date=_publication_date(metadata),
        doi=_doi(data, metadata),
        license=_license_id(metadata),
        canonical_url=_canonical_url(data, record_id),
    )


def _require_request_id(record_id: str) -> str:
    text = (record_id or "").strip()
    if _RECORD_ID.fullmatch(text) is None:
        raise CollectorFailure("invalid_content", "zenodo record id must be digits")
    return text


def _record_id(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if _RECORD_ID.fullmatch(text) is None:
        return None
    return text


def _clean_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    title = " ".join(value.split())
    if not title:
        return None
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "zenodo title exceeds limit")
    return title


def _creators(metadata: dict) -> tuple[str, ...]:
    """One name per creator object. Names are not joined, split, or deduped."""
    value = metadata.get("creators")
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "zenodo creators are not a list")
    if len(value) > MAX_CREATORS:
        raise CollectorFailure("content_too_large", "zenodo creator list exceeds limit")
    names: list[str] = []
    for entry in value:
        name = _creator_name(entry)
        if name:
            names.append(name)
    return tuple(names)


def _creator_name(entry: object) -> str:
    if not isinstance(entry, dict):
        return ""
    raw = entry.get("name")
    if not isinstance(raw, str):
        person = entry.get("person_or_org")
        if isinstance(person, dict) and isinstance(person.get("name"), str):
            raw = person.get("name")
        else:
            return ""
    if not isinstance(raw, str):
        return ""
    name = " ".join(raw.split())
    if not name:
        return ""
    if len(name) > MAX_CREATOR_NAME_CHARS:
        raise CollectorFailure("content_too_large", "zenodo creator name exceeds limit")
    return name


def _publication_date(metadata: dict) -> str:
    value = metadata.get("publication_date")
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    match = _DATE.fullmatch(text)
    if match is None:
        return UNKNOWN
    year = int(match.group(1))
    if year < 1000 or year > 9999:
        return UNKNOWN
    month = match.group(2)
    day = match.group(3)
    if month is not None and not 1 <= int(month) <= 12:
        return UNKNOWN
    if day is not None and not 1 <= int(day) <= 31:
        return UNKNOWN
    return text


def _doi(data: dict, metadata: dict) -> str | None:
    candidates: list[object] = [metadata.get("doi"), data.get("doi"), data.get("doi_url")]
    links = data.get("links")
    if isinstance(links, dict):
        candidates.append(links.get("doi"))
        candidates.append(links.get("self_doi"))
    for candidate in candidates:
        parsed = _parse_doi(candidate)
        if parsed:
            return parsed
    return None


def _parse_doi(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    if _DOI.fullmatch(text):
        return text
    return None


def _license_id(metadata: dict) -> str:
    """License id from ``metadata.license``. Missing and non-ids stay unknown."""
    if not isinstance(metadata, dict) or "license" not in metadata:
        return UNKNOWN
    for candidate in _license_candidates(metadata.get("license")):
        if isinstance(candidate, str) and _LICENSE_ID.fullmatch(candidate.strip()):
            return candidate.strip()
    return UNKNOWN


def _license_candidates(value: object) -> list[object]:
    if isinstance(value, dict):
        return [value.get("id")]
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        found: list[object] = []
        for item in value:
            if isinstance(item, dict):
                found.append(item.get("id"))
            else:
                found.append(item)
        return found
    return []


def _canonical_url(data: dict, record_id: str) -> str:
    links = data.get("links") if isinstance(data.get("links"), dict) else {}
    candidate = links.get("self_html")
    if isinstance(candidate, str) and _is_record_page(candidate, record_id):
        try:
            return canonicalize_url(candidate.strip())
        except ValueError:
            pass
    return canonicalize_url(f"https://zenodo.org/records/{record_id}")


def _is_record_page(url: str, record_id: str) -> bool:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host not in _RECORD_HOSTS:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    path = parsed.path.rstrip("/") or "/"
    return path == f"/records/{record_id}"


def _is_metadata_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host != "zenodo.org":
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 3 or parts[0] != "api" or parts[1] != "records":
        return False
    if _RECORD_ID.fullmatch(parts[2]) is None:
        return False
    lowered = parsed.path.lower()
    if any(token in lowered for token in ("/files", "/media", "/content", ".pdf")):
        return False
    return True


def _looks_like_file_bytes(payload: bytes) -> bool:
    head = payload.lstrip().removeprefix(b"\xef\xbb\xbf")
    return head.startswith((b"%PDF", b"PK\x03\x04", b"\x89PNG"))
