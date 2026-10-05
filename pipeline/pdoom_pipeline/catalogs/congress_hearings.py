"""Offline catalog of public US congressional hearings on artificial intelligence risk.

Rows are hearing metadata and canonical URLs. This module does not fetch pages
and does not store transcripts. US federal government works are public domain.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

RIGHTS = "us_government_work"
CATALOG_ID = "us_congress_ai_hearings"
UNKNOWN_DATE = "unknown"
OFFICIAL_DOMAINS = frozenset({"house.gov", "senate.gov", "congress.gov"})
MAX_TEXT_CHARS = 500
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HOST_LABEL_RE = re.compile(r"[a-z0-9-]+")
FORBIDDEN_KEYS = frozenset(
    {
        "transcript",
        "transcript_text",
        "full_text",
        "body",
        "testimony_text",
        "content",
        "quotation",
        "quote",
    }
)


@dataclass(frozen=True)
class CongressHearing:
    id: str
    title: str
    committee: str
    date: str
    canonical_url: str
    rights: str


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / "us_congress_ai_hearings.json"


def official_congress_hostname(hostname: str) -> bool:
    """True when the host is house.gov, senate.gov, congress.gov, or a subdomain."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host:
        return False
    labels = host.split(".")
    if len(labels) < 2:
        return False
    if any(not label or HOST_LABEL_RE.fullmatch(label) is None for label in labels):
        return False
    return ".".join(labels[-2:]) in OFFICIAL_DOMAINS


def validate_canonical_url(url: str) -> str:
    raw = (url or "").strip()
    if raw != (url or ""):
        raise ValueError("canonical URL must not have surrounding whitespace")
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"canonical URL must be https: {url}")
    if parsed.username or parsed.password:
        raise ValueError(f"canonical URL must not include userinfo: {url}")
    if parsed.query or parsed.fragment:
        raise ValueError(f"canonical URL must not include a query or fragment: {url}")
    if parsed.port not in (None, 443):
        raise ValueError(f"canonical URL must use the default https port: {url}")
    if not official_congress_hostname(parsed.hostname or ""):
        raise ValueError(
            "canonical URL host is not a house.gov, senate.gov, or congress.gov page: "
            f"{url}"
        )
    return raw


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        raise ValueError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}: {value!r}")
    year, month, day = (int(part) for part in value.split("-"))
    date(year, month, day)
    return value


def _reject_stored_transcript(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN_KEYS.intersection(value)
        if found:
            names = ", ".join(sorted(found))
            raise ValueError(f"{path} must not store transcript content ({names})")
        for key, item in value.items():
            _reject_stored_transcript(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_stored_transcript(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if len(value) > MAX_TEXT_CHARS:
            raise ValueError(f"{path} exceeds {MAX_TEXT_CHARS} characters")
        return
    if value is None or isinstance(value, (int, float, bool)):
        return
    raise ValueError(f"{path} has an unsupported JSON type")


def _text(record: dict, key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    if value != value.strip():
        raise ValueError(f"{key} must not have surrounding whitespace")
    return value


def hearing_from_record(record: dict) -> CongressHearing:
    if not isinstance(record, dict):
        raise ValueError("hearing row must be an object")
    _reject_stored_transcript(record, "hearing")
    hearing_id = _text(record, "id")
    if ID_RE.fullmatch(hearing_id) is None:
        raise ValueError(f"id must be a lowercase slug: {hearing_id}")
    rights = record.get("rights")
    if rights != RIGHTS:
        raise ValueError(f"rights must be {RIGHTS}")
    return CongressHearing(
        id=hearing_id,
        title=_text(record, "title"),
        committee=_text(record, "committee"),
        date=validate_date(record.get("date")),
        canonical_url=validate_canonical_url(_text(record, "canonical_url")),
        rights=rights,
    )


def load_hearings(path: Path | None = None) -> list[CongressHearing]:
    catalog_file = path or default_catalog_path()
    payload = json.loads(catalog_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("catalog must be an object")
    _reject_stored_transcript(payload)
    if payload.get("catalog_id") != CATALOG_ID:
        raise ValueError(f"catalog_id must be {CATALOG_ID}")
    if payload.get("rights") != RIGHTS:
        raise ValueError(f"catalog rights must be {RIGHTS}")
    rows = payload.get("hearings")
    if not isinstance(rows, list) or not rows:
        raise ValueError("catalog hearings must be a non-empty list")
    hearings = [hearing_from_record(row) for row in rows]
    ids = [hearing.id for hearing in hearings]
    urls = [hearing.canonical_url for hearing in hearings]
    if len(ids) != len(set(ids)):
        raise ValueError("hearing ids must be unique")
    if len(urls) != len(set(urls)):
        raise ValueError("canonical URLs must be unique")
    return hearings
