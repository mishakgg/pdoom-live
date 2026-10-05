"""NSF Award Search metadata for one award.

Reads a single record from the public Award Search API:

https://api.nsf.gov/services/v1/awards.json?id={award_id}

The parsed record keeps the award id, title, agency, start date or effective
award date, investigator names as separate people, the public award page, and
the abstract. The abstract is a US government work. Investigator contact
details, program-officer names, publication lists, project-outcome reports,
attachments, and PDFs are not stored.

This module is callable on its own. It is not imported by the belief runner.
``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher

COLLECTOR_VERSION = "nsf-awards-metadata-0.1.0"
API_ORIGIN = "https://api.nsf.gov"
AWARDS_PATH = "/services/v1/awards.json"
CANONICAL_AWARD_URL = "https://www.nsf.gov/awardsearch/show-award/?AWD_ID={award_id}"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_ABSTRACT_CHARS = 50_000
MAX_NAME_CHARS = 300
MAX_INVESTIGATORS = 40
_AWARD_ID = re.compile(r"^[0-9]{7}$")
_EMAIL = re.compile(r"\S+@\S+")
_MIN_YEAR = 1950
_MAX_YEAR = 2100


@dataclass(frozen=True)
class NsfInvestigator:
    """One named investigator. Distinct people stay distinct records."""

    name: str
    role: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "role": self.role}


@dataclass(frozen=True)
class NsfAward:
    award_id: str
    title: str
    agency: str
    date: str
    date_source: str
    investigators: tuple[NsfInvestigator, ...]
    canonical_url: str
    abstract_text: str

    def as_record(self) -> dict[str, object]:
        return {
            "award_id": self.award_id,
            "title": self.title,
            "agency": self.agency,
            "date": self.date,
            "date_source": self.date_source,
            "investigators": [person.as_dict() for person in self.investigators],
            "canonical_url": self.canonical_url,
            "abstract": {
                "text": self.abstract_text,
                "rights": RIGHTS_US_GOVERNMENT_WORK,
            },
        }


class NsfAwardsCollector:
    """Retrieve one NSF award's metadata. Not wired into belief collection."""

    collector = "nsf_awards"
    platform = "nsf_awards"
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

    def retrieve(self, award_id: str) -> NsfAward:
        url = award_request_url(award_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if _looks_like_attachment(hop) or not _is_award_search_url(hop):
                raise CollectorFailure("blocked_by_policy", "nsf collector only reads award search json")
        content_type = result.headers.get("content-type", "")
        if "pdf" in content_type.lower() or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        award = parse_award(result.body)
        if award.award_id != _require_award_id(award_id):
            raise CollectorFailure("invalid_content", "nsf award id mismatch")
        return award


def award_request_url(award_id: str) -> str:
    """JSON search URL for one award id. Not a PDF, attachment, or outcomes report."""
    cleaned = _require_award_id(award_id)
    url = f"{API_ORIGIN}{AWARDS_PATH}?{urlencode({'id': cleaned})}"
    if not _is_award_search_url(url) or _looks_like_attachment(url):
        raise CollectorFailure("blocked_by_policy", "nsf collector only reads award search json")
    return url


def canonical_award_url(award_id: str) -> str:
    """Public award page. The trailing slash is the URL NSF serves."""
    return CANONICAL_AWARD_URL.format(award_id=_require_award_id(award_id))


def parse_award(payload: bytes) -> NsfAward:
    """Parse one Award Search JSON body. Performs no I/O.

    An empty body, an empty award list, or an award object without an id and
    title does not become an award. A missing start date falls back to the
    effective award date. If both are missing, the date stays unknown.
    """
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "nsf award payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed nsf award payload: {exc}") from exc
    award = _one_award(data)
    award_id = _response_award_id(award.get("id"))
    title = _title(award.get("title"))
    date, date_source = _start_or_effective_date(award)
    return NsfAward(
        award_id=award_id,
        title=title,
        agency=_agency(award.get("agency")),
        date=date,
        date_source=date_source,
        investigators=_investigators(award),
        canonical_url=canonical_award_url(award_id),
        abstract_text=_abstract_text(award.get("abstractText")),
    )


def _one_award(data: object) -> dict:
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "nsf award payload is not an award")
    response = data.get("response")
    if not isinstance(response, dict):
        raise CollectorFailure("invalid_content", "nsf award payload is not an award")
    if "award" not in response:
        raise CollectorFailure("not_found", "nsf award payload did not contain an award")
    raw = response.get("award")
    if raw is None or raw == [] or raw == "":
        raise CollectorFailure("not_found", "nsf award payload did not contain an award")
    if isinstance(raw, dict):
        awards = [raw]
    elif isinstance(raw, list):
        awards = raw
    else:
        raise CollectorFailure("invalid_content", "nsf award payload is not an award")
    if len(awards) != 1 or not isinstance(awards[0], dict):
        raise CollectorFailure("invalid_content", "nsf award payload must contain one award")
    award = awards[0]
    if not award:
        raise CollectorFailure("not_found", "nsf award payload did not contain an award")
    return award


def _require_award_id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, str):
        raise CollectorFailure("invalid_content", "nsf award id is missing")
    award_id = value.strip()
    if not _AWARD_ID.fullmatch(award_id) or _looks_like_attachment(award_id):
        raise CollectorFailure("invalid_content", "nsf award id is missing")
    return award_id


def _response_award_id(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    return _require_award_id(value)


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "nsf award title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "nsf award title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "nsf award title exceeds limit")
    return title


def _agency(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    agency = " ".join(value.split())
    if not agency or len(agency) > 40:
        return UNKNOWN
    return agency


def _start_or_effective_date(award: dict) -> tuple[str, str]:
    start = _calendar_date(award.get("startDate"))
    if start:
        return start, "startDate"
    effective = _calendar_date(award.get("date"))
    if effective:
        return effective, "date"
    return UNKNOWN, UNKNOWN


def _calendar_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parsed = None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        break
    if parsed is None or not (_MIN_YEAR <= parsed.year <= _MAX_YEAR):
        return None
    return parsed.isoformat()


def _investigators(award: dict) -> tuple[NsfInvestigator, ...]:
    people: list[NsfInvestigator] = []
    seen: set[str] = set()

    def add(raw: object, role: str) -> None:
        if not isinstance(raw, str):
            return
        name = _person_name(raw)
        if not name:
            return
        if len(name) > MAX_NAME_CHARS:
            raise CollectorFailure("content_too_large", "nsf investigator name exceeds limit")
        key = name.casefold()
        if key in seen:
            return
        seen.add(key)
        people.append(NsfInvestigator(name=name, role=role))

    pi_values = _string_list(award.get("pi"))
    if pi_values:
        for item in pi_values:
            add(item, "pi")
    else:
        add(_structured_pi_name(award), "pi")
    for item in _string_list(award.get("coPDPI")):
        add(item, "co_pi")
    if not people:
        add(award.get("pdPIName"), "pi")
    if len(people) > MAX_INVESTIGATORS:
        raise CollectorFailure("content_too_large", "nsf investigator list exceeds limit")
    return tuple(people)


def _structured_pi_name(award: dict) -> str:
    middle = award.get("piMiddeInitial")
    if not isinstance(middle, str) or not middle.strip():
        middle = award.get("piMiddleInitial")
    parts = [
        _person_name(part)
        for part in (award.get("piFirstName"), middle, award.get("piLastName"))
        if isinstance(part, str)
    ]
    return " ".join(part for part in parts if part)


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _person_name(value: str) -> str:
    without_email = _EMAIL.sub(" ", value)
    return " ".join(without_email.split())


def _abstract_text(value: object) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "nsf abstract is not text")
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) > MAX_ABSTRACT_CHARS:
        raise CollectorFailure("content_too_large", "nsf abstract exceeds limit")
    return text


def _is_award_search_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.nsf.gov":
        return False
    if parsed.path != AWARDS_PATH or parsed.fragment:
        return False
    query = dict(pair.split("=", 1) for pair in parsed.query.split("&") if "=" in pair)
    return set(query) == {"id"} and bool(_AWARD_ID.fullmatch(query["id"]))


def _looks_like_attachment(value: str) -> bool:
    lowered = value.lower()
    return (
        ".pdf" in lowered
        or "/pdf" in lowered
        or lowered.startswith("%pdf")
        or "projectoutcomes" in lowered
        or "/attachment" in lowered
    )
