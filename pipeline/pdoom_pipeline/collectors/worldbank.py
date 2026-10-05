"""World Bank document metadata.

Confirms one public Documents & Reports record, World Development Report
2026: The Promise of Artificial Intelligence. The JSON API is documented at
https://documents.worldbank.org/en/publication/documents-reports/api and is
served at search.worldbank.org. The call reads that one metadata record.
It does not download a PDF, a text rendition, or the abstract.

Stored fields are the document id, title, document date, canonical URL, and
rights. The date is the calendar date on ``docdt``. Disclosure, storage, and
modification timestamps are not substituted. Rights stay unknown unless the
record states a reuse licence. Security classification "Public", disclosure
status, and the public document page are not a licence.

This module is not imported by belief collection or any job. ``runner_wired``
stays false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "worldbank-metadata-0.1.0"
API_ORIGIN = "https://search.worldbank.org"
API_HOST = "search.worldbank.org"
API_PATH = "/api/v3/wds"
DOCUMENTS_HOST = "documents.worldbank.org"
FIELDS = "id,display_title,docdt,url,guid,seccl,disclstat"
CONFIRMED_DOCUMENT_ID = "40125825"
CONFIRMED_GUID = "099090426145520570"
CONFIRMED_TITLE = "World Development Report 2026: The Promise of Artificial Intelligence"
CONFIRMED_DATE = "2026-08-04"
CONFIRMED_CANONICAL_URL = f"https://{DOCUMENTS_HOST}/curated/en/{CONFIRMED_GUID}"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_RIGHTS_CHARS = 300
UNKNOWN = "unknown"

_DOCUMENT_ID = re.compile(r"^[0-9]{5,12}$")
_DOCDT = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$"
)
_LICENSE_KEYS = ("license", "licence", "reuseLicense", "reuseLicence")
_COPYRIGHT_KEYS = ("copyright", "rights", "rightsStatement")
_REUSE = re.compile(
    r"(creative\s*commons|\bcc(?:[\s-]?by(?:[\s-]?(?:nc|nd|sa|igo))*|[\s-]?(?:0|zero))\b|\bpublic domain\b|\bopen government licen[cs]e\b|\bogl\b)",
    re.I,
)
_DOCUMENT_PATHS = ("/curated/", "/en/publication/documents-reports/documentdetail/")


@dataclass(frozen=True)
class WorldBankDocument:
    """Metadata for one public document. The abstract and file bytes are not copied."""

    document_id: str
    title: str
    date: str
    canonical_url: str
    rights: str

    def as_record(self) -> dict[str, str]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "date": self.date,
            "canonical_url": self.canonical_url,
            "rights": self.rights,
        }


class WorldBankCollector:
    """Retrieve the one confirmed document. The default fetcher makes one attempt."""

    collector = "worldbank"
    platform = "worldbank"
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

    def retrieve(self, document_id: str = CONFIRMED_DOCUMENT_ID) -> WorldBankDocument:
        url = document_request_url(document_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        hops = result.requested_urls or [result.url]
        if result.url != url or any(not _is_metadata_url(hop) for hop in hops):
            raise CollectorFailure("blocked_by_policy", "world bank retrieval does not follow another url")
        if _payload_is_file(result.body) or "pdf" in result.headers.get("content-type", "").lower():
            raise CollectorFailure("blocked_by_policy", "world bank pdf is not downloaded")
        document = parse_document(result.body)
        if document.document_id != CONFIRMED_DOCUMENT_ID or document.canonical_url != CONFIRMED_CANONICAL_URL:
            raise CollectorFailure("invalid_content", "world bank document does not match the confirmed record")
        return document


def document_request_url(document_id: str = CONFIRMED_DOCUMENT_ID) -> str:
    """JSON URL for the confirmed document. It does not address a PDF or a text file."""
    if not isinstance(document_id, str) or _looks_like_file(document_id) or "://" in document_id.lower():
        raise CollectorFailure("blocked_by_policy", "world bank pdf and text files are not downloaded")
    cleaned = document_id.strip()
    if cleaned != CONFIRMED_DOCUMENT_ID:
        raise CollectorFailure("blocked_by_policy", "only the confirmed world bank document is retrieved")
    url = f"{API_ORIGIN}{API_PATH}?format=json&rows=1&id={cleaned}&fl={FIELDS}"
    if not _is_metadata_url(url):
        raise CollectorFailure("unsafe_url", "world bank retrieval stays on the documents metadata api")
    return url


def parse_document(payload: bytes) -> WorldBankDocument:
    """Read document id, title, document date, canonical URL, and rights.

    The date comes from ``docdt`` only. Rights come from a licence or copyright
    field when that text states a reuse licence. A public page, "Public", and
    "Disclosed" stay ``unknown``. Abstracts and file URLs are ignored.
    """
    if _payload_is_file(payload):
        raise CollectorFailure("blocked_by_policy", "world bank pdf is not downloaded")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "world bank payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed world bank payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "world bank payload is not an object")
    return _document(_one_document(data))


def _one_document(data: dict) -> dict:
    if "documents" in data:
        return _from_envelope(data)
    if "id" in data or "display_title" in data:
        return data
    raise CollectorFailure("invalid_content", "world bank payload missing document")


def _from_envelope(data: dict) -> dict:
    documents = data.get("documents")
    if not isinstance(documents, dict):
        raise CollectorFailure("invalid_content", "world bank documents field was not an object")
    total = data.get("total")
    if total not in (1, "1"):
        error = "blocked_by_policy" if isinstance(total, int) and total > 1 else "invalid_content"
        raise CollectorFailure(error, "world bank retrieval is one document")
    chosen: list[tuple[str, dict]] = []
    for key, item in documents.items():
        if key == "facets":
            continue
        if not isinstance(item, dict) or not item:
            continue
        chosen.append((key, item))
    if len(chosen) != 1:
        error = "blocked_by_policy" if len(chosen) > 1 else "invalid_content"
        raise CollectorFailure(error, "world bank retrieval is one document")
    key, item = chosen[0]
    document_id = _document_id(item.get("id"))
    if key not in {document_id, f"D{document_id}"}:
        raise CollectorFailure("invalid_content", "world bank document id mismatch")
    return item


def _document(item: dict) -> WorldBankDocument:
    return WorldBankDocument(
        document_id=_document_id(item.get("id")),
        title=_title(item),
        date=_date(item.get("docdt")),
        canonical_url=_canonical_url(item.get("url")),
        rights=_rights(item),
    )


def _document_id(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "world bank document id is missing")
    text = value.strip()
    if not _DOCUMENT_ID.fullmatch(text) or _looks_like_file(text):
        raise CollectorFailure("invalid_content", "world bank document id is missing")
    return text


def _title(item: dict) -> str:
    value = item.get("display_title")
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "world bank title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "world bank title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "world bank title exceeds limit")
    return title


def _date(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    match = _DOCDT.fullmatch(value.strip())
    if match is None:
        return UNKNOWN
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not (1000 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= 31):
        return UNKNOWN
    if match.group(4) is not None:
        hour, minute, second = int(match.group(4)), int(match.group(5)), int(match.group(6))
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            return UNKNOWN
    return f"{year:04d}-{month:02d}-{day:02d}"


def _canonical_url(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if not text or _looks_like_file(text):
        return UNKNOWN
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() not in {"http", "https"} or host != DOCUMENTS_HOST:
        return UNKNOWN
    if parsed.username or parsed.password:
        return UNKNOWN
    try:
        canonical = canonicalize_url(parsed._replace(scheme="https").geturl())
    except ValueError:
        return UNKNOWN
    checked = urlparse(canonical)
    if checked.scheme != "https" or checked.hostname != DOCUMENTS_HOST or checked.query or checked.fragment:
        return UNKNOWN
    if _looks_like_file(canonical) or not checked.path.startswith(_DOCUMENT_PATHS):
        return UNKNOWN
    return canonical


def _rights(item: dict) -> str:
    for key in _LICENSE_KEYS + _COPYRIGHT_KEYS:
        text = _rights_text(item, key)
        if text is None or _REUSE.search(text) is None or _is_public_page(text):
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
        raise CollectorFailure("content_too_large", "world bank rights label exceeds limit")
    return text


def _is_public_page(text: str) -> bool:
    """A document page URL is not a reuse licence, even when it shares the host."""
    if _REUSE.search(text) is None:
        return False
    parsed = urlparse(text.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    return (parsed.hostname or "").lower() == DOCUMENTS_HOST


def _is_metadata_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != API_PATH:
        return False
    if parsed.fragment or _looks_like_file(url):
        return False
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return (
        query.get("format") == "json"
        and query.get("rows") == "1"
        and query.get("id") == CONFIRMED_DOCUMENT_ID
        and query.get("fl") == FIELDS
        and set(query) == {"format", "rows", "id", "fl"}
    )


def _payload_is_file(payload: bytes) -> bool:
    stripped = payload.lstrip(b"\xef\xbb\xbf \t\r\n")
    lowered = stripped[:64].lower()
    return lowered.startswith(b"%pdf") or lowered.startswith(b"<") or lowered.startswith(b"<!doctype")


def _looks_like_file(value: str) -> bool:
    lowered = value.lower().split("#", 1)[0]
    path = lowered.split("?", 1)[0]
    return (
        path.endswith(".pdf")
        or path.endswith(".txt")
        or path.endswith(".zip")
        or "/pdf/" in path
        or "/text/" in path
        or lowered.startswith("%pdf")
    )
