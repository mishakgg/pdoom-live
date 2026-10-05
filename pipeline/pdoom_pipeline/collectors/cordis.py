"""CORDIS public project metadata.

Reads one project from the public CORDIS search JSON used by the fact sheet.
The response is project metadata only. Project documents, deliverables, and
PDFs are not requested.

Project 101222135, "Safety Mechanisms for Artificial General Intelligence
(AGI)", is an AGI safety project. Its objective is longer than 400 characters,
so that text is not stored. The fact sheet does not state a reuse licence, so
rights stay unknown. Coordinator and participant names are kept as separate
labels and are not resolved to people.

This module is not wired into the belief runner.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "cordis-0.1.0"
API_ORIGIN = "https://cordis.europa.eu"
SEARCH_PATH = "/search/en"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_DESCRIPTION_CHARS = 400
MAX_TITLE_CHARS = 500
MAX_NAME_CHARS = 300
MAX_RIGHTS_CHARS = 200
MAX_ORGANIZATIONS = 100

_PROJECT_ID = re.compile(r"^[0-9]{1,12}$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_ROLE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_RIGHTS_KEYS = ("license", "licence", "rights", "reuse")
_DOCUMENT_MARKERS = (".pdf", "/pdf", "downloadpublic", "/documents/", "documentids=")


@dataclass(frozen=True)
class CordisOrganization:
    """One coordinator or participant name. Names are not merged."""

    name: str
    role: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "role": self.role}


@dataclass(frozen=True)
class CordisProject:
    """Metadata for one CORDIS project fact sheet."""

    project_id: str
    title: str
    start_date: str
    canonical_url: str
    organizations: tuple[CordisOrganization, ...]
    rights: str
    description: str | None = None

    def as_dict(self) -> dict[str, object]:
        record: dict[str, object] = {
            "project_id": self.project_id,
            "title": self.title,
            "start_date": self.start_date,
            "canonical_url": self.canonical_url,
            "organizations": [organization.as_dict() for organization in self.organizations],
            "rights": self.rights,
        }
        if self.description is not None:
            record["description"] = self.description
        return record


class CordisCollector:
    """Retrieve one public project. The default fetcher makes a single attempt."""

    collector = "cordis"
    platform = "cordis"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, project_id: str) -> CordisProject:
        expected_id = _validated_id(project_id)
        url = project_request_url(expected_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        targets = list(result.requested_urls or [])
        if result.url not in targets:
            targets.append(result.url)
        for hop in targets:
            if not _is_search_url(hop):
                raise CollectorFailure("blocked_by_policy", "cordis collector only reads project search metadata")
        if result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf payloads are not collected")
        project = parse_project(result.body)
        if project.project_id != expected_id:
            raise CollectorFailure("invalid_content", "cordis project id mismatch")
        return project

    def parse(self, payload: bytes) -> CordisProject:
        return parse_project(payload)


def project_request_url(project_id: str) -> str:
    """JSON search URL for one project id. The URL is not a document or PDF."""
    project_id = _validated_id(project_id)
    query = urlencode(
        {
            "format": "json",
            "num": "1",
            "q": f"contenttype='project' AND id={project_id}",
        }
    )
    url = f"{API_ORIGIN}{SEARCH_PATH}?{query}"
    if not _is_search_url(url):
        raise CollectorFailure("blocked_by_policy", "cordis retrieval stays on the project search api")
    return url


def parse_project(payload: bytes) -> CordisProject:
    """Return id, title, start date, parties, fact-sheet URL, and rights.

    A description is included only when the objective is present and at most
    400 characters. A missing or longer objective stays absent. Rights are
    ``unknown`` unless this record states a reuse licence.
    """
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf payloads are not collected")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "cordis payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed cordis payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "cordis payload was not an object")
    project = _project_object(data)
    project_id = _project_id(project.get("id"))
    description = _description(project.get("objective"))
    return CordisProject(
        project_id=project_id,
        title=_title(project.get("title")),
        start_date=_start_date(project.get("startDate")),
        canonical_url=_canonical_url(project_id),
        organizations=_organizations(project),
        rights=_rights(project),
        description=description,
    )


def _validated_id(value: object) -> str:
    if isinstance(value, bool) or value is None:
        raise CollectorFailure("invalid_content", "cordis project id is missing")
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "cordis project id is missing")
    text = value.strip()
    if _is_document_target(text) or not _PROJECT_ID.fullmatch(text):
        raise CollectorFailure("invalid_content", "cordis project id is not a project id")
    return text


def _project_id(value: object) -> str:
    return _validated_id(value)


def _is_document_target(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("%pdf") or any(marker in lowered for marker in _DOCUMENT_MARKERS)


def _is_search_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "cordis.europa.eu" or parsed.path != SEARCH_PATH:
        return False
    if _is_document_target(url):
        return False
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return query.get("format") == "json" and query.get("num") == "1"


def _project_object(data: dict) -> dict:
    header = _header(data)
    total = header.get("totalHits")
    if total is not None and str(total) == "0":
        raise CollectorFailure("not_found", "cordis project was not found")
    hits = data.get("hits")
    if not isinstance(hits, dict) or "hit" not in hits:
        raise CollectorFailure("invalid_content", "cordis response missing hits")
    hit = hits.get("hit")
    if isinstance(hit, list):
        if len(hit) == 0:
            raise CollectorFailure("not_found", "cordis project was not found")
        if len(hit) != 1:
            raise CollectorFailure("invalid_content", "cordis response was not a single project")
        hit = hit[0]
    if not isinstance(hit, dict):
        raise CollectorFailure("invalid_content", "cordis hit was not an object")
    project = hit.get("project")
    if not isinstance(project, dict):
        raise CollectorFailure("invalid_content", "cordis hit missing project")
    if project.get("contenttype") != "project":
        raise CollectorFailure("blocked_by_policy", "cordis collector only reads project metadata")
    return project


def _header(data: dict) -> dict:
    result = data.get("result")
    if not isinstance(result, dict):
        return {}
    header = result.get("header")
    if not isinstance(header, dict):
        return {}
    return header


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "cordis project title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "cordis project title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "cordis title exceeds limit")
    return title


def _start_date(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if not _DATE.fullmatch(text):
        return UNKNOWN
    year_text, month_text, day_text = text.split("-")
    try:
        parsed = datetime(int(year_text), int(month_text), int(day_text))
    except ValueError:
        return UNKNOWN
    if parsed.year < 1980 or parsed.year > 2100:
        return UNKNOWN
    return text


def _description(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > MAX_DESCRIPTION_CHARS or _is_document_target(text):
        return None
    return text


def _rights(project: dict) -> str:
    for key in _RIGHTS_KEYS:
        if key not in project:
            continue
        text = _rights_text(project.get(key))
        if text:
            return text
    return UNKNOWN


def _rights_text(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("name", "title", "url"):
            if key not in value:
                continue
            found = _rights_text(value.get(key))
            if found:
                return found
        return None
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > MAX_RIGHTS_CHARS or _is_document_target(text):
        return None
    return text


def _organizations(project: dict) -> tuple[CordisOrganization, ...]:
    relations = project.get("relations")
    associations = relations.get("associations") if isinstance(relations, dict) else None
    raw = associations.get("organization") if isinstance(associations, dict) else None
    if raw is None:
        return ()
    if isinstance(raw, dict):
        items = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        raise CollectorFailure("invalid_content", "cordis organizations are not a list")
    if len(items) > MAX_ORGANIZATIONS:
        raise CollectorFailure("content_too_large", "cordis organization list exceeds limit")
    organizations: list[CordisOrganization] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _organization_name(item)
        if name is None:
            continue
        organizations.append(CordisOrganization(name=name, role=_role(item)))
    return tuple(organizations)


def _organization_name(item: dict) -> str | None:
    value = item.get("legalName")
    if not isinstance(value, str) or not value.strip():
        value = item.get("shortName") if isinstance(item.get("shortName"), str) else ""
    if not isinstance(value, str):
        return None
    name = " ".join(value.split())
    if not name:
        return None
    if len(name) > MAX_NAME_CHARS:
        raise CollectorFailure("content_too_large", "cordis organization name exceeds limit")
    return name


def _role(item: dict) -> str:
    raw = None
    attributes = item.get("@attributes")
    if isinstance(attributes, dict):
        raw = attributes.get("type")
    if not isinstance(raw, str):
        raw = item.get("role")
    if not isinstance(raw, str):
        return UNKNOWN
    role = "".join(raw.split()).lower()
    if not _ROLE.fullmatch(role):
        return UNKNOWN
    return role


def _canonical_url(project_id: str) -> str:
    raw = f"{API_ORIGIN}/project/id/{project_id}"
    try:
        canonical = canonicalize_url(raw)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "cordis canonical url could not be built") from exc
    parsed = urlparse(canonical)
    if parsed.scheme != "https" or parsed.hostname != "cordis.europa.eu":
        raise CollectorFailure("blocked_by_policy", "cordis canonical url must stay on cordis")
    if parsed.path != f"/project/id/{project_id}" or parsed.query or parsed.fragment:
        raise CollectorFailure("blocked_by_policy", "cordis canonical url must be the project fact sheet")
    if _is_document_target(canonical):
        raise CollectorFailure("blocked_by_policy", "project documents are not collected")
    return canonical
