"""Internet Archive item metadata.

Confirms one item from the public metadata API:

https://archive.org/metadata/{identifier}/metadata

The confirmed item is ``micro_IA41152647_0412``, the Internet Archive record
for NASA Technical Memorandum 88268, "Rapid Prototyping Facility for Flight
Research in Artificial-Intelligence-Based Flight Systems Concepts"
(SuDocs NAS 1.15:88268, October 1986). NASA's technical report server
describes that memorandum as a work of the US government. This module does
not download the memorandum or any other item file.

Stored fields are the identifier, title, date, creator names as separate
strings, canonical details URL, mediatype, and a rights label. The date is
the metadata ``date`` only. A missing or unusable date stays ``unknown``;
``publicdate``, ``addeddate``, ``year``, and scan times are not substitutes.
Creator names are not split or merged.

``rights`` is ``us_government_work`` only when the item is in a US
government-document collection and a creator or publisher name is a United
States corporate author (it starts with "United States" as its own words).
Every other item stays ``unknown``.

Descriptions are not stored. A description longer than 400 characters is
never kept in full. Reviews and file bytes are not stored. This collector
is not wired into belief collection, and ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "internet-archive-metadata-0.1.0"
API_HOST = "archive.org"
UNKNOWN = "unknown"
US_GOVERNMENT_WORK = "us_government_work"
MAX_RESPONSE_BYTES = 200_000
MAX_DESCRIPTION_CHARS = 400
MAX_TITLE_CHARS = 2_000
MAX_CREATORS = 50
MAX_NAME_CHARS = 300
MAX_DEPTH = 8
MAX_LIST = 2_000

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
_MEDIATYPE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_FILE_SUFFIXES = (".pdf", ".zip", ".jp2", ".jpg", ".jpeg", ".png", ".txt", ".xml", ".gz", ".torrent", ".djvu")
_GOVERNMENT_COLLECTIONS = frozenset(
    {
        "government-documents",
        "usgovernmentdocuments",
        "us-government-printing-office",
        "us-gpo",
        "usgovernmentmirrors",
    }
)
_BYTE_KEYS = frozenset(
    {
        "filebytes",
        "pdfbytes",
        "contentbytes",
        "imagebytes",
        "itembody",
        "rawbytes",
        "mediabytes",
    }
)
_REVIEW_KEYS = frozenset(
    {
        "reviews",
        "review",
        "reviewbody",
        "reviewtitle",
        "reviewer",
        "reviewdate",
        "reviewoperator",
        "reviewtime",
        "microreview",
    }
)
_FILE_MAGIC = (b"%PDF", b"PK\x03\x04", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*")


@dataclass(frozen=True)
class InternetArchiveItem:
    """Metadata retained for one Internet Archive item."""

    identifier: str
    title: str
    date: str
    creators: tuple[str, ...]
    canonical_url: str
    mediatype: str
    rights: str

    def as_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "title": self.title,
            "date": self.date,
            "creators": list(self.creators),
            "canonical_url": self.canonical_url,
            "mediatype": self.mediatype,
            "rights": self.rights,
        }


class InternetArchiveCollector:
    """Read one item's metadata. Item files are not requested."""

    collector = "internet_archive"
    platform = "internet_archive"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, identifier: str) -> InternetArchiveItem:
        """Fetch metadata for one identifier. Does not follow redirects or file links."""
        ident = _require_identifier(identifier)
        url = metadata_request_url(ident)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if _url_is_file(hop):
                raise CollectorFailure("blocked_by_policy", "internet archive item files are not downloaded")
        if _is_file_bytes(result.body):
            raise CollectorFailure("blocked_by_policy", "internet archive item file bytes are not stored")
        item = parse_item(result.body)
        if item.identifier != ident:
            raise CollectorFailure("invalid_content", "internet archive identifier mismatch")
        return item

    def parse(self, payload: bytes) -> InternetArchiveItem:
        """Parse a metadata JSON body. Performs no I/O."""
        return parse_item(payload)


def metadata_request_url(identifier: str) -> str:
    """JSON metadata URL for one item. This is never a ``/download/`` URL."""
    ident = _require_identifier(identifier)
    url = f"https://{API_HOST}/metadata/{quote(ident, safe='')}/metadata"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.query or parsed.fragment:
        raise CollectorFailure("unsafe_url", "refusing internet archive url")
    if parsed.path != f"/metadata/{ident}/metadata" or _url_is_file(url):
        raise CollectorFailure("blocked_by_policy", "internet archive item files are not downloaded")
    return url


def parse_item(payload: bytes) -> InternetArchiveItem:
    """Return identifier, title, date, creators, canonical URL, mediatype, and rights."""
    if _is_file_bytes(payload):
        raise CollectorFailure("blocked_by_policy", "internet archive item file bytes are not stored")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "internet archive metadata exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed internet archive payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "internet archive payload was not an object")
    _reject_embedded_bytes(data)
    if "error" in data and not any(key in data for key in ("result", "metadata", "identifier")):
        message = data.get("error")
        text = message if isinstance(message, str) and message.strip() else "internet archive item was not found"
        raise CollectorFailure("not_found", " ".join(text.split())[:200])
    metadata = _without_reviews_and_long_description(_metadata_object(data))
    return _item_from_metadata(metadata)


def _item_from_metadata(metadata: Mapping[str, object]) -> InternetArchiveItem:
    identifier = _require_identifier(_one_string(metadata.get("identifier"), "identifier"))
    _check_access_url(identifier, metadata.get("identifier-access"))
    return InternetArchiveItem(
        identifier=identifier,
        title=_title(metadata.get("title")),
        date=_date(metadata.get("date")),
        creators=_creators(metadata.get("creator")),
        canonical_url=_canonical_details_url(identifier),
        mediatype=_mediatype(metadata.get("mediatype")),
        rights=_rights(metadata),
    )


def _metadata_object(data: Mapping[str, object]) -> Mapping[str, object]:
    result = data.get("result")
    nested = data.get("metadata")
    if isinstance(result, dict):
        return result
    if isinstance(nested, dict):
        return nested
    if "identifier" in data or "title" in data:
        return data
    raise CollectorFailure("invalid_content", "internet archive metadata object is missing")


def _without_reviews_and_long_description(metadata: Mapping[str, object]) -> dict[str, object]:
    kept: dict[str, object] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise CollectorFailure("invalid_content", "internet archive metadata keys must be strings")
        if _norm_key(key) in _REVIEW_KEYS:
            continue
        if key == "description" or _norm_key(key) == "description":
            if isinstance(value, str) and len(value) > MAX_DESCRIPTION_CHARS:
                continue
            # Short descriptions are not part of the stored record either.
            continue
        if _norm_key(key) in {"files", "file"}:
            continue
        kept[key] = value
    return kept


def _require_identifier(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "invalid internet archive identifier")
    ident = value.strip()
    if not _IDENTIFIER.fullmatch(ident) or ".." in ident or ident.lower().endswith(_FILE_SUFFIXES):
        raise CollectorFailure("invalid_content", "invalid internet archive identifier")
    if _url_is_file(ident):
        raise CollectorFailure("blocked_by_policy", "internet archive item files are not downloaded")
    return ident


def _one_string(value: object, label: str) -> str:
    if isinstance(value, str):
        parts = _clean_strings([value])
    elif isinstance(value, list):
        parts = _clean_strings(value)
    else:
        parts = []
    distinct = list(dict.fromkeys(parts))
    if len(distinct) != 1:
        raise CollectorFailure("invalid_content", f"internet archive {label} is missing")
    return distinct[0]


def _title(value: object) -> str:
    title = _one_string(value, "title")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "internet archive title exceeds limit")
    return title


def _mediatype(value: object) -> str:
    text = _one_string(value, "mediatype").lower()
    if not _MEDIATYPE.fullmatch(text):
        raise CollectorFailure("invalid_content", "invalid internet archive mediatype")
    return text


def _creators(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        names = _clean_strings([value])
    elif isinstance(value, list):
        names = _clean_strings(value)
    else:
        raise CollectorFailure("invalid_content", "internet archive creator was not a name or list")
    if len(names) > MAX_CREATORS:
        raise CollectorFailure("content_too_large", "internet archive creator list exceeds limit")
    for name in names:
        if len(name) > MAX_NAME_CHARS:
            raise CollectorFailure("content_too_large", "internet archive creator name exceeds limit")
    return tuple(dict.fromkeys(names))


def _clean_strings(values: list[object]) -> list[str]:
    names: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = " ".join(value.split())
        if text:
            names.append(text)
    return names


def _date(value: object) -> str:
    if value is None:
        return UNKNOWN
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [item for item in value if isinstance(item, str)]
    else:
        return UNKNOWN
    normalized = [_normalize_date(item) for item in values if item.strip()]
    if not normalized:
        return UNKNOWN
    distinct = list(dict.fromkeys(normalized))
    if len(distinct) != 1:
        return UNKNOWN
    return distinct[0]


def _normalize_date(value: str) -> str:
    text = value.strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    match = _DATE.fullmatch(text)
    if match is None:
        return UNKNOWN
    year = int(match.group(1))
    if year < 1000 or year > 9999:
        return UNKNOWN
    month = match.group(2)
    day = match.group(3)
    if month is None:
        return f"{year:04d}"
    if not 1 <= int(month) <= 12:
        return UNKNOWN
    if day is None:
        return f"{year:04d}-{month}"
    if not 1 <= int(day) <= 31:
        return UNKNOWN
    return f"{year:04d}-{month}-{day}"


def _rights(metadata: Mapping[str, object]) -> str:
    collections = [_collection_name(name) for name in _party_names(metadata.get("collection"))]
    if not any(name in _GOVERNMENT_COLLECTIONS for name in collections):
        return UNKNOWN
    parties = _party_names(metadata.get("creator")) + _party_names(metadata.get("publisher"))
    if any(_is_united_states_corporate_name(name) for name in parties):
        return US_GOVERNMENT_WORK
    return UNKNOWN


def _party_names(value: object) -> list[str]:
    if isinstance(value, str):
        return _clean_strings([value])
    if isinstance(value, list):
        return _clean_strings(value)
    return []


def _collection_name(value: str) -> str:
    return value.casefold()


def _is_united_states_corporate_name(name: str) -> bool:
    text = " ".join(name.split()).casefold()
    return text == "united states" or text.startswith("united states ") or text.startswith("united states.")


def _canonical_details_url(identifier: str) -> str:
    url = f"https://{API_HOST}/details/{identifier}"
    try:
        canonical = canonicalize_url(url)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "invalid internet archive canonical url") from exc
    if canonical != url:
        raise CollectorFailure("invalid_content", "invalid internet archive canonical url")
    return canonical


def _check_access_url(identifier: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        return
    text = value.strip()
    if _url_is_file(text):
        raise CollectorFailure("blocked_by_policy", "internet archive item files are not downloaded")
    if _details_identifier(text) != identifier:
        raise CollectorFailure("invalid_content", "identifier does not match canonical url")


def _details_identifier(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {API_HOST, "www.archive.org"} or parsed.username or parsed.password:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "details":
        return parts[1]
    return None


def _url_is_file(value: str) -> bool:
    lowered = value.lower()
    if "/download/" in lowered or lowered.endswith(_FILE_SUFFIXES):
        return True
    parsed = urlparse(value)
    return any(part.lower() == "download" for part in parsed.path.split("/"))


def _is_file_bytes(payload: bytes) -> bool:
    head = payload.lstrip()[:16]
    return head.startswith(_FILE_MAGIC)


def _reject_embedded_bytes(node: object, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise CollectorFailure("invalid_content", "internet archive metadata is too nested")
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                raise CollectorFailure("invalid_content", "internet archive metadata keys must be strings")
            if _norm_key(key) in _BYTE_KEYS and _present(value):
                raise CollectorFailure("blocked_by_policy", "internet archive item file bytes are not stored")
            _reject_embedded_bytes(value, depth + 1)
        return
    if isinstance(node, list):
        if len(node) > MAX_LIST:
            raise CollectorFailure("content_too_large", "internet archive metadata is too large")
        for item in node:
            _reject_embedded_bytes(item, depth + 1)
        return
    if isinstance(node, str) and _data_url_is_file(node):
        raise CollectorFailure("blocked_by_policy", "internet archive item file bytes are not stored")


def _data_url_is_file(value: str) -> bool:
    if not value.startswith("data:"):
        return False
    header = value[5:40].lower()
    return header.startswith(("application/pdf", "application/octet-stream", "application/zip", "image/"))


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (bytes, list, dict)):
        return len(value) > 0
    return True


def _norm_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())
