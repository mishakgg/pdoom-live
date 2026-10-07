"""A bounded private batch is committed only after Drive readback verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Callable, Iterable, Protocol

from .scratch import BoundedScratch, CHUNK_BYTES, StorageStop

MAX_BATCH_BYTES = 128 * 1024 * 1024
MAX_FILES = 32
PENDING = "state/pending.json"
CHECKPOINT = "state/checkpoint.json"


@dataclass(frozen=True)
class DrivePin:
    email: str
    permission_id: str
    folder_id: str

    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise StorageStop("target account email is required")
        for value in (self.permission_id, self.folder_id):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
                raise StorageStop("verified account and folder IDs are required")


@dataclass(frozen=True)
class Artifact:
    name: str
    size: int
    sha256: str
    retention: dict
    chunks: Callable[[], Iterable[bytes]]

    def descriptor(self) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", self.name) or self.name in {".", ".."}:
            raise StorageStop("invalid batch file name")
        if not 0 < self.size <= MAX_BATCH_BYTES or not re.fullmatch(r"[a-f0-9]{64}", self.sha256):
            raise StorageStop("invalid admitted artifact size/hash")
        # These are supplied by the rights/admission owner, never inferred here.
        if self.retention.get("mode") not in {"metadata", "evidence", "licensed_fulltext"}:
            raise StorageStop("retention mode must be explicit")
        if not self.retention.get("decision_id") or not self.retention.get("rights_basis"):
            raise StorageStop("rights decision and basis are required")
        if self.retention.get("admitted") is not True:
            raise StorageStop("artifact has not passed admission")
        return {"name": self.name, "size": self.size, "sha256": self.sha256,
                "retention": self.retention}


class DriveBackend(Protocol):
    def about(self) -> dict: ...
    def get(self, file_id: str) -> dict | None: ...
    def allocate_id(self) -> str: ...
    def begin(self, file_id: str, folder_id: str, metadata: dict, size: int) -> str: ...
    def probe(self, session: str, size: int) -> int | None: ...
    def chunk(self, session: str, offset: int, data: bytes, total: int) -> int: ...


def _private_owner(meta: dict, pin: DrivePin) -> bool:
    owners = meta.get("owners") or []
    permissions = meta.get("permissions") or []
    return (meta.get("ownedByMe") is True and len(owners) == 1
            and owners[0].get("permissionId") == pin.permission_id
            and owners[0].get("emailAddress", "").lower() == pin.email.lower()
            and len(permissions) == 1 and permissions[0].get("type") == "user"
            and permissions[0].get("id") == pin.permission_id
            and permissions[0].get("role") == "owner")


class Supervisor:
    def __init__(self, scratch: BoundedScratch, drive: DriveBackend, pin: DrivePin):
        self.scratch, self.drive, self.pin = scratch, drive, pin

    def preflight(self, bytes_needed: int) -> dict:
        self.scratch.check_write(0)
        about = self.drive.about()
        user = about.get("user") or {}
        if (user.get("emailAddress", "").lower() != self.pin.email.lower()
                or user.get("permissionId") != self.pin.permission_id):
            raise StorageStop("authenticated Drive account does not match pin")
        quota = about.get("storageQuota") or {}
        try:
            limit, usage = int(quota["limit"]), int(quota["usage"])
        except (KeyError, TypeError, ValueError):
            raise StorageStop("Drive quota is unavailable; claimed capacity is not assumed") from None
        if (limit <= 0 or usage < 0 or bytes_needed < 0
                or (bytes_needed > 0 and limit - usage < bytes_needed)):
            raise StorageStop("insufficient verified Drive quota")
        root = self.drive.get(self.pin.folder_id)
        if (not root or root.get("id") != self.pin.folder_id or root.get("trashed") is not False
                or root.get("mimeType") != "application/vnd.google-apps.folder"
                or root.get("driveId") or not root.get("capabilities", {}).get("canAddChildren")
                or not _private_owner(root, self.pin)):
            raise StorageStop("Drive root is unavailable, shared, or outside pinned personal ownership")
        for state in (self.scratch.read_json(CHECKPOINT), self.scratch.read_json(PENDING)):
            if state and state.get("pin") != asdict(self.pin):
                raise StorageStop("durable state belongs to another account/root")
        return {"quota_limit_bytes": limit, "quota_usage_bytes": usage,
                "quota_free_bytes": limit - usage, "local_bytes": self.scratch.usage()}

    def submit(self, artifacts: list[Artifact], *, cursor_after: dict,
               cleanup_inputs: list[str] | None = None) -> dict:
        if not 0 < len(artifacts) <= MAX_FILES:
            raise StorageStop("invalid batch file count")
        descriptors = [a.descriptor() for a in artifacts]
        if len({a["name"] for a in descriptors}) != len(descriptors):
            raise StorageStop("duplicate batch file names")
        if sum(a["size"] for a in descriptors) > MAX_BATCH_BYTES:
            raise StorageStop("batch byte bound exceeded")
        # Caller cannot queue an unbounded backlog: one pending batch only.
        identity = {"files": descriptors, "cursor_after": cursor_after, "pin": asdict(self.pin)}
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(encoded) > 128 * 1024:
            raise StorageStop("batch metadata exceeds bound")
        batch_id = hashlib.sha256(encoded).hexdigest()
        self.preflight(0)  # Identity/privacy validation also applies to idempotent cleanup.
        checkpoint = self.scratch.read_json(CHECKPOINT)
        if checkpoint and checkpoint.get("batch_id") == batch_id:
            if self.scratch.read_json(PENDING):
                self.resume()
            return checkpoint
        pending = self.scratch.read_json(PENDING)
        if pending and pending.get("batch_id") != batch_id:
            raise StorageStop("finish pending batch before accepting another")
        if pending and pending["phase"] == "uploading":
            return self.resume()
        if not pending:
            clean = cleanup_inputs or []
            for relative in clean:
                if not relative.startswith("runner/"):
                    raise StorageStop("only tracked runner inputs may be cleaned")
                self.scratch.path(relative)
            pending = {**identity, "batch_id": batch_id, "phase": "preparing",
                       "cleanup_inputs": clean, "entries": []}
            for i, descriptor in enumerate(descriptors):
                pending["entries"].append({**descriptor, "local": f"staging/{batch_id}/{i}.bin",
                                            "key": f"{batch_id}-{i}", "staged": False})
        # Reserve uncommitted files plus the bounded manifest before staging.
        self.preflight(self._remaining_upload_bytes(pending, checkpoint))
        self.scratch.atomic_json(PENDING, pending)
        for artifact, entry in zip(artifacts, pending["entries"]):
            if entry["staged"]:
                self._local_verify(entry)
                continue
            digest = self.scratch.atomic_bytes(entry["local"], artifact.chunks(), max_bytes=entry["size"])
            if digest["size"] != entry["size"] or digest["sha256"] != entry["sha256"]:
                raise StorageStop("artifact bytes differ from admitted descriptor")
            entry.update(digest, staged=True)
            self.scratch.atomic_json(PENDING, pending)
        pending["phase"] = "uploading"
        self.scratch.atomic_json(PENDING, pending)
        return self.resume()

    def _local_verify(self, entry: dict) -> None:
        p = self.scratch.path(entry["local"])
        if not p.is_file() or p.stat().st_size != entry["size"]:
            raise StorageStop("pending local bytes are missing or changed")
        sha = hashlib.sha256()
        md5 = hashlib.md5(usedforsecurity=False)
        with p.open("rb") as handle:
            while data := handle.read(CHUNK_BYTES):
                sha.update(data)
                md5.update(data)
        if sha.hexdigest() != entry["sha256"] or md5.hexdigest() != entry["md5"]:
            raise StorageStop("pending local checksum mismatch")

    def _remote_verify(self, entry: dict, remote: dict) -> None:
        try:
            size = int(remote.get("size", -1))
        except (TypeError, ValueError):
            size = -1
        if (remote.get("id") != entry["remote_id"] or remote.get("trashed") is not False
                or remote.get("parents") != [self.pin.folder_id]
                or not _private_owner(remote, self.pin)
                or remote.get("appProperties", {}).get("pdoom_key") != entry["key"]
                or size != entry["size"] or remote.get("md5Checksum") != entry["md5"]
                or (remote.get("sha256Checksum") and remote["sha256Checksum"] != entry["sha256"])):
            raise StorageStop("remote bytes, checksum, ownership or parent verification failed")

    def _upload(self, entry: dict, pending: dict) -> None:
        self._local_verify(entry)
        if not entry.get("remote_id"):
            remote_id = self.drive.allocate_id()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", remote_id):
                raise StorageStop("invalid generated remote file ID")
            entry["remote_id"] = remote_id
            self.scratch.atomic_json(PENDING, pending)  # Durable ID BEFORE remote mutation.
        remote = self.drive.get(entry["remote_id"])
        if remote:
            self._remote_verify(entry, remote)
            return  # Lost completion response: reuse verified preallocated file.
        session = entry.get("session")
        offset = self.drive.probe(session, entry["size"]) if session else None
        if offset is None:
            metadata = {"name": entry["name"], "appProperties": {"pdoom_key": entry["key"],
                        "sha256": entry["sha256"]}, "mimeType": "application/octet-stream"}
            session = self.drive.begin(entry["remote_id"], self.pin.folder_id, metadata, entry["size"])
            entry["session"] = session
            self.scratch.atomic_json(PENDING, pending)
            offset = 0
        if not 0 <= offset <= entry["size"]:
            raise StorageStop("invalid resumable offset")
        with self.scratch.path(entry["local"]).open("rb") as handle:
            handle.seek(offset)
            calls = 0
            max_calls = (entry["size"] + CHUNK_BYTES - 1) // CHUNK_BYTES + 3
            while offset < entry["size"]:
                calls += 1
                if calls > max_calls:
                    raise StorageStop("resumable request budget exhausted; retain batch")
                data = handle.read(min(CHUNK_BYTES, entry["size"] - offset))
                advanced = self.drive.chunk(session, offset, data, entry["size"])
                if not offset < advanced <= offset + len(data):
                    raise StorageStop("resumable upload did not make bounded progress")
                offset = advanced
                handle.seek(offset)
                entry["offset"] = offset
                self.scratch.atomic_json(PENDING, pending)
        remote = self.drive.get(entry["remote_id"])
        if not remote:
            raise StorageStop("completed upload is not available for readback")
        self._remote_verify(entry, remote)

    @staticmethod
    def _manifest_bytes(pending: dict, checkpoint: dict | None, *, reserve: bool = False) -> bytes:
        files = []
        for entry in pending["entries"]:
            row = {k: entry[k] for k in ("name", "size", "sha256", "retention")}
            # Generated IDs are bounded to 200 ASCII bytes. Before allocation this
            # gives a conservative manifest reservation, without arbitrary headroom.
            row["md5"] = entry.get("md5", "0" * 32) if reserve else entry["md5"]
            row["remote_id"] = entry.get("remote_id", "x" * 200) if reserve else entry["remote_id"]
            files.append(row)
        receipt = {"schema_version": "1", "batch_id": pending["batch_id"], "pin": pending["pin"],
                   "cursor_after": pending["cursor_after"], "previous_manifest_id":
                   (checkpoint or {}).get("manifest_id"), "files": files}
        return json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    def _remaining_upload_bytes(self, pending: dict, checkpoint: dict | None) -> int:
        remaining = 0
        for entry in pending["entries"] + ([pending["manifest"]] if pending.get("manifest") else []):
            if entry.get("staged", True):
                self._local_verify(entry)
            remote = self.drive.get(entry["remote_id"]) if entry.get("remote_id") else None
            if remote:
                self._remote_verify(entry, remote)
            else:
                # Reserve the full incomplete object: Drive quota may only account
                # for its bytes on completion, regardless of the resumable offset.
                remaining += entry["size"]
        if not pending.get("manifest"):
            remaining += len(self._manifest_bytes(pending, checkpoint, reserve=True))
        return remaining

    def resume(self) -> dict:
        pending = self.scratch.read_json(PENDING)
        if not pending:
            return self.scratch.read_json(CHECKPOINT) or {}
        self.preflight(0)
        checkpoint = self.scratch.read_json(CHECKPOINT)
        if checkpoint and checkpoint.get("batch_id") == pending["batch_id"]:
            # No remote mutation or upload capacity is needed after commit.
            self._cleanup(pending)
            return checkpoint
        if pending["phase"] == "preparing":
            raise StorageStop("incomplete preparation; restage the same admitted batch")
        self.preflight(self._remaining_upload_bytes(pending, checkpoint))
        for entry in pending["entries"]:
            self._upload(entry, pending)
        if not pending.get("manifest"):
            raw = self._manifest_bytes(pending, checkpoint)
            relative = f"staging/{pending['batch_id']}/manifest.json"
            digest = self.scratch.atomic_bytes(relative, [raw], max_bytes=len(raw), metadata=True)
            pending["manifest"] = {"name": f"manifest-{pending['batch_id']}.json", "local": relative,
                                   "key": pending["batch_id"] + "-manifest", **digest}
            self.scratch.atomic_json(PENDING, pending)
        self._upload(pending["manifest"], pending)
        checkpoint = {"schema_version": "1", "pin": pending["pin"], "batch_id": pending["batch_id"],
                      "manifest_id": pending["manifest"]["remote_id"], "cursor_after": pending["cursor_after"]}
        self.scratch.atomic_json(CHECKPOINT, checkpoint)  # Only full verified manifest commits.
        self._cleanup(pending)
        return checkpoint

    def _cleanup(self, pending: dict) -> None:
        for entry in pending["entries"] + [pending["manifest"]]:
            self.scratch.path(entry["local"]).unlink(missing_ok=True)
        for relative in pending.get("cleanup_inputs", []):
            if not relative.startswith("runner/"):
                raise StorageStop("invalid cleanup target in journal")
            self.scratch.path(relative).unlink(missing_ok=True)
        batch_dir = self.scratch.path(f"staging/{pending['batch_id']}")
        if batch_dir.exists():
            batch_dir.rmdir()  # Nonempty unexpected contents stop cleanup, never recursive delete.
        self.scratch.path(PENDING).unlink(missing_ok=True)
