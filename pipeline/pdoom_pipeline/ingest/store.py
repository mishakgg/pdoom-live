"""Idempotent observation store.

Identical content does not create another item. A changed hash appends a version
and keeps the previous hash. Version numbers stay with the hash that first
received them, including across a saved and reloaded store. Same canonical URL
from another platform is linked only when the normalized title matches;
otherwise it stays a duplicate candidate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
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
    current_hash: str = ""

    @property
    def content_version(self) -> int:
        if not self.versions:
            return 0
        return max(int(version["content_version"]) for version in self.versions)

    @property
    def latest(self) -> dict[str, Any]:
        if self.current_hash:
            for version in self.versions:
                if version["content_hash"] == self.current_hash:
                    return version
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
        known = _known_version(item, observation.content_hash)
        if known is not None and (observation.platform == item.platform or not item.versions):
            item.current_hash = observation.content_hash
            self._index(item, observation)
            return IngestResult("unchanged", logical_key, int(known["content_version"]), observation.content_hash)
        if observation.platform == item.platform and item.versions:
            latest = item.latest
            if latest["content_hash"] == observation.content_hash:
                item.current_hash = observation.content_hash
                self._index(item, observation)
                return IngestResult("unchanged", logical_key, int(latest["content_version"]), observation.content_hash)
        elif item.versions and item.latest["content_hash"] == observation.content_hash:
            item.current_hash = observation.content_hash
            self._index(item, observation)
            return IngestResult("unchanged", logical_key, int(item.latest["content_version"]), observation.content_hash)
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
        item.current_hash = observation.content_hash
        if not item.canonical_url:
            item.canonical_url = observation.canonical_url
        self._index(item, observation)
        status = "new" if item.content_version == 1 else "version_changed"
        return IngestResult(status, logical_key, item.content_version, observation.content_hash)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.to_dict(), sort_keys=True), encoding="utf-8")
        temporary.replace(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "observation-store/1.0.0",
            "items": [
                {
                    "logical_key": item.logical_key,
                    "canonical_url": item.canonical_url,
                    "platform": item.platform,
                    "upstream_ids": item.upstream_ids,
                    "current_hash": item.current_hash,
                    "versions": item.versions,
                }
                for item in self.items.values()
            ],
            "duplicate_candidates": self.duplicate_candidates,
            "runs": self.runs,
        }

    @classmethod
    def load(cls, path: Path) -> "ObservationStore":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ObservationStore":
        store = cls()
        for raw in payload.get("items") or []:
            item = StoredItem(
                logical_key=raw["logical_key"],
                canonical_url=raw["canonical_url"],
                platform=raw["platform"],
                upstream_ids=list(raw.get("upstream_ids") or []),
                versions=list(raw.get("versions") or []),
                current_hash=raw.get("current_hash") or (raw["versions"][-1]["content_hash"] if raw.get("versions") else ""),
            )
            store.items[item.logical_key] = item
            if item.canonical_url:
                store.by_url[item.canonical_url] = item.logical_key
            for upstream in item.upstream_ids:
                store.by_upstream[(upstream["platform"], upstream["upstream_id"])] = item.logical_key
        store.duplicate_candidates = list(payload.get("duplicate_candidates") or [])
        store.runs = list(payload.get("runs") or [])
        return store

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


def _known_version(item: StoredItem, content_hash: str) -> dict[str, Any] | None:
    for version in item.versions:
        if version.get("content_hash") == content_hash:
            return version
    return None


def _title_key(title: str | None) -> str:
    return " ".join((title or "").lower().split())
