"""OECD.AI policy-observatory metadata.

Confirms one public Policy Navigator entry, "OECD AI Policy Observatory
(OECD.AI)", from the unauthenticated JSON API at api.oecdai.org. English
OECD.AI dashboard pages are allowed by robots.txt; the French dashboard
paths are not requested. The call reads one initiative record. It does not
download storage files, images, or policy text.

The stored fields are title, publisher, start year, canonical URL, and
rights. ``startYear`` is the date. Record-maintenance timestamps and dates
mentioned only in narrative fields are not substituted; a missing start year
stays unknown. Rights stay unknown unless the payload states a reuse licence.
"All rights reserved" is not a reuse licence.

This module is not imported by belief collection or any job. No source row is
added, so runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "oecd-ai-metadata-0.1.0"
API_ORIGIN = "https://api.oecdai.org"
API_HOST = "api.oecdai.org"
ENTRY_PREFIX = "/policy-initiatives/s/"
CANONICAL_PREFIX = "https://oecd.ai/en/dashboards/policy-initiatives/"
CONFIRMED_SLUG = "oecd-ai-policy-observatory-oecdai-9635"
CONFIRMED_TITLE = "OECD AI Policy Observatory (OECD.AI)"
CONFIRMED_PUBLISHER = "OECD/GPAI"
CONFIRMED_DATE = "2020"
CONFIRMED_CANONICAL_URL = CANONICAL_PREFIX + CONFIRMED_SLUG
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_PUBLISHER_CHARS = 300
MAX_RIGHTS_CHARS = 300
UNKNOWN = "unknown"

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_YEAR = re.compile(r"^\d{4}$")
_LICENSE_KEYS = ("license", "licence", "reuseLicense", "reuseLicence")
_COPYRIGHT_KEYS = ("copyright", "rightsStatement")
_RESERVATION = re.compile(
    r"^(?:all rights reserved\.?|copyright|unknown|none|n/?a|©(?:\s*\d{4})?(?:\s*oecd)?\.?(?:\s*all rights reserved\.?)?)$",
    re.I,
)
_REUSE = re.compile(
    r"(creative commons|\bcc[\s-]?by\b|\bcc0\b|\bcc[\s-]?zero\b|\bogl\b|open government licen[cs]e|public domain)",
    re.I,
)


@dataclass(frozen=True)
class OecdAiEntry:
    """Metadata for one policy initiative. Narrative fields are not copied."""

    title: str
    publisher: str
    date: str
    canonical_url: str
    rights: str

    def as_record(self) -> dict[str, str]:
        return {
            "title": self.title,
            "publisher": self.publisher,
            "date": self.date,
            "canonical_url": self.canonical_url,
            "rights": self.rights,
        }


class OecdAiCollector:
    """Retrieve the one confirmed policy entry. The default fetcher makes one attempt."""

    collector = "oecd_ai"
    platform = "oecd_ai"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, slug: str = CONFIRMED_SLUG) -> OecdAiEntry:
        if slug != CONFIRMED_SLUG:
            raise CollectorFailure("blocked_by_policy", "only the confirmed oecd.ai policy entry is retrieved")
        url = confirmed_entry_url()
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url] or result.url != url:
            raise CollectorFailure("blocked_by_policy", "oecd.ai retrieval does not follow another url")
        if _looks_like_document(result.url) or _payload_is_document(result.body):
            raise CollectorFailure("blocked_by_policy", "policy text was not requested")
        entry = parse_policy(result.body)
        if entry.canonical_url != CONFIRMED_CANONICAL_URL:
            raise CollectorFailure("invalid_content", "oecd.ai entry does not match the confirmed policy")
        return entry


def confirmed_entry_url() -> str:
    """JSON URL for the confirmed initiative. It does not address a file or a list."""
    slug = quote(CONFIRMED_SLUG, safe="")
    url = f"{API_ORIGIN}{ENTRY_PREFIX}{slug}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != f"{ENTRY_PREFIX}{CONFIRMED_SLUG}":
        raise CollectorFailure("unsafe_url", "oecd.ai retrieval stays on the policy initiative api")
    if parsed.query or parsed.fragment or _looks_like_document(url) or parsed.path.rstrip("/").endswith("/public"):
        raise CollectorFailure("blocked_by_policy", "policy files and policy lists are not requested")
    return url


def parse_policy(payload: bytes) -> OecdAiEntry:
    """Read title, publisher, start year, canonical URL, and rights.

    The date comes from ``startYear`` only. Rights come from a licence field,
    or from a copyright field when that text states a reuse licence. Any of
    those that are missing or blank stay ``unknown``.
    """
    if _payload_is_document(payload):
        raise CollectorFailure("blocked_by_policy", "policy text was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "oecd.ai payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed oecd.ai payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "oecd.ai payload is not an object")
    if isinstance(data.get("data"), list) or isinstance(data.get("resultList"), list):
        raise CollectorFailure("blocked_by_policy", "oecd.ai retrieval is one entry, not a policy list")
    return _entry(data)


def _entry(item: dict) -> OecdAiEntry:
    return OecdAiEntry(
        title=_title(item),
        publisher=_publisher(item),
        date=_date(item.get("startYear")),
        canonical_url=_canonical_url(item.get("slug")),
        rights=_rights(item),
    )


def _title(item: dict) -> str:
    for key in ("englishName", "originalName"):
        value = item.get(key)
        if not isinstance(value, str):
            continue
        title = " ".join(value.split())
        if not title:
            continue
        if len(title) > MAX_TITLE_CHARS:
            raise CollectorFailure("content_too_large", "oecd.ai title exceeds limit")
        return title
    raise CollectorFailure("invalid_content", "oecd.ai title is missing")


def _publisher(item: dict) -> str:
    for value in (
        item.get("responsibleOrganisation"),
        item.get("intergovernmentalOrganisation"),
        item.get("gaiinCountry"),
    ):
        name = _org_name(value)
        if name:
            return name
    return UNKNOWN


def _org_name(value: object) -> str | None:
    if isinstance(value, str):
        text = " ".join(value.split())
    elif isinstance(value, dict):
        raw = value.get("name")
        if not isinstance(raw, str) or not raw.strip():
            raw = value.get("englishName")
        if not isinstance(raw, str):
            return None
        text = " ".join(raw.split())
    else:
        return None
    if not text:
        return None
    if len(text) > MAX_PUBLISHER_CHARS:
        raise CollectorFailure("content_too_large", "oecd.ai publisher exceeds limit")
    return text


def _date(value: object) -> str:
    if isinstance(value, bool) or value is None:
        return UNKNOWN
    if isinstance(value, int):
        year = value
    elif isinstance(value, str) and _YEAR.fullmatch(value.strip()):
        year = int(value.strip())
    else:
        return UNKNOWN
    if 1000 <= year <= 9999:
        return f"{year:04d}"
    return UNKNOWN


def _canonical_url(slug: object) -> str:
    if not isinstance(slug, str) or not _SLUG.fullmatch(slug) or len(slug) > 180:
        return UNKNOWN
    if _looks_like_document(slug):
        return UNKNOWN
    try:
        return canonicalize_url(CANONICAL_PREFIX + slug)
    except ValueError:
        return UNKNOWN


def _rights(item: dict) -> str:
    for key in _LICENSE_KEYS:
        text = _rights_text(item, key)
        if text is None or _RESERVATION.fullmatch(text):
            continue
        return text
    for key in _COPYRIGHT_KEYS:
        text = _rights_text(item, key)
        if text is None or _RESERVATION.fullmatch(text) or _REUSE.search(text) is None:
            continue
        return text
    return UNKNOWN


def _rights_text(item: dict, key: str) -> str | None:
    if key not in item:
        return None
    value = item.get(key)
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or "\x00" in text:
        return None
    if len(text) > MAX_RIGHTS_CHARS:
        raise CollectorFailure("content_too_large", "oecd.ai rights label exceeds limit")
    return text


def _payload_is_document(payload: bytes) -> bool:
    stripped = payload.lstrip(b"\xef\xbb\xbf \t\r\n")
    lowered = stripped[:64].lower()
    return lowered.startswith(b"%pdf") or lowered.startswith(b"<") or lowered.startswith(b"<!doctype")


def _looks_like_document(value: str) -> bool:
    lowered = value.lower()
    return ".pdf" in lowered or "/pdf/" in lowered or "/storage/" in lowered or lowered.startswith("%pdf")
