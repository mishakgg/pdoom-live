"""One writer, F:-only paths and per-write accounting, including atomic copies."""
from __future__ import annotations

from contextlib import AbstractContextManager
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat
from typing import Callable, Iterable

HARD_MAX_BYTES = 25_000_000_000  # Decimal GB, never 25 GiB.
TASK_ROOT = PureWindowsPath(r"F:\CodexTaskScratch\pdoom-live")
COLLECTION_ROOT = Path(str(TASK_ROOT / "collection"))
METADATA_RESERVE = 4 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


class StorageStop(RuntimeError):
    """A fail-closed storage/account/verification condition; no raw API errors."""


def validate_windows_path(value: str) -> None:
    p = PureWindowsPath(value)
    if not p.is_absolute() or p.drive.lower() != "f:" or ".." in p.parts:
        raise StorageStop("scratch must be an absolute F: path")
    if not p.is_relative_to(TASK_ROOT):
        raise StorageStop("scratch must stay inside the designated task tree")
    if any(":" in part for part in p.parts[1:]):
        raise StorageStop("alternate data streams are prohibited")


def _plain(path: Path) -> None:
    """Reject symbolic links, Windows junctions and all other reparse points."""
    for p in (path, *path.parents):
        if p.exists() or p.is_symlink():
            info = p.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise StorageStop("scratch contains a link or reparse point")


class BoundedScratch(AbstractContextManager):
    """All collector writes must use this lease; external writers are unsupported.

    The one fixed root contains staging, retries, state, caches, logs and TEMP.
    A process-exit-released OS lock avoids time-based stale-lock stealing.
    """
    def __init__(self, *, max_bytes: int = HARD_MAX_BYTES,
                 min_free_bytes: int = 5_000_000_000,
                 free_bytes: Callable[[Path], int] | None = None):
        if not METADATA_RESERVE < max_bytes <= HARD_MAX_BYTES or min_free_bytes < 0:
            raise StorageStop("invalid byte budget or disk reserve")
        self.root = COLLECTION_ROOT
        # No supported configurable root or C: fallback.
        validate_windows_path(str(self.root))
        _plain(self.root)
        self.max_bytes = max_bytes
        self.min_free_bytes = min_free_bytes
        self.free_bytes = free_bytes or (lambda p: shutil.disk_usage(p).free)
        self._lock = None

    def __enter__(self):
        _plain(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        _plain(self.root)
        lock_path = self.root / "writer.lock"
        _plain(lock_path)
        self._lock = lock_path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self._lock.seek(0)
                if not self._lock.read(1):
                    self._lock.write(b"0")
                    self._lock.flush()
                self._lock.seek(0)
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lock.close()
            self._lock = None
            raise StorageStop("another collection writer holds the lease") from None
        try:
            self.check_write(0)
            for name in ("temp", "cache", "logs", "staging", "state"):
                self.path(name).mkdir(exist_ok=True)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *args):
        if self._lock is not None:
            if os.name == "nt":
                import msvcrt
                self._lock.seek(0)
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_UNLCK, 1)
            self._lock.close()
            self._lock = None

    def path(self, relative: str) -> Path:
        p = Path(relative)
        if p.is_absolute() or p.drive or ".." in p.parts or ":" in relative or "\\" in relative:
            raise StorageStop("invalid relative scratch path")
        for part in p.parts:
            base = part.split(".")[0].upper()
            device = base in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
            numbered = (base.startswith(("COM", "LPT")) and len(base) == 4
                        and base[-1] in "123456789¹²³")
            if device or numbered or part.endswith((" ", ".")) or any(c in part for c in '<>|?*"'):
                raise StorageStop("invalid Windows scratch filename")
        target = self.root / p
        _plain(target)
        if not target.resolve().is_relative_to(self.root.resolve()):
            raise StorageStop("scratch path escapes root")
        return target

    def usage(self) -> int:
        _plain(self.root)
        size = 0
        for base, dirs, files in os.walk(self.root, followlinks=False):
            for name in dirs + files:
                p = Path(base) / name
                _plain(p)
                if p.is_file():
                    info = p.stat()
                    if info.st_nlink != 1:
                        raise StorageStop("scratch hard links are prohibited")
                    size += info.st_size
        return size

    def check_write(self, additional_bytes: int, *, metadata: bool = False) -> None:
        if self._lock is None:
            raise StorageStop("a writer lease is required")
        if additional_bytes < 0:
            raise StorageStop("negative reservation")
        reserve = 0 if metadata else METADATA_RESERVE
        if self.usage() + additional_bytes + reserve > self.max_bytes:
            raise StorageStop("collection byte cap reached")
        if self.free_bytes(self.root) - additional_bytes < self.min_free_bytes:
            raise StorageStop("low disk reserve reached")

    def atomic_json(self, relative: str, payload: dict) -> None:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(raw) > METADATA_RESERVE // 4:
            raise StorageStop("state/manifest exceeds bounded metadata size")
        self.atomic_bytes(relative, [raw], max_bytes=len(raw), metadata=True)

    def atomic_bytes(self, relative: str, chunks: Iterable[bytes], *,
                     max_bytes: int, metadata: bool = False) -> dict:
        if not 0 <= max_bytes <= self.max_bytes:
            raise StorageStop("invalid stream limit")
        target = self.path(relative)
        temporary = self.path(relative + ".writing")
        target.parent.mkdir(parents=True, exist_ok=True)
        # An interrupted gateway write is ours; an input/source file is never removed.
        temporary.unlink(missing_ok=True)
        self.check_write(max_bytes, metadata=metadata)
        sha = hashlib.sha256()
        md5 = hashlib.md5(usedforsecurity=False)
        written = 0
        try:
            with temporary.open("xb") as handle:
                for chunk in chunks:
                    if not isinstance(chunk, bytes):
                        raise StorageStop("stream chunks must be bytes")
                    if len(chunk) > CHUNK_BYTES:
                        raise StorageStop("stream chunk exceeds memory bound")
                    if written + len(chunk) > max_bytes:
                        raise StorageStop("stream exceeded admitted size")
                    self.check_write(len(chunk), metadata=metadata)
                    handle.write(chunk)
                    handle.flush()
                    written += len(chunk)
                    sha.update(chunk)
                    md5.update(chunk)
                os.fsync(handle.fileno())
            self.path(relative)  # Recheck containment before atomic replacement.
            os.replace(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return {"size": written, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}

    def read_json(self, relative: str) -> dict | None:
        p = self.path(relative)
        if not p.exists():
            return None
        if p.stat().st_size > METADATA_RESERVE // 4:
            raise StorageStop("state is too large")
        try:
            value = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, OSError):
            raise StorageStop("invalid or unreadable durable state") from None

    def runtime_environment(self) -> dict[str, str]:
        """Use before launching a collector. Gateway enforcement is still required."""
        return {"TEMP": str(self.path("temp")), "TMP": str(self.path("temp")),
                "TMPDIR": str(self.path("temp")), "XDG_CACHE_HOME": str(self.path("cache")),
                "PIP_CACHE_DIR": str(self.path("cache/pip")),
                "npm_config_cache": str(self.path("cache/npm")),
                "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
