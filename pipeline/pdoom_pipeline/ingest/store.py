"""Idempotent observation store.

Identical content does not create another item. A changed hash appends a version
and keeps the previous hash. Same canonical URL from another platform is linked
only when the normalized title matches; otherwise it stays a duplicate candidate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pdoom_pipeline.contracts import SourceObservation


@dataclass
class IngestResult:
    status: str
    logical_key: str
    content_version: int
    content_hash: str


@dataclass
class StoredItem:
    logical_key: str
    canonical_url: str
    platform: str
    upstream_ids: list[dict[str, str]]
    versions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def content_version(self) -> int:
        return len(self.versions)

    @property
    def latest(self) -> dict[str, Any]:
        return self.versions[-1]


class ObservationStore:
    def __init__(self):
        self.items: dict[str, StoredItem] = {}
        self.by_url: dict[str, str] = {}
        self.by_upstream: dict[tuple[str, str], str] = {}
        self.duplicate_candidates: list[dict[str, str]] = []
        self.runs: list[dict[str, Any]] = []

    def ingest(self, observation: SourceObservation) -> IngestResult:
        if not observation.content_hash:
            observation.finalize_hash()
        url_key = self.by_url.get(observation.canonical_url)
        upstream_key = None
        if observation.upstream_id:
            upstream_key = self.by_upstream.get((observation.platform, observation.upstream_id))
        if url_key and upstream_key and url_key != upstream_key:
            self.duplicate_candidates.append(
                {
                    "canonical_url": observation.canonical_url,
                    "platform": observation.platform,
                    "upstream_id": observation.upstream_id or "",
                    "reason": "url_and_upstream_point_at_different_items",
                }
            )
            return IngestResult("duplicate_candidate", url_key, self.items[url_key].content_version, observation.content_hash)
        logical_key = upstream_key or url_key
        if logical_key is None:
            logical_key = observation.canonical_url or f"{observation.platform}:{observation.upstream_id}"
            item = StoredItem(
                logical_key=logical_key,
                canonical_url=observation.canonical_url,
                platform=observation.platform,
                upstream_ids=[],
            )
            self.items[logical_key] = item
        else:
            item = self.items[logical_key]
        if observation.platform == item.platform and item.versions:
            latest = item.latest
            if latest["content_hash"] == observation.content_hash:
                self._index(item, observation)
                return IngestResult("unchanged", logical_key, item.content_version, observation.content_hash)
        elif item.versions and item.latest["content_hash"] == observation.content_hash:
            self._index(item, observation)
            return IngestResult("unchanged", logical_key, item.content_version, observation.content_hash)
        elif item.versions and observation.platform != item.platform:
            if _title_key(item.latest.get("title")) != _title_key(observation.title):
                self.duplicate_candidates.append(
                    {
                        "canonical_url": observation.canonical_url,
                        "platform": observation.platform,
                        "upstream_id": observation.upstream_id or "",
                        "reason": "same_url_different_title",
                    }
                )
                return IngestResult("duplicate_candidate", logical_key, item.content_version, observation.content_hash)
        version = _version_record(observation, item.content_version + 1)
        item.versions.append(version)
        if not item.canonical_url:
            item.canonical_url = observation.canonical_url
        self._index(item, observation)
        status = "new" if item.content_version == 1 else "version_changed"
        return IngestResult(status, logical_key, item.content_version, observation.content_hash)

    def _index(self, item: StoredItem, observation: SourceObservation) -> None:
        self.by_url[observation.canonical_url] = item.logical_key
        if observation.upstream_id:
            self.by_upstream[(observation.platform, observation.upstream_id)] = item.logical_key
            record = {"platform": observation.platform, "upstream_id": observation.upstream_id}
            if record not in item.upstream_ids:
                item.upstream_ids.append(record)

    def record_run(self, run: dict[str, Any]) -> None:
        self.runs.append(run)


def _version_record(observation: SourceObservation, content_version: int) -> dict[str, Any]:
    return {
        "content_version": content_version,
        "content_hash": observation.content_hash,
        "canonical_url": observation.canonical_url,
        "published_at": observation.published_at,
        "observed_at": observation.observed_at,
        "title": observation.title,
        "platform": observation.platform,
        "upstream_id": observation.upstream_id,
        "source_identity": observation.source_identity,
        "collection_method": observation.collection_method,
        "collector": observation.collector,
        "collector_version": observation.collector_version,
        "author_candidates": [candidate.__dict__.copy() for candidate in observation.author_candidates],
        "segments": [
            {
                "segment_kind": segment.segment_kind,
                "sequence": segment.sequence,
                "text": segment.text,
                "start_char": segment.start_char,
                "end_char": segment.end_char,
                "segment_hash": segment.segment_hash,
            }
            for segment in observation.segments
        ],
        "metadata": observation.metadata,
    }


def _title_key(title: str | None) -> str:
    return " ".join((title or "").lower().split())
