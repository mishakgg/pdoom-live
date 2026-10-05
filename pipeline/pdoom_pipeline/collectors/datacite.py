"""DataCite DOI metadata.

Retrieves one record from the public DataCite REST API. The response is JSON
metadata only. Files are not requested. Abstracts and descriptions are not
stored. Creator names stay separate and are not merged.

This module is not imported by the collector package and is not wired into
belief collection. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, quote, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "datacite-0.1.0"
API_ORIGIN = "https://api.datacite.org"
API_HOST = "api.datacite.org"
SELECT_FIELDS = "doi,titles,creators,publicationYear,publisher,rightsList"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_CREATORS = 200
MAX_CREATOR_NAME_CHARS = 300
MAX_LICENSE_CHARS = 500
MAX_PUBLISHER_CHARS = 300

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.I)
_PREFIX = re.compile(r"^10\.\d{4,9}$")
_SUFFIX = re.compile(r"^[-._;()A-Za-z0-9]+$")
_FILE_SUFFIXES = (".pdf", ".zip", ".xml", ".tgz", ".gz", ".tar", ".doc", ".docx")


@dataclass(frozen=True)
class DataCiteWork:
    doi: str
    title: str
    creators: tuple[str, ...]
    publication_year: str
    publisher: str
    license: str
    canonical_url: str

    def as_dict(self) -> dict[str, object]:
        return {
            "doi": self.doi,
            "title": self.title,
            "creators": list(self.creators),
            "publication_year": self.publication_year,
            "publisher": self.publisher,
            "license": self.license,
            "canonical_url": self.canonical_url,
        }


class DataCiteCollector:
    """Fetch and parse one DataCite DOI. This collector is not wired."""

    collector = "datacite"
    platform = "datacite"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10,
            max_redirects=0,
            max_attempts=1,
        )

    def record_url(self, doi: str) -> str:
        return datacite_record_url(doi)

    def retrieve(self, doi: str) -> DataCiteWork:
        url = self.record_url(doi)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if not _is_metadata_url(hop):
                raise CollectorFailure("blocked_by_policy", "datacite retrieval stays on one doi record")
        if _body_is_file(result.body):
            raise CollectorFailure("blocked_by_policy", "datacite files are not downloaded")
        return parse_datacite_work(result.body)

    def parse(self, payload: bytes) -> DataCiteWork:
        return parse_datacite_work(payload)


def datacite_record_url(doi: str) -> str:
    """JSON metadata URL for one DOI. Descriptions and files are not requested."""
    bare = _request_doi(doi)
    encoded = "/".join(quote(part, safe="") for part in bare.split("/"))
    query = urlencode({"fields[dois]": SELECT_FIELDS})
    url = f"{API_ORIGIN}/dois/{encoded}?{query}"
    if not _is_metadata_url(url):
        raise CollectorFailure("unsafe_url", "datacite retrieval stays on one doi record")
    return url


def parse_datacite_work(payload: bytes) -> DataCiteWork:
    """Return DOI, title, creator names, year, publisher, license, and doi.org URL.

    A missing publication year or license is the string ``unknown``. Abstracts,
    descriptions, and file bytes are ignored when a payload contains them.
    """
    if _body_is_file(payload):
        raise CollectorFailure("blocked_by_policy", "datacite files are not downloaded")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "datacite payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed datacite payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "datacite payload was not an object")
    attributes = _one_work(data)
    doi = _response_doi(attributes)
    return DataCiteWork(
        doi=doi,
        title=_title(attributes.get("titles")),
        creators=_creators(attributes.get("creators")),
        publication_year=_year(attributes.get("publicationYear")),
        publisher=_publisher(attributes.get("publisher")),
        license=_license(attributes.get("rightsList")),
        canonical_url=_canonical_doi_url(doi),
    )


def _one_work(data: dict) -> dict:
    if "errors" in data and "data" not in data:
        raise CollectorFailure("invalid_content", "datacite error response")
    item = data.get("data", data)
    if isinstance(item, list):
        if len(item) != 1 or not isinstance(item[0], dict):
            raise CollectorFailure("invalid_content", "expected exactly one datacite doi")
        item = item[0]
    if not isinstance(item, dict):
        raise CollectorFailure("invalid_content", "datacite record was not an object")
    attributes = item.get("attributes", item)
    if not isinstance(attributes, dict):
        raise CollectorFailure("invalid_content", "datacite attributes were not an object")
    if not attributes.get("doi") and isinstance(item.get("id"), str):
        attributes = {**attributes, "doi": item["id"]}
    return attributes


def _request_doi(value: str) -> str:
    text = _DOI_PREFIX.sub("", (value or "").strip())
    return _validated_doi(text, missing="invalid datacite doi")


def _response_doi(attributes: dict) -> str:
    raw = attributes.get("doi")
    if not isinstance(raw, str):
        raise CollectorFailure("invalid_content", "datacite work missing doi")
    return _validated_doi(raw.strip(), missing="datacite work missing doi")


def _validated_doi(text: str, *, missing: str) -> str:
    if not text or any(character.isspace() for character in text):
        raise CollectorFailure("invalid_content", missing)
    if text.lower().startswith(("http://", "https://", "file:", "ftp:")):
        raise CollectorFailure("invalid_content", missing)
    if _looks_like_file(text):
        raise CollectorFailure("blocked_by_policy", "datacite files are not downloaded")
    parts = text.split("/")
    if len(parts) < 2 or not _PREFIX.fullmatch(parts[0]):
        raise CollectorFailure("invalid_content", missing)
    if any(part in {"", ".", ".."} or not _SUFFIX.fullmatch(part) for part in parts[1:]):
        raise CollectorFailure("invalid_content", missing)
    return text


def _canonical_doi_url(doi: str) -> str:
    direct = f"https://doi.org/{doi}"
    dx = f"https://dx.doi.org/{doi}"
    try:
        canonical = canonicalize_url(direct)
        other = canonicalize_url(dx)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "datacite doi could not be canonicalized") from exc
    parsed = urlparse(canonical)
    if canonical != other or parsed.scheme != "https" or parsed.hostname != "doi.org":
        raise CollectorFailure("invalid_content", "datacite doi did not canonicalize to doi.org")
    if parsed.path.strip("/") != doi:
        raise CollectorFailure("invalid_content", "canonical doi url did not keep the doi")
    return canonical


def _title(value: object) -> str:
    candidates: list[tuple[str, bool]] = []
    if isinstance(value, str):
        candidates.append((value, True))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                candidates.append((item, True))
            elif isinstance(item, dict) and isinstance(item.get("title"), str):
                title_type = item.get("titleType")
                candidates.append((item["title"], title_type in (None, "")))
    ordered = [text for text, primary in candidates if primary]
    ordered.extend(text for text, primary in candidates if not primary)
    for text in ordered:
        cleaned = " ".join(text.split())
        if not cleaned:
            continue
        if len(cleaned) > MAX_TITLE_CHARS:
            raise CollectorFailure("content_too_large", "datacite title exceeds limit")
        return cleaned
    raise CollectorFailure("invalid_content", "datacite work missing title")


def _creators(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "datacite creators were not a list")
    if len(value) > MAX_CREATORS:
        raise CollectorFailure("content_too_large", "datacite creator list exceeds limit")
    names: list[str] = []
    for entry in value:
        name = _creator_name(entry)
        if name:
            names.append(name)
    return tuple(names)


def _creator_name(entry: object) -> str:
    """One creator's own name. Other creator records are left untouched."""
    if isinstance(entry, str):
        return _bounded_name(entry)
    if not isinstance(entry, dict):
        return ""
    raw = entry.get("name")
    if isinstance(raw, str) and raw.strip():
        return _bounded_name(raw)
    parts: list[str] = []
    for key in ("givenName", "familyName"):
        piece = entry.get(key)
        if isinstance(piece, str):
            cleaned = " ".join(piece.split())
            if cleaned:
                parts.append(cleaned)
    if not parts:
        return ""
    return _bounded_name(" ".join(parts))


def _bounded_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        return ""
    if len(cleaned) > MAX_CREATOR_NAME_CHARS:
        raise CollectorFailure("content_too_large", "datacite creator name exceeds limit")
    return cleaned


def _year(value: object) -> str:
    if isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, int) and 1000 <= value <= 9999:
        return f"{value:04d}"
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 4 and text.isdigit() and 1000 <= int(text) <= 9999:
            return text
    return UNKNOWN


def _publisher(value: object) -> str:
    if isinstance(value, str):
        text = " ".join(value.split())
    elif isinstance(value, dict) and isinstance(value.get("name"), str):
        text = " ".join(value["name"].split())
    else:
        return UNKNOWN
    if not text:
        return UNKNOWN
    if len(text) > MAX_PUBLISHER_CHARS:
        raise CollectorFailure("content_too_large", "datacite publisher exceeds limit")
    return text


def _license(value: object) -> str:
    if not isinstance(value, list):
        return UNKNOWN
    for entry in value:
        if not isinstance(entry, dict):
            continue
        url = _license_url(entry.get("rightsUri"))
        if url:
            return url
        identifier = _license_id(entry.get("rightsIdentifier"))
        if identifier:
            return identifier
    return UNKNOWN


def _license_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text or _looks_like_file(text):
        return ""
    parsed = urlparse(text)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    if len(text) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "datacite license exceeds limit")
    return text


def _license_id(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    if not text or "://" in text or _looks_like_file(text) or any(ord(char) < 32 for char in text):
        return ""
    if len(text) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "datacite license exceeds limit")
    return text


def _is_metadata_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.username or parsed.password:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "dois":
        return False
    if any(part.lower() in {"media", "download", "content", "files"} for part in parts):
        return False
    if _looks_like_file(parsed.path) or ".pdf" in parsed.query.lower():
        return False
    fields = parse_qs(parsed.query).get("fields[dois]", [])
    if len(fields) != 1 or fields[0] != SELECT_FIELDS:
        return False
    lowered = fields[0].lower()
    if "description" in lowered or "xml" in lowered or "abstract" in lowered:
        return False
    return True


def _looks_like_file(value: str) -> bool:
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith(_FILE_SUFFIXES) or "/download" in lowered or lowered.startswith("%pdf")


def _body_is_file(payload: bytes) -> bool:
    stripped = payload.lstrip()
    return stripped.startswith(b"%PDF") or stripped.startswith(b"PK\x03\x04")
