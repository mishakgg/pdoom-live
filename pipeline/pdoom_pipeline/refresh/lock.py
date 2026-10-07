"""Single-host lock so two refreshes cannot assemble the same collection."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class RefreshOverlap(RuntimeError):
    pass


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        return _windows_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _windows_alive(pid: int) -> bool:
    """Read process state without sending a console signal or terminating it.

    Access denied or an unexpected API error means unknown, so refuse overlap.
    This is deliberately not os.kill(pid, 0), which is unsafe on Windows.
    """
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only.
    if not handle:
        return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER: no PID.
    try:
        result = kernel.WaitForSingleObject(handle, 0)
        return result != 0  # WAIT_OBJECT_0 means exited; unknown stays locked.
    finally:
        kernel.CloseHandle(handle)


class RefreshLock:
    def __init__(self, path: Path, *, stale_after: float = 6 * 60 * 60):
        self.path = path
        self.stale_after = stale_after
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            self._reclaim_or_refuse()
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        self._held = True

    def release(self) -> None:
        if self._held and self.path.exists():
            self.path.unlink()
        self._held = False

    def __enter__(self) -> "RefreshLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    def _reclaim_or_refuse(self) -> None:
        try:
            existing = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RefreshOverlap("refresh lock is unreadable; explicit recovery is required") from exc
        try:
            pid = int(existing["pid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RefreshOverlap("refresh lock has no valid process identity; explicit recovery is required") from exc
        started = existing.get("started_at") or ""
        if _alive(pid):
            raise RefreshOverlap(
                f"refresh already running as pid {pid} since {started}. "
                "Wait for it to finish. If that process is gone, delete the lock file and run once again."
            )
        self.path.unlink()
