"""Idempotent observation store.

Identical content does not create another item. A changed hash appends a version
and keeps the previous hash. Version numbers stay with the hash that first
received them, including across a saved and reloaded store. Same canonical URL
from another platform is linked only when the normalized title matches;
otherwise it stays a duplicate candidate.
"""

from __future__ import annotations

import json
import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pdoom_pipeline.contracts import SourceObservation
from pdoom_pipeline.ingest.writes import WriteBytes, atomic_bytes


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
        self.by_upstream: dict[tuple[str, str, str], str] = {}
        self.duplicate_candidates: list[dict[str, str]] = []
        self.runs: list[dict[str, Any]] = []

    def ingest(self, observation: SourceObservation) -> IngestResult:
        if not observation.content_hash:
            observation.finalize_hash()
        url_key = self.by_url.get(observation.canonical_url)
        upstream_key = None
        if observation.upstream_id:
            upstream_key = self.by_upstream.get(_upstream_key(observation.platform, observation.upstream_id, observation.source_identity))
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
        if known is not None:
            provenance_changed = _remember_provenance(known, observation)
            item.current_hash = observation.content_hash
            self._index(item, observation)
            return IngestResult("version_changed" if provenance_changed else "unchanged", logical_key,
                                int(known["content_version"]), observation.content_hash)
        if item.versions and observation.platform != item.platform:
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
        _remember_provenance(version, observation)
        item.versions.append(version)
        item.current_hash = observation.content_hash
        if not item.canonical_url:
            item.canonical_url = observation.canonical_url
        self._index(item, observation)
        status = "new" if item.content_version == 1 else "version_changed"
        return IngestResult(status, logical_key, item.content_version, observation.content_hash)

    def save(self, path: Path, write_bytes: WriteBytes | None = None) -> None:
        atomic_bytes(path, json.dumps(self.to_dict(), sort_keys=True).encode(), write_bytes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "observation-store/1.1.0",
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
        schema = payload.get("schema_version") or "observation-store/1.0.0"
        if schema not in {"observation-store/1.0.0", "observation-store/1.1.0"}:
            raise ValueError("unsupported observation store schema; explicit migration required")
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
            for version in item.versions:
                _ensure_provenance(version)
            if schema == "observation-store/1.0.0":
                _check_legacy_rss_identity(item)
        store._rebuild_indexes()
        store.duplicate_candidates = list(payload.get("duplicate_candidates") or [])
        store.runs = list(payload.get("runs") or [])
        return store

    def _index(self, item: StoredItem, observation: SourceObservation) -> None:
        self.by_url[observation.canonical_url] = item.logical_key
        if observation.upstream_id:
            self.by_upstream[_upstream_key(observation.platform, observation.upstream_id, observation.source_identity)] = item.logical_key
            record = {"platform": observation.platform, "upstream_id": observation.upstream_id,
                      "source_identity": observation.source_identity}
            if record not in item.upstream_ids:
                item.upstream_ids.append(record)

    def _rebuild_indexes(self) -> None:
        self.by_url, self.by_upstream = {}, {}
        for item in self.items.values():
            if item.canonical_url:
                self.by_url[item.canonical_url] = item.logical_key
            observations = [row for version in item.versions for row in _ensure_provenance(version)]
            for row in observations:
                if row.get("canonical_url"):
                    self.by_url[row["canonical_url"]] = item.logical_key
                if row.get("upstream_id"):
                    self.by_upstream[_upstream_key(row["platform"], row["upstream_id"], row["source_identity"])] = item.logical_key
            # Old stores recorded alternate upstream IDs separately. Scope a
            # legacy RSS alias only when its owning source can be recovered.
            aliases = []
            for upstream in item.upstream_ids:
                identities = {upstream["source_identity"]} if upstream.get("source_identity") else {
                    row["source_identity"] for row in observations if row["platform"] == upstream["platform"]
                    and row.get("upstream_id") == upstream["upstream_id"]}
                if not identities:
                    candidates = {row["source_identity"] for row in observations if row["platform"] == upstream["platform"]}
                    if len(candidates) == 1:
                        identities = candidates
                if upstream["platform"] != "rss" or len(identities) == 1:
                    for identity in identities or {""}:
                        self.by_upstream[_upstream_key(upstream["platform"], upstream["upstream_id"], identity)] = item.logical_key
                        alias = {**upstream, "source_identity": identity}
                        if alias not in aliases:
                            aliases.append(alias)
            item.upstream_ids = aliases

    def retain_sources(self, admitted_ids: set[str], evidence_ids: set[str]) -> None:
        """Revoke per-source observations, including historical provenance bytes."""
        for key, item in list(self.items.items()):
            kept = []
            for version in item.versions:
                observations = [row for row in _ensure_provenance(version) if row["source_identity"] in admitted_ids]
                if not observations:
                    continue
                current = next((row for row in observations if row["provenance_id"] == version.get("current_provenance_id")), observations[-1])
                for row in observations:
                    for field in ("upstream_version", "raw_body", "article_text", "evidence_body"):
                        (row.get("metadata") or {}).pop(field, None)
                    if row["source_identity"] not in evidence_ids:
                        row["segments"] = []
                    row["provenance_id"] = hashlib.sha256(_provenance_material(row).encode()).hexdigest()
                version["provenance_observations"] = observations
                _project_provenance(version, current)
                kept.append(version)
            item.versions = kept
            if not kept:
                del self.items[key]
                continue
            if not any(version["content_hash"] == item.current_hash for version in kept):
                item.current_hash = kept[-1]["content_hash"]
            # Do not let a revoked source's old upstream aliases bind a new item.
            item.upstream_ids = [row for row in item.upstream_ids if row.get("source_identity") in admitted_ids]
        self._rebuild_indexes()

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
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "segment_hash": segment.segment_hash,
            }
            for segment in observation.segments
        ],
        "metadata": deepcopy(observation.metadata),
    }


def _known_version(item: StoredItem, content_hash: str) -> dict[str, Any] | None:
    for version in item.versions:
        if version.get("content_hash") == content_hash:
            return version
    return None


_PROVENANCE_FIELDS = ("canonical_url", "published_at", "observed_at", "title", "platform", "upstream_id",
                      "source_identity", "collection_method", "collector", "collector_version",
                      "author_candidates", "segments", "metadata")


def _upstream_key(platform: str, upstream_id: str, source_identity: str) -> tuple[str, str, str]:
    # RSS GUIDs need only be unique inside their feed. Other admitted APIs use
    # platform-wide identifiers (repository, work, or paper IDs).
    return platform, source_identity if platform == "rss" else "", upstream_id


def _check_legacy_rss_identity(item: StoredItem) -> None:
    if item.platform != "rss":
        return
    rows = [row for version in item.versions for row in _ensure_provenance(version) if row.get("platform") == "rss"]
    # A source may move an item URL and another source may observe that known
    # alias. Follow those same-source/same-URL links rather than rejecting a
    # legitimate moved item merely because its logical URL remains stable.
    urls, owners = {item.canonical_url}, set()
    while True:
        connected = [row for row in rows if row.get("canonical_url") in urls or row.get("source_identity") in owners]
        next_urls = urls | {row.get("canonical_url") for row in connected}
        next_owners = owners | {row.get("source_identity") for row in connected}
        if (next_urls, next_owners) == (urls, owners):
            break
        urls, owners = next_urls, next_owners
    conflicts = {row.get("source_identity") for row in rows if row.get("source_identity") not in owners}
    if conflicts:
        record = hashlib.sha256(item.logical_key.encode()).hexdigest()[:16]
        def safe(value):
            value = str(value or "unknown")
            return value if re.fullmatch(r"[A-Za-z0-9:_.-]{1,100}", value) else hashlib.sha256(value.encode()).hexdigest()[:16]
        sources = ", ".join(sorted(safe(identity) for identity in owners | conflicts))
        raise ValueError(f"legacy RSS identity reconciliation required for record {record}; sources: {sources}; store unchanged")


def _provenance_material(row: dict) -> str:
    payload = {key: deepcopy(row.get(key)) for key in _PROVENANCE_FIELDS if key != "observed_at"}
    # Old stores did not retain timecodes. Missing and explicit unknown match.
    for segment in payload.get("segments") or []:
        segment.setdefault("start_ms", None)
        segment.setdefault("end_ms", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _ensure_provenance(version: dict) -> list[dict]:
    rows = version.get("provenance_observations")
    if rows is None:
        row = {key: deepcopy(version.get(key)) for key in _PROVENANCE_FIELDS}
        row["provenance_revision"] = 1
        row["provenance_id"] = hashlib.sha256(_provenance_material(row).encode()).hexdigest()
        rows = version["provenance_observations"] = [row]
        _project_provenance(version, row)
    return rows


def _project_provenance(version: dict, row: dict) -> None:
    for key in _PROVENANCE_FIELDS:
        version[key] = deepcopy(row.get(key))
    version["current_provenance_id"] = row["provenance_id"]
    version["provenance_revision"] = row["provenance_revision"]


def _remember_provenance(version: dict, observation: SourceObservation) -> bool:
    rows = _ensure_provenance(version)
    candidate = _version_record(observation, int(version["content_version"]))
    candidate = {key: candidate.get(key) for key in _PROVENANCE_FIELDS}
    material = _provenance_material(candidate)
    previous = next((row for row in rows if _provenance_material(row) == material), None)
    if previous is not None:
        changed = version.get("current_provenance_id") != previous["provenance_id"]
        _project_provenance(version, previous)
        return changed
    candidate["provenance_revision"] = max(row["provenance_revision"] for row in rows) + 1
    candidate["provenance_id"] = hashlib.sha256(material.encode()).hexdigest()
    rows.append(candidate)
    _project_provenance(version, candidate)
    return True


def _title_key(title: str | None) -> str:
    return " ".join((title or "").lower().split())
