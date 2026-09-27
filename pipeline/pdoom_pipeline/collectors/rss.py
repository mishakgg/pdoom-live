"""RSS and Atom collector. Item text is stored as untrusted evidence, not instructions."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as UnsafeElementTree

import defusedxml.ElementTree as ET

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "rss-0.1.0"
MAX_ITEMS = 100
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
DC_NS = {"dc": "http://purl.org/dc/elements/1.1/"}

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
    if not value:
        return None
    raw = value.strip()
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
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
    published = _parse_time(_text(_child(entry, ["pubDate", "published", "atom:published", "updated", "atom:updated", "dc:date"])))
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


def discover_feed_urls(html: str) -> list[str]:
    """Read rel=alternate feed links. Page text is not executed."""
    urls: list[str] = []
    lowered = html.lower()
    if "alternate" not in lowered:
        return urls
    try:
        root = ET.fromstring(html.encode("utf-8"))
    except ET.ParseError:
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
