"""One writer, explicit contained paths and per-write accounting, including copies."""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
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


def _posix_absolute(value: Path) -> Path:
    raw = str(value)
    path = Path(value)
    if (os.name != "posix" or not path.is_absolute() or path.anchor != "/"
            or ".." in path.parts or "\\" in raw or "\x00" in raw):
        raise StorageStop("POSIX paths must be explicit absolute paths without traversal")
    return path


def _owned(path: Path, *, private: bool = False) -> None:
    """Existing POSIX nodes must be ordinary, current-user owned and not writable by others."""
    _plain(path)
    if not path.exists():
        return
    info = path.lstat()
    if info.st_uid != os.geteuid():
        raise StorageStop("POSIX path must be owned by the current user")
    if info.st_mode & (0o077 if private else 0o022):
        raise StorageStop("POSIX scratch must be private" if private else
                          "POSIX path must not be writable by other users")
    if stat.S_ISDIR(info.st_mode):
        required = 0o700 if private else 0o500
        if info.st_mode & required != required:
            raise StorageStop("POSIX directory lacks required owner access")
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise StorageStop("POSIX path must be an ordinary file or directory")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise StorageStop("scratch hard links are prohibited")


def _scan_error(error: OSError) -> None:
    raise StorageStop("unable to safely account for directory contents") from None


@dataclass(frozen=True)
class ScratchPaths:
    """Explicit host layout; selecting a path does not authorize collection or OAuth.

    The caller supplies a trusted, existing workspace. POSIX roots must be
    distinct descendants; seed data is read-only input, outside scratch accounting.
    """
    mode: str = "windows"
    workspace_base: Path | None = None
    collection_root: Path | None = None
    seed_root: Path | None = None

    def validate(self) -> Path:
        if self.mode == "windows":
            if any(p is not None for p in (self.workspace_base, self.collection_root, self.seed_root)):
                raise StorageStop("Windows mode uses the fixed F: collection root")
            validate_windows_path(str(COLLECTION_ROOT))
            if not COLLECTION_ROOT.is_absolute():
                raise StorageStop("Windows mode requires a native absolute Windows filesystem path")
            _plain(COLLECTION_ROOT)
            return COLLECTION_ROOT
        if self.mode != "posix" or any(p is None for p in
                                      (self.workspace_base, self.collection_root, self.seed_root)):
            raise StorageStop("POSIX mode requires workspace, collection and seed roots")
        base, root, seed = map(_posix_absolute,
                              (self.workspace_base, self.collection_root, self.seed_root))
        if (base == Path("/") or root == base or seed == base or not root.is_relative_to(base)
                or not seed.is_relative_to(base) or root.is_relative_to(seed)
                or seed.is_relative_to(root)):
            raise StorageStop("POSIX roots must be separate descendants of the trusted workspace")
        if not base.is_dir() or not root.parent.is_dir() or not seed.is_dir():
            raise StorageStop("workspace, collection parent and seed root must already exist")
        for target in (base, root.parent, seed):
            current = target
            while True:
                _owned(current)
                if current == base:
                    break
                current = current.parent
        _owned(root, private=True)
        if root.exists() and not root.is_dir():
            raise StorageStop("collection root must be a dedicated directory")
        return root

    def validate_seed(self, value: Path) -> Path:
        self.validate()
        seed = Path(value)
        if self.mode == "windows":
            validate_windows_path(str(seed))
            _plain(seed)
            return seed
        seed = _posix_absolute(seed)
        if seed != Path(self.seed_root):
            raise StorageStop("pilot seed directory differs from the configured seed root")
        for base, dirs, files in os.walk(seed, followlinks=False, onerror=_scan_error):
            for name in dirs + files:
                _owned(Path(base) / name)
        return seed


class BoundedScratch(AbstractContextManager):
    """All collector writes must use this lease; external writers are unsupported.

    The dedicated root contains staging, retries, state, caches, logs and TEMP.
    A process-exit-released OS lock avoids time-based stale-lock stealing.
    """
    def __init__(self, *, paths: ScratchPaths | None = None,
                 max_bytes: int = HARD_MAX_BYTES,
                 min_free_bytes: int = 5_000_000_000,
                 free_bytes: Callable[[Path], int] | None = None):
        if not METADATA_RESERVE < max_bytes <= HARD_MAX_BYTES or min_free_bytes < 0:
            raise StorageStop("invalid byte budget or disk reserve")
        self.paths = paths or ScratchPaths(mode="windows")
        self.root = self.paths.validate()
        self.max_bytes = max_bytes
        self.min_free_bytes = min_free_bytes
        self.free_bytes = free_bytes or (lambda p: shutil.disk_usage(p).free)
        self._lock = None
        self._lease_pid = None

    def __enter__(self):
        if self._lock is not None:
            raise StorageStop("writer lease is already active")
        self.paths.validate()
        if self.paths.mode == "posix":
            self.root.mkdir(mode=0o700, exist_ok=True)
        else:
            self.root.mkdir(parents=True, exist_ok=True)
        self._check_path(self.root)
        lock_path = self.root / "writer.lock"
        self._check_path(lock_path)
        if self.paths.mode == "posix":
            flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW
            self._lock = os.fdopen(os.open(lock_path, flags, 0o600), "a+b")
        else:
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
        self._lease_pid = os.getpid()
        try:
            self.check_write(0)
            for name in ("temp", "cache", "logs", "staging", "state"):
                self._mkdir(self.path(name))
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *args):
        if self._lock is not None:
            if os.name == "nt" and not self._lock.closed:
                import msvcrt
                self._lock.seek(0)
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_UNLCK, 1)
            self._lock.close()
            self._lock = None
        self._lease_pid = None

    def _require_lease(self) -> None:
        if (self._lock is None or self._lock.closed
                or self._lease_pid != os.getpid()):
            raise StorageStop("a writer lease is required")

    def _check_path(self, target: Path) -> None:
        _plain(target)
        if self.paths.mode == "posix":
            self.paths.validate()
            current = target
            while current != self.root:
                _owned(current, private=True)
                current = current.parent
            _owned(self.root, private=True)

    def _mkdir(self, target: Path) -> None:
        self._require_lease()
        if self.paths.mode == "windows":
            target.mkdir(parents=True, exist_ok=True)
            return
        for node in (*reversed(target.relative_to(self.root).parents), target.relative_to(self.root)):
            p = self.root / node
            self._check_path(p)
            self._require_lease()
            p.mkdir(mode=0o700, exist_ok=True)
            self._check_path(p)

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
        self._check_path(target)
        if not target.resolve().is_relative_to(self.root.resolve()):
            raise StorageStop("scratch path escapes root")
        return target

    def _mutation_path(self, relative: str) -> Path:
        self._require_lease()
        target = self.path(relative)
        # Compare validated, normalized Paths, including native Windows aliases.
        # The lock and its temporary namespace may never be gateway payloads.
        for reserved in (self.root / "writer.lock", self.root / "writer.lock.writing"):
            if target == reserved or reserved in target.parents:
                raise StorageStop("writer lock namespace is reserved")
        if target == self.root:
            raise StorageStop("scratch root is not a mutation target")
        return target

    def usage(self) -> int:
        self._check_path(self.root)
        size = 0
        for base, dirs, files in os.walk(self.root, followlinks=False,
                                         onerror=_scan_error if self.paths.mode == "posix" else None):
            for name in dirs + files:
                p = Path(base) / name
                self._check_path(p)
                if p.is_file():
                    info = p.stat()
                    if info.st_nlink != 1:
                        raise StorageStop("scratch hard links are prohibited")
                    size += info.st_size
        return size

    def check_write(self, additional_bytes: int, *, metadata: bool = False) -> None:
        self._require_lease()
        if additional_bytes < 0:
            raise StorageStop("negative reservation")
        reserve = 0 if metadata else METADATA_RESERVE
        if self.usage() + additional_bytes + reserve > self.max_bytes:
            raise StorageStop("collection byte cap reached")
        if self.free_bytes(self.root) - additional_bytes < self.min_free_bytes:
            raise StorageStop("low disk reserve reached")
        self._require_lease()

    def atomic_json(self, relative: str, payload: dict) -> None:
        self._require_lease()
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(raw) > METADATA_RESERVE // 4:
            raise StorageStop("state/manifest exceeds bounded metadata size")
        self.atomic_bytes(relative, [raw], max_bytes=len(raw), metadata=True)

    def atomic_bytes(self, relative: str, chunks: Iterable[bytes], *,
                     max_bytes: int, metadata: bool = False) -> dict:
        self._require_lease()
        if not 0 <= max_bytes <= self.max_bytes:
            raise StorageStop("invalid stream limit")
        target = self._mutation_path(relative)
        normalized = target.relative_to(self.root).as_posix()
        temporary = self._mutation_path(normalized + ".writing")
        self._mkdir(target.parent)
        # An interrupted gateway write is ours; an input/source file is never removed.
        self._require_lease()
        temporary.unlink(missing_ok=True)
        self.check_write(max_bytes, metadata=metadata)
        sha = hashlib.sha256()
        md5 = hashlib.md5(usedforsecurity=False)
        written = 0
        try:
            self._require_lease()
            if self.paths.mode == "posix":
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                handle = os.fdopen(os.open(temporary, flags, 0o600), "wb")
            else:
                handle = temporary.open("xb")
            with handle:
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
                self._require_lease()
                os.fsync(handle.fileno())
            self._mutation_path(relative)  # Recheck lease/containment before replacement.
            os.replace(temporary, target)
        except BaseException:
            # A released lease cannot remove a partial now owned by another writer.
            self._require_lease()
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
