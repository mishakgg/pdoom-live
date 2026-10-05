"""Mastodon public status metadata.

Reads one public status and keeps its URL, account display name, published
time, and a short excerpt of the status text already in the payload. A
missing or unusable ``created_at`` stays ``unknown``.

The request is one ``/api/v1/statuses/:id`` lookup. Media bytes, timeline
pages, and conversation threads are refused. This module is not imported by
the belief runner or a job.

Text in the payload is data, not instructions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, unquote, urlparse

from pdoom_pipeline.contracts import excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import TRACKING_PARAMS, canonicalize_url, hostname_is_blocked

COLLECTOR_VERSION = "mastodon-metadata-0.1.0"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_EXCERPT_CHARS = 500
MAX_DISPLAY_NAME_CHARS = 200

_STATUS_ID = re.compile(r"^[0-9]{1,20}$")
_MEDIA_EXT = re.compile(
    r"\.(?:png|jpe?g|gif|webp|avif|mp4|m4v|webm|mov|mp3|m4a|wav|ogg|flac|aac|opus)$",
    re.I,
)
_DATA_MEDIA = re.compile(br"data:(?:image|video|audio)/", re.I)
_PAGING_PARAMS = frozenset({"max_id", "since_id", "min_id", "limit", "page", "offset", "cursor"})
_REFUSED_PATH_PARTS = frozenset(
    {
        "media_proxy",
        "timelines",
        "context",
        "favourited_by",
        "reblogged_by",
        "history",
        "media",
    }
)
_BLOCK_TAGS = frozenset({"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "blockquote"})


@dataclass(frozen=True)
class MastodonStatusMetadata:
    """One public status, reduced to the fields this reader keeps."""

    status_url: str
    display_name: str
    published_at: str
    excerpt: str

    def as_dict(self) -> dict[str, str]:
        return {
            "status_url": self.status_url,
            "display_name": self.display_name,
            "published_at": self.published_at,
            "excerpt": self.excerpt,
        }


class MastodonMetadataCollector:
    """Retrieve or parse one public status. The default fetcher makes one attempt."""

    collector = "mastodon_metadata"
    platform = "mastodon"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, status_url: str) -> MastodonStatusMetadata:
        """Fetch one status JSON document. Media, timeline, and thread URLs are refused."""
        api_url = status_request_url(status_url)
        result = self.fetcher.get(api_url, headers={"Accept": "application/json"})
        if result.requested_urls != [api_url]:
            raise CollectorFailure("blocked_by_policy", "refusing a redirected mastodon fetch")
        record = self.parse(result.body)
        if _status_id_from_url(record.status_url) != _status_id_from_url(api_url):
            raise CollectorFailure("invalid_content", "mastodon status id mismatch")
        return record

    def parse(self, payload: bytes) -> MastodonStatusMetadata:
        """Parse one status object. Performs no I/O."""
        return parse_status(payload)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name in {"script", "style"}:
            self._skip += 1
        if name in _BLOCK_TAGS or name == "br":
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name in {"script", "style"} and self._skip:
            self._skip -= 1
        if name in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def status_request_url(status_url: str) -> str:
    """Return the single status API URL for a public web, ActivityPub, or API URL."""
    parsed, parts = _parsed_status_target(status_url)
    status_id = _status_id_from_parts(parts)
    if status_id is None:
        raise CollectorFailure("invalid_content", "not a single mastodon status url")
    host = parsed.hostname.lower().rstrip(".")
    port = parsed.port
    netloc = host if port in {None, 443} else f"{host}:{port}"
    return f"https://{netloc}/api/v1/statuses/{status_id}"


def parse_status(payload: bytes) -> MastodonStatusMetadata:
    """Read one public status object from JSON bytes."""
    if isinstance(payload, bytearray):
        payload = bytes(payload)
    if not isinstance(payload, bytes):
        raise CollectorFailure("invalid_content", "mastodon status payload must be bytes")
    if _is_media_bytes(payload) or _DATA_MEDIA.search(payload):
        raise CollectorFailure("blocked_by_policy", "mastodon media was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "mastodon status payload exceeds 200KB")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed mastodon payload: {exc}") from exc
    if isinstance(data, list) or (isinstance(data, dict) and isinstance(data.get("statuses"), list)):
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon timeline page")
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "mastodon status payload was not an object")
    if "ancestors" in data or "descendants" in data:
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon thread")
    visibility = data.get("visibility")
    if not isinstance(visibility, str):
        raise CollectorFailure("invalid_content", "mastodon status visibility is missing")
    if visibility != "public":
        raise CollectorFailure("blocked_by_policy", "refusing a non-public mastodon status")
    status_url, _status_id = _require_status_url(data)
    return MastodonStatusMetadata(
        status_url=status_url,
        display_name=_display_name(data.get("account")),
        published_at=_published_at(data.get("created_at")),
        excerpt=_status_excerpt(data.get("content")),
    )


def _parsed_status_target(status_url: str):
    if not isinstance(status_url, str) or not status_url.strip():
        raise CollectorFailure("invalid_content", "mastodon status url is missing")
    raw = status_url.strip()
    if "\\" in raw:
        raise CollectorFailure("unsafe_url", "refusing mastodon url")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname:
        raise CollectorFailure("unsafe_url", "mastodon status url must be https")
    if parsed.username or parsed.password:
        raise CollectorFailure("unsafe_url", "mastodon status url has userinfo")
    if parsed.fragment:
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon url fragment")
    host = parsed.hostname.lower().rstrip(".")
    if hostname_is_blocked(host):
        raise CollectorFailure("unsafe_url", "blocked mastodon host")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    names = [key.lower() for key, _value in pairs]
    if any(name in _PAGING_PARAMS for name in names):
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon timeline page")
    if any(name not in TRACKING_PARAMS for name in names):
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon query")
    if _MEDIA_EXT.search(parsed.path or ""):
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon media url")
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise CollectorFailure("unsafe_url", "refusing mastodon url")
    lowered = [part.lower() for part in parts]
    if any(part in _REFUSED_PATH_PARTS for part in lowered):
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon media, timeline, or thread path")
    if "accounts" in lowered and "statuses" in lowered:
        raise CollectorFailure("blocked_by_policy", "refusing a mastodon timeline page")
    return parsed, parts


def _require_status_url(data: dict) -> tuple[str, str]:
    web = _canonical_status(data.get("url"))
    activity = _canonical_status(data.get("uri"))
    if web is None and activity is None:
        raise CollectorFailure("invalid_content", "mastodon status url is missing")
    if web is not None and activity is not None and web[1] != activity[1]:
        raise CollectorFailure("invalid_content", "mastodon status url does not match uri")
    chosen = web if web is not None else activity
    if chosen is None:
        raise CollectorFailure("invalid_content", "mastodon status url is missing")
    status_url, status_id = chosen
    payload_id = data.get("id")
    if not isinstance(payload_id, str) or payload_id != status_id:
        raise CollectorFailure("invalid_content", "mastodon status id does not match url")
    return status_url, status_id


def _canonical_status(value: object) -> tuple[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "mastodon status url is invalid")
    text = value.strip()
    if not text:
        return None
    try:
        canonical = canonicalize_url(text)
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "mastodon status url is invalid") from exc
    if urlparse(canonical).scheme != "https":
        raise CollectorFailure("invalid_content", "mastodon status url must be https")
    status_id = _status_id_from_url(canonical)
    if status_id is None:
        raise CollectorFailure("invalid_content", "mastodon status url is not a single status")
    return canonical, status_id


def _status_id_from_url(url: str) -> str | None:
    parts = [unquote(part) for part in urlparse(url).path.split("/") if part]
    return _status_id_from_parts(parts)


def _status_id_from_parts(parts: list[str]) -> str | None:
    lowered = [part.lower() for part in parts]
    if len(parts) == 4 and lowered[:3] == ["api", "v1", "statuses"] and _STATUS_ID.fullmatch(parts[3]):
        return parts[3]
    if len(parts) == 4 and lowered[0] == "users" and lowered[2] == "statuses" and _STATUS_ID.fullmatch(parts[3]):
        if parts[1] and parts[1] not in {".", ".."}:
            return parts[3]
    if len(parts) == 2 and parts[0].startswith("@") and _STATUS_ID.fullmatch(parts[1]):
        user = parts[0][1:]
        if user and "/" not in user and user not in {".", ".."}:
            return parts[1]
    return None


def _display_name(account: object) -> str:
    if not isinstance(account, dict):
        return UNKNOWN
    raw = account.get("display_name")
    if not isinstance(raw, str):
        return UNKNOWN
    text = " ".join(raw.split())
    if not text:
        return UNKNOWN
    if len(text) > MAX_DISPLAY_NAME_CHARS:
        raise CollectorFailure("content_too_large", "mastodon display name exceeds limit")
    return text


def _published_at(value: object) -> str:
    """Keep a timezone-aware status ``created_at``. Anything else stays unknown."""
    if not isinstance(value, str) or not value or len(value) > 40 or value != value.strip():
        return UNKNOWN
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return UNKNOWN
    if parsed.tzinfo is None:
        return UNKNOWN
    return value


def _status_excerpt(value: object) -> str:
    """Excerpt status content. Nested boost, quote, and preview bodies are not read."""
    if not isinstance(value, str) or not value.strip():
        return UNKNOWN
    if len(value.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "mastodon status content exceeds limit")
    text = _html_text(value)
    if not text:
        return UNKNOWN
    short, _truncated = excerpt(text, MAX_EXCERPT_CHARS)
    return short or UNKNOWN


def _html_text(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except RecursionError as exc:
        raise CollectorFailure("invalid_content", "mastodon status content is too nested") from exc
    return " ".join("".join(parser.parts).split())


def _is_media_bytes(blob: bytes) -> bool:
    if blob.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"ID3", b"OggS", b"fLaC")):
        return True
    if len(blob) >= 12 and blob[4:8] == b"ftyp":
        return True
    return blob.startswith(b"RIFF") and len(blob) >= 12 and blob[8:12] in {b"WAVE", b"AVI ", b"WEBP"}
