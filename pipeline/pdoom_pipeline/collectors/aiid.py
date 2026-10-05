"""AI Incident Database metadata.

Confirms one public incident, incident 1, from the statically published
page-data JSON at incidentdatabase.ai. The GraphQL API requires a login and
is not called. The saved record is the incident id, title, date, canonical
URL, rights, and the description when that description is at most 400
characters. A longer description is omitted rather than truncated. Report
bodies, report PDFs, and editor notes are not stored.

Rights stay unknown unless the incident object itself states a reuse licence.
"All rights reserved" is not a reuse licence. A licence mentioned only in a
description, an editor note, or a linked report does not count.

Similar incidents stay separate records. Their titles are not folded into
this incident. This module is not imported by belief collection or any job.
No source row is added, so runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher

COLLECTOR_VERSION = "aiid-metadata-0.1.0"
API_ORIGIN = "https://incidentdatabase.ai"
API_HOST = "incidentdatabase.ai"
CONFIRMED_INCIDENT_ID = "1"
CONFIRMED_TITLE = "Google\u2019s YouTube Kids App Presents Inappropriate Content"
CONFIRMED_DATE = "2015-05-19"
CONFIRMED_DESCRIPTION = (
    "YouTube\u2019s content filtering and recommendation algorithms exposed children to "
    "disturbing and inappropriate videos."
)
CONFIRMED_CANONICAL_URL = f"{API_ORIGIN}/cite/{CONFIRMED_INCIDENT_ID}/"
PAGE_DATA_PATH = f"/page-data/cite/{CONFIRMED_INCIDENT_ID}/page-data.json"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_DESCRIPTION_CHARS = 400
MAX_RIGHTS_CHARS = 300
UNKNOWN = "unknown"

_INCIDENT_ID = re.compile(r"[1-9][0-9]{0,6}")
_CITE_PATH = re.compile(rf"^(?:https://{re.escape(API_HOST)})?/cite/([1-9][0-9]{{0,6}})/?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LICENSE_KEYS = ("license", "licence", "reuseLicense", "reuseLicence")
_COPYRIGHT_KEYS = ("copyright", "rights", "rightsStatement")
_RESERVATION = re.compile(
    r"^(?:all rights reserved\.?|copyright|unknown|none|n/?a)$",
    re.I,
)
_REUSE = re.compile(
    r"(creative commons|\bcc[\s-]?by\b|\bcc0\b|\bcc[\s-]?zero\b|\bogl\b|open government licen[cs]e|public domain)",
    re.I,
)


@dataclass(frozen=True)
class AiidIncident:
    """Metadata for one incident. Report narratives are not copied."""

    incident_id: str
    title: str
    date: str
    canonical_url: str
    rights: str
    description: str | None = None

    def as_record(self) -> dict[str, str]:
        record = {
            "incident_id": self.incident_id,
            "title": self.title,
            "date": self.date,
            "canonical_url": self.canonical_url,
            "rights": self.rights,
        }
        if self.description is not None:
            record["description"] = self.description
        return record


class AiidCollector:
    """Retrieve the one confirmed incident. The default fetcher makes one attempt."""

    collector = "aiid"
    platform = "aiid"
    collector_version = COLLECTOR_VERSION
    runner_wired = False

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, incident_id: str = CONFIRMED_INCIDENT_ID) -> AiidIncident:
        url = confirmed_incident_url(incident_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        if requested != [url] or result.url != url:
            raise CollectorFailure("blocked_by_policy", "aiid retrieval does not follow another url")
        for hop in requested:
            if _looks_like_report(hop):
                raise CollectorFailure("blocked_by_policy", "incident reports are not downloaded")
        if _payload_is_document(result.body):
            raise CollectorFailure("blocked_by_policy", "incident reports are not downloaded")
        entry = parse_incident(result.body)
        if entry.incident_id != CONFIRMED_INCIDENT_ID or entry.canonical_url != CONFIRMED_CANONICAL_URL:
            raise CollectorFailure("invalid_content", "aiid incident does not match the confirmed record")
        return entry


def confirmed_incident_url(incident_id: str = CONFIRMED_INCIDENT_ID) -> str:
    """JSON URL for the confirmed incident. It does not address a report or a PDF."""
    text = (incident_id or "").strip()
    if text != CONFIRMED_INCIDENT_ID or _looks_like_report(text):
        raise CollectorFailure("blocked_by_policy", "only the confirmed incident json record is retrieved")
    url = f"{API_ORIGIN}{PAGE_DATA_PATH}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != PAGE_DATA_PATH:
        raise CollectorFailure("unsafe_url", "aiid retrieval stays on the incident page-data json")
    if parsed.query or parsed.fragment or _looks_like_report(url):
        raise CollectorFailure("blocked_by_policy", "incident reports are not downloaded")
    return url


def parse_incident(payload: bytes) -> AiidIncident:
    """Read one incident's id, title, date, canonical URL, rights, and short description.

    A description longer than 400 characters is omitted. Report nodes, editor
    notes, and similar-incident lists are not copied and are not merged into
    this record. Rights come from a licence field on the incident, or from a
    copyright field when that text states a reuse licence.
    """
    if _payload_is_document(payload):
        raise CollectorFailure("blocked_by_policy", "incident reports are not downloaded")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "aiid payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed aiid payload: {exc}") from exc
    incident, paths = _one_incident(data)
    incident_id = _incident_id(incident.get("incident_id"))
    _reject_other_incident(paths, incident_id)
    return AiidIncident(
        incident_id=incident_id,
        title=_title(incident.get("title")),
        date=_date(incident.get("date")),
        canonical_url=_canonical_url(incident_id),
        rights=_rights(incident),
        description=_description(incident.get("description")),
    )


def _one_incident(data: object) -> tuple[dict, list[str]]:
    if isinstance(data, list):
        raise CollectorFailure("blocked_by_policy", "similar incident titles are not merged")
    if not isinstance(data, dict) or not data:
        raise CollectorFailure("invalid_content", "aiid payload is not one incident")
    if isinstance(data.get("incidents"), list):
        raise CollectorFailure("blocked_by_policy", "similar incident titles are not merged")
    if "result" in data:
        return _from_page_data(data)
    if "incident_id" not in data or "title" not in data:
        raise CollectorFailure("invalid_content", "aiid payload is not one incident")
    return data, _path_values(data)


def _from_page_data(data: dict) -> tuple[dict, list[str]]:
    result = data.get("result")
    if not isinstance(result, dict):
        raise CollectorFailure("invalid_content", "aiid payload is not one incident")
    inner = result.get("data")
    if isinstance(inner, list) or isinstance(result.get("data"), list):
        raise CollectorFailure("blocked_by_policy", "similar incident titles are not merged")
    if not isinstance(inner, dict):
        raise CollectorFailure("invalid_content", "aiid payload is not one incident")
    if isinstance(inner.get("incidents"), list):
        raise CollectorFailure("blocked_by_policy", "similar incident titles are not merged")
    incident = inner.get("incident")
    if isinstance(incident, list):
        raise CollectorFailure("blocked_by_policy", "similar incident titles are not merged")
    if not isinstance(incident, dict):
        raise CollectorFailure("invalid_content", "aiid payload is not one incident")
    paths = _path_values(data)
    page = result.get("pageContext")
    if isinstance(page, dict):
        paths.extend(_path_values(page))
        page_id = page.get("incident_id")
        if page_id is not None and _incident_id(page_id) != _incident_id(incident.get("incident_id")):
            raise CollectorFailure("invalid_content", "aiid page does not match the incident")
    return incident, paths


def _path_values(item: dict) -> list[str]:
    found: list[str] = []
    for key in ("path", "originalPath", "url", "canonical_url"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
    return found


def _reject_other_incident(paths: list[str], incident_id: str) -> None:
    for path in paths:
        if _looks_like_report(path):
            continue
        cited = _cite_id(path)
        if cited is not None and cited != incident_id:
            raise CollectorFailure("invalid_content", "aiid path does not match the incident")


def _incident_id(value: object) -> str:
    if isinstance(value, bool) or value is None:
        raise CollectorFailure("invalid_content", "aiid incident id is missing")
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise CollectorFailure("invalid_content", "aiid incident id is missing")
    if _INCIDENT_ID.fullmatch(text) is None or _looks_like_report(text):
        raise CollectorFailure("invalid_content", "aiid incident id is missing")
    return text


def _cite_id(value: str) -> str | None:
    match = _CITE_PATH.fullmatch(value.strip())
    if match is None:
        return None
    return match.group(1)


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "aiid title is missing")
    title = " ".join(value.split())
    if not title or "\x00" in title:
        raise CollectorFailure("invalid_content", "aiid title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "aiid title exceeds limit")
    return title


def _date(value: object) -> str:
    """Use the incident ``date`` only. Report dates are not substituted."""
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if _DATE.fullmatch(text) is None:
        return UNKNOWN
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return UNKNOWN
    if parsed.year < 1990 or parsed.year > 2100:
        return UNKNOWN
    return parsed.isoformat()


def _canonical_url(incident_id: str) -> str:
    url = f"{API_ORIGIN}/cite/{incident_id}/"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != f"/cite/{incident_id}/":
        raise CollectorFailure("invalid_content", "aiid canonical url is invalid")
    if _looks_like_report(url):
        raise CollectorFailure("blocked_by_policy", "incident reports are not downloaded")
    return url


def _description(value: object) -> str | None:
    """Keep a description only when it is present and at most 400 characters."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or "\x00" in text:
        return None
    if len(text) > MAX_DESCRIPTION_CHARS:
        return None
    return text


def _rights(incident: dict) -> str:
    for key in _LICENSE_KEYS:
        text = _rights_text(incident, key)
        if text is None or _RESERVATION.fullmatch(text):
            continue
        return text
    for key in _COPYRIGHT_KEYS:
        text = _rights_text(incident, key)
        if text is None or _RESERVATION.fullmatch(text) or _REUSE.search(text) is None:
            continue
        return text
    return UNKNOWN


def _rights_text(incident: dict, key: str) -> str | None:
    if key not in incident:
        return None
    value = incident.get(key)
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or "\x00" in text:
        return None
    if len(text) > MAX_RIGHTS_CHARS:
        raise CollectorFailure("content_too_large", "aiid rights label exceeds limit")
    return text


def _payload_is_document(payload: bytes) -> bool:
    stripped = payload.lstrip(b"\xef\xbb\xbf \t\r\n")
    lowered = stripped[:64].lower()
    return lowered.startswith(b"%pdf") or lowered.startswith(b"<") or lowered.startswith(b"<!doctype")


def _looks_like_report(value: str) -> bool:
    lowered = value.lower()
    return (
        ".pdf" in lowered
        or "%pdf" in lowered
        or "/reports/" in lowered
        or lowered.rstrip("/").endswith("/reports")
        or "/api/graphql" in lowered
    )
