"""medRxiv preprint metadata.

Retrieves one record from the public details API at https://api.medrxiv.org/.
The call is JSON metadata. Abstracts, JATS XML, and PDFs are not requested
or retained. A license is copied only when the details object includes one;
otherwise it stays unknown.

This module is not imported by the belief runner. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "medrxiv-0.1.0"
API_ORIGIN = "https://api.medrxiv.org"
CONTENT_ORIGIN = "https://www.medrxiv.org"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_AUTHORS = 200
MAX_AUTHOR_CHARS = 300
MAX_TITLE_CHARS = 2_000
MAX_LICENSE_CHARS = 80

_DOI = re.compile(r"^10\.1101/\d{4}\.\d{2}\.\d{2}\.\d+$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


@dataclass(frozen=True)
class MedrxivPreprint:
    """Bibliographic fields for one medRxiv preprint. Authors are not merged."""

    title: str
    authors: tuple[str, ...]
    date: str
    doi: str
    version: str
    canonical_url: str
    license: str

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "date": self.date,
            "doi": self.doi,
            "version": self.version,
            "canonical_url": self.canonical_url,
            "license": self.license,
        }


class MedrxivCollector:
    """Fetch and parse one medRxiv details record. Not wired into belief collection."""

    collector = "medrxiv"
    platform = "medrxiv"
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

    def retrieve(self, doi: str) -> MedrxivPreprint:
        requested = request_doi(doi)
        url = details_url(requested)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        hops = result.requested_urls or [result.url]
        for hop in hops:
            if not _is_details_url(hop):
                raise CollectorFailure("blocked_by_policy", "medrxiv collector only reads details metadata")
        if _payload_is_pdf(result.body) or "pdf" in result.headers.get("content-type", "").lower():
            raise CollectorFailure("blocked_by_policy", "medrxiv pdf is not downloaded")
        preprint = parse_medrxiv_preprint(result.body)
        if preprint.doi != requested:
            raise CollectorFailure("invalid_content", "medrxiv doi mismatch")
        return preprint


def details_url(doi: str) -> str:
    """JSON details URL for one medRxiv DOI. This is not a content or PDF URL."""
    bare = request_doi(doi)
    url = f"{API_ORIGIN}/details/medrxiv/{bare}/na/json"
    if not _is_details_url(url):
        raise CollectorFailure("unsafe_url", "medrxiv retrieval stays on the details api")
    return url


def request_doi(value: str) -> str:
    text = (value or "").strip()
    lowered = text.lower()
    if _looks_like_full_text(lowered):
        raise CollectorFailure("blocked_by_policy", "medrxiv pdf and full text are not downloaded")
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            lowered = text.lower()
            break
    if lowered.startswith(("http://", "https://")) or _looks_like_full_text(lowered):
        raise CollectorFailure("blocked_by_policy", "medrxiv retrieval uses the details api")
    if not _DOI.fullmatch(text):
        raise CollectorFailure("invalid_content", "invalid medrxiv doi")
    return text


def parse_medrxiv_preprint(payload: bytes) -> MedrxivPreprint:
    """Read title, separate author names, date, DOI, version, URL, and license.

    The abstract, JATS path, and any PDF link in the payload are ignored.
    Author names are split on semicolons and are not merged or deduplicated.
    """
    if _payload_is_pdf(payload):
        raise CollectorFailure("blocked_by_policy", "medrxiv pdf is not downloaded")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "medrxiv payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed medrxiv payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "medrxiv payload was not an object")
    _require_ok(data)
    item = _one_preprint(data.get("collection"))
    server = item.get("server")
    if isinstance(server, str) and server.strip().lower() != "medrxiv":
        raise CollectorFailure("invalid_content", "not a medrxiv preprint")
    doi = _response_doi(item.get("doi"))
    version = _version(item.get("version"))
    return MedrxivPreprint(
        title=_title(item.get("title")),
        authors=_authors(item.get("authors")),
        date=_date(item.get("date")),
        doi=doi,
        version=version,
        canonical_url=_canonical_url(doi, version),
        license=_license(item),
    )


def _is_details_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.medrxiv.org":
        return False
    if parsed.query or parsed.fragment:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 5 or parts[0] != "details" or parts[1] != "medrxiv":
        return False
    if parts[-2:] != ["na", "json"]:
        return False
    doi = "/".join(parts[2:-2])
    if not _DOI.fullmatch(doi):
        return False
    return not _looks_like_full_text(parsed.path.lower())


def _require_ok(data: dict) -> None:
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        raise CollectorFailure("invalid_content", "medrxiv payload missing messages")
    statuses: list[object] = []
    for message in messages:
        if isinstance(message, dict):
            statuses.append(message.get("status"))
    if "ok" in statuses:
        return
    if any(isinstance(status, str) and "no post" in status.lower() for status in statuses):
        raise CollectorFailure("not_found", "medrxiv preprint was not found")
    raise CollectorFailure("invalid_content", "medrxiv status was not ok")


def _one_preprint(collection: object) -> dict:
    """Return one version. Later versions do not absorb earlier author lists."""
    if not isinstance(collection, list) or not collection or not all(isinstance(item, dict) for item in collection):
        raise CollectorFailure("invalid_content", "medrxiv collection did not contain a preprint")
    if len(collection) == 1:
        return collection[0]
    ranked: list[tuple[int, dict]] = []
    for item in collection:
        version = _version(item.get("version"))
        if version == UNKNOWN:
            continue
        ranked.append((int(version), item))
    if not ranked:
        raise CollectorFailure("invalid_content", "medrxiv versions are ambiguous")
    best = max(number for number, _item in ranked)
    chosen = [item for number, item in ranked if number == best]
    if len(chosen) != 1:
        raise CollectorFailure("invalid_content", "medrxiv versions are ambiguous")
    return chosen[0]


def _response_doi(value: object) -> str:
    text = str(value or "").strip()
    if not _DOI.fullmatch(text):
        raise CollectorFailure("invalid_content", "medrxiv preprint missing doi")
    return text


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "medrxiv preprint missing title")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "medrxiv preprint missing title")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "medrxiv title exceeds limit")
    return title


def _authors(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "medrxiv authors were not a string of names")
    names: list[str] = []
    for part in value.split(";"):
        name = " ".join(part.split())
        if not name:
            continue
        if len(name) > MAX_AUTHOR_CHARS:
            raise CollectorFailure("content_too_large", "medrxiv author name exceeds limit")
        names.append(name)
        if len(names) > MAX_AUTHORS:
            raise CollectorFailure("content_too_large", "medrxiv author list exceeds limit")
    return tuple(names)


def _date(value: object) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return UNKNOWN
    year_text, month_text, day_text = value.split("-")
    year, month, day = int(year_text), int(month_text), int(day_text)
    if year < 2019 or year > 2100 or not 1 <= month <= 12 or not 1 <= day <= 31:
        return UNKNOWN
    return value


def _version(value: object) -> str:
    if isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return UNKNOWN
    if not text.isdigit():
        return UNKNOWN
    number = int(text)
    if number < 1 or number > 99:
        return UNKNOWN
    return str(number)


def _license(item: dict) -> str:
    if "license" not in item:
        return UNKNOWN
    value = item.get("license")
    if not isinstance(value, str):
        return UNKNOWN
    text = " ".join(value.split())
    if not text or text.upper() in {"NA", "N/A", "NONE", "NULL"}:
        return UNKNOWN
    if len(text) > MAX_LICENSE_CHARS:
        raise CollectorFailure("content_too_large", "medrxiv license exceeds limit")
    return text


def _canonical_url(doi: str, version: str) -> str:
    suffix = f"v{version}" if version != UNKNOWN else ""
    raw = f"{CONTENT_ORIGIN}/content/{doi}{suffix}"
    if _looks_like_full_text(raw.lower()):
        raise CollectorFailure("blocked_by_policy", "medrxiv pdf and full text are not stored")
    try:
        canonical = canonicalize_url(raw)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "invalid medrxiv canonical url") from exc
    parsed = urlparse(canonical)
    if parsed.scheme != "https" or parsed.hostname != "www.medrxiv.org":
        raise CollectorFailure("invalid_content", "invalid medrxiv canonical url")
    if not parsed.path.startswith("/content/") or _looks_like_full_text(parsed.path.lower()):
        raise CollectorFailure("blocked_by_policy", "medrxiv pdf and full text are not stored")
    return canonical


def _looks_like_full_text(value: str) -> bool:
    lowered = value.lower()
    return (
        ".pdf" in lowered
        or "/pdf" in lowered
        or lowered.endswith(".xml")
        or ".source.xml" in lowered
        or "/jats" in lowered
        or lowered.startswith("%pdf")
    )


def _payload_is_pdf(payload: bytes) -> bool:
    return payload.lstrip().startswith(b"%PDF")
