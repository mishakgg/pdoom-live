"""OpenReview public note metadata.

The collector reads one page of the unauthenticated notes search API.
GET /notes is not called: OpenReview answers that route with a browser
challenge, and this adapter does not try to clear it. PDF URLs are not
requested. A missing publication timestamp stays unknown.

This adapter is callable on its own. It is not wired into the belief runner.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "openreview-0.1.0"
SEARCH_URL = "https://api2.openreview.net/notes/search"
MAX_LIMIT = 5
MAX_NOTES = 5
MAX_TERM_LENGTH = 200
ABSTRACT_LIMIT = 1500
# 2000-01-01 and 2100-01-01 in milliseconds. Values outside this stay unknown.
_MIN_MS = 946_684_800_000
_MAX_MS = 4_102_444_800_000
_DATE_FIELDS = ("pdate", "tcdate", "cdate")
_NOTE_ID = re.compile(r"^[A-Za-z0-9_-]{4,128}$")
_ALLOWED_TYPES = ("application/json", "text/plain", "application/octet-stream", "")


@dataclass(frozen=True)
class OpenReviewNote:
    title: str
    note_id: str
    forum_id: str
    canonical_url: str
    date: str
    authors: tuple[str, ...]


class OpenReviewCollector:
    collector = "openreview"
    platform = "openreview"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=_ALLOWED_TYPES,
            max_bytes=200_000,
            max_redirects=0,
            max_attempts=1,
            timeout=10,
        )

    def collect_search(
        self,
        *,
        source_identity: str,
        term: str,
        observed_at: str,
        limit: int = 1,
    ) -> list[SourceObservation]:
        url = search_url(term, limit=limit)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if not _is_search_url(hop):
                raise CollectorFailure("blocked_by_policy", "openreview collector only reads notes search metadata")
        content_type = result.headers.get("content-type", "")
        if "pdf" in content_type.lower() or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf responses are not collected")
        return self.parse(result.body, source_identity=source_identity, observed_at=observed_at)

    def retrieve(self, payload: bytes) -> list[OpenReviewNote]:
        return [_record(note) for note in _load_notes(payload)]

    def parse(self, payload: bytes, *, source_identity: str, observed_at: str) -> list[SourceObservation]:
        observations = []
        for note in _load_notes(payload):
            observations.append(_observation(note, source_identity=source_identity, observed_at=observed_at))
        return observations


def search_url(term: str, *, limit: int = 1) -> str:
    cleaned = " ".join((term or "").split())
    if not cleaned or len(cleaned) > MAX_TERM_LENGTH or any(ord(char) < 32 for char in cleaned):
        raise CollectorFailure("invalid_content", "search term must be 1 to 200 characters")
    if "://" in cleaned or "/pdf" in cleaned.lower():
        raise CollectorFailure("blocked_by_policy", "search term must not be a url or pdf path")
    if limit < 1 or limit > MAX_LIMIT:
        raise CollectorFailure("invalid_content", "limit must be between 1 and 5")
    query = urlencode(
        {
            "term": cleaned,
            "content": "all",
            "group": "all",
            "source": "forum",
            "limit": str(limit),
        }
    )
    return f"{SEARCH_URL}?{query}"


def _is_search_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "api2.openreview.net"
        and parsed.path == "/notes/search"
        and "/pdf" not in (parsed.path + "?" + parsed.query).lower()
    )


def _load_notes(payload: bytes) -> list[dict]:
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf payloads are not collected")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed openreview payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "openreview payload was not an object")
    name = str(data.get("name") or "")
    if "ChallengeRequired" in name or name == "ForbiddenError":
        raise CollectorFailure("blocked_by_policy", "openreview required a browser challenge")
    notes = data.get("notes")
    if not isinstance(notes, list):
        raise CollectorFailure("invalid_content", "openreview response missing notes")
    if len(notes) > MAX_NOTES:
        raise CollectorFailure("content_too_large", "openreview response has more notes than the bounded page")
    parsed: list[dict] = []
    for note in notes:
        if not isinstance(note, dict):
            raise CollectorFailure("invalid_content", "openreview note was not an object")
        if note.get("ddate"):
            continue
        _require_ids(note)
        parsed.append(note)
    return parsed


def _require_ids(note: dict) -> None:
    note_id = note.get("id")
    forum_id = note.get("forum") or note_id
    if not isinstance(note_id, str) or not _NOTE_ID.fullmatch(note_id):
        raise CollectorFailure("invalid_content", "openreview note id is missing")
    if not isinstance(forum_id, str) or not _NOTE_ID.fullmatch(forum_id):
        raise CollectorFailure("invalid_content", "openreview forum id is missing")


def _record(note: dict) -> OpenReviewNote:
    note_id = str(note["id"])
    forum_id = str(note.get("forum") or note_id)
    content = note.get("content") if isinstance(note.get("content"), dict) else {}
    date, _field_name = _publication_date(note)
    return OpenReviewNote(
        title=_title(content),
        note_id=note_id,
        forum_id=forum_id,
        canonical_url=_forum_url(forum_id, note_id),
        date=date,
        authors=_authors(content),
    )


def _observation(note: dict, *, source_identity: str, observed_at: str) -> SourceObservation:
    record = _record(note)
    content = note.get("content") if isinstance(note.get("content"), dict) else {}
    abstract = _plain_text(_field(content, "abstract"))
    text, truncated = excerpt(abstract, ABSTRACT_LIMIT)
    date, date_field = _publication_date(note)
    published_at = None if date == "unknown" else date
    version = note.get("version")
    mdate = note.get("mdate")
    readers = note.get("readers")
    if isinstance(readers, list) and "everyone" in readers:
        listed_public: bool | None = True
    elif isinstance(readers, list):
        listed_public = False
    else:
        listed_public = None
    observation = SourceObservation(
        source_identity=source_identity,
        platform="openreview",
        upstream_id=record.note_id,
        canonical_url=record.canonical_url,
        observed_at=observed_at,
        published_at=published_at,
        author_candidates=[
            AuthorCandidate(
                name=name,
                role="author",
                attribution_method="openreview_author_metadata",
                confidence="high",
            )
            for name in record.authors
        ],
        title=record.title or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "forum_id": record.forum_id,
            "note_id": record.note_id,
            "date": date,
            "date_field": date_field,
            "venue": _plain_text(_field(content, "venue")) or None,
            "license": note.get("license") if isinstance(note.get("license"), str) else None,
            "listed_public": listed_public,
            "pdf_referenced": _field(content, "pdf") is not None,
            "truncated": truncated,
            "upstream_version": f"{record.note_id}:{version if version is not None else ''}:{mdate if mdate is not None else ''}",
            "rights": "OpenReview note metadata and a short abstract excerpt. The PDF is not downloaded.",
        },
        collection_method="openreview_api",
        collector="openreview",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _publication_date(note: dict) -> tuple[str, str]:
    """Publication date, then true creation, then creation. Anything else stays unknown."""
    for field in _DATE_FIELDS:
        parsed = _timestamp_to_utc(note.get(field))
        if parsed:
            return parsed, field
    return "unknown", "unknown"


def _timestamp_to_utc(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if re.fullmatch(r"-?\d+", text):
            value = int(text)
        else:
            return _iso_to_utc(text)
    if isinstance(value, float):
        if not value.is_integer():
            return None
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value >= 10**12:
        millis = value
    elif value >= 10**9:
        millis = value * 1000
    else:
        return None
    if millis < _MIN_MS or millis >= _MAX_MS:
        return None
    try:
        parsed = datetime.fromtimestamp(millis / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_to_utc(value: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    utc = parsed.astimezone(timezone.utc)
    if utc.year < 2000 or utc.year >= 2100:
        return None
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _forum_url(forum_id: str, note_id: str) -> str:
    if forum_id == note_id:
        raw = f"https://openreview.net/forum?id={forum_id}"
    else:
        raw = f"https://openreview.net/forum?id={forum_id}&noteId={note_id}"
    try:
        canonical = canonicalize_url(raw)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "openreview canonical url could not be built") from exc
    parsed = urlparse(canonical)
    if parsed.netloc != "openreview.net" or parsed.path != "/forum" or "/pdf" in canonical.lower():
        raise CollectorFailure("blocked_by_policy", "openreview canonical url must be a forum page")
    return canonical


def _field(content: dict, name: str) -> object:
    value = content.get(name)
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def _title(content: dict) -> str:
    return _plain_text(_field(content, "title"))


def _authors(content: dict) -> tuple[str, ...]:
    value = _field(content, "authors")
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return (cleaned,) if cleaned and len(cleaned) <= 200 else ()
    if not isinstance(value, list):
        return ()
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            item = item.get("name") or item.get("fullname") or ""
        if not isinstance(item, str):
            continue
        cleaned = " ".join(item.split())
        if cleaned and len(cleaned) <= 200:
            names.append(cleaned)
        if len(names) >= 50:
            break
    return tuple(names)


def _plain_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())
