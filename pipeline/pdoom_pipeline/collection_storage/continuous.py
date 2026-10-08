"""Bounded single-host metadata queue; no credentials, scheduler, or publication.

Each call performs one bounded slice, not a loop around the legacy pilot. The
existing Supervisor remains the only remote writer. A full DriveBackend plus
bounded download_chunks is required; the document connector is not that backend.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import time
from typing import Callable, Iterable, Protocol

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.refresh.admission import public_url
from .pilot import PIN_KEYS
from .scratch import BoundedScratch, CHUNK_BYTES, METADATA_RESERVE, StorageStop
from .supervisor import Artifact, CHECKPOINT, DrivePin, PENDING, Supervisor

JOURNAL = "state/continuous.json"
INDEX = "state/continuous-index.jsonl"
PAYLOAD = "runner/continuous/payload.jsonl"
SNAPSHOT = "runner/continuous/state.jsonl"
SCHEMA = "continuous-metadata/1"
HEX = re.compile(r"[a-f0-9]{64}\Z")
SOURCE_AUTHORS = {
    "person:holden-karnofsky": "Holden Karnofsky", "person:jack-clark": "Jack Clark",
    "person:nathan-lambert": "Nathan Lambert", "person:yoshua-bengio": "Yoshua Bengio",
    "person:jan-leike": "Jan Leike", "person:paul-christiano": "Paul Christiano",
}
TOKEN = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _hash(value, *, ascii_only=False) -> str:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
           if ascii_only else _json(value))
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ReviewedProfile:
    """A separately reviewed explicit subset; never modifies the exact-eight pilot."""
    profile_id: str
    version: str
    source_pins: tuple[dict, ...]
    max_items_per_source: int = 100

    def __post_init__(self):
        if (not TOKEN.fullmatch(self.profile_id) or not TOKEN.fullmatch(self.version)
                or not 1 <= self.max_items_per_source <= 500
                or not 1 <= len(self.source_pins) <= 8):
            raise StorageStop("invalid explicit reviewed profile")
        original = json.loads(Path(__file__).with_name("pilot_sources.json").read_text())
        by_id = {p["id"]: p for p in original}
        ids = [p.get("id") for p in self.source_pins]
        if len(set(ids)) != len(ids) or any(by_id.get(p.get("id")) != p for p in self.source_pins):
            raise StorageStop("subset must contain exact existing reviewed pilot pins")
        # Copy caller-owned nested objects; a changed profile never changes a running stream.
        object.__setattr__(self, "source_pins", tuple(json.loads(_json(self.source_pins))))

    @property
    def digest(self):
        return _hash(asdict(self))

    def validate(self, registry: list[dict]) -> list[dict]:
        by_id = {}
        for row in registry:
            if row.get("id") in by_id:
                raise StorageStop("duplicate registry source identity")
            by_id[row.get("id")] = row
        selected = []
        for pin in self.source_pins:
            row = by_id.get(pin["id"])
            if (row is None or {k: row.get(k) for k in PIN_KEYS} != pin
                    or row.get("collection_policy") is not None
                    or row.get("allowed_fetch_origins") not in (None, [])):
                raise StorageStop("reviewed source identity, rights or origin changed")
            if pin["owner_person_id"] == "person:victoria-krakovna":
                raise StorageStop("source requires a statement candidate; metadata-only profile is incompatible")
            public_url(pin["canonical_url"])
            selected.append(dict(row))
        return selected


@dataclass(frozen=True)
class QueueLimits:
    shard_bytes: int = 64 * 1024 * 1024
    seal_seconds: float = 300.0
    record_bytes: int = 16 * 1024
    records_per_shard: int = 4096
    index_entries: int = 65536
    state_bytes: int = 16 * 1024 * 1024
    pause_bytes: int = 20_000_000_000
    resume_bytes: int = 12_500_000_000
    retry_attempts: int = 6

    def __post_init__(self):
        if (not 1 <= self.shard_bytes <= 64 * 1024 * 1024
                or not 0 < self.seal_seconds <= 300 or not math.isfinite(self.seal_seconds)
                or not 256 <= self.record_bytes <= min(CHUNK_BYTES, self.shard_bytes)
                or not 1 <= self.records_per_shard <= 4096
                or not 1 <= self.index_entries <= 65536
                or not 65536 <= self.state_bytes <= 16 * 1024 * 1024
                or not 0 < self.resume_bytes < self.pause_bytes <= 20_000_000_000
                or self.resume_bytes > 12_500_000_000
                or not 1 <= self.retry_attempts <= 6):
            raise StorageStop("invalid bounded queue limits")

    @property
    def reservation(self):
        # Payload + staged copy, new state + staged copy + atomic index replacement.
        return 2 * self.shard_bytes + 3 * self.state_bytes + METADATA_RESERVE


@dataclass
class SourceSlice:
    """Producer output must be bounded; validators advance only after full iteration.

    Producers must honor stop() and max_items before allocating/fetching. The
    queue also bounds serialization, record count, bytes and elapsed time.
    """
    records: Iterable[dict]
    cursor_after: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    feed_complete: bool = True


class RestorableBackend(Protocol):
    """The strict DriveBackend methods plus a bounded read-only byte stream.

    No implementation may fabricate about/quota, IDs or resumable semantics to
    adapt the ordinary document connector. Authentication is caller-injected.
    """
    def download_chunks(self, file_id: str, *, chunk_bytes: int,
                        max_bytes: int) -> Iterable[bytes]: ...


@dataclass(frozen=True)
class RecoveryPin:
    manifest_id: str
    manifest_sha256: str
    generation: int


class _GuardedBackend:
    def __init__(self, backend, stop):
        self.backend, self.stop = backend, stop

    def __getattr__(self, name):
        method = getattr(self.backend, name)
        def call(*args, **kwargs):
            if self.stop():
                raise StorageStop("cancelled or deadline reached; pending transaction retained")
            try:
                return method(*args, **kwargs)
            except StorageStop:
                raise
            except Exception:
                raise StorageStop("transport outcome unknown; reconcile durable IDs before retry") from None
        return call


class ContinuousQueue:
    def __init__(self, *, scratch: BoundedScratch, drive, pin: DrivePin,
                 profile: ReviewedProfile, stream_id: str, limits: QueueLimits | None = None,
                 clock: Callable[[], float] = time.time,
                 fault: Callable[[str], None] | None = None):
        if not TOKEN.fullmatch(stream_id) or stream_id in {".", ".."}:
            raise StorageStop("explicit stable stream identity required")
        if scratch.min_free_bytes < 5_000_000_000:
            raise StorageStop("continuous queue requires the five GB free reserve")
        if not callable(getattr(drive, "download_chunks", None)):
            raise StorageStop("bounded verified remote reads are required; connector is insufficient")
        self.scratch, self.drive, self.pin, self.profile = scratch, drive, pin, profile
        self.stream_id, self.limits, self.clock = stream_id, limits or QueueLimits(), clock
        self.profile_hash = profile.digest
        self.fault = fault or (lambda phase: None)
        self._stop = lambda: False

    def _supervisor(self):
        return Supervisor(self.scratch, _GuardedBackend(self.drive, self._stop), self.pin)

    def _save(self, journal):
        self.scratch.atomic_json(JOURNAL, journal)

    def _identity(self):
        return {"schema": SCHEMA, "stream_id": self.stream_id,
                "profile_hash": self.profile_hash, "pin": asdict(self.pin),
                "limits": asdict(self.limits)}

    def _journal(self):
        journal = self.scratch.read_json(JOURNAL)
        if journal and any(journal.get(k) != v for k, v in self._identity().items()):
            raise StorageStop("queue stream, account, profile or limits changed")
        if self.profile.digest != self.profile_hash:
            raise StorageStop("profile mutated after queue creation")
        return journal

    def _remove(self, relative):
        # Fixed namespace only, never journal-supplied paths or the writer lock.
        if relative not in {PAYLOAD, SNAPSHOT, PAYLOAD + ".writing", SNAPSHOT + ".writing"}:
            raise StorageStop("invalid queue cleanup target")
        self.scratch._mutation_path(relative).unlink(missing_ok=True)

    def _chunks(self, relative):
        with self.scratch.path(relative).open("rb") as handle:
            while block := handle.read(CHUNK_BYTES):
                yield block

    @staticmethod
    def _coalesce(lines):
        buffered = bytearray()
        for line in lines:
            if not isinstance(line, bytes) or len(line) > CHUNK_BYTES:
                raise StorageStop("queue line exceeds bounded physical write size")
            if len(buffered) + len(line) > CHUNK_BYTES:
                yield bytes(buffered)
                buffered.clear()
            buffered.extend(line)
        if buffered:
            yield bytes(buffered)

    def _lines(self, relative):
        path = self.scratch.path(relative)
        if not path.exists():
            return
        if path.stat().st_size > self.limits.state_bytes:
            raise StorageStop("dedup state exceeds explicit limit")
        with path.open("rb") as handle:
            while line := handle.readline(65537):
                if len(line) > 65536 or not line.endswith(b"\n"):
                    raise StorageStop("invalid bounded state line")
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError):
                    raise StorageStop("invalid state JSON") from None
                if not isinstance(row, dict):
                    raise StorageStop("invalid state row")
                yield row

    def _state(self, relative=INDEX):
        rows = self._lines(relative)
        header = next(rows, None)
        if header is None:
            return None
        expected_keys = set(self._identity()) | {"kind", "generation", "sources", "index_entries",
                                                  "previous_manifest_id", "previous_manifest_sha256"}
        if set(header) != expected_keys or not isinstance(header.get("sources"), dict):
            raise StorageStop("unexpected state snapshot fields")
        for source in header["sources"].values():
            if not isinstance(source, dict) or set(source) - {"cursor", "etag", "last_modified", "retry_not_before", "failures"}:
                raise StorageStop("unexpected source state fields")
            for field in ("cursor", "etag", "last_modified"):
                value = source.get(field)
                if value is not None and (not isinstance(value, str) or len(value.encode()) > 2048):
                    raise StorageStop("source state validator exceeds bound")
            if (not isinstance(source.get("retry_not_before", 0), (int, float))
                    or not math.isfinite(source.get("retry_not_before", 0))
                    or not isinstance(source.get("failures", 0), int)
                    or not 0 <= source.get("failures", 0) <= 32):
                raise StorageStop("source state backoff is invalid")
        if (header.get("kind") != "state" or any(header.get(k) != v for k, v in self._identity().items())
                or not isinstance(header.get("generation"), int)
                or not 1 <= header["generation"] <= 2**53
                or set(header.get("sources", {})) - {p["id"] for p in self.profile.source_pins}):
            raise StorageStop("state snapshot identity or source mismatch")
        seen, versions = set(), {}
        for row in rows:
            if (set(row) != {"key", "hash", "version"} or not HEX.fullmatch(str(row["key"]))
                    or not HEX.fullmatch(str(row["hash"])) or not isinstance(row["version"], int)
                    or not 1 <= row["version"] <= self.limits.index_entries):
                raise StorageStop("invalid dedup index entry")
            pair = (row["key"], row["hash"])
            if pair in seen or row["version"] != versions.get(row["key"], 0) + 1:
                raise StorageStop("duplicate or discontinuous dedup state")
            seen.add(pair)
            versions[row["key"]] = row["version"]
            if len(seen) > self.limits.index_entries:
                raise StorageStop("dedup index entry limit reached; review required")
        if len(seen) != header.get("index_entries"):
            raise StorageStop("dedup snapshot count mismatch")
        return header

    def _lookup(self, key, content_hash, delta):
        version = 0
        rows = self._lines(INDEX)
        next(rows, None)
        for row in rows:
            if row["key"] == key:
                if row["hash"] == content_hash:
                    return row["version"], True
                version = max(version, row["version"])
        for row in delta.values():
            if row["key"] == key:
                if row["hash"] == content_hash:
                    return row["version"], True
                version = max(version, row["version"])
        return version + 1, False

    def _record(self, row, source):
        allowed = {"upstream_id", "canonical_url", "title", "published_at", "observed_at", "author"}
        if not isinstance(row, dict) or set(row) - allowed:
            raise StorageStop("record contains disallowed raw/evidence/claim fields")
        caps = {"upstream_id": 2048, "canonical_url": 4096, "title": 4096,
                "published_at": 80, "observed_at": 80, "author": 512}
        for field, cap in caps.items():
            value = row.get(field)
            if value is not None and (not isinstance(value, str) or len(value.encode("utf-8")) > cap):
                raise StorageStop("metadata field exceeds explicit bound")
        if not row.get("canonical_url") or not row.get("observed_at"):
            raise StorageStop("source URL and observation time are mandatory")
        public_url(row["canonical_url"])
        expected_author = SOURCE_AUTHORS.get(source["owner_person_id"])
        if expected_author and row.get("author") != expected_author:
            raise StorageStop("metadata item does not match the reviewed exact author rule")
        if not row.get("upstream_id") and row["canonical_url"] == source["canonical_url"]:
            raise StorageStop("metadata item lacks a stable upstream identity or item URL")
        content = {k: row.get(k) for k in sorted(allowed - {"observed_at"})}
        key = _hash([source["id"], row.get("upstream_id") or row["canonical_url"]])
        return {"schema": SCHEMA, "source_id": source["id"], "source_url": source["canonical_url"],
                "logical_key": key, "content_hash": _hash(content), "profile_hash": self.profile_hash,
                **{k: row.get(k) for k in sorted(allowed)}}

    def _download(self, file_id, size):
        try:
            stream = _GuardedBackend(self.drive, self._stop).download_chunks(
                file_id, chunk_bytes=CHUNK_BYTES, max_bytes=size)
            iterator = iter(stream)
            while True:
                # A lazy backend performs its next request inside next(). Stop
                # before advancing it as well as after an in-flight response.
                if self._stop():
                    raise StorageStop("cancelled or deadline reached during bounded read")
                try:
                    block = next(iterator)
                except StopIteration:
                    break
                if self._stop():
                    raise StorageStop("cancelled or deadline reached during bounded read")
                yield block
        except StorageStop:
            raise
        except Exception:
            raise StorageStop("bounded remote read failed; retained state requires reconciliation") from None

    def _remote_read(self, file_id, *, size, sha256, md5, key, target):
        if not 0 < size <= self.limits.state_bytes or not HEX.fullmatch(str(sha256)):
            raise StorageStop("remote read exceeds bound or lacks pinned hash")
        meta = _GuardedBackend(self.drive, self._stop).get(file_id)
        entry = {"remote_id": file_id, "size": size, "sha256": sha256, "md5": md5, "key": key}
        self._supervisor()._remote_verify(entry, meta or {})
        stream = self._download(file_id, size)
        digest = self.scratch.atomic_bytes(target, stream, max_bytes=size)
        if digest != {"size": size, "sha256": sha256, "md5": md5}:
            raise StorageStop("download checksum mismatch; local state not advanced")
        return digest

    def _manifest(self, file_id, expected_hash=None):
        meta = _GuardedBackend(self.drive, self._stop).get(file_id) or {}
        try:
            size = int(meta["size"])
            sha = expected_hash or meta["appProperties"]["sha256"]
            key = meta["appProperties"]["pdoom_key"]
            md5 = meta["md5Checksum"]
        except (KeyError, TypeError, ValueError):
            raise StorageStop("remote manifest receipt incomplete") from None
        if not 0 < size <= METADATA_RESERVE // 4:
            raise StorageStop("remote manifest exceeds metadata limit")
        self._supervisor()._remote_verify({"remote_id": file_id, "size": size, "sha256": sha,
                                          "md5": md5, "key": key}, meta)
        data = bytearray()
        for block in self._download(file_id, size):
            if not isinstance(block, bytes) or len(block) > CHUNK_BYTES or len(data) + len(block) > size:
                raise StorageStop("remote manifest read exceeded bounds")
            data.extend(block)
        if (len(data) != size or hashlib.sha256(data).hexdigest() != sha
                or hashlib.md5(data, usedforsecurity=False).hexdigest() != md5):
            raise StorageStop("remote manifest checksum mismatch")
        try:
            result = json.loads(data)
        except (ValueError, UnicodeError):
            raise StorageStop("invalid remote manifest") from None
        if (not isinstance(result, dict) or result.get("pin") != asdict(self.pin)
                or not HEX.fullmatch(str(result.get("batch_id")))
                or key != result["batch_id"] + "-manifest"):
            raise StorageStop("manifest account or transaction identity mismatch")
        files = result.get("files")
        if not isinstance(files, list) or not 1 <= len(files) <= 2:
            raise StorageStop("manifest file count mismatch")
        try:
            descriptors = [{k: row[k] for k in ("name", "size", "sha256", "retention")} for row in files]
        except (KeyError, TypeError):
            raise StorageStop("manifest descriptors are malformed") from None
        if _hash({"files": descriptors, "cursor_after": result.get("cursor_after"),
                  "pin": result["pin"]}, ascii_only=True) != result["batch_id"]:
            raise StorageStop("manifest batch hash mismatch")
        return result, sha

    def _head(self):
        journal = self._journal() or {}
        return {"manifest_id": journal.get("manifest_id"),
                "manifest_sha256": journal.get("manifest_sha256")}

    def _verify_local(self, relative, descriptor):
        path = self.scratch.path(relative)
        if not path.is_file():
            raise StorageStop("missing dedup snapshot; explicit restore is required")
        if path.stat().st_size != descriptor["size"] or not 0 < descriptor["size"] <= self.limits.state_bytes:
            raise StorageStop("local snapshot size mismatch")
        digest, size = hashlib.sha256(), 0
        for block in self._chunks(relative):
            size += len(block)
            digest.update(block)
        if size != descriptor["size"] or digest.hexdigest() != descriptor["sha256"]:
            raise StorageStop("local snapshot checksum mismatch")

    def _finish(self, journal, checkpoint):
        expected = journal["cursor_after"]
        if checkpoint.get("cursor_after") != expected:
            raise StorageStop("checkpoint does not match sealed generation")
        manifest, manifest_hash = self._manifest(checkpoint["manifest_id"], journal.get("restore_manifest_sha256"))
        if (manifest["batch_id"] != checkpoint["batch_id"] or manifest["cursor_after"] != expected
                or manifest.get("previous_manifest_id") != journal.get("previous_manifest_id")):
            raise StorageStop("manifest chain differs from sealed generation")
        self.fault("manifest_verified")
        self._verify_local(SNAPSHOT, journal["snapshot"])
        self._state(SNAPSHOT)
        self.scratch.atomic_bytes(INDEX, self._chunks(SNAPSHOT),
                                  max_bytes=journal["snapshot"]["size"])
        self.fault("index_installed")
        committed = {**self._identity(), "phase": "cleaning", "generation": expected["generation"],
                     "manifest_id": checkpoint["manifest_id"], "manifest_sha256": manifest_hash,
                     "last_outcome": expected["status"], "index": journal["snapshot"]}
        self._save(committed)
        self.fault("checkpoint_installed")
        return self._clean(committed)

    def _clean(self, journal):
        self.scratch._require_lease()
        checkpoint = self.scratch.read_json(CHECKPOINT) or {}
        cursor = checkpoint.get("cursor_after", {})
        if (checkpoint.get("manifest_id") != journal.get("manifest_id")
                or cursor.get("generation") != journal.get("generation")
                or cursor.get("profile_hash") != self.profile_hash):
            raise StorageStop("cleanup head differs from the durable checkpoint")
        self._verify_local(INDEX, journal["index"])
        for relative in (PAYLOAD, SNAPSHOT, PAYLOAD + ".writing", SNAPSHOT + ".writing"):
            self._remove(relative)
        self.fault("cleanup")
        journal = {**journal, "phase": "collecting", "attempts": 0, "retry_not_before": 0}
        self._save(journal)
        return {"status": "committed", "generation": journal["generation"],
                "manifest_id": journal["manifest_id"], "manifest_sha256": journal["manifest_sha256"],
                "outcome": journal["last_outcome"], "public_import": False}

    def _upload(self, journal):
        checkpoint = self.scratch.read_json(CHECKPOINT)
        if checkpoint and checkpoint.get("cursor_after") == journal["cursor_after"]:
            pending = self.scratch.read_json(PENDING)
            if pending:
                if pending.get("batch_id") != checkpoint["batch_id"]:
                    raise StorageStop("committed queue has a conflicting pending transaction")
                self._supervisor().resume()
            return self._finish(journal, checkpoint)
        if self.clock() < journal.get("retry_not_before", 0):
            return {"status": "paused", "reason": "backoff", "retry_not_before": journal["retry_not_before"]}
        if journal.get("attempts", 0) >= self.limits.retry_attempts:
            raise StorageStop("retry attempt bound reached; explicit operator reconciliation required")
        artifacts = []
        for relative, key in ((PAYLOAD, "payload"), (SNAPSHOT, "snapshot")):
            descriptor = journal.get(key)
            if descriptor and descriptor["size"]:
                artifacts.append(Artifact(descriptor["name"], descriptor["size"], descriptor["sha256"],
                                          journal["retention"], lambda p=relative: self._chunks(p)))
        journal["phase"] = "uploading"
        self._save(journal)
        self.fault("uploading")
        try:
            checkpoint = self._supervisor().submit(artifacts, cursor_after=journal["cursor_after"])
            self.fault("supervisor_committed")
            return self._finish(journal, checkpoint)
        except StorageStop:
            durable = self._journal()
            if durable and durable.get("phase") in {"cleaning", "collecting"}:
                # _finish may already have installed the index and durable head.
                # Never roll its cleanup state back using this stale sealed copy.
                raise
            journal["attempts"] = journal.get("attempts", 0) + 1
            journal["retry_not_before"] = self.clock() + min(60, 2**journal["attempts"])
            # Never log arbitrary transport exceptions, response bodies or session URLs.
            journal["phase"] = "sealed"
            self._save(journal)
            raise

    def run_cycle(self, *, registry: list[dict], producer: Callable, released: bool = False,
                  cancelled: Callable[[], bool] | None = None, deadline: float | None = None):
        """Advance/recover one transaction. Repeated calls collect genuinely new slices.

        Returns paused/backoff without sleeping. The caller owns scheduling and
        must have established a sole cloud coordinator; this is not a remote lease.
        """
        self.scratch._require_lease()
        if not released:
            raise StorageStop("explicit bounded profile release required")
        self._stop = lambda: bool((cancelled and cancelled()) or
                                 (deadline is not None and self.clock() >= deadline))
        journal = self._journal()
        if self._stop():
            return {"status": "paused", "reason": "cancelled_or_deadline"}
        self._supervisor().preflight(0)
        checkpoint = self.scratch.read_json(CHECKPOINT)
        if journal and journal["phase"] == "cleaning":
            return self._clean(journal)
        sources = self.profile.validate(registry)
        if journal and journal["phase"] == "restoring":
            return self._finish_restore(journal)
        if journal and journal["phase"] in {"sealed", "uploading"}:
            # Rights/account/root are rechecked before any resumed mutation.
            return self._upload(journal)
        if self.scratch.read_json(PENDING):
            raise StorageStop("another supervisor transaction is pending")
        if not journal:
            if not checkpoint or checkpoint.get("cursor_after") != {"kind": "drive-smoke", "synthetic": True}:
                raise StorageStop("verified synthetic smoke required before a new stream")
            journal = {**self._identity(), "phase": "collecting", "generation": 0,
                       "manifest_id": checkpoint["manifest_id"], "manifest_sha256": None}
            if self.scratch.path(INDEX).exists():
                raise StorageStop("unbound dedup state; explicit restore is required")
            self._save(journal)
        elif not checkpoint or checkpoint.get("manifest_id") != journal["manifest_id"]:
            raise StorageStop("local head mismatch; explicit reconciliation required")
        if journal.get("index"):
            self._verify_local(INDEX, journal["index"])
        state = self._state()
        if journal["generation"] and (not state or state["generation"] != journal["generation"]):
            raise StorageStop("missing or mismatched dedup state; never reset silently")
        if self._stop():
            return {"status": "paused", "reason": "cancelled_or_deadline"}
        admitted = self.scratch.usage() + self.limits.reservation
        if (admitted >= self.limits.pause_bytes or
                (journal.get("capacity_paused") and admitted >= self.limits.resume_bytes)):
            journal["capacity_paused"] = True
            self._save(journal)
            return {"status": "paused", "reason": "capacity", "accounted_with_reservation": admitted}
        self.scratch.check_write(self.limits.reservation)
        self._supervisor().preflight(self.limits.shard_bytes + self.limits.state_bytes + METADATA_RESERVE // 4)
        for relative in (PAYLOAD, SNAPSHOT, PAYLOAD + ".writing", SNAPSHOT + ".writing"):
            self._remove(relative)
        generation = journal["generation"] + 1
        if generation > 2**53:
            raise StorageStop("generation limit reached")
        source_state = json.loads(_json((state or {}).get("sources", {})))
        delta, outcomes = {}, {}
        index_count = (state or {}).get("index_entries", 0)
        count, total, started, interrupted = 0, 0, None, False
        def records():
            nonlocal count, total, started, interrupted
            for source in sources:
                identity = source["id"]
                previous = source_state.get(identity, {})
                if self.clock() < previous.get("retry_not_before", 0):
                    outcomes[identity] = "backoff"
                    continue
                if self._stop():
                    outcomes[identity] = "interrupted"
                    interrupted = True
                    break
                try:
                    result = producer(source, dict(previous), self.profile.max_items_per_source, self._stop)
                    if not isinstance(result, SourceSlice):
                        raise StorageStop("producer returned invalid bounded slice")
                    if not isinstance(result.feed_complete, bool) or not isinstance(result.not_modified, bool):
                        raise StorageStop("slice completeness flags must be explicit booleans")
                    if result.not_modified and (not result.feed_complete or not
                            (previous.get("etag") or previous.get("last_modified"))):
                        raise StorageStop("304 requires a previously completed conditional response")
                    if result.not_modified and result.cursor_after != previous.get("cursor"):
                        raise StorageStop("304 cannot advance an unexamined source cursor")
                    if not result.feed_complete and (not result.cursor_after or result.etag or result.last_modified):
                        raise StorageStop("partial feed requires continuation and no whole-feed validators")
                    source_count = 0
                    complete = True
                    for row in result.records:
                        if result.not_modified:
                            raise StorageStop("304 slice cannot contain new records")
                        if source_count >= self.profile.max_items_per_source:
                            raise StorageStop("producer exceeded reviewed per-source item bound")
                        source_count += 1
                        if (self._stop() or count >= self.limits.records_per_shard
                                or (started is not None and self.clock() - started >= self.limits.seal_seconds)):
                            complete = False
                            interrupted = True
                            break
                        item = self._record(row, source)
                        version, duplicate = self._lookup(item["logical_key"], item["content_hash"], delta)
                        if duplicate:
                            continue
                        item["content_version"] = version
                        raw = _json(item) + b"\n"
                        if len(raw) > self.limits.record_bytes:
                            raise StorageStop("record exceeds explicit byte bound")
                        if total + len(raw) > self.limits.shard_bytes:
                            complete = False
                            interrupted = True
                            break
                        if index_count + len(delta) >= self.limits.index_entries:
                            raise StorageStop("dedup index limit reached; no silent eviction")
                        if started is None:
                            started = self.clock()
                        delta[(item["logical_key"], item["content_hash"])] = {
                            "key": item["logical_key"], "hash": item["content_hash"], "version": version}
                        count += 1
                        total += len(raw)
                        yield raw
                    if not complete:
                        outcomes[identity] = "interrupted"
                        break
                    fields = {"cursor": result.cursor_after, "etag": result.etag,
                              "last_modified": result.last_modified}
                    if any(v is not None and (not isinstance(v, str) or len(v.encode()) > 2048) for v in fields.values()):
                        raise StorageStop("source cursor or validator exceeds bound")
                    source_state[identity] = {**previous, **fields, "retry_not_before": 0, "failures": 0}
                    outcomes[identity] = "unchanged" if result.not_modified else "succeeded" if result.feed_complete else "partial"
                except CollectorFailure as exc:
                    if exc.error_class in {"blocked_by_policy", "unauthorized", "unsafe_url"}:
                        raise StorageStop("source authorization or policy requires review") from None
                    failures = min(previous.get("failures", 0) + 1, 32)
                    delay = min(3600, max(1, exc.retry_after if exc.retry_after is not None else 2**min(failures, 6)))
                    source_state[identity] = {**previous, "failures": failures,
                                              "retry_not_before": self.clock() + delay}
                    outcomes[identity] = "failed"
        payload = self.scratch.atomic_bytes(PAYLOAD, self._coalesce(records()), max_bytes=self.limits.shard_bytes)
        self.fault("payload_written")
        status = "interrupted" if interrupted else "partial" if any(v in {"failed", "backoff", "partial"} for v in outcomes.values()) else "succeeded"
        if outcomes and all(v == "failed" for v in outcomes.values()):
            status = "failed"
        elif outcomes and all(v == "backoff" for v in outcomes.values()):
            status = "skipped"
        header = {**self._identity(), "kind": "state", "generation": generation,
                  "sources": source_state, "index_entries": index_count + len(delta),
                  "previous_manifest_id": journal["manifest_id"],
                  "previous_manifest_sha256": journal.get("manifest_sha256")}
        def snapshot():
            raw = _json(header) + b"\n"
            if len(raw) > 65536:
                raise StorageStop("state header exceeds bound")
            yield raw
            old = self._lines(INDEX)
            next(old, None)
            for row in old:
                yield _json(row) + b"\n"
            for row in delta.values():
                yield _json(row) + b"\n"
        state_descriptor = self.scratch.atomic_bytes(SNAPSHOT, self._coalesce(snapshot()), max_bytes=self.limits.state_bytes)
        self._state(SNAPSHOT)
        self.fault("snapshot_written")
        cursor = {"kind": "continuous-metadata", "schema": SCHEMA, "stream_id": self.stream_id,
                  "generation": generation, "profile_hash": self.profile_hash, "status": status,
                  "outcomes": outcomes, "records": count, "state_sha256": state_descriptor["sha256"],
                  "previous_manifest_sha256": journal.get("manifest_sha256"),
                  "public_import": False, "publication": {"imported": False, "public_revocations_applied": False}}
        retention = {"admitted": True, "mode": "metadata", "decision_id": self.profile_hash,
                     "rights_basis": {s["id"]: s["rights_notes"] for s in sources},
                     "evidence": False, "extraction": False, "public_import": False}
        sealed = {**self._identity(), "phase": "sealed", "generation": generation,
                  "previous_manifest_id": journal["manifest_id"], "cursor_after": cursor,
                  "payload": {**payload, "name": f"g{generation}-metadata.jsonl"},
                  "snapshot": {**state_descriptor, "name": f"g{generation}-state.jsonl"},
                  "retention": retention, "attempts": 0, "retry_not_before": 0}
        self._save(sealed)
        self.fault("sealed")
        return self._upload(sealed)

    def restore(self, recovery: RecoveryPin, *, sole_coordinator_confirmed: bool = False):
        """Restore from an externally verified exact head, never latest-name discovery.

        This deliberately cannot detect another host holding the same root. The
        operator must end the old executor; a local timeout is not fencing.
        """
        self.scratch._require_lease()
        if not sole_coordinator_confirmed:
            raise StorageStop("restoration requires confirmed sole coordinator ownership")
        if self._journal() or self.scratch.read_json(PENDING) or self.scratch.path(INDEX).exists():
            raise StorageStop("restore requires an empty queue workspace")
        self._supervisor().preflight(0)
        if not HEX.fullmatch(str(recovery.manifest_sha256)):
            raise StorageStop("explicit manifest hash pin required")
        manifest, digest = self._manifest(recovery.manifest_id, recovery.manifest_sha256)
        cursor = manifest.get("cursor_after", {})
        if (cursor.get("kind") != "continuous-metadata" or cursor.get("stream_id") != self.stream_id
                or cursor.get("generation") != recovery.generation or cursor.get("profile_hash") != self.profile_hash
                or cursor.get("public_import") is not False):
            raise StorageStop("restored stream, generation or profile mismatch")
        state_files = [r for r in manifest["files"] if r["name"] == f"g{recovery.generation}-state.jsonl"]
        if len(state_files) != 1:
            raise StorageStop("missing or ambiguous remote state snapshot")
        for i, row in enumerate(manifest["files"]):
            self._supervisor()._remote_verify({**row, "key": f"{manifest['batch_id']}-{i}"},
                                              self.drive.get(row["remote_id"]) or {})
            retention = row.get("retention", {})
            if (retention.get("mode") != "metadata" or retention.get("decision_id") != self.profile_hash
                    or retention.get("evidence") is not False or retention.get("extraction") is not False
                    or retention.get("public_import") is not False):
                raise StorageStop("restored retention boundary mismatch")
        row = state_files[0]
        if row["sha256"] != cursor.get("state_sha256"):
            raise StorageStop("state hash differs from committed cursor")
        self._remote_read(row["remote_id"], size=row["size"], sha256=row["sha256"], md5=row["md5"],
                          key=f"{manifest['batch_id']}-{manifest['files'].index(row)}", target=SNAPSHOT)
        header = self._state(SNAPSHOT)
        if (header["generation"] != recovery.generation
                or header["previous_manifest_id"] != manifest.get("previous_manifest_id")
                or header["previous_manifest_sha256"] != cursor.get("previous_manifest_sha256")):
            raise StorageStop("restored manifest/state chain mismatch")
        # Journal first: any interrupted installation remains explicitly recoverable.
        journal = {**self._identity(), "phase": "restoring", "generation": recovery.generation,
                   "previous_manifest_id": manifest.get("previous_manifest_id"), "cursor_after": cursor,
                   "snapshot": row, "retention": row["retention"], "attempts": 0, "retry_not_before": 0}
        checkpoint = {"schema_version": "1", "pin": asdict(self.pin), "batch_id": manifest["batch_id"],
                      "manifest_id": recovery.manifest_id, "cursor_after": cursor}
        journal["restore_checkpoint"] = checkpoint
        journal["restore_manifest_sha256"] = recovery.manifest_sha256
        self._save(journal)
        self.fault("restore_journal")
        return self._finish_restore(journal)

    def _finish_restore(self, journal):
        checkpoint = journal["restore_checkpoint"]
        manifest, _ = self._manifest(checkpoint["manifest_id"], journal["restore_manifest_sha256"])
        if manifest["cursor_after"] != journal["cursor_after"]:
            raise StorageStop("restore journal no longer matches pinned manifest")
        self._verify_local(SNAPSHOT, journal["snapshot"])
        self._state(SNAPSHOT)
        self.scratch.atomic_json(CHECKPOINT, checkpoint)
        self.fault("restore_checkpoint")
        return self._finish(journal, checkpoint)
