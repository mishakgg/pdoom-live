"""Public ORCID record metadata.

Reads one record from the public API at https://pub.orcid.org/. The stored
record keeps the ORCID iD, the published name, and affiliation organization
names as separate strings. ``/record``, ``/works``, and ``/biography`` are
not requested. Biography prose and works lists are not stored.

A record is not attached to any other person. A second ORCID iD stays a
second record. A missing affiliation stays ``unknown``. This collector is
not wired into the belief runner: ``runner_wired`` is false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pdoom_pipeline.errors import (
    BLOCKED_BY_POLICY,
    CONTENT_TOO_LARGE,
    INVALID_CONTENT,
    UNSAFE_URL,
    CollectorFailure,
)
from pdoom_pipeline.fetch import SafeFetcher

COLLECTOR_VERSION = "orcid-public-0.1.0"
UNKNOWN = "unknown"
API_ORIGIN = "https://pub.orcid.org"
API_HOST = "pub.orcid.org"
MAX_RESPONSE_BYTES = 200_000
MAX_NAME_CHARS = 300
MAX_AFFILIATION_CHARS = 300
MAX_AFFILIATIONS = 40

# Section reads for one record. The full record and the works list are omitted.
METADATA_SECTIONS = (
    "personal-details",
    "employments",
    "educations",
    "qualifications",
    "invited-positions",
    "memberships",
    "services",
    "distinctions",
)
AFFILIATION_SECTIONS = METADATA_SECTIONS[1:]
_EXCLUDED_SECTIONS = frozenset(
    {
        "activities",
        "biography",
        "email",
        "emails",
        "fundings",
        "peer-review",
        "peer-reviews",
        "person",
        "record",
        "research-resources",
        "researcher-urls",
        "work",
        "works",
    }
)
# Nested objects that must not contribute text or a second identifier.
_IGNORED_KEYS = frozenset(
    {
        "biography",
        "content",
        "email",
        "emails",
        "external-identifier",
        "external-identifiers",
        "fundings",
        "keyword",
        "keywords",
        "peer-reviews",
        "research-resources",
        "researcher-url",
        "researcher-urls",
        "work",
        "works",
    }
)

_ORCID_ID = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")
_ORCID_IN_TEXT = re.compile(r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]")


@dataclass(frozen=True)
class OrcidPublicRecord:
    """One public ORCID record, not linked to any other person."""

    orcid_id: str
    published_name: str
    affiliations: tuple[str, ...] | str

    def as_dict(self) -> dict[str, str | list[str]]:
        affiliations: str | list[str]
        if isinstance(self.affiliations, str):
            affiliations = self.affiliations
        else:
            affiliations = list(self.affiliations)
        return {
            "orcid_id": self.orcid_id,
            "published_name": self.published_name,
            "affiliations": affiliations,
        }


class OrcidPublicCollector:
    """Retrieve one public ORCID record. ``runner_wired`` stays false."""

    collector = "orcid_public"
    platform = "orcid"
    collector_version = COLLECTOR_VERSION
    runner_wired = False

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            max_redirects=0,
            max_attempts=1,
            timeout=10.0,
        )

    def retrieve(self, orcid_id: str) -> OrcidPublicRecord:
        """Fetch metadata sections for one ORCID iD. Does not follow redirects."""
        orcid_id = _require_orcid(orcid_id)
        sections: dict[str, dict] = {}
        for section in METADATA_SECTIONS:
            url = metadata_url(orcid_id, section)
            result = self.fetcher.get(url, headers={"Accept": "application/json"})
            if result.url != url or result.requested_urls != [url]:
                raise CollectorFailure(BLOCKED_BY_POLICY, "refusing a redirected orcid fetch")
            if _forbidden_url(result.url):
                raise CollectorFailure(BLOCKED_BY_POLICY, "orcid biography and works are not requested")
            body = _decode_object(result.body)
            _reject_excluded_path(body)
            sections[section] = body
        return _record_from_sections(orcid_id, sections)

    def parse(self, payload: bytes, *, orcid_id: str) -> OrcidPublicRecord:
        """Parse a saved public metadata document. Performs no I/O."""
        orcid_id = _require_orcid(orcid_id)
        data = _decode_object(payload)
        return _record_from_sections(orcid_id, _sections_from_document(data))


def metadata_url(orcid_id: str, section: str) -> str:
    """HTTPS URL for one public metadata section. Works and biography are refused."""
    orcid_id = _require_orcid(orcid_id)
    if not isinstance(section, str) or section in _EXCLUDED_SECTIONS:
        raise CollectorFailure(BLOCKED_BY_POLICY, "orcid biography and works are not requested")
    if section not in METADATA_SECTIONS:
        raise CollectorFailure(INVALID_CONTENT, "orcid section is not public record metadata")
    url = f"{API_ORIGIN}/v3.0/{orcid_id}/{section}"
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.hostname != API_HOST
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parts != ["v3.0", orcid_id, section]
    ):
        raise CollectorFailure(UNSAFE_URL, "refusing orcid url")
    return url


def _record_from_sections(orcid_id: str, sections: dict[str, dict]) -> OrcidPublicRecord:
    for body in sections.values():
        _reject_excluded_path(body)
    mentioned = _mentioned_orcids(sections)
    if mentioned != {orcid_id}:
        raise CollectorFailure(INVALID_CONTENT, "orcid id mismatch")
    names: list[str] = []
    for section in AFFILIATION_SECTIONS:
        block = sections.get(section)
        if not isinstance(block, dict):
            continue
        for name in _affiliation_names(block):
            if name in names:
                continue
            if len(names) >= MAX_AFFILIATIONS:
                raise CollectorFailure(CONTENT_TOO_LARGE, "orcid affiliation list exceeds limit")
            names.append(name)
    affiliations: tuple[str, ...] | str = tuple(names) if names else UNKNOWN
    return OrcidPublicRecord(
        orcid_id=orcid_id,
        published_name=_published_name(sections.get("personal-details")),
        affiliations=affiliations,
    )


def _sections_from_document(data: dict) -> dict[str, dict]:
    sections: dict[str, dict] = {}
    for section in METADATA_SECTIONS:
        if section not in data:
            continue
        block = data[section]
        if not isinstance(block, dict):
            raise CollectorFailure(INVALID_CONTENT, "orcid section was not an object")
        sections[section] = block
    if sections:
        return sections
    detected = _detect_section(data)
    if detected is None:
        raise CollectorFailure(INVALID_CONTENT, "orcid metadata sections are missing")
    return {detected: data}


def _detect_section(data: dict) -> str | None:
    path = data.get("path")
    if not isinstance(path, str):
        return None
    part = path.rstrip("/").split("/")[-1].lower()
    if part in _EXCLUDED_SECTIONS:
        raise CollectorFailure(BLOCKED_BY_POLICY, "orcid biography and works are not stored")
    if part in METADATA_SECTIONS:
        return part
    return None


def _reject_excluded_path(data: dict) -> None:
    path = data.get("path")
    if not isinstance(path, str):
        return
    parts = {part.lower() for part in path.split("/") if part}
    if parts & _EXCLUDED_SECTIONS:
        raise CollectorFailure(BLOCKED_BY_POLICY, "orcid biography and works are not stored")


def _mentioned_orcids(sections: dict[str, dict]) -> set[str]:
    found: set[str] = set()
    for body in sections.values():
        found.update(_orcids_in(body))
    return found


def _orcids_in(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _IGNORED_KEYS:
                continue
            if key in {"path", "uri"} and isinstance(value, str):
                found.update(_ORCID_IN_TEXT.findall(value))
            else:
                found.update(_orcids_in(value))
    elif isinstance(node, list):
        for item in node:
            found.update(_orcids_in(item))
    return found


def _published_name(section: object) -> str:
    if not isinstance(section, dict):
        return UNKNOWN
    name = section.get("name")
    if not isinstance(name, dict) or not _is_public(name):
        return UNKNOWN
    credit = _text_value(name.get("credit-name"))
    if credit:
        return credit
    given = _text_value(name.get("given-names"))
    family = _text_value(name.get("family-name"))
    parts = [part for part in (given, family) if part]
    if not parts:
        return UNKNOWN
    published = " ".join(parts)
    if len(published) > MAX_NAME_CHARS:
        raise CollectorFailure(CONTENT_TOO_LARGE, "orcid published name exceeds limit")
    return published


def _affiliation_names(section: dict) -> list[str]:
    groups = section.get("affiliation-group")
    if groups is None:
        return []
    if not isinstance(groups, list):
        raise CollectorFailure(INVALID_CONTENT, "orcid affiliation group is not a list")
    names: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        summaries = group.get("summaries")
        if summaries is None:
            continue
        if not isinstance(summaries, list):
            raise CollectorFailure(INVALID_CONTENT, "orcid affiliation summaries are not a list")
        for summary in summaries:
            if not isinstance(summary, dict):
                continue
            for key, item in summary.items():
                if not isinstance(key, str) or not key.endswith("-summary") or not isinstance(item, dict):
                    continue
                if not _is_public(item):
                    continue
                organization = item.get("organization")
                if not isinstance(organization, dict):
                    continue
                name = _clean_text(
                    organization.get("name"),
                    limit=MAX_AFFILIATION_CHARS,
                    kind="affiliation name",
                )
                if name:
                    names.append(name)
    return names


def _text_value(node: object) -> str | None:
    if isinstance(node, dict):
        if not _is_public(node):
            return None
        return _clean_text(node.get("value"), limit=MAX_NAME_CHARS, kind="published name")
    return _clean_text(node, limit=MAX_NAME_CHARS, kind="published name")


def _clean_text(value: object, *, limit: int, kind: str) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or any(ord(char) < 32 for char in text):
        return None
    if len(text) > limit:
        raise CollectorFailure(CONTENT_TOO_LARGE, f"orcid {kind} exceeds limit")
    return text


def _is_public(node: dict) -> bool:
    visibility = node.get("visibility")
    if visibility is None:
        return True
    if not isinstance(visibility, str):
        return False
    return visibility.strip().lower() == "public"


def _decode_object(payload: bytes) -> dict:
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure(CONTENT_TOO_LARGE, "orcid response exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure(INVALID_CONTENT, f"malformed orcid payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure(INVALID_CONTENT, "orcid payload was not an object")
    return data


def _require_orcid(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure(INVALID_CONTENT, "invalid orcid id")
    text = value.strip()
    if text.endswith("x"):
        text = text[:-1] + "X"
    if not _ORCID_ID.fullmatch(text):
        raise CollectorFailure(INVALID_CONTENT, "invalid orcid id")
    digits = text.replace("-", "")
    if _check_digit(digits[:-1]) != digits[-1]:
        raise CollectorFailure(INVALID_CONTENT, "invalid orcid id")
    return text


def _check_digit(base_digits: str) -> str:
    """ISO 7064 mod 11-2 check digit used by ORCID iDs."""
    total = 0
    for char in base_digits:
        total = (total + int(char)) * 2
    result = (12 - (total % 11)) % 11
    return "X" if result == 10 else str(result)


def _forbidden_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != API_HOST:
        return True
    if parsed.query or parsed.fragment or parsed.username:
        return True
    parts = {part.lower() for part in parsed.path.split("/") if part}
    return bool(parts & _EXCLUDED_SECTIONS)
