"""Durable per-source collection checkpoints.

The file is the simplest store that already matches the pipeline: JSON next
to the collection, rewritten atomically. It is not a second database.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.ingest.writes import WriteBytes, atomic_bytes

SCHEMA = "collection-state/1.0.0"
MAX_ERRORS = 8


def utc_now(now: str | None = None) -> datetime:
    if now:
        return datetime.fromisoformat(now.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CollectionState:
    def __init__(self, path: Path, write_bytes: WriteBytes | None = None):
        self.path = path
        self.write_bytes = write_bytes
        self.sources: dict[str, dict[str, Any]] = {}
        self.items: dict[str, dict[str, Any]] = {}
        self.cursor: str | None = None
        self.schema_version = SCHEMA
        self.bindings: dict[str, str] = {}
        self.raw_bodies: dict[str, dict] = {}

    @classmethod
    def load(cls, path: Path, write_bytes: WriteBytes | None = None) -> "CollectionState":
        state = cls(path, write_bytes)
        if not path.exists():
            return state
        payload = json.loads(path.read_text(encoding="utf-8"))
        state.schema_version = payload.get("schema_version") or SCHEMA
        state.sources = dict(payload.get("sources") or {})
        state.items = dict(payload.get("items") or {})
        state.cursor = payload.get("cursor")
        state.bindings = dict(payload.get("bindings") or {})
        state.raw_bodies = dict(payload.get("raw_bodies") or {})
        return state

    def save(self) -> None:
        payload = {
            "schema_version": SCHEMA,
            "cursor": self.cursor,
            "sources": self.sources,
            "items": self.items,
            "bindings": self.bindings,
            "raw_bodies": self.raw_bodies,
        }
        atomic_bytes(self.path, json.dumps(payload, sort_keys=True).encode(), self.write_bytes)

    def bind(self, identity: str, fingerprint: str) -> None:
        previous = self.bindings.get(identity)
        if previous is not None and previous != fingerprint:
            raise CollectorFailure("blocked_by_policy", "source identity changed; explicit admission review is required")
        self.bindings[identity] = fingerprint

    def source(self, key: str) -> dict[str, Any]:
        row = self.sources.get(key)
        if row is None:
            row = {
                "source_identity": key,
                "canonical_url": key,
                "etag": None,
                "last_modified": None,
                "cursor": None,
                "content_versions": [],
                "last_attempt_at": None,
                "last_success_at": None,
                "last_outcome": None,
                "retry_not_before": None,
                "consecutive_failures": 0,
                "errors": [],
            }
            self.sources[key] = row
        return row

    def eligible(self, key: str, now: str) -> bool:
        row = self.sources.get(key)
        if not row or not row.get("retry_not_before"):
            return True
        return utc_now(now) >= utc_now(row["retry_not_before"])

    def conditional_headers(self, key: str) -> dict[str, str]:
        row = self.sources.get(key) or {}
        headers: dict[str, str] = {}
        if row.get("etag"):
            headers["If-None-Match"] = row["etag"]
        if row.get("last_modified"):
            headers["If-Modified-Since"] = row["last_modified"]
        return headers

    def record_attempt(self, key: str, *, identity: str, url: str, now: str) -> None:
        row = self.source(key)
        if row.get("last_attempt_at") and row["source_identity"] != identity:
            raise CollectorFailure("blocked_by_policy", "fetch URL is already bound to another source identity")
        row["source_identity"] = identity
        row["canonical_url"] = url
        row["last_attempt_at"] = now

    def record_outcome(
        self,
        key: str,
        *,
        outcome: str,
        now: str,
        success: bool,
        etag: str | None = None,
        last_modified: str | None = None,
        cursor: str | None = None,
        content_hash: str | None = None,
        error_class: str | None = None,
        message: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        row = self.source(key)
        row["last_outcome"] = outcome
        row["last_attempt_at"] = now
        if success:
            if cursor is not None:
                row["cursor"] = cursor
            row["last_success_at"] = now
            row["consecutive_failures"] = 0
            row["retry_not_before"] = None
            if etag:
                row["etag"] = etag
            if last_modified:
                row["last_modified"] = last_modified
            if content_hash:
                self._note_hash(row, content_hash)
        else:
            row["consecutive_failures"] = int(row.get("consecutive_failures") or 0) + 1
            delay = retry_after if retry_after is not None else min(60.0, 2 ** min(row["consecutive_failures"], 5))
            row["retry_not_before"] = iso(utc_now(now) + timedelta(seconds=max(delay, 0)))
            errors = list(row.get("errors") or [])
            errors.append({"at": now, "error_class": error_class or "collector_bug", "message": (message or "")[:300]})
            row["errors"] = errors[-MAX_ERRORS:]

    def _note_hash(self, row: dict[str, Any], content_hash: str) -> None:
        versions = list(row.get("content_versions") or [])
        if any(item.get("content_hash") == content_hash for item in versions):
            row["content_versions"] = versions
            return
        versions.append({"content_hash": content_hash, "content_version": len(versions) + 1})
        row["content_versions"] = versions

    def remember_item(self, item: dict[str, Any], statements: list[dict]) -> None:
        key = item["canonical_url"]
        previous = self.items.get(key) or {"versions": [], "statements": []}
        versions = list(previous.get("versions") or [])
        content_hash = item.get("content_hash")
        if content_hash and not any(version.get("content_hash") == content_hash for version in versions):
            versions.append(
                {
                    "content_hash": content_hash,
                    "content_version": len(versions) + 1,
                    "observed_at": item.get("observed_at"),
                    "published_at": item.get("published_at"),
                    "title": item.get("title"),
                }
            )
        current_version = next(version["content_version"] for version in versions if version["content_hash"] == content_hash)
        stored = {k: v for k, v in item.items() if k not in {"evidence_body", "summary", "article_text"}}
        stored["content_version"] = current_version
        stored["retained_versions"] = versions
        self.items[key] = {"item": stored, "statements": statements, "versions": versions}

    def retained_for(self, urls: set[str]) -> tuple[list[dict], list[dict]]:
        observations = []
        statements = []
        for key, payload in self.items.items():
            if key in urls:
                continue
            item = dict(payload["item"])
            item["ingest_status"] = "unchanged"
            observations.append(item)
            statements.extend(payload.get("statements") or [])
        return observations, statements

    def body_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.path.parent / "bodies" / digest

    def write_body(self, url: str, body: bytes, *, expires_at: str, rights_basis: str) -> None:
        path = self.body_path(url)
        atomic_bytes(path, body, self.write_bytes)
        self.raw_bodies[url] = {"expires_at": expires_at, "rights_basis": rights_basis}

    def read_body(self, url: str, *, now: str | None = None) -> bytes | None:
        permission = self.raw_bodies.get(url)
        if not permission or utc_now(permission["expires_at"]) <= utc_now(now):
            return None
        path = self.body_path(url)
        if not path.exists():
            return None
        return path.read_bytes()

    def purge_bodies(self, allowed: dict[str, dict]) -> None:
        """Delete only this state's URL-hashed cache files, including legacy bodies."""
        allowed_digests = {self.body_path(url).name for url in allowed}
        directory = self.path.parent / "bodies"
        if directory.exists():
            for path in directory.iterdir():
                if path.is_file() and len(path.name) == 64 and all(char in "0123456789abcdef" for char in path.name):
                    if path.name not in allowed_digests:
                        path.unlink()
        self.raw_bodies = allowed
