"""RSS and Atom collector. Item text is stored as untrusted evidence, not instructions."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as UnsafeElementTree

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.safe_xml import XmlParseError as _XmlParseError
from pdoom_pipeline.safe_xml import fromstring as _fromstring
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "rss-0.1.0"
MAX_ITEMS = 100
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
DC_NS = {"dc": "http://purl.org/dc/elements/1.1/"}
# RFC 822 zone names parsed by email.utils, in hours and minutes.
_NAMED_OFFSET_MINUTES = {
    "UT": 0,
    "UTC": 0,
    "GMT": 0,
    "AST": -4 * 60,
    "ADT": -3 * 60,
    "EST": -5 * 60,
    "EDT": -4 * 60,
    "CST": -6 * 60,
    "CDT": -5 * 60,
    "MST": -7 * 60,
    "MDT": -6 * 60,
    "PST": -8 * 60,
    "PDT": -7 * 60,
}
# A trailing zone. Two-digit offsets must follow a clock (`:SS+05`), so a
# calendar day such as 2026-03-03 is not read as an offset of -03.
_EXPLICIT_ZONE = re.compile(
    r"(?P<token>"
    r"[+-]\d{2}:\d{2}(?::\d{2})?"
    r"|[+-]\d{4}"
    r"|(?<=:\d{2})[+-]\d{2}"
    r"|(?<![A-Za-z])(?:UTC|UT|GMT|AST|ADT|EDT|EST|CDT|CST|MDT|MST|PDT|PST)"
    r"|(?<![A-Za-z])[Zz]"
    r")\s*$",
    re.IGNORECASE,
)
_DATE_PRIORITY = ("pubdate", "published", "updated", "date")

ALLOWED_TYPES = (
    "application/rss+xml",
    "application/atom+xml",
    "application/xml",
    "text/xml",
    "text/plain",
    "application/octet-stream",
)


def _text(element: UnsafeElementTree.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return " ".join(element.text.split())


def _parse_time(value: str | None) -> str | None:
    utc, _source_timezone = _parse_timestamp(value)
    return utc


def _parse_timestamp(value: str | None) -> tuple[str | None, str | None]:
    """Return a UTC instant and the original source offset.

    An explicit offset keeps that UTC instant. The offset text is returned
    unchanged. A missing or unreadable date is ``(None, None)`` and is not
    replaced with an observation time.
    """
    if not value or not value.strip():
        return None, None
    raw = value.strip()
    token = _explicit_zone(raw)
    if token is not None:
        delta = _zone_delta(token)
        civil = _parse_unaware(raw[: raw.rfind(token)].strip()) if delta is not None else None
        if civil is not None and delta is not None:
            return _format_utc(civil - delta), token
    return _parse_legacy_timestamp(raw)


def _explicit_zone(raw: str) -> str | None:
    match = _EXPLICIT_ZONE.search(raw)
    if match is None:
        return None
    return match.group("token")


def _zone_delta(token: str) -> timedelta | None:
    upper = token.upper()
    if upper == "Z" or upper in _NAMED_OFFSET_MINUTES:
        minutes = 0 if upper == "Z" else _NAMED_OFFSET_MINUTES[upper]
        return timedelta(minutes=minutes)
    match = re.fullmatch(r"([+-])(\d{2})(?::?(\d{2}))?(?::(\d{2}))?", token)
    if match is None:
        return None
    hours = int(match.group(2))
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)
    if hours > 23 or minutes > 59 or seconds > 59:
        return None
    delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if match.group(1) == "-":
        return -delta
    return delta


def _parse_unaware(text: str) -> datetime | None:
    if not text:
        return None
    parsed = _parse_datetime(text)
    if parsed is None or parsed.tzinfo is not None:
        return None
    return parsed


def _parse_legacy_timestamp(raw: str) -> tuple[str | None, str | None]:
    parsed = _parse_datetime(raw)
    if parsed is None:
        return None, None
    offset = parsed.utcoffset() if parsed.tzinfo is not None else None
    if offset is None:
        return _format_utc(parsed.replace(tzinfo=None)), None
    return _format_utc(parsed), _format_offset(offset)


def _parse_datetime(text: str) -> datetime | None:
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        parsed = None
    iso = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return parsed


def _format_utc(value: datetime) -> str:
    """Format a naive UTC clock or an aware instant as ``YYYY-MM-DDTHH:MM:SSZ``."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_offset(delta: timedelta | None) -> str | None:
    if delta is None:
        return None
    total = int(delta.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if seconds:
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{sign}{hours:02d}:{minutes:02d}"


def _date_text(entry: UnsafeElementTree.Element) -> str:
    found: dict[str, str] = {}
    for child in list(entry):
        key = _date_key(child.tag)
        if key is None or key in found:
            continue
        text = _text(child)
        if text:
            found[key] = text
    for key in _DATE_PRIORITY:
        if key in found:
            return found[key]
    return ""


def _date_key(tag: str) -> str | None:
    if tag.lower() == "dc:date":
        return "date"
    namespace = ""
    local = tag
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
    lowered = local.lower()
    if lowered in {"pubdate", "published", "updated"}:
        return lowered
    if lowered == "date" and namespace == DC_NS["dc"]:
        return "date"
    return None


def _child(parent: UnsafeElementTree.Element, names: list[str]) -> UnsafeElementTree.Element | None:
    for name in names:
        found = parent.find(name)
        if found is not None:
            return found
    return None


class RssCollector:
    collector = "rss"
    platform = "rss"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(allowed_content_types=ALLOWED_TYPES, max_bytes=1_000_000)

    def collect(self, *, source_identity: str, feed_url: str, observed_at: str) -> list[SourceObservation]:
        try:
            result = self.fetcher.get(feed_url)
        except CollectorFailure:
            raise
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise CollectorFailure("collector_bug", str(exc)) from exc
        return self.parse(result.body, source_identity=source_identity, feed_url=feed_url, observed_at=observed_at)

    def parse(
        self,
        payload: bytes,
        *,
        source_identity: str,
        feed_url: str,
        observed_at: str,
        max_bytes: int = 1_000_000,
        max_items: int = MAX_ITEMS,
    ) -> list[SourceObservation]:
        if len(payload) > max_bytes:
            raise CollectorFailure("content_too_large", "feed exceeds parser cap")
        if max_items < 1 or max_items > 500:
            raise CollectorFailure("invalid_content", "max_items out of range")
        try:
            root = _fromstring(payload)
        except _XmlParseError as exc:
            raise CollectorFailure("invalid_content", f"malformed feed: {exc}") from exc
        items = _entries(root)
        observations: list[SourceObservation] = []
        for index, entry in enumerate(items[:max_items]):
            observations.append(_entry_to_observation(entry, source_identity=source_identity, feed_url=feed_url, observed_at=observed_at, index=index))
        return observations


def _entries(root: UnsafeElementTree.Element) -> list[UnsafeElementTree.Element]:
    tag = root.tag.lower()
    if tag == "rss" or tag.endswith("}rss") or root.find("channel") is not None:
        channel = root.find("channel")
        if channel is None:
            raise CollectorFailure("invalid_content", "rss feed has no channel")
        return list(channel.findall("item"))
    if tag.endswith("feed") or tag == "feed":
        entries = root.findall("atom:entry", ATOM_NS)
        if not entries:
            entries = [child for child in list(root) if child.tag.endswith("entry")]
        return entries
    raise CollectorFailure("parser_unsupported", f"unsupported feed root: {root.tag}")


def _entry_to_observation(entry, *, source_identity: str, feed_url: str, observed_at: str, index: int) -> SourceObservation:
    title = _text(_child(entry, ["title", "atom:title"]))
    link = _link(entry)
    guid = _text(_child(entry, ["guid", "id", "atom:id"])) or link or f"{feed_url}#{index}"
    try:
        canonical = canonicalize_url(link) if link else canonicalize_url(feed_url)
    except ValueError:
        canonical = canonicalize_url(feed_url)
    published, source_timezone = _parse_timestamp(_date_text(entry))
    author_name = _text(_child(entry, ["author", "dc:creator"]))
    if not author_name:
        for child in list(entry):
            if child.tag.split("}")[-1] in {"creator", "author"} and (child.text or "").strip():
                author_name = _text(child)
                break
    if not author_name:
        atom_author = entry.find("atom:author/atom:name", ATOM_NS)
        if atom_author is None:
            atom_author = entry.find("author/name")
        author_name = _text(atom_author)
    description = _text(_child(entry, ["description", "summary", "atom:summary"]))
    encoded = entry.find("content:encoded", CONTENT_NS)
    body = _text(encoded) or description
    text, truncated = excerpt(body, 1500)
    full_for_hash, _ = excerpt(body, 50_000)
    candidates = []
    if author_name:
        candidates.append(
            AuthorCandidate(
                name=author_name,
                role="author",
                attribution_method="feed_author_field",
                confidence="medium",
            )
        )
    observation = SourceObservation(
        source_identity=source_identity,
        platform="rss",
        upstream_id=guid,
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=published,
        author_candidates=candidates,
        title=title or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "feed_url": feed_url,
            "truncated": truncated,
            "upstream_version": full_for_hash,
            "transcript_url": _transcript_url(entry),
            "source_timezone": source_timezone,
        },
        collection_method="rss_feed",
        collector="rss",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _transcript_url(entry) -> str | None:
    for child in list(entry):
        if child.tag.split("}")[-1] != "transcript":
            continue
        href = child.attrib.get("url") or (child.text or "").strip()
        if href.startswith("http"):
            return href
    return None


def _link(entry) -> str:
    for child in list(entry):
        if child.tag == "link" or child.tag.endswith("}link"):
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if child.text and child.text.strip():
                return child.text.strip()
    return ""


def podcast_episode_metadata(payload: bytes) -> list[dict[str, str]]:
    """Return episode title, publication time, canonical URL, and enclosure URL.

    The enclosure value is the remote audio URL. Audio bytes are not fetched.
    A missing title or publication time is recorded as ``unknown``.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise CollectorFailure("invalid_content", "podcast feed must be bytes")
    if len(payload) > 1_000_000:
        raise CollectorFailure("content_too_large", "feed exceeds parser cap")
    try:
        root = _fromstring(payload)
    except _XmlParseError as exc:
        raise CollectorFailure("invalid_content", f"malformed feed: {exc}") from exc
    return [_podcast_episode_record(entry) for entry in _entries(root)[:MAX_ITEMS]]


def _podcast_episode_record(entry: UnsafeElementTree.Element) -> dict[str, str]:
    title = _text(_child(entry, ["title", "atom:title"]))
    published = _parse_time(_date_text(entry))
    return {
        "title": title or "unknown",
        "published_at": published or "unknown",
        "canonical_url": _http_url(_link(entry)),
        "enclosure_url": _http_url(_enclosure_url(entry)),
    }


def _http_url(value: str) -> str:
    try:
        return canonicalize_url(value)
    except ValueError:
        return "unknown"


def _enclosure_url(entry: UnsafeElementTree.Element) -> str:
    for child in list(entry):
        if child.tag.split("}")[-1] != "enclosure":
            continue
        return (child.attrib.get("url") or "").strip()
    return ""


def discover_feed_urls(html: str) -> list[str]:
    """Read rel=alternate feed links. Page text is not executed."""
    urls: list[str] = []
    lowered = html.lower()
    if "alternate" not in lowered:
        return urls
    try:
        root = _fromstring(html.encode("utf-8"))
    except _XmlParseError:
        return urls
    for element in root.iter():
        rel = (element.attrib.get("rel") or "").lower().split()
        type_ = (element.attrib.get("type") or "").lower()
        href = element.attrib.get("href")
        if href and "alternate" in rel and any(token in type_ for token in ("rss", "atom", "xml")):
            urls.append(href.strip())
    return urls


def parse_fetch_result(result: FetchResult, *, source_identity: str, observed_at: str) -> list[SourceObservation]:
    return RssCollector().parse(result.body, source_identity=source_identity, feed_url=result.url, observed_at=observed_at)
