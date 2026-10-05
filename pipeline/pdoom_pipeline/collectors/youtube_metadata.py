"""Public YouTube video metadata.

Accepts one metadata record and returns its video id, title, channel name,
published time, and canonical watch URL. Media bytes, caption transcripts,
and download URLs are refused.

This module does not call the YouTube API and does not download video,
audio, or caption tracks. Text in the record is data, not instructions.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, NoReturn
from urllib.parse import parse_qsl, unquote, urlparse

from pdoom_pipeline.errors import (
    BLOCKED_BY_POLICY,
    CONTENT_TOO_LARGE,
    INVALID_CONTENT,
    CollectorFailure,
)
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "youtube-metadata-0.1.0"
MAX_BYTES = 65_536
MAX_DEPTH = 8
MAX_NODES = 400
MAX_STRING = 8_000
MAX_TITLE = 200
MAX_CHANNEL = 200

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_GOOGLEVIDEO_URL = re.compile(r"(?:https?:)?//[^/\s\"']*googlevideo\.com", re.I)
_MEDIA_EXT = re.compile(
    r"\.(?:mp4|m4v|webm|mkv|mov|m4a|mp3|wav|flac|aac|ogg|opus|m3u8|ts)(?:$|[?#])",
    re.I,
)
_VTT = re.compile(r"^\ufeff?\s*WEBVTT\b", re.I)
_SRT_CUE = re.compile(
    r"(?:^|\n)\s*(?:\d+\s*\n\s*)?\d{2}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[,.]\d{3}"
)
_TIMED_TEXT = re.compile(r"<\s*text\b[^>]*\bstart\s*=", re.I)
_TRANSCRIPT_TAG = re.compile(r"<\s*transcript\b", re.I)
_DATA_MEDIA = re.compile(r"^data:(?:video|audio)/", re.I)
_BASE64_TEXT = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")

_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
        "youtu.be",
    }
)
_CAPTION_KEYS = frozenset(
    {
        "transcript",
        "transcripts",
        "caption",
        "captions",
        "captiontrack",
        "captiontracks",
        "timedtext",
        "subtitle",
        "subtitles",
        "webvtt",
        "closedcaption",
        "closedcaptions",
        "captiontranscript",
        "srt",
    }
)
_MEDIA_KEYS = frozenset(
    {
        "mediabytes",
        "videobytes",
        "audiobytes",
        "rawmedia",
        "rawvideo",
        "rawaudio",
        "mediabase64",
        "videobase64",
        "audiobase64",
        "contentbytes",
    }
)
_DOWNLOAD_KEYS = frozenset(
    {
        "downloadurl",
        "mediadownloadurl",
        "videodownloadurl",
        "audiodownloadurl",
        "streamurl",
        "streamingurl",
        "contenturl",
        "streamingdata",
        "adaptiveformats",
        "signaturecipher",
    }
)
_CUE_TEXT_KEYS = frozenset({"text", "utf8"})
_CUE_TIME_KEYS = frozenset(
    {"start", "startms", "tstartms", "offset", "dur", "duration", "end", "endms"}
)
_VIDEO_ID_PATHS = (
    ("video_id",),
    ("videoId",),
    ("id",),
    ("snippet", "resourceId", "videoId"),
)
_TITLE_PATHS = (
    ("title",),
    ("snippet", "title"),
    ("name",),
)
_CHANNEL_PATHS = (
    ("channel_name",),
    ("channelName",),
    ("channel_title",),
    ("channelTitle",),
    ("snippet", "channelTitle"),
    ("author_name",),
    ("authorName",),
)
_PUBLISHED_PATHS = (
    ("published_at",),
    ("publishedAt",),
    ("published_time",),
    ("publishedTime",),
    ("published",),
    ("snippet", "publishedAt"),
    ("uploadDate",),
)
_URL_PATHS = (
    ("canonical_url",),
    ("canonicalUrl",),
    ("watch_url",),
    ("watchUrl",),
    ("url",),
)


def _fail(error_class: str, message: str) -> NoReturn:
    raise CollectorFailure(error_class, message)


@dataclass(frozen=True)
class YouTubeVideoMetadata:
    video_id: str
    title: str
    channel_name: str
    published_at: str
    canonical_url: str

    def as_dict(self) -> dict[str, str]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "channel_name": self.channel_name,
            "published_at": self.published_at,
            "canonical_url": self.canonical_url,
        }


class YouTubeMetadataCollector:
    """Parse one public video metadata record. No network and no media."""

    collector = "youtube_metadata"
    platform = "youtube"
    collector_version = COLLECTOR_VERSION

    def parse(self, payload: bytes | str | Mapping[str, Any]) -> YouTubeVideoMetadata:
        record = _load_record(payload)
        _reject_disallowed(record)
        return _metadata_from_record(record)


def _load_record(payload: bytes | str | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(payload, (bytes, bytearray)):
        blob = bytes(payload)
        if _is_media_bytes(blob):
            _fail(BLOCKED_BY_POLICY, "youtube metadata contains media bytes")
        if len(blob) > MAX_BYTES:
            _fail(CONTENT_TOO_LARGE, "youtube metadata record is too large")
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            _fail(INVALID_CONTENT, "youtube metadata record is not utf-8 json")
        return _record_from_text(text)
    if isinstance(payload, str):
        if len(payload.encode("utf-8")) > MAX_BYTES:
            _fail(CONTENT_TOO_LARGE, "youtube metadata record is too large")
        return _record_from_text(payload)
    if isinstance(payload, Mapping):
        return payload
    _fail(INVALID_CONTENT, "youtube metadata record must be a json object")


def _record_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if _is_transcript_document(stripped):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains a caption transcript")
    if stripped.startswith(("http://", "https://")) and _contains_download_url(stripped):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains a download url")
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        _fail(INVALID_CONTENT, "youtube metadata record is not json")
    if not isinstance(data, dict):
        _fail(INVALID_CONTENT, "youtube metadata record must be an object")
    return data


def _reject_disallowed(node: Any, *, key: str = "", depth: int = 0, state: dict[str, int] | None = None) -> None:
    if state is None:
        state = {"nodes": 0}
    state["nodes"] += 1
    if state["nodes"] > MAX_NODES:
        _fail(CONTENT_TOO_LARGE, "youtube metadata record is too large")
    if depth > MAX_DEPTH:
        _fail(INVALID_CONTENT, "youtube metadata record is too nested")
    norm = _norm_key(key) if key else ""
    if norm in _CAPTION_KEYS and _present(node):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains a caption transcript")
    if norm in _MEDIA_KEYS and _present(node):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains media bytes")
    if norm in _DOWNLOAD_KEYS and _present(node):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains a download url")
    if isinstance(node, (bytes, bytearray)):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains media bytes")
    if isinstance(node, str):
        _reject_string(node, norm)
        return
    if isinstance(node, Mapping):
        if _is_caption_cue(node):
            _fail(BLOCKED_BY_POLICY, "youtube metadata contains a caption transcript")
        for child_key, child in node.items():
            if not isinstance(child_key, str):
                _fail(INVALID_CONTENT, "youtube metadata keys must be strings")
            _reject_disallowed(child, key=child_key, depth=depth + 1, state=state)
        return
    if isinstance(node, list):
        if _list_is_media(node):
            _fail(BLOCKED_BY_POLICY, "youtube metadata contains media bytes")
        for child in node:
            _reject_disallowed(child, key=key, depth=depth + 1, state=state)
        return
    if isinstance(node, (int, float, bool)) or node is None:
        return
    _fail(INVALID_CONTENT, "youtube metadata record has an unsupported value")


def _reject_string(value: str, key: str) -> None:
    if _is_transcript_document(value):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains a caption transcript")
    if _DATA_MEDIA.match(value.strip()):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains media bytes")
    if key != "etag" and _base64_is_media(value):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains media bytes")
    if _contains_download_url(value):
        _fail(BLOCKED_BY_POLICY, "youtube metadata contains a download url")
    if len(value) > MAX_STRING:
        _fail(CONTENT_TOO_LARGE, "youtube metadata field is too large")


def _metadata_from_record(record: Mapping[str, Any]) -> YouTubeVideoMetadata:
    video_id = _one(_video_id_values(record), "video id")
    if not _VIDEO_ID.fullmatch(video_id):
        _fail(INVALID_CONTENT, "invalid video id")
    title = _plain(_one(_strings_at(record, _TITLE_PATHS), "title"), "title", MAX_TITLE)
    channel_name = _plain(
        _one(_strings_at(record, _CHANNEL_PATHS), "channel name"),
        "channel name",
        MAX_CHANNEL,
    )
    published_at = _one_published(_strings_at(record, _PUBLISHED_PATHS))
    url_video_id, canonical_url = _one_watch_url(_strings_at(record, _URL_PATHS))
    if video_id != url_video_id:
        _fail(INVALID_CONTENT, "video id does not match canonical watch url")
    return YouTubeVideoMetadata(
        video_id=video_id,
        title=title,
        channel_name=channel_name,
        published_at=published_at,
        canonical_url=canonical_url,
    )


def _video_id_values(record: Mapping[str, Any]) -> list[str]:
    found: list[str] = []
    for path in _VIDEO_ID_PATHS:
        value = _dig(record, path)
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
        elif isinstance(value, Mapping) and path == ("id",):
            nested = value.get("videoId", value.get("video_id"))
            if isinstance(nested, str) and nested.strip():
                found.append(nested.strip())
    return found


def _strings_at(record: Mapping[str, Any], paths: tuple[tuple[str, ...], ...]) -> list[str]:
    found: list[str] = []
    for path in paths:
        value = _dig(record, path)
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
    return found


def _one(values: list[str], label: str) -> str:
    distinct = list(dict.fromkeys(values))
    if not distinct:
        _fail(INVALID_CONTENT, f"missing {label}")
    if len(distinct) > 1:
        _fail(INVALID_CONTENT, f"conflicting {label}")
    return distinct[0]


def _one_published(values: list[str]) -> str:
    if not values:
        _fail(INVALID_CONTENT, "missing published time")
    normalized = [_normalize_published(value) for value in values]
    distinct = list(dict.fromkeys(normalized))
    if len(distinct) > 1:
        _fail(INVALID_CONTENT, "conflicting published time")
    return distinct[0]


def _one_watch_url(values: list[str]) -> tuple[str, str]:
    if not values:
        _fail(INVALID_CONTENT, "missing canonical watch url")
    canonicals = [_canonical_watch(value) for value in values]
    distinct = list(dict.fromkeys(canonicals))
    if len(distinct) > 1:
        _fail(INVALID_CONTENT, "conflicting canonical watch url")
    canonical = distinct[0]
    return canonical.rsplit("v=", 1)[1], canonical


def _plain(value: str, label: str, limit: int) -> str:
    if not value or len(value) > limit or any(ord(char) < 32 for char in value):
        _fail(INVALID_CONTENT, f"invalid {label}")
    return value


def _normalize_published(value: str) -> str:
    text = value.strip()
    iso = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        _fail(INVALID_CONTENT, "invalid published time")
    if parsed.tzinfo is None:
        _fail(INVALID_CONTENT, "published time needs a timezone")
    utc = parsed.astimezone(timezone.utc).replace(microsecond=0)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_watch(url: str) -> str:
    raw = url.strip()
    if any(ord(char) < 32 for char in raw):
        _fail(INVALID_CONTENT, "invalid canonical watch url")
    parsed_raw = urlparse(raw)
    if parsed_raw.username or parsed_raw.password:
        _fail(INVALID_CONTENT, "invalid canonical watch url")
    try:
        canonical = canonicalize_url(raw)
    except ValueError:
        _fail(INVALID_CONTENT, "invalid canonical watch url")
    video_id = _video_id_from_youtube_url(canonical)
    if video_id is None:
        _fail(INVALID_CONTENT, "canonical watch url must identify a youtube video")
    return f"https://www.youtube.com/watch?v={video_id}"


def _video_id_from_youtube_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in _YOUTUBE_HOSTS or parsed.username or parsed.password:
        return None
    if host == "youtu.be":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 1 and _VIDEO_ID.fullmatch(parts[0]):
            return parts[0]
        return None
    if parsed.path == "/watch":
        ids = [value for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key == "v"]
        if len(ids) == 1 and _VIDEO_ID.fullmatch(ids[0]):
            return ids[0]
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"} and _VIDEO_ID.fullmatch(parts[1]):
        return parts[1]
    return None


def _dig(node: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = node
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (bytes, bytearray, list, Mapping)):
        return len(value) > 0
    return True


def _norm_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _is_caption_cue(node: Mapping[str, Any]) -> bool:
    norms = {_norm_key(key) for key in node if isinstance(key, str)}
    return bool(norms & _CUE_TEXT_KEYS) and bool(norms & _CUE_TIME_KEYS)


def _is_transcript_document(value: str) -> bool:
    text = value.lstrip("\ufeff").strip()
    if not text:
        return False
    if _VTT.match(text) or _TRANSCRIPT_TAG.search(text) or _TIMED_TEXT.search(text):
        return True
    return _SRT_CUE.search(text) is not None


def _is_media_bytes(blob: bytes) -> bool:
    if len(blob) >= 12 and blob[4:8] == b"ftyp":
        return True
    if blob.startswith((b"ID3", b"OggS", b"fLaC", b"\x1a\x45\xdf\xa3")):
        return True
    if blob.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        return True
    return blob.startswith(b"RIFF") and len(blob) >= 12 and blob[8:12] in {b"WAVE", b"AVI "}


def _list_is_media(values: list[Any]) -> bool:
    if len(values) < 12:
        return False
    if not all(_is_byte(item) for item in values):
        return False
    return _is_media_bytes(bytes(values[:32]))


def _is_byte(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 255


def _base64_is_media(value: str) -> bool:
    compact = value.strip()
    if len(compact) < 32 or len(compact) % 4 != 0 or not _BASE64_TEXT.fullmatch(compact):
        return False
    try:
        decoded = base64.b64decode(compact, validate=True)
    except ValueError:
        return False
    return _is_media_bytes(decoded)


def _contains_download_url(value: str) -> bool:
    if _GOOGLEVIDEO_URL.search(value):
        return True
    candidates = [value]
    decoded = unquote(value)
    if decoded != value:
        candidates.append(decoded)
    for candidate in candidates:
        lowered = candidate.lower()
        if "googlevideo.com" in lowered and "videoplayback" in lowered:
            return True
        for url in _URL_RE.findall(candidate):
            if _url_is_download(url):
                return True
    return False


def _url_is_download(url: str) -> bool:
    parsed = urlparse(url.rstrip(").,;]"))
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return False
    if host == "googlevideo.com" or host.endswith(".googlevideo.com"):
        return True
    path = (parsed.path or "").lower()
    query = unquote(parsed.query).lower()
    if "videoplayback" in path or "/timedtext" in path:
        return True
    if _MEDIA_EXT.search(path):
        return True
    return "mime=video" in query or "mime=audio" in query
