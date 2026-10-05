"""OpenAlex author metadata.

Reads one author from the public authors API. OpenAlex metadata is CC0.
The stored record is the OpenAlex id, display name, ORCID when the payload
has one, and the last known institution name. A missing ORCID stays
``unknown``. A missing institution name stays ``unknown``.

This module fetches by OpenAlex author id only. It does not search by name,
does not compare two authors, and does not attach a record to a tracked
person. It is not wired into belief collection.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher

COLLECTOR_VERSION = "openalex-authors-0.1.0"
API_ORIGIN = "https://api.openalex.org"
MAILTO = "collector@pdoom.live"
SELECT_FIELDS = ("id", "display_name", "orcid", "ids", "last_known_institutions")
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_NAME_CHARS = 300
MAX_INSTITUTION_CHARS = 300
MAX_INSTITUTIONS = 20

# Confirmed from the public authors API on 2026-10-05. ORCID was null and
# last_known_institutions was empty. Topics on that record are machine learning
# and AI, including "Ethics and Social Impacts of AI".
CONFIRMED_AUTHOR_ID = "A5020400986"
CONFIRMED_DISPLAY_NAME = "Dan Hendrycks"
DATA_LICENSE = "CC0"

_AUTHOR_ID = re.compile(r"^A[0-9]{1,12}$")
_ORCID = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")


@dataclass(frozen=True)
class OpenAlexAuthorMetadata:
    """One OpenAlex author. No person id and no probability."""

    openalex_id: str
    display_name: str
    orcid: str
    last_known_institution: str

    def as_record(self) -> dict[str, str]:
        return {
            "openalex_id": self.openalex_id,
            "display_name": self.display_name,
            "orcid": self.orcid,
            "last_known_institution": self.last_known_institution,
        }


class OpenAlexAuthorsCollector:
    """Retrieve one author by OpenAlex id. The default fetcher makes one attempt."""

    collector = "openalex_authors"
    platform = "openalex"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, openalex_author_id: str) -> OpenAlexAuthorMetadata:
        author_id = normalize_openalex_author_id(openalex_author_id)
        url = author_request_url(author_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url]:
            raise CollectorFailure("blocked_by_policy", "refusing a redirected openalex author fetch")
        if len(result.body) > MAX_RESPONSE_BYTES:
            raise CollectorFailure("content_too_large", "openalex author response exceeds 200KB")
        record = self.parse(result.body)
        if record.openalex_id != author_id:
            raise CollectorFailure("invalid_content", "openalex author id mismatch")
        return record

    def parse(self, payload: bytes) -> OpenAlexAuthorMetadata:
        return parse_author(payload)


def author_request_url(openalex_author_id: str) -> str:
    """HTTPS URL for one author. It has no search, no filter, and no PDF."""
    author_id = normalize_openalex_author_id(openalex_author_id)
    query = urlencode({"select": ",".join(SELECT_FIELDS), "mailto": MAILTO})
    url = f"{API_ORIGIN}/authors/{author_id}?{query}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.openalex.org":
        raise CollectorFailure("unsafe_url", "openalex author retrieval stays on the authors api")
    if parsed.path != f"/authors/{author_id}":
        raise CollectorFailure("blocked_by_policy", "refusing a non-author openalex path")
    if ".pdf" in url.lower() or "search=" in parsed.query or "filter=" in parsed.query:
        raise CollectorFailure("blocked_by_policy", "openalex author retrieval is one id lookup")
    return url


def confirmed_author_url() -> str:
    return author_request_url(CONFIRMED_AUTHOR_ID)


def parse_author(payload: bytes) -> OpenAlexAuthorMetadata:
    """Read one author object. A list of authors is rejected rather than reduced."""
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "openalex author response exceeds 200KB")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed openalex author payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "openalex author payload is not an object")
    if "results" in data or "group_by" in data:
        raise CollectorFailure("invalid_content", "openalex author list is not a single author")
    return _author_from_object(data)


def normalize_openalex_author_id(value: str) -> str:
    """Return the short OpenAlex author id. Names and ORCID keys are rejected."""
    raw = (value or "").strip()
    if not raw or any(char in raw for char in "\r\n\x00"):
        raise CollectorFailure("invalid_content", "openalex author id must look like A123")
    lowered = raw.lower()
    if lowered.endswith(".pdf") or "/pdf/" in lowered or lowered.startswith("%pdf"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if "://" in raw or lowered.startswith("openalex.org/") or lowered.startswith("api.openalex.org/"):
        candidate = raw if "://" in raw else f"https://{raw}"
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or parsed.query or parsed.fragment or parsed.username:
            raise CollectorFailure("invalid_content", "openalex author id must look like A123")
        parts = [part for part in parsed.path.split("/") if part]
        if host == "openalex.org" and len(parts) == 1:
            token = parts[0]
        elif host == "api.openalex.org" and len(parts) == 2 and parts[0] == "authors":
            token = parts[1]
        else:
            raise CollectorFailure("invalid_content", "openalex author id must look like A123")
    else:
        if "/" in raw or "?" in raw or lowered.startswith("orcid:"):
            raise CollectorFailure("invalid_content", "openalex author id must look like A123")
        token = raw
    token = token.upper()
    if not _AUTHOR_ID.fullmatch(token):
        raise CollectorFailure("invalid_content", "openalex author id must look like A123")
    return token


def _author_from_object(data: dict) -> OpenAlexAuthorMetadata:
    openalex_id = _openalex_id(data)
    return OpenAlexAuthorMetadata(
        openalex_id=openalex_id,
        display_name=_display_name(data.get("display_name")),
        orcid=_orcid(data),
        last_known_institution=_last_known_institution(data.get("last_known_institutions")),
    )


def _openalex_id(data: dict) -> str:
    raw_id = data.get("id")
    if not isinstance(raw_id, str):
        raise CollectorFailure("invalid_content", "openalex author id is missing")
    author_id = normalize_openalex_author_id(raw_id)
    ids = data.get("ids")
    if isinstance(ids, dict) and isinstance(ids.get("openalex"), str) and ids.get("openalex").strip():
        try:
            nested = normalize_openalex_author_id(ids["openalex"])
        except CollectorFailure as exc:
            raise CollectorFailure("invalid_content", "openalex author ids disagree") from exc
        if nested != author_id:
            raise CollectorFailure("invalid_content", "openalex author ids disagree")
    return author_id


def _display_name(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "openalex author display name is missing")
    name = " ".join(value.split())
    if not name:
        raise CollectorFailure("invalid_content", "openalex author display name is missing")
    if len(name) > MAX_NAME_CHARS:
        raise CollectorFailure("content_too_large", "openalex author display name exceeds limit")
    return name


def _orcid(data: dict) -> str:
    """Copy a single ORCID. Disagreement or absence stays unknown.

    ``observed_orcids`` is ignored. Those values are not this author's ORCID.
    """
    primary = _orcid_value(data.get("orcid")) if "orcid" in data else None
    ids = data.get("ids")
    nested = None
    if isinstance(ids, dict) and "orcid" in ids:
        nested = _orcid_value(ids.get("orcid"))
    if primary and nested and primary != nested:
        return UNKNOWN
    if primary:
        return primary
    if nested:
        return nested
    return UNKNOWN


def _orcid_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in {"none", "null", "unknown"}:
        return None
    if "://" in text or text.lower().startswith("orcid.org/"):
        candidate = text if "://" in text else f"https://{text}"
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        if host not in {"orcid.org", "www.orcid.org"}:
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 1:
            return None
        text = parts[0]
    if text[-1] in {"x", "X"}:
        text = text[:-1] + "X"
    if not _ORCID.fullmatch(text):
        return None
    return text


def _last_known_institution(value: object) -> str:
    """First last-known institution name. Other affiliations are not consulted."""
    if value is None:
        return UNKNOWN
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "last known institutions are not a list")
    if len(value) > MAX_INSTITUTIONS:
        raise CollectorFailure("content_too_large", "last known institution list exceeds limit")
    for item in value:
        if not isinstance(item, dict):
            continue
        raw = item.get("display_name")
        if not isinstance(raw, str):
            continue
        name = " ".join(raw.split())
        if not name:
            continue
        if len(name) > MAX_INSTITUTION_CHARS:
            raise CollectorFailure("content_too_large", "last known institution name exceeds limit")
        return name
    return UNKNOWN
