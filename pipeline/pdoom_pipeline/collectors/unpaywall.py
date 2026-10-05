"""Unpaywall license metadata for one DOI.

Reads one record from the public API::

    https://api.unpaywall.org/v2/{doi}?email=...

The body is JSON metadata. PDF URLs in a payload are ignored and are not
fetched. Abstracts are ignored. This module does not write a PDF file.

The API requires an email query parameter. ``pdoom-live@example.com`` is a
fixture contact, not a person's inbox. Unpaywall rejects that placeholder
domain with HTTP 422. The request uses ``pdoom-live@pdoom.live``, a fixture
contact for this project, not a person's inbox.

The stored record keeps the DOI, title, year, license, OA status, and the
canonical doi.org URL. A missing license stays ``unknown``. OA status is not
copied into the license. This module is not imported by the collector package
and is not wired into belief collection. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "unpaywall-0.1.0"
API_ORIGIN = "https://api.unpaywall.org"
API_HOST = "api.unpaywall.org"
# Fixture contact for this project, not a person's inbox.
FIXTURE_CONTACT = "pdoom-live@pdoom.live"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_LICENSE_CHARS = 80
MAX_DOI_CHARS = 200

_OA_STATUS = frozenset({"bronze", "closed", "gold", "green", "hybrid"})
_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.I)
_PREFIX = re.compile(r"^10\.\d{4,9}$")
_SUFFIX = re.compile(r"^[-._;()A-Za-z0-9]+$")
_LICENSE = re.compile(rf"^[a-z0-9][a-z0-9.+-]{{0,{MAX_LICENSE_CHARS - 1}}}$")
_FILE_SUFFIXES = (".pdf", ".zip", ".xml", ".tgz", ".gz", ".tar", ".doc", ".docx")


@dataclass(frozen=True)
class UnpaywallWork:
    doi: str
    title: str
    year: int | str
    license: str
    oa_status: str
    canonical_url: str

    def as_dict(self) -> dict[str, object]:
        return {
            "doi": self.doi,
            "title": self.title,
            "year": self.year,
            "license": self.license,
            "oa_status": self.oa_status,
            "canonical_url": self.canonical_url,
        }


class UnpaywallCollector:
    """Fetch and parse one Unpaywall DOI. This collector is not wired."""

    collector = "unpaywall"
    platform = "unpaywall"
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
        return unpaywall_record_url(doi)

    def retrieve(self, doi: str) -> UnpaywallWork:
        requested = _request_doi(doi)
        url = unpaywall_record_url(requested)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        hops = list(result.requested_urls or [])
        if result.url:
            hops.append(result.url)
        for hop in hops:
            if not _is_metadata_url(hop):
                raise CollectorFailure("blocked_by_policy", "unpaywall retrieval stays on one doi record")
        if _body_is_file(result.body):
            raise CollectorFailure("blocked_by_policy", "unpaywall pdfs are not downloaded")
        work = parse_unpaywall_work(result.body)
        if work.doi.lower() != requested.lower():
            raise CollectorFailure("invalid_content", "unpaywall doi mismatch")
        return work

    def parse(self, payload: bytes) -> UnpaywallWork:
        return parse_unpaywall_work(payload)


def unpaywall_record_url(doi: str) -> str:
    """JSON metadata URL for one DOI. The path is the API record, never a PDF."""
    bare = _request_doi(doi)
    encoded = "/".join(quote(part, safe="") for part in bare.split("/"))
    query = urlencode({"email": FIXTURE_CONTACT})
    url = f"{API_ORIGIN}/v2/{encoded}?{query}"
    if not _is_metadata_url(url):
        raise CollectorFailure("unsafe_url", "unpaywall retrieval stays on one doi record")
    return url


def parse_unpaywall_work(payload: bytes) -> UnpaywallWork:
    """Return DOI, title, year, license, OA status, and the doi.org URL.

    A missing license or OA status is the string ``unknown``. Abstracts, PDF
    URLs, and file bytes are not copied onto the record.
    """
    if _body_is_file(payload):
        raise CollectorFailure("blocked_by_policy", "unpaywall pdfs are not downloaded")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "unpaywall payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", "malformed unpaywall payload") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "unpaywall payload was not an object")
    _raise_api_error(data)
    doi = _response_doi(data.get("doi"))
    return UnpaywallWork(
        doi=doi,
        title=_title(data.get("title")),
        year=_year(data.get("year")),
        license=_license(data.get("best_oa_location")),
        oa_status=_oa_status(data.get("oa_status")),
        canonical_url=_canonical_doi_url(doi),
    )


def _request_doi(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise CollectorFailure("invalid_content", "invalid unpaywall doi")
    if _looks_like_file(raw):
        raise CollectorFailure("blocked_by_policy", "unpaywall pdfs are not downloaded")
    text = _DOI_PREFIX.sub("", raw).strip()
    return _validated_doi(text, missing="invalid unpaywall doi")


def _response_doi(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "unpaywall work missing doi")
    return _validated_doi(value.strip(), missing="unpaywall work missing doi")


def _validated_doi(text: str, *, missing: str) -> str:
    if not text or len(text) > MAX_DOI_CHARS or any(character.isspace() for character in text):
        raise CollectorFailure("invalid_content", missing)
    if text.lower().startswith(("http://", "https://", "file:", "ftp:")):
        raise CollectorFailure("invalid_content", missing)
    if _looks_like_file(text):
        raise CollectorFailure("blocked_by_policy", "unpaywall pdfs are not downloaded")
    parts = text.split("/")
    if len(parts) < 2 or not _PREFIX.fullmatch(parts[0]):
        raise CollectorFailure("invalid_content", missing)
    if any(part in {"", ".", ".."} or not _SUFFIX.fullmatch(part) for part in parts[1:]):
        raise CollectorFailure("invalid_content", missing)
    if any(part.lower() in {"pdf", "pdfdirect", "download"} for part in parts):
        raise CollectorFailure("blocked_by_policy", "unpaywall pdfs are not downloaded")
    return text


def _canonical_doi_url(doi: str) -> str:
    direct = f"https://doi.org/{doi}"
    dx = f"https://dx.doi.org/{doi}"
    try:
        canonical = canonicalize_url(direct)
        other = canonicalize_url(dx)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "unpaywall doi could not be canonicalized") from exc
    parsed = urlparse(canonical)
    if canonical != other or parsed.scheme != "https" or parsed.hostname != "doi.org":
        raise CollectorFailure("invalid_content", "unpaywall doi did not canonicalize to doi.org")
    if parsed.path.strip("/") != doi or _looks_like_file(canonical):
        raise CollectorFailure("invalid_content", "canonical doi url did not keep the doi")
    return canonical


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "unpaywall work missing title")
    text = " ".join(value.split())
    if not text:
        raise CollectorFailure("invalid_content", "unpaywall work missing title")
    if len(text) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "unpaywall title exceeds limit")
    return text


def _year(value: object) -> int | str:
    if isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, int) and 1000 <= value <= 9999:
        return value
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 4 and text.isdigit() and 1000 <= int(text) <= 9999:
            return int(text)
    return UNKNOWN


def _license(location: object) -> str:
    """License from ``best_oa_location`` only. A missing value stays unknown."""
    if not isinstance(location, dict) or "license" not in location:
        return UNKNOWN
    token = _license_token(location.get("license"))
    return token or UNKNOWN


def _license_token(value: object) -> str:
    if not isinstance(value, str):
        return ""
    if any(ord(char) < 32 for char in value):
        return ""
    text = " ".join(value.split()).lower()
    if not text or _looks_like_file(text) or "://" in text or "/" in text:
        return ""
    if len(text) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "unpaywall license exceeds limit")
    if not _LICENSE.fullmatch(text):
        return ""
    return text


def _oa_status(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip().lower()
    if text in _OA_STATUS:
        return text
    return UNKNOWN


def _is_metadata_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.username or parsed.password:
        return False
    if parsed.fragment or parsed.port not in (None, 443):
        return False
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "v2":
        return False
    if any(part.lower() in {"pdf", "pdfdirect", "download", "content", "files"} for part in parts):
        return False
    if _looks_like_file(parsed.path) or ".pdf" in parsed.query.lower() or "pdfdirect" in parsed.query.lower():
        return False
    doi = "/".join(parts[1:])
    try:
        validated = _validated_doi(doi, missing="invalid unpaywall doi")
    except CollectorFailure:
        return False
    if validated != doi:
        return False
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"email"} or query.get("email") != [FIXTURE_CONTACT]:
        return False
    return True


def _looks_like_file(value: str) -> bool:
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    if lowered.startswith("%pdf") or "pdfdirect" in lowered or "/pdf/" in lowered or lowered.endswith("/pdf"):
        return True
    return lowered.endswith(_FILE_SUFFIXES)


def _body_is_file(payload: bytes) -> bool:
    stripped = payload.lstrip()
    return stripped.startswith(b"%PDF") or stripped.startswith(b"PK\x03\x04")


def _raise_api_error(data: dict) -> None:
    if data.get("error") is not True:
        return
    message = data.get("message")
    text = " ".join(message.split()) if isinstance(message, str) else "unpaywall error"
    if len(text) > 200:
        text = text[:200]
    status = data.get("HTTP_status_code")
    if status == 404:
        raise CollectorFailure("not_found", text or "unpaywall doi was not found")
    raise CollectorFailure("invalid_content", text or "unpaywall error")
